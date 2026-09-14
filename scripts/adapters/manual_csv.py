# -*- coding: utf-8 -*-
"""수동 입력 CSV 어댑터.

유료·로그인 필요·이용약관상 자동수집이 불명확한 데이터는 우회하지 않고
여기로 받는다. 파일이 비어 있으면 오류가 아니라 'manual_empty' 상태다.

모든 템플릿은 `row_type` 열을 가진다. SAMPLE 행은 입력 예시이므로
대시보드에 절대 포함하지 않는다.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from core.config import MANUAL_DIR
from core.model import DataPoint

from .base import Adapter

# 시계열로 변환하는 파일 → (필수열, 처리방식)
TIMESERIES_FILES = {
    "solar_supply_chain_prices.csv": ["date", "metric_id", "value", "unit"],
    "company_kpi_manual.csv": ["period", "company_id", "kpi_key", "value", "unit"],
    "manual_estimates.csv": ["period", "company_id", "metric_id", "value", "unit"],
}
# 레코드로 그대로 넘기는 파일 (시계열 아님)
RECORD_FILES = {
    "ppa_deals_manual.csv": ["announced_date", "buyer", "solar_mw"],
    "company_capacity_pipeline.csv": ["company_id", "asset_name", "capacity_mw"],
}


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "y", "yes", "예", "o")


class ManualCsvAdapter(Adapter):
    name = "manual_csv"

    def __init__(self, source_id: str, cfg: dict):
        super().__init__(source_id, cfg)
        self.filename: str = cfg.get("file", "")
        #: 시계열이 아닌 파일은 여기에 레코드로 담긴다
        self.records: list[dict] = []
        self.is_empty = False

    # ------------------------------------------------------------------
    def collect(self) -> list[DataPoint]:
        path = MANUAL_DIR / self.filename
        if not path.exists():
            self.is_empty = True
            self.warnings.append(f"{self.filename} 없음 — 템플릿을 채우면 자동 반영됩니다")
            return []

        # '#' 로 시작하는 줄은 필드 설명 주석
        df = pd.read_csv(path, comment="#", skip_blank_lines=True, dtype=str)
        df.columns = [c.strip() for c in df.columns]

        if "row_type" in df.columns:
            before = len(df)
            df = df[df["row_type"].str.strip().str.upper() != "SAMPLE"]
            if len(df) == 0 and before > 0:
                self.is_empty = True
                return []
        if df.empty:
            self.is_empty = True
            return []

        if self.filename in RECORD_FILES:
            self._load_records(df)
            return []
        return self._load_timeseries(df)

    # ------------------------------------------------------------------
    def _load_records(self, df: pd.DataFrame) -> None:
        required = RECORD_FILES[self.filename]
        self.expect_columns(list(df.columns), required, self.filename)
        self.records = [
            {k: (None if pd.isna(v) else str(v).strip()) for k, v in row.items()}
            for row in df.to_dict("records")
        ]

    # ------------------------------------------------------------------
    def _load_timeseries(self, df: pd.DataFrame) -> list[DataPoint]:
        required = TIMESERIES_FILES.get(self.filename)
        if not required:
            raise ValueError(f"알 수 없는 수동입력 파일: {self.filename}")
        self.expect_columns(list(df.columns), required, self.filename)

        points: list[DataPoint] = []
        bad = 0

        for i, row in enumerate(df.to_dict("records"), start=2):
            try:
                value = float(str(row.get("value", "")).replace(",", "").strip())
            except (TypeError, ValueError):
                bad += 1
                continue

            # 기간·기준일
            if "date" in required:
                period, as_of = self._parse_date(row.get("date"))
            else:
                period, as_of = self._parse_period(row.get("period"))
            if not period:
                bad += 1
                continue

            # 지표·엔티티
            if self.filename == "company_kpi_manual.csv":
                metric_id = str(row.get("kpi_key", "")).strip()
                entity = str(row.get("company_id", "")).strip()
            elif self.filename == "manual_estimates.csv":
                metric_id = str(row.get("metric_id", "")).strip()
                entity = str(row.get("company_id", "")).strip()
            else:
                metric_id = str(row.get("metric_id", "")).strip()
                entity = str(row.get("entity") or "GLOBAL").strip() or "GLOBAL"

            if not metric_id or not entity:
                bad += 1
                continue

            unit = str(row.get("unit", "")).strip()
            currency = (str(row.get("currency", "")).strip() or None)
            src_name = str(row.get("source_name", "")).strip() or f"수기입력 · {self.filename}"
            src_url = str(row.get("source_url", "")).strip()
            note = str(row.get("note", "")).strip()
            if note.lower() == "nan":
                note = ""

            is_est = _truthy(row.get("is_estimate")) or self.filename == "manual_estimates.csv"

            points.append(self.point(
                metric_id=metric_id, value=value, unit=unit, currency=currency,
                period=period, as_of=as_of, entity=entity,
                frequency=self.freq, is_estimate=is_est, is_manual=True,
                confidence=0.7 if is_est else 0.85,
                source_name=src_name, source_url=src_url, note=note,
                # 수기입력이라도 원 출처가 IR·공시면 tier 를 sources.yaml 값으로 쓴다
            ))

        if bad:
            self.warnings.append(f"{self.filename}: {bad}개 행 건너뜀 (값·날짜 형식 확인)")
        if not points:
            self.is_empty = True
        return points

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_date(raw) -> tuple[str, dt.date]:
        s = str(raw or "").strip()
        try:
            d = dt.date.fromisoformat(s)
            return d.isoformat(), d
        except ValueError:
            return "", dt.date.today()

    @staticmethod
    def _parse_period(raw) -> tuple[str, dt.date]:
        """2026Q1 / 2026-03 / 2026-03-31 을 받는다."""
        s = str(raw or "").strip().upper()
        if len(s) == 6 and s[4] == "Q":
            try:
                y, q = int(s[:4]), int(s[5])
                last = (dt.date(y, q * 3, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
                return s, last
            except ValueError:
                return "", dt.date.today()
        try:
            d = dt.date.fromisoformat(s)
            return d.isoformat(), d
        except ValueError:
            pass
        if len(s) == 7 and s[4] == "-":
            try:
                y, m = int(s[:4]), int(s[5:7])
                last = (dt.date(y, m, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
                return s, last
            except ValueError:
                return "", dt.date.today()
        return "", dt.date.today()
