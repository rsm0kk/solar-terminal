# -*- coding: utf-8 -*-
"""네이버 금융 — 국내 4사 일별 시세 (키 불필요).

KRX Open API 는 별도 키가 필요하고(401), 한국투자증권 KIS 는 계좌·앱키가 필요하다.
주가는 공개 시세 조회로 충분히 커버되므로 여기서 받는다.
1일 1회만 호출한다 (대량·고빈도 조회 금지).
"""
from __future__ import annotations

import ast
import datetime as dt

from core.config import companies as load_companies
from core.http import fetch_text
from core.model import DataPoint

from .base import Adapter

ENDPOINT = "https://api.finance.naver.com/siseJson.naver"
DAYS_BACK = 400          # 52주 고점·연초대비 계산에 필요
CACHE_TTL = 6 * 3600

EXPECTED_HEADER = ["날짜", "시가", "고가", "저가", "종가", "거래량", "외국인소진율"]


class NaverStockAdapter(Adapter):
    name = "naver_stock"

    def collect(self) -> list[DataPoint]:
        cfg = load_companies()
        targets = [
            (c["id"], c["name"], str(c["stock_code"]).zfill(6))
            for c in cfg.get("companies", [])
            if c.get("stock_code")
        ]

        end = dt.date.today()
        start = end - dt.timedelta(days=DAYS_BACK)
        points: list[DataPoint] = []
        failed: list[str] = []

        for cid, cname, code in targets:
            try:
                rows = self._fetch_symbol(code, start, end)
            except Exception as e:
                failed.append(f"{cname}({str(e)[:60]})")
                continue

            for r in rows:
                d, o, h, l, c, vol, fr = r
                points.append(self.point(
                    metric_id="close_price", value=float(c), unit="원", currency="KRW",
                    period=d.isoformat(), as_of=d, entity=cid,
                    frequency="business_daily", confidence=0.95,
                    source_name="네이버 금융", source_url=f"https://finance.naver.com/item/main.naver?code={code}",
                ))
                points.append(self.point(
                    metric_id="trade_volume", value=float(vol), unit="주",
                    period=d.isoformat(), as_of=d, entity=cid,
                    frequency="business_daily", confidence=0.95,
                    source_name="네이버 금융",
                ))
                if fr is not None:
                    points.append(self.point(
                        metric_id="foreign_ratio", value=float(fr), unit="%",
                        period=d.isoformat(), as_of=d, entity=cid,
                        frequency="business_daily", confidence=0.9,
                        source_name="네이버 금융",
                    ))

        if failed:
            self.warnings.append("일부 종목 실패: " + ", ".join(failed))
        if not points:
            raise ValueError("네이버 금융: 전 종목 수집 실패 — " + "; ".join(failed))
        return points

    # ------------------------------------------------------------------
    def _fetch_symbol(self, code: str, start: dt.date, end: dt.date) -> list[tuple]:
        text = fetch_text(ENDPOINT, params={
            "symbol": code, "requestType": 1,
            "startTime": start.strftime("%Y%m%d"),
            "endTime": end.strftime("%Y%m%d"),
            "timeframe": "day",
        }, cache_ttl=CACHE_TTL)

        # 응답이 JSON 이 아니라 파이썬/JS 리터럴 형태다. 공백·개행을 정리해 파싱한다.
        cleaned = text.strip().replace("\n", "").replace("\t", "").replace("\r", "")
        if not cleaned.startswith("["):
            raise ValueError(f"예상치 못한 응답 형식: {cleaned[:80]!r}")
        try:
            data = ast.literal_eval(cleaned)
        except (ValueError, SyntaxError) as e:
            raise ValueError(f"시세 파싱 실패: {e}") from None

        if not isinstance(data, list) or len(data) < 2:
            raise ValueError("시세 행이 없음")

        header = [str(x).strip() for x in data[0]]
        self.expect_columns(header, EXPECTED_HEADER[:6], f"네이버 시세/{code}")

        idx = {name: header.index(name) for name in header}
        out: list[tuple] = []
        for row in data[1:]:
            try:
                d = dt.datetime.strptime(str(row[idx["날짜"]]), "%Y%m%d").date()
                o = row[idx["시가"]]; h = row[idx["고가"]]
                l = row[idx["저가"]]; c = row[idx["종가"]]
                vol = row[idx["거래량"]]
                fr = row[idx["외국인소진율"]] if "외국인소진율" in idx else None
            except (KeyError, IndexError, ValueError):
                continue
            if c in (None, 0):
                continue      # 휴장·결측을 0 으로 저장하지 않는다
            out.append((d, o, h, l, c, vol, fr))

        self.expect_min_rows(len(out), 20, f"네이버 시세/{code}")
        return out
