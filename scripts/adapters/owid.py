# -*- coding: utf-8 -*-
"""Our World in Data — 국가별 태양광 발전량·비중·설비용량 (연간, 키 불필요).

라이선스: CC BY 4.0. grapher CSV 공개 배포 경로를 그대로 사용한다.
"""
from __future__ import annotations

import datetime as dt
import io

import pandas as pd

from core.http import fetch_text
from core.model import DataPoint

from .base import COUNTRIES, OWID_NAMES, Adapter

BASE = "https://ourworldindata.org/grapher/{slug}.csv"
CACHE_TTL = 12 * 3600  # 연간 데이터라 하루 한 번이면 충분


class OwidAdapter(Adapter):
    name = "owid"

    def collect(self) -> list[DataPoint]:
        datasets: dict[str, str] = self.cfg.get("datasets", {})
        if not datasets:
            raise ValueError("sources.yaml 에 owid datasets 미정의")

        points: list[DataPoint] = []
        for metric_id, slug in datasets.items():
            points.extend(self._collect_one(metric_id, slug))
        return points

    # ------------------------------------------------------------------
    def _collect_one(self, metric_id: str, slug: str) -> list[DataPoint]:
        url = BASE.format(slug=slug)
        # csvType=full 이라야 전체 연도 시계열이 온다 (filtered 는 그래프 기본선택만)
        text = fetch_text(url, params={"csvType": "full", "useColumnShortNames": "true"},
                          cache_ttl=CACHE_TTL, timeout=90)
        df = pd.read_csv(io.StringIO(text))

        self.expect_columns(list(df.columns), ["entity", "year"], f"OWID/{slug}")
        self.expect_min_rows(len(df), 100, f"OWID/{slug}")

        meta_cols = {"entity", "code", "year"}
        value_cols = [
            c for c in df.columns
            if c not in meta_cols and not c.endswith("__original_year")
        ]
        if not value_cols:
            raise ValueError(f"OWID/{slug}: 값 컬럼을 찾지 못함. 컬럼={list(df.columns)}")
        vcol = value_cols[0]
        ycol = f"{vcol}__original_year"
        has_orig = ycol in df.columns

        # 관심 국가만 (ISO3 코드 우선, 없으면 국가명 매핑)
        if "code" in df.columns:
            df["iso3"] = df["code"]
        else:
            df["iso3"] = None
        df["iso3"] = df["iso3"].fillna(df["entity"].map(OWID_NAMES))

        wanted = set(COUNTRIES) | {"EU27"}
        df = df[df["iso3"].isin(wanted)]
        if df.empty:
            raise ValueError(f"OWID/{slug}: 대상 국가 데이터 없음 (국가명 스키마 변경 의심)")

        unit = {
            "solar_generation_twh": "TWh",
            "solar_share_pct": "%",
            "solar_capacity_gw": "GW",
        }.get(metric_id, "")

        # 최근 25년만 (그 이전은 대시보드에서 안 쓴다)
        this_year = dt.date.today().year
        df = df[df["year"] >= this_year - 25]

        points: list[DataPoint] = []
        for row in df.itertuples(index=False):
            value = getattr(row, vcol, None)
            if pd.isna(value):
                continue
            year = int(row.year)

            # original_year 가 다르면 OWID 가 직전값을 이월한 것 → 추정치로 표시
            is_est = False
            note = ""
            if has_orig:
                oy = getattr(row, ycol, None)
                if pd.notna(oy) and int(oy) != year:
                    is_est = True
                    note = f"OWID 이월값 (원 관측연도 {int(oy)})"

            points.append(self.point(
                metric_id=metric_id,
                value=float(value),
                unit=unit,
                period=str(year),
                as_of=dt.date(year, 12, 31),
                entity=str(row.iso3),
                frequency="yearly",
                is_estimate=is_est,
                confidence=0.8 if is_est else 0.95,
                source_url=f"https://ourworldindata.org/grapher/{slug}",
                note=note,
            ))
        return points
