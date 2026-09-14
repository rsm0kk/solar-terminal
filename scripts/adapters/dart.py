# -*- coding: utf-8 -*-
"""OpenDART — 공시 목록 + 분기 재무 (DART_API_KEY 필요).

누적 → 단독분기 변환이 이 어댑터의 핵심이자 가장 틀리기 쉬운 부분이다.

  - 손익계산서(IS/CIS): 누적값을 차분해 단독분기로 만든다.
      Q1 = 1Q누적
      Q2 = 반기누적 - 1Q누적
      Q3 = 3Q누적 - 반기누적
      Q4 = 연간(사업보고서) - 3Q누적
  - 재무상태표(BS): 분기말 잔액이므로 차분하지 않고 그대로 쓴다.

변환 결과는 quality.check_quarterly_conversion 으로 검증한다
(단독분기 4개 합 == 연간 누적).
"""
from __future__ import annotations

import datetime as dt
import io
import re
import zipfile
from typing import Optional

import xml.etree.ElementTree as ET

from core.config import CACHE_DIR, companies as load_companies, get_key
from core.http import FetchError, fetch, fetch_json
from core.model import DataPoint, QualityIssue
from core.quality import check_quarterly_conversion

from .base import Adapter

BASE = "https://opendart.fss.or.kr/api"
CORP_CODE_CACHE = CACHE_DIR / "CORPCODE.xml"
CORP_CODE_TTL = 30 * 24 * 3600

# 보고서 코드 → (분기순번, 라벨)
REPORTS = {
    "11013": (1, "1분기보고서"),
    "11012": (2, "반기보고서"),
    "11014": (3, "3분기보고서"),
    "11011": (4, "사업보고서"),
}

# 계정과목명은 회사마다 다르다. 우선순위 순으로 매칭한다.
ACCOUNT_PATTERNS = {
    "revenue_q": [
        "매출액", "수익(매출액)", "영업수익", "매출", "매출및지분법손익",
    ],
    "op_profit_q": [
        "영업이익", "영업이익(손실)", "영업손익", "영업이익(영업손실)",
    ],
    "net_profit_q": [
        "당기순이익", "당기순이익(손실)", "당기순손익", "당기순이익(당기순손실)",
        "분기순이익", "분기순이익(손실)", "분기순손익",
        "반기순이익", "반기순이익(손실)", "반기순손익",
        "연결당기순이익", "총당기순이익",
    ],
}

# 정확매칭이 실패했을 때만 쓰는 완화 매칭.
# 지배/비지배 지분 귀속 항목은 전체 순이익이 아니므로 반드시 제외한다.
RELAXED = {
    "net_profit_q": (
        re.compile(r"^(당기|분기|반기|연결)?순(이익|손익)"),
        re.compile(r"지배|비지배|주당|포괄"),
    ),
    "op_profit_q": (
        re.compile(r"^영업(이익|손익)"),
        re.compile(r"지배|비지배|주당"),
    ),
}
# 재무상태표 항목 (차분하지 않음)
BS_ACCOUNTS = {
    "total_assets": ["자산총계"],
    "total_liabilities": ["부채총계"],
    "cash_equiv": ["현금및현금성자산"],
    "short_borrowings": ["단기차입금"],
    "long_borrowings": ["장기차입금"],
}

WON_TO_BN = 1e9        # 원 → 십억원


def _norm(s: str) -> str:
    return re.sub(r"[\s ]+", "", s or "")


class DartAdapter(Adapter):
    name = "dart"

    def __init__(self, source_id: str, cfg: dict):
        super().__init__(source_id, cfg)
        self.key = get_key("DART_API_KEY")
        self.quality_issues: list[QualityIssue] = []
        self.filings: list[dict] = []

    # ------------------------------------------------------------------
    def collect(self) -> list[DataPoint]:
        if not self.key:
            raise FetchError("DART_API_KEY 미설정")

        corp_map = self._load_corp_codes()
        comps = load_companies().get("companies", [])

        points: list[DataPoint] = []
        for c in comps:
            corp_code = c.get("corp_code") or self._match_corp(corp_map, c)
            if not corp_code:
                self.warnings.append(f"{c['name']}: DART 고유번호 매칭 실패")
                continue
            try:
                points.extend(self._financials(c, corp_code))
            except Exception as e:
                self.warnings.append(f"{c['name']} 재무 실패: {str(e)[:100]}")
            try:
                self._collect_filings(c, corp_code)
            except Exception as e:
                self.warnings.append(f"{c['name']} 공시 실패: {str(e)[:100]}")

        if not points and not self.filings:
            raise FetchError("DART: 재무·공시 모두 수집 실패")
        return points

    # ------------------------------------------------------------------
    def _load_corp_codes(self) -> dict[str, str]:
        """고유번호 전체 목록. stock_code → corp_code 매핑을 만든다."""
        need_download = True
        if CORP_CODE_CACHE.exists():
            age = dt.datetime.now().timestamp() - CORP_CODE_CACHE.stat().st_mtime
            need_download = age > CORP_CODE_TTL

        if need_download:
            raw = fetch(f"{BASE}/corpCode.xml", params={"crtfc_key": self.key}, timeout=120)
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    inner = [n for n in zf.namelist() if n.upper().endswith(".XML")][0]
                    CORP_CODE_CACHE.write_bytes(zf.read(inner))
            except zipfile.BadZipFile:
                # 키 오류 등이면 XML 에러 메시지가 그대로 온다
                raise FetchError(f"corpCode 응답이 ZIP 이 아님: {raw[:200]!r}") from None

        root = ET.fromstring(CORP_CODE_CACHE.read_text(encoding="utf-8"))
        by_stock: dict[str, str] = {}
        self._by_name: dict[str, str] = {}
        for item in root.iter("list"):
            corp_code = (item.findtext("corp_code") or "").strip()
            stock_code = (item.findtext("stock_code") or "").strip()
            corp_name = _norm(item.findtext("corp_name") or "")
            if corp_code and stock_code:
                by_stock[stock_code] = corp_code
            if corp_code and corp_name:
                self._by_name.setdefault(corp_name, corp_code)
        return by_stock

    def _match_corp(self, by_stock: dict[str, str], company: dict) -> Optional[str]:
        code = str(company.get("stock_code") or "").zfill(6)
        if code in by_stock:
            return by_stock[code]
        return self._by_name.get(_norm(company.get("name", "")))

    # ------------------------------------------------------------------
    def _collect_filings(self, company: dict, corp_code: str) -> None:
        days = int(self.cfg.get("filing_days", 180))
        end = dt.date.today()
        start = end - dt.timedelta(days=days)
        js = fetch_json(f"{BASE}/list.json", params={
            "crtfc_key": self.key, "corp_code": corp_code,
            "bgn_de": start.strftime("%Y%m%d"), "end_de": end.strftime("%Y%m%d"),
            "page_count": 100,
        }, cache_ttl=3600)

        status = js.get("status")
        if status == "013":       # 조회된 데이터 없음
            return
        if status != "000":
            raise FetchError(f"list.json status={status} {js.get('message')}")

        for it in js.get("list", []):
            rcept_no = it.get("rcept_no", "")
            self.filings.append({
                "company_id": company["id"],
                "company": company["name"],
                "date": it.get("rcept_dt", ""),
                "title": (it.get("report_nm") or "").strip(),
                "filer": (it.get("flr_nm") or "").strip(),
                "rcept_no": rcept_no,
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                "kind": self._classify(it.get("report_nm") or ""),
            })

    @staticmethod
    def _classify(title: str) -> str:
        t = _norm(title)
        if any(k in t for k in ("단일판매", "공급계약")):
            return "공급계약"
        if any(k in t for k in ("유상증자", "전환사채", "신주인수권부사채", "교환사채")):
            return "자금조달"
        if "타법인주식" in t or "출자" in t:
            return "타법인출자"
        if any(k in t for k in ("사업보고서", "분기보고서", "반기보고서")):
            return "정기보고서"
        if "주식등의대량보유" in t or "임원ㆍ주요주주" in t or "임원·주요주주" in t:
            return "지분변동"
        if "유형자산" in t:
            return "설비투자"
        return "기타"

    # ------------------------------------------------------------------
    def _financials(self, company: dict, corp_code: str) -> list[DataPoint]:
        quarters_back = int(self.cfg.get("quarters_back", 12))
        this_year = dt.date.today().year
        years = list(range(this_year - (quarters_back // 4) - 1, this_year + 1))

        # (year, qnum) → {metric: 누적금액}
        cumulative: dict[tuple[int, int], dict[str, float]] = {}
        balance: dict[tuple[int, int], dict[str, float]] = {}

        for year in years:
            for reprt_code, (qnum, _label) in REPORTS.items():
                try:
                    rows = self._fetch_statement(corp_code, year, reprt_code)
                except FetchError:
                    continue
                if not rows:
                    continue
                cum, bal = self._extract(rows)
                if cum:
                    cumulative[(year, qnum)] = cum
                if bal:
                    balance[(year, qnum)] = bal

        if not cumulative and not balance:
            raise FetchError("재무 데이터 없음")

        points: list[DataPoint] = []
        points.extend(self._to_standalone(company, cumulative))
        points.extend(self._balance_points(company, balance))
        return points

    def _fetch_statement(self, corp_code: str, year: int, reprt_code: str) -> list[dict]:
        js = fetch_json(f"{BASE}/fnlttSinglAcntAll.json", params={
            "crtfc_key": self.key, "corp_code": corp_code,
            "bsns_year": year, "reprt_code": reprt_code,
            "fs_div": "CFS",     # 연결 우선
        }, cache_ttl=12 * 3600)

        if js.get("status") == "013":
            # 연결이 없으면 개별로 재시도
            js = fetch_json(f"{BASE}/fnlttSinglAcntAll.json", params={
                "crtfc_key": self.key, "corp_code": corp_code,
                "bsns_year": year, "reprt_code": reprt_code, "fs_div": "OFS",
            }, cache_ttl=12 * 3600)
        if js.get("status") != "000":
            return []
        return js.get("list", []) or []

    @staticmethod
    def _amount(row: dict, field: str) -> Optional[float]:
        raw = (row.get(field) or "").replace(",", "").strip()
        if raw in ("", "-"):
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def _extract(self, rows: list[dict]) -> tuple[dict[str, float], dict[str, float]]:
        """보고서 1건에서 누적 손익 + 기말 재무상태를 뽑는다."""
        cum: dict[str, float] = {}
        bal: dict[str, float] = {}
        is_rows: list[tuple[str, dict]] = []

        for row in rows:
            sj = (row.get("sj_div") or "").upper()
            nm = _norm(row.get("account_nm", ""))

            if sj in ("IS", "CIS"):
                is_rows.append((nm, row))
                for metric, patterns in ACCOUNT_PATTERNS.items():
                    if metric in cum:
                        continue
                    if nm in [_norm(p) for p in patterns]:
                        # 누적금액 우선. 없으면 당기금액(회사에 따라 누적을 여기 넣음)
                        v = self._amount(row, "thstrm_add_amount")
                        if v is None:
                            v = self._amount(row, "thstrm_amount")
                        if v is not None:
                            cum[metric] = v
            elif sj == "BS":
                for metric, patterns in BS_ACCOUNTS.items():
                    if metric in bal:
                        continue
                    if nm in [_norm(p) for p in patterns]:
                        v = self._amount(row, "thstrm_amount")
                        if v is not None:
                            bal[metric] = v

        # 정확매칭이 실패한 지표만 완화 매칭으로 한 번 더 시도한다.
        # (회사마다 '분기순이익(손실)' 등 표기가 제각각이라 놓치는 분기가 생긴다)
        for metric, (want, avoid) in RELAXED.items():
            if metric in cum:
                continue
            for nm, row in is_rows:
                if want.match(nm) and not avoid.search(nm):
                    v = self._amount(row, "thstrm_add_amount")
                    if v is None:
                        v = self._amount(row, "thstrm_amount")
                    if v is not None:
                        cum[metric] = v
                        break
        return cum, bal

    # ------------------------------------------------------------------
    def _to_standalone(
        self, company: dict, cumulative: dict[tuple[int, int], dict[str, float]]
    ) -> list[DataPoint]:
        """누적 손익을 단독분기로 차분한다."""
        points: list[DataPoint] = []
        metrics = set()
        for d in cumulative.values():
            metrics.update(d)

        for metric in metrics:
            standalone: dict[str, float] = {}
            annual_cum: dict[str, float] = {}

            years = sorted({y for (y, _q) in cumulative})
            for year in years:
                prev_cum = 0.0
                for q in (1, 2, 3, 4):
                    cur = cumulative.get((year, q), {}).get(metric)
                    if cur is None:
                        # 이 분기 보고서가 없으면 다음 분기의 차분 기준이 깨진다.
                        # 잘못된 값을 만들지 않도록 해당 분기는 건너뛰고 기준도 리셋한다.
                        prev_cum = None
                        continue
                    if prev_cum is None:
                        prev_cum = cur
                        continue
                    val = cur - prev_cum
                    standalone[f"{year}Q{q}"] = val
                    prev_cum = cur
                    if q == 4:
                        annual_cum[f"{year}Q4"] = cur

            # 변환 검증: 단독분기 4개 합 == 연간 누적
            self.quality_issues.extend(
                check_quarterly_conversion(annual_cum, standalone,
                                           label=f"{company['id']}.{metric}")
            )

            for period, val in standalone.items():
                year, qn = int(period[:4]), int(period[-1])
                as_of = dt.date(year, qn * 3, 1)
                as_of = (as_of.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
                points.append(self.point(
                    metric_id=metric, value=round(val / WON_TO_BN, 3), unit="십억원",
                    currency="KRW", period=period, as_of=as_of, entity=company["id"],
                    frequency="quarterly", confidence=0.95,
                    source_name="OpenDART", source_url="https://opendart.fss.or.kr",
                    note="누적 손익계산서를 직전분기 차감으로 단독분기 환산",
                ))
        return points

    def _balance_points(
        self, company: dict, balance: dict[tuple[int, int], dict[str, float]]
    ) -> list[DataPoint]:
        """재무상태표는 분기말 잔액 그대로. 순차입금만 파생 계산."""
        points: list[DataPoint] = []
        for (year, q), vals in sorted(balance.items()):
            as_of = dt.date(year, q * 3, 1)
            as_of = (as_of.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
            period = f"{year}Q{q}"

            borrowings = vals.get("short_borrowings", 0.0) + vals.get("long_borrowings", 0.0)
            cash = vals.get("cash_equiv")
            if borrowings and cash is not None:
                points.append(self.point(
                    metric_id="net_debt",
                    value=round((borrowings - cash) / WON_TO_BN, 3),
                    unit="십억원", currency="KRW", period=period, as_of=as_of,
                    entity=company["id"], frequency="quarterly", confidence=0.85,
                    source_name="OpenDART", source_url="https://opendart.fss.or.kr",
                    note="단기차입금+장기차입금-현금성자산. 리스부채·사채 미포함이라 실제 순차입금과 다를 수 있음",
                ))
        return points
