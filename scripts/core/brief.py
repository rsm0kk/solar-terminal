# -*- coding: utf-8 -*-
"""아침 브리핑 생성기 (규칙 기반, LLM 호출 없음).

문장에는 반드시 숫자와 비교 기준을 넣는다. 데이터가 없으면 추측하지 않고
'데이터 없음'과 그 이유를 적는다.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from .config import companies as load_companies, metrics as load_metrics
from .signals import _pct_change, _series_points
from .store import Store


def _fmt(v: float, unit: str = "") -> str:
    if v is None:
        return "-"
    av = abs(v)
    if av >= 1000:
        s = f"{v:,.0f}"
    elif av >= 100:
        s = f"{v:,.1f}"
    elif av >= 1:
        s = f"{v:,.2f}"
    else:
        s = f"{v:,.4f}".rstrip("0").rstrip(".")
    return f"{s}{unit}" if unit else s


def _arrow(pct: float) -> str:
    if pct > 0.05:
        return "상승"
    if pct < -0.05:
        return "하락"
    return "보합"


class BriefBuilder:
    def __init__(self, store: Store, signal_result: dict, statuses: list):
        self.store = store
        self.sig = signal_result
        self.statuses = statuses
        self.metrics = (load_metrics() or {}).get("metrics", {})
        self.companies = {c["id"]: c for c in load_companies().get("companies", [])}
        self.today = dt.date.today()

    # ------------------------------------------------------------------
    def _line(self, metric_id: str, name: str, entity: Optional[str] = None,
              window: str = "wow") -> dict:
        """지표 한 줄. 데이터가 없으면 사유를 담아 반환한다."""
        mcfg = self.metrics.get(metric_id, {})
        unit = mcfg.get("unit", "")
        pts = _series_points(self.store, metric_id, entity)
        if not pts:
            return {"metric_id": metric_id, "name": name, "ok": False,
                    "text": f"{name}: 데이터 없음 (수집되지 않음)"}

        chg = _pct_change(pts, self.today, window)
        last_date, last_val = pts[-1]
        age = (self.today - last_date).days

        if chg is None or chg.get("prev") is None:
            return {"metric_id": metric_id, "name": name, "ok": True, "pct": None,
                    "value": last_val, "unit": unit, "as_of": last_date.isoformat(),
                    "text": f"{name} {_fmt(last_val, unit)} ({last_date.isoformat()} 기준, 비교 시점 데이터 부족)"}

        wl = {"wow": "전주", "mom": "전월", "yoy": "전년동기", "dod": "전일", "qoq": "전분기"}.get(window, window)
        return {
            "metric_id": metric_id, "name": name, "ok": True,
            "pct": round(chg["pct"], 2), "value": chg["current"], "unit": unit,
            "as_of": chg["as_of"].isoformat(), "age_days": age,
            "text": (f"{name} {_fmt(chg['current'], unit)}, {wl} 대비 {chg['pct']:+.1f}% "
                     f"{_arrow(chg['pct'])} ({chg['as_of'].isoformat()} 기준)"),
        }

    # ------------------------------------------------------------------
    def build(self, filings: list[dict], ppa_deals: list[dict]) -> dict[str, Any]:
        supply = self._supply()
        global_demand = self._global(ppa_deals)
        korea = self._korea()
        companies = self._companies()
        events = self._events(filings)
        headline = self._headline(supply, global_demand, korea, companies)

        return {
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "as_of": self.today.isoformat(),
            "headline": headline,
            "supply_chain": supply,
            "global_demand": global_demand,
            "korea": korea,
            "companies": companies,
            "events": events,
            "disclaimer": (
                "규칙 기반 자동 생성입니다. 시그널 점수는 방향성 참고치이며 "
                "실적 확정치나 투자 권유가 아닙니다."
            ),
        }

    # ------------------------------------------------------------------
    def _supply(self) -> dict:
        return {
            "폴리실리콘": [
                self._line("poly_price_china_dense", "중국 N-type dense"),
                self._line("poly_price_nonchina", "비중국산"),
                self._line("nonchina_poly_premium", "비중국산 프리미엄"),
            ],
            "웨이퍼": [
                self._line("wafer_price_m10", "N-type M10"),
                self._line("wafer_price_g12", "N-type G12"),
            ],
            "셀": [
                self._line("cell_price_topcon_m10", "M10 TOPCon"),
                self._line("cell_price_topcon_g12", "G12 TOPCon"),
            ],
            "모듈": [
                self._line("module_price_china_fob", "중국 FOB"),
                self._line("module_price_us_ddp", "미국 DDP"),
                self._line("cell_module_spread", "셀→모듈 스프레드"),
            ],
        }

    def _global(self, ppa_deals: list[dict]) -> dict:
        out = {
            "미국": [
                self._line("us_solar_generation_gwh", "미국 태양광 발전량", "USA", "yoy"),
                self._line("solar_generation_monthly_twh", "미국 월간 태양광", "USA", "yoy"),
            ],
            "중국": [self._line("solar_generation_monthly_twh", "중국 월간 태양광", "CHN", "yoy")],
            "유럽·인도": [
                self._line("solar_generation_monthly_twh", "독일 월간 태양광", "DEU", "yoy"),
                self._line("solar_generation_monthly_twh", "인도 월간 태양광", "IND", "yoy"),
            ],
        }
        # 데이터센터 PPA — 확정 계약만 집계
        confirmed = [d for d in ppa_deals
                     if str(d.get("official", "0")).strip() == "1"
                     and str(d.get("datacenter_linked", "0")).strip() == "1"]
        if confirmed:
            recent = sorted(confirmed, key=lambda d: str(d.get("announced_date", "")), reverse=True)[:3]
            total_mw = 0.0
            for d in confirmed:
                try:
                    total_mw += float(d.get("solar_mw") or 0)
                except (TypeError, ValueError):
                    pass
            items = [{"ok": True, "text": f"확정 데이터센터 연계 태양광 PPA 누적 {total_mw:,.0f}MW ({len(confirmed)}건)"}]
            for d in recent:
                items.append({"ok": True, "text": (
                    f"{d.get('announced_date','')} {d.get('buyer','')} "
                    f"{d.get('solar_mw','')}MW ({d.get('country','')})")})
            out["데이터센터 PPA"] = items
        else:
            out["데이터센터 PPA"] = [{"ok": False, "text": (
                "확정 계약 데이터 없음 — data/manual/ppa_deals_manual.csv 에 "
                "official=1 인 계약을 입력하면 집계됩니다")}]
        return out

    def _korea(self) -> dict:
        return {
            "발전량": [
                self._line("kr_solar_generation", "국내 태양광 발전량", "KOR", "yoy"),
                self._line("ghi_normal_dev_pct", "일사량 평년대비(전남)", "jeonnam", "level"),
            ],
            "SMP": [self._line("smp_land", "육지 SMP", "KOR"),
                    self._line("smp_jeju", "제주 SMP", "KOR")],
            "REC": [self._line("rec_spot_price", "REC 현물가", "KOR"),
                    self._line("rec_spot_volume", "REC 거래량", "KOR")],
            "PPA": [self._line("smp_rec_revenue", "SMP+REC 환산수익", "KOR")],
        }

    def _companies(self) -> dict:
        out: dict[str, Any] = {}
        for cid, comp in self.companies.items():
            sc = (self.sig.get("companies") or {}).get(cid, {})
            price = self._line("close_price", "주가", cid, "wow")
            drivers = sc.get("top_drivers") or []

            lines = [price["text"]]
            if sc:
                lines.append(
                    f"시그널 {sc.get('total', 0):+.2f}점 ({sc.get('verdict', '판단보류')}), "
                    f"전주 대비 {sc.get('delta', 0):+.2f} · "
                    f"사용 지표 {sc.get('signals_used', 0)}개 · 신뢰도 {sc.get('confidence', 0):.0%}"
                )
            for d in drivers:
                lines.append(f"  · {d['label']} {d['pct']:+.1f}% → {d['score']:+d}점 (가중 {d['weight']})")
            if sc.get("excluded"):
                names = ", ".join(e["label"] for e in sc["excluded"][:4])
                lines.append(f"  · 제외된 지표: {names}")

            out[comp["name"]] = {
                "company_id": cid,
                "verdict": sc.get("verdict", "판단보류"),
                "score": sc.get("total"),
                "delta": sc.get("delta"),
                "confidence": sc.get("confidence"),
                "lines": lines,
                "thesis": comp.get("thesis", ""),
            }
        return out

    def _events(self, filings: list[dict]) -> dict:
        recent_cut = (self.today - dt.timedelta(days=7)).strftime("%Y%m%d")
        recent = [f for f in filings if str(f.get("date", "")) >= recent_cut]
        recent.sort(key=lambda f: str(f.get("date", "")), reverse=True)

        by_kind: dict[str, list] = {}
        for f in recent:
            by_kind.setdefault(f.get("kind", "기타"), []).append(f)

        out: dict[str, Any] = {}
        important = [k for k in ("공급계약", "자금조달", "설비투자", "타법인출자", "정기보고서")
                     if k in by_kind]
        out["공시"] = [
            {"ok": True, "text": f"{f['date']} {f['company']} [{f['kind']}] {f['title'][:60]}",
             "url": f.get("url", "")}
            for k in important for f in by_kind[k][:3]
        ] or [{"ok": True, "text": f"최근 7일 주요 공시 없음 (전체 {len(recent)}건)"}]

        # 실적 발표 예상 시점 (분기 종료 후 약 45일)
        earnings = []
        for cid, comp in self.companies.items():
            latest = self.store.latest("revenue_q", cid)
            if not latest:
                continue
            earnings.append({"ok": True, "text": (
                f"{comp['name']} 최근 반영 분기 {latest['period']} "
                f"(매출 {_fmt(float(latest['value']))}십억원)")})
        out["실적"] = earnings or [{"ok": False, "text": "분기 실적 데이터 없음"}]

        stale = [s for s in self.statuses if getattr(s, "state", "") in ("stale", "error", "no_key")]
        out["데이터 점검"] = [
            {"ok": False, "text": f"{s.label}: {s.state} — {s.message[:90]}"} for s in stale[:6]
        ] or [{"ok": True, "text": "모든 소스 정상"}]
        return out

    # ------------------------------------------------------------------
    def _headline(self, supply: dict, global_demand: dict, korea: dict, companies: dict) -> list[str]:
        """오늘 가장 중요한 변화 3개 — 변화율 절대값이 큰 순으로 고른다."""
        cands: list[tuple[float, str]] = []

        for group in (supply, korea):
            for _section, lines in group.items():
                for ln in lines:
                    if ln.get("ok") and ln.get("pct") is not None:
                        cands.append((abs(ln["pct"]), ln["text"]))
        for _section, lines in global_demand.items():
            for ln in lines:
                if isinstance(ln, dict) and ln.get("ok") and ln.get("pct") is not None:
                    cands.append((abs(ln["pct"]), ln["text"]))

        cands.sort(key=lambda x: x[0], reverse=True)
        head = [t for _p, t in cands[:3]]

        # 시그널 변화가 큰 기업도 헤드라인 후보
        moves = sorted(
            ((abs(c.get("delta") or 0), name, c) for name, c in companies.items()),
            key=lambda x: x[0], reverse=True)
        if moves and moves[0][0] >= 0.5:
            _d, name, c = moves[0]
            head.append(f"{name} 시그널 {c['score']:+.2f}점 ({c['verdict']}), 전주 대비 {c['delta']:+.2f}")

        if not head:
            head = ["오늘 판단 가능한 변화 없음 — 공급망 가격·SMP/REC 데이터가 아직 채워지지 않았습니다."]
        return head[:3]
