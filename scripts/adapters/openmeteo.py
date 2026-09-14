# -*- coding: utf-8 -*-
"""Open-Meteo — 국내 권역별 일사량 실측·예보 (키 불필요).

실측(past_days)과 예보(forecast_days)를 한 번에 받되, 예보분은 is_estimate=True
로 구분한다. 실제 발전량과 기상 기반 예상치를 섞지 않기 위해서다.
"""
from __future__ import annotations

import datetime as dt

from core.http import fetch_json
from core.model import DataPoint

from .base import KR_REGIONS, Adapter

ENDPOINT = "https://api.open-meteo.com/v1/forecast"
PAST_DAYS = 92        # API 최대치
FORECAST_DAYS = 7
CACHE_TTL = 3 * 3600


class OpenMeteoAdapter(Adapter):
    name = "openmeteo"

    def collect(self) -> list[DataPoint]:
        today = dt.date.today()
        points: list[DataPoint] = []
        failed: list[str] = []

        for rid, rname, lat, lon in KR_REGIONS:
            try:
                js = fetch_json(ENDPOINT, params={
                    "latitude": lat, "longitude": lon,
                    "daily": "shortwave_radiation_sum,sunshine_duration",
                    "timezone": "Asia/Seoul",
                    "past_days": PAST_DAYS,
                    "forecast_days": FORECAST_DAYS,
                }, cache_ttl=CACHE_TTL)
            except Exception as e:
                failed.append(f"{rname}({e})")
                continue

            daily = js.get("daily") or {}
            times = daily.get("time") or []
            if not times:
                failed.append(f"{rname}(daily.time 없음)")
                continue

            units = js.get("daily_units") or {}
            ghi_unit = units.get("shortwave_radiation_sum", "MJ/m²")
            # 모델 검증기가 다루기 쉽게 ASCII 로 정규화 (표시는 그대로)
            ghi_unit = ghi_unit.replace("m²", "m2")

            rad = daily.get("shortwave_radiation_sum") or []
            sun = daily.get("sunshine_duration") or []

            for i, tstr in enumerate(times):
                try:
                    d = dt.date.fromisoformat(tstr)
                except ValueError:
                    continue
                is_fc = d > today
                note = "forecast" if is_fc else ""

                if i < len(rad) and rad[i] is not None:
                    points.append(self.point(
                        metric_id="ghi_daily", value=float(rad[i]), unit=ghi_unit,
                        period=d.isoformat(), as_of=d, entity=rid,
                        frequency="daily", is_estimate=is_fc,
                        confidence=0.7 if is_fc else 0.95,
                        note=note, source_name="Open-Meteo",
                        source_url="https://open-meteo.com/en/docs",
                    ))

                if i < len(sun) and sun[i] is not None:
                    points.append(self.point(
                        metric_id="sunshine_hours", value=float(sun[i]) / 3600.0, unit="h",
                        period=d.isoformat(), as_of=d, entity=rid,
                        frequency="daily", is_estimate=is_fc,
                        confidence=0.7 if is_fc else 0.95,
                        note=note, source_name="Open-Meteo",
                        source_url="https://open-meteo.com/en/docs",
                    ))

        if failed:
            self.warnings.append("일부 권역 실패: " + ", ".join(failed))
        if not points:
            raise ValueError("Open-Meteo: 전 권역 수집 실패 — " + "; ".join(failed))
        return points
