# -*- coding: utf-8 -*-
"""FRED — 거시지표 (FRED_API_KEY 필요)."""
from __future__ import annotations

import datetime as dt

from core.config import get_key
from core.http import FetchError, fetch_json
from core.model import DataPoint

from .base import Adapter

ENDPOINT = "https://api.stlouisfed.org/fred/series/observations"
YEARS_BACK = 4
CACHE_TTL = 6 * 3600

# FRED 시리즈별 단위·주기 (sources.yaml 의 series 와 함께 사용)
SERIES_META = {
    "DEXKOUS": ("usd_krw", "KRW/USD", "daily", "KRW"),
    "DEXCHUS": ("usd_cny", "CNY/USD", "daily", "CNY"),
}


class FredAdapter(Adapter):
    name = "fred"

    def collect(self) -> list[DataPoint]:
        key = get_key("FRED_API_KEY")
        if not key:
            raise FetchError("FRED_API_KEY 미설정")

        start = (dt.date.today() - dt.timedelta(days=365 * YEARS_BACK)).isoformat()
        points: list[DataPoint] = []
        failed: list[str] = []

        for series_id, meta in (self.cfg.get("series") or {}).items():
            label = meta[0] if isinstance(meta, list) else str(meta)
            unit_cfg = meta[1] if isinstance(meta, list) and len(meta) > 1 else ""
            metric_id, unit, freq, currency = SERIES_META.get(
                series_id, (series_id.lower(), unit_cfg, self.freq, None))

            try:
                js = fetch_json(ENDPOINT, params={
                    "series_id": series_id, "api_key": key, "file_type": "json",
                    "observation_start": start,
                }, cache_ttl=CACHE_TTL)
            except Exception as e:
                failed.append(f"{series_id}({str(e)[:60]})")
                continue

            obs = js.get("observations") or []
            if not obs:
                failed.append(f"{series_id}(관측치 없음 — 시리즈 ID 확인 필요)")
                continue

            for o in obs:
                raw = o.get("value")
                if raw in (None, "", "."):     # FRED 결측 표기
                    continue
                try:
                    v = float(raw)
                    d = dt.date.fromisoformat(o["date"])
                except (ValueError, KeyError):
                    continue
                points.append(self.point(
                    metric_id=metric_id, value=v, unit=unit, currency=currency,
                    period=d.isoformat(), as_of=d, entity="USA" if metric_id != "usd_krw" else "KOR",
                    frequency=freq, confidence=0.98,
                    source_name=f"FRED · {label}",
                    source_url=f"https://fred.stlouisfed.org/series/{series_id}",
                ))

        if failed:
            self.warnings.append("시리즈 실패: " + ", ".join(failed))
        if not points:
            raise FetchError("FRED: 전 시리즈 실패 — " + "; ".join(failed))
        return points
