# -*- coding: utf-8 -*-
"""Ember — 월간 국가별 태양광 발전량·전력수요 (키 불필요).

Ember REST API(api.ember-energy.org)는 2026년 기준 API 키를 요구한다.
여기서는 Ember 가 공식적으로 공개 배포하는 월간 전체 CSV 를 사용한다.
잠금·유료 데이터를 우회하는 것이 아니라 공개 다운로드 경로다.

라이선스: CC BY-SA 4.0
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from core.config import RAW_DIR
from core.http import download_cached
from core.model import DataPoint

from .base import COUNTRIES, Adapter

CACHE_TTL = 3 * 24 * 3600      # 월간 데이터 — 3일 캐시면 충분 (70MB)
YEARS_BACK = 6

USE_COLS = ["Area", "ISO 3 code", "Date", "Category", "Subcategory", "Variable", "Unit", "Value"]

# (Category, Variable, Unit) → metric_id
WANTED = {
    ("Electricity generation", "Solar", "TWh"): "solar_generation_monthly_twh",
    ("Electricity demand", "Demand", "TWh"): "electricity_demand_monthly_twh",
}


class EmberAdapter(Adapter):
    name = "ember"

    def collect(self) -> list[DataPoint]:
        url = self.cfg.get("url")
        if not url:
            raise ValueError("sources.yaml 에 ember url 미정의")

        dest = RAW_DIR / "ember_monthly_full_release.csv"
        download_cached(url, dest, CACHE_TTL)

        wanted_iso = set(self.cfg.get("countries") or COUNTRIES.keys())
        cutoff = dt.date.today().replace(day=1) - dt.timedelta(days=365 * YEARS_BACK)

        frames: list[pd.DataFrame] = []
        checked_schema = False
        total_rows = 0

        # 70MB — 청크로 읽어 필요한 행만 남긴다
        for chunk in pd.read_csv(dest, chunksize=200_000, usecols=lambda c: c in USE_COLS,
                                 low_memory=False):
            if not checked_schema:
                self.expect_columns(list(chunk.columns), USE_COLS, "Ember CSV")
                checked_schema = True
            total_rows += len(chunk)

            m = chunk["ISO 3 code"].isin(wanted_iso)
            if not m.any():
                continue
            sub = chunk[m]

            keys = list(zip(sub["Category"], sub["Variable"], sub["Unit"]))
            sub = sub[[k in WANTED for k in keys]]
            if not sub.empty:
                frames.append(sub)

        self.expect_min_rows(total_rows, 100_000, "Ember CSV")
        if not frames:
            raise ValueError("Ember: 대상 국가/지표 행이 하나도 없음 (스키마 변경 의심)")

        df = pd.concat(frames, ignore_index=True)
        # 'ISO 3 code' 처럼 공백이 든 컬럼명은 itertuples 에서 위치기반(_1)으로 바뀐다.
        # 이름으로 안전하게 접근하려고 먼저 정규화한다.
        df = df.rename(columns={"ISO 3 code": "iso3"})
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"].notna() & (df["Date"].dt.date >= cutoff)]

        points: list[DataPoint] = []
        for row in df.itertuples(index=False):
            metric_id = WANTED.get((row.Category, row.Variable, row.Unit))
            if not metric_id or pd.isna(row.Value):
                continue
            d: dt.date = row.Date.date()
            # 월 데이터는 해당 월 말일을 기준일로 삼는다
            last_day = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
            points.append(self.point(
                metric_id=metric_id,
                value=float(row.Value),
                unit=str(row.Unit),
                period=f"{d.year:04d}-{d.month:02d}",
                as_of=last_day,
                entity=str(row.iso3),
                frequency="monthly",
                confidence=0.95,
                source_url="https://ember-energy.org/data/monthly-electricity-data/",
            ))

        if not points:
            raise ValueError("Ember: 기간 필터 후 남은 포인트 없음")
        return points
