# -*- coding: utf-8 -*-
"""EIA — 미국 태양광 발전량·전력수요 (EIA_API_KEY 필요).

2026-08-16 실키로 검증한 결과:
  · electric-power-operational-data + sectorid=99(All Sectors) → 정상.
    단위는 "thousand megawatthours" = GWh 다.
  · **응답이 매우 느리다 (70~85초).** 기본 타임아웃 45초로는 무조건 실패하므로
    이 어댑터만 타임아웃을 크게 잡는다.
  · operating-generator-capacity route 는 기간을 1개월로 좁혀도 504 를 돌려준다
    (EIA 쪽 문제). 설비용량 대신 소매판매(전력수요)를 받는다.

한 항목이 실패해도 나머지는 수집한다.
"""
from __future__ import annotations

import datetime as dt

from core.config import get_key
from core.http import FetchError, fetch_json
from core.model import DataPoint

from .base import Adapter

BASE = "https://api.eia.gov/v2"
YEARS_BACK = 5
CACHE_TTL = 12 * 3600
# EIA v2 는 응답이 느리다 (실측 70~85초). 재시도는 1회만 — 504 가 나는 route 를
# 3번 재시도하면 5분을 그냥 버린다.
EIA_TIMEOUT = 200
EIA_RETRIES = 1


class EiaAdapter(Adapter):
    name = "eia"

    def collect(self) -> list[DataPoint]:
        key = get_key("EIA_API_KEY")
        if not key:
            raise FetchError("EIA_API_KEY 미설정 — https://www.eia.gov/opendata/register.php")

        start = (dt.date.today() - dt.timedelta(days=365 * YEARS_BACK)).strftime("%Y-%m")
        points: list[DataPoint] = []
        failed: list[str] = []

        for fn, label in ((self._generation, "태양광 발전량"), (self._demand, "전력 소매판매")):
            try:
                points.extend(fn(key, start))
            except Exception as e:
                failed.append(f"{label}({str(e)[:80]})")

        if failed:
            self.warnings.append("EIA 일부 실패: " + "; ".join(failed))
        if not points:
            raise FetchError("EIA: 전 항목 실패 — " + "; ".join(failed))
        return points

    # ------------------------------------------------------------------
    def _generation(self, key: str, start: str) -> list[DataPoint]:
        """미국 전체 태양광 월간 발전량.

        단위 "thousand megawatthours" = 1,000 MWh = 1 GWh 이므로 값을 그대로 GWh 로 쓴다.
        sectorid=99 는 'All Sectors' 로 실응답에서 확인했다.
        """
        js = fetch_json(f"{BASE}/electricity/electric-power-operational-data/data/", params={
            "api_key": key, "frequency": "monthly",
            "data[0]": "generation",
            "facets[fueltypeid][]": "SUN",
            "facets[location][]": "US",
            "facets[sectorid][]": "99",       # 전 부문 합계 (All Sectors)
            "start": start, "length": 500, "sort[0][column]": "period", "sort[0][direction]": "desc",
        }, cache_ttl=CACHE_TTL, timeout=EIA_TIMEOUT, retries=EIA_RETRIES)

        rows = ((js.get("response") or {}).get("data")) or []
        if not rows:
            raise ValueError("응답에 data 없음 (route·facet 확인 필요)")

        # 단위가 바뀌면 조용히 1000배 틀린 값이 들어간다 — 확인하고 넘어간다
        unit = str(rows[0].get("generation-units", ""))
        if unit and "thousand megawatthours" not in unit.lower():
            self.warnings.append(f"발전량 단위가 예상과 다름: {unit!r} (GWh 환산 재확인 필요)")

        out: list[DataPoint] = []
        for r in rows:
            v = r.get("generation")
            period = r.get("period")
            if v in (None, "") or not period:
                continue
            try:
                # EIA 단위는 thousand megawatthours = GWh
                val = float(v)
                y, m = int(period[:4]), int(period[5:7])
            except (ValueError, TypeError):
                continue
            last = (dt.date(y, m, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
            out.append(self.point(
                metric_id="us_solar_generation_gwh", value=val, unit="GWh",
                period=f"{y:04d}-{m:02d}", as_of=last, entity="USA",
                frequency="monthly", confidence=0.98,
                source_name="EIA Electric Power Operational Data",
                source_url="https://www.eia.gov/opendata/browser/electricity",
                note=("EIA-923 유틸리티 규모(1MW 이상)만 집계. 지붕형 분산전원 제외 — "
                      "분산 포함인 Ember 대비 약 25% 낮다"),
            ))
        return out

    # ------------------------------------------------------------------
    def _demand(self, key: str, start: str) -> list[DataPoint]:
        """미국 전력 소매판매 = 전력수요 대리지표 (백만 MWh).

        원래 여기서 태양광 설비용량(operating-generator-capacity)을 받으려 했으나
        그 route 는 기간을 1개월로 좁혀도 EIA 가 504 를 돌려준다(2026-08-16 확인).
        설비용량은 OWID 연간 시계열로 대체하고, 여기서는 수요를 받는다.
        전력수요는 태양광·전력기기 양쪽 수요의 1차 동인이다.
        """
        js = fetch_json(f"{BASE}/electricity/retail-sales/data/", params={
            "api_key": key, "frequency": "monthly",
            "data[0]": "sales",
            "facets[stateid][]": "US",
            "facets[sectorid][]": "ALL",
            "start": start, "length": 500,
            "sort[0][column]": "period", "sort[0][direction]": "desc",
        }, cache_ttl=CACHE_TTL, timeout=EIA_TIMEOUT, retries=EIA_RETRIES)

        rows = ((js.get("response") or {}).get("data")) or []
        if not rows:
            raise ValueError("응답에 data 없음")

        out: list[DataPoint] = []
        for r in rows:
            v = r.get("sales")
            period = r.get("period")
            if v in (None, "") or not period:
                continue
            try:
                val = float(v)
                y, m = int(period[:4]), int(period[5:7])
            except (ValueError, TypeError):
                continue
            last = (dt.date(y, m, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
            out.append(self.point(
                metric_id="us_electricity_sales", value=val,
                unit=str(r.get("sales-units") or "million kWh"),
                period=f"{y:04d}-{m:02d}", as_of=last, entity="USA",
                frequency="monthly", confidence=0.98,
                source_name="EIA Retail Sales",
                source_url="https://www.eia.gov/opendata/browser/electricity/retail-sales",
            ))
        return out
