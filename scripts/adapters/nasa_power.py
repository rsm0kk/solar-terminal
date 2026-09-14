# -*- coding: utf-8 -*-
"""NASA POWER — 일사량 장기평년 + 독립 실측 (키 불필요, public domain).

두 가지 역할:
  1. 월별 장기평년(climatology)을 받아 '평년 대비' 계산의 기준선을 만든다.
  2. 같은 GHI 를 Open-Meteo 와 독립적으로 실측해 출처 간 교차검증을 가능하게 한다.
     (단위를 kWh/m2/day → MJ/m2 로 환산해 같은 축에서 비교 가능하게 맞춘다)
"""
from __future__ import annotations

import datetime as dt
import json

from core.config import PROCESSED_DIR
from core.http import fetch_json
from core.model import DataPoint

from .base import KR_REGIONS, Adapter

CLIMATOLOGY_EP = "https://power.larc.nasa.gov/api/temporal/climatology/point"
DAILY_EP = "https://power.larc.nasa.gov/api/temporal/daily/point"

FILL = -999.0
KWH_TO_MJ = 3.6          # 1 kWh/m2 = 3.6 MJ/m2
LAG_DAYS = 10            # POWER 는 수일~열흘 지연 발행
WINDOW_DAYS = 120
CACHE_TTL = 12 * 3600

NORMALS_FILE = PROCESSED_DIR / "ghi_normals.json"
MONTH_KEYS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


class NasaPowerAdapter(Adapter):
    name = "nasa_power"

    def collect(self) -> list[DataPoint]:
        normals = self._collect_normals()
        if normals:
            NORMALS_FILE.write_text(
                json.dumps(normals, ensure_ascii=False, indent=2), encoding="utf-8")

        points = self._collect_daily()
        if not points and not normals:
            raise ValueError("NASA POWER: 평년·실측 모두 수집 실패")
        return points

    # ------------------------------------------------------------------
    def _collect_normals(self) -> dict:
        """권역별 월간 장기평년 GHI (MJ/m2/day)."""
        out: dict[str, dict] = {}
        for rid, rname, lat, lon in KR_REGIONS:
            try:
                js = fetch_json(CLIMATOLOGY_EP, params={
                    "parameters": "ALLSKY_SFC_SW_DWN", "community": "RE",
                    "longitude": lon, "latitude": lat, "format": "JSON",
                }, cache_ttl=30 * 24 * 3600)   # 평년값은 거의 안 바뀐다
                param = ((js.get("properties") or {}).get("parameter") or {})
                monthly = param.get("ALLSKY_SFC_SW_DWN") or {}
                vals = {}
                for i, mk in enumerate(MONTH_KEYS, start=1):
                    v = monthly.get(mk)
                    if v is None or v == FILL:
                        continue
                    vals[f"{i:02d}"] = round(float(v) * KWH_TO_MJ, 3)
                if vals:
                    out[rid] = {"region": rname, "unit": "MJ/m2", "monthly": vals}
            except Exception as e:
                self.warnings.append(f"평년값 실패 {rname}: {str(e)[:80]}")
        return out

    # ------------------------------------------------------------------
    def _collect_daily(self) -> list[DataPoint]:
        end = dt.date.today() - dt.timedelta(days=LAG_DAYS)
        start = end - dt.timedelta(days=WINDOW_DAYS)
        points: list[DataPoint] = []

        for rid, rname, lat, lon in KR_REGIONS:
            try:
                js = fetch_json(DAILY_EP, params={
                    "parameters": "ALLSKY_SFC_SW_DWN", "community": "RE",
                    "longitude": lon, "latitude": lat,
                    "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
                    "format": "JSON",
                }, cache_ttl=CACHE_TTL)
            except Exception as e:
                self.warnings.append(f"실측 실패 {rname}: {str(e)[:80]}")
                continue

            param = ((js.get("properties") or {}).get("parameter") or {})
            series = param.get("ALLSKY_SFC_SW_DWN") or {}
            if not series:
                self.warnings.append(f"실측 비어있음 {rname}")
                continue

            for datestr, v in series.items():
                if v is None or v == FILL:
                    continue          # 결측을 0 으로 채우지 않는다
                try:
                    d = dt.datetime.strptime(datestr, "%Y%m%d").date()
                except ValueError:
                    continue
                points.append(self.point(
                    metric_id="ghi_daily",
                    value=round(float(v) * KWH_TO_MJ, 3),
                    unit="MJ/m2",
                    period=d.isoformat(), as_of=d, entity=rid,
                    frequency="daily", confidence=0.9,
                    source_name="NASA POWER",
                    source_url="https://power.larc.nasa.gov",
                    note="kWh/m2/day 를 MJ/m2 로 환산 (x3.6)",
                ))
        return points
