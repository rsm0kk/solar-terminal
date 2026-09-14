# -*- coding: utf-8 -*-
"""증분 데이터 스토어.

핵심 계약 2가지:
  1. 수집 실패는 기존 정상 데이터를 절대 덮어쓰지 않는다 (0/null 덮어쓰기 금지).
  2. 같은 키의 값이 바뀌면 '과거 데이터 수정'으로 감지해 품질보고서에 남긴다.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from .config import HISTORY_DIR
from .model import DataPoint, QualityIssue

HISTORY_FILE = HISTORY_DIR / "points.parquet"
REVISION_LOG = HISTORY_DIR / "revisions.parquet"

# point_key 를 구성하는 열 (중복 판단키)
KEY_COLS = ["metric_id", "entity", "period", "source_name"]

_COLUMNS = [
    "metric_id", "entity", "value", "unit", "currency", "period",
    "as_of_date", "published_at", "fetched_at",
    "source_name", "source_url", "source_tier", "frequency",
    "is_estimate", "is_manual", "confidence", "revision_id", "note",
]


class Store:
    def __init__(self, path: Path = HISTORY_FILE):
        self.path = path
        self.df = self._load()
        self.issues: list[QualityIssue] = []

    # ---------------------------------------------------------------
    def _load(self) -> pd.DataFrame:
        if self.path.exists():
            try:
                df = pd.read_parquet(self.path)
                for c in _COLUMNS:
                    if c not in df.columns:
                        df[c] = None
                return df[_COLUMNS]
            except Exception as e:
                # 손상된 스토어로 전체가 죽지 않게 백업 후 새로 시작
                bad = self.path.with_suffix(f".corrupt-{dt.datetime.now():%Y%m%d%H%M%S}.parquet")
                try:
                    self.path.rename(bad)
                    print(f"  [주의] 스토어 읽기 실패({e}). {bad.name} 로 보관하고 새로 만듭니다.")
                except Exception:
                    pass
        return pd.DataFrame(columns=_COLUMNS)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.df.to_parquet(self.path, index=False)

    # ---------------------------------------------------------------
    def merge(self, points: Iterable[DataPoint]) -> dict[str, int]:
        """새 포인트를 병합한다. 반환: {inserted, revised, unchanged, skipped_null}"""
        rows = [p.to_row() for p in points]
        stat = {"inserted": 0, "revised": 0, "unchanged": 0, "skipped_null": 0}
        if not rows:
            return stat

        new = pd.DataFrame(rows)
        for c in _COLUMNS:
            if c not in new.columns:
                new[c] = None
        new = new[_COLUMNS]

        if self.df.empty:
            # 최초 적재에서도 값이 없는 포인트는 넣지 않는다
            keep = new["value"].notna()
            stat["skipped_null"] = int((~keep).sum())
            self.df = new[keep].reset_index(drop=True)
            stat["inserted"] = len(self.df)
            return stat

        existing = self.df.set_index(KEY_COLS, drop=False)
        out_rows: list[dict] = []

        for row in new.to_dict("records"):
            key = tuple(row[c] for c in KEY_COLS)

            if key not in existing.index:
                if row["value"] is None or pd.isna(row["value"]):
                    # 값 없는 신규 포인트는 저장하지 않는다 (빈 시계열 방지)
                    stat["skipped_null"] += 1
                    continue
                out_rows.append(row)
                stat["inserted"] += 1
                continue

            prev = existing.loc[key]
            if isinstance(prev, pd.DataFrame):
                prev = prev.iloc[-1]

            new_val, old_val = row["value"], prev["value"]

            # 계약 1: 실패/결측이 기존 정상값을 덮어쓰지 못한다
            if new_val is None or pd.isna(new_val):
                stat["skipped_null"] += 1
                continue

            if old_val is not None and not pd.isna(old_val) and float(new_val) != float(old_val):
                # 계약 2: 과거 데이터 수정 감지
                self.issues.append(QualityIssue(
                    severity="warn",
                    kind="revision",
                    metric_id=str(row["metric_id"]),
                    entity=str(row["entity"]),
                    period=str(row["period"]),
                    source_name=str(row["source_name"]),
                    detail=f"동일 출처의 과거값 수정: {old_val} → {new_val} ({row['unit']})",
                ))
                self._log_revision(row, old_val)
                stat["revised"] += 1
            else:
                stat["unchanged"] += 1

            out_rows.append(row)  # 최신값으로 갱신

        updated = pd.DataFrame(out_rows) if out_rows else pd.DataFrame(columns=_COLUMNS)
        if not updated.empty:
            combined = pd.concat([self.df, updated], ignore_index=True)
            # 같은 키는 마지막(=이번 수집분)만 남긴다
            combined = combined.drop_duplicates(subset=KEY_COLS, keep="last")
            self.df = combined.reset_index(drop=True)

        return stat

    def _log_revision(self, row: dict, old_value) -> None:
        rec = pd.DataFrame([{
            "logged_at": dt.datetime.now().isoformat(timespec="seconds"),
            "metric_id": row["metric_id"], "entity": row["entity"],
            "period": row["period"], "source_name": row["source_name"],
            "old_value": old_value, "new_value": row["value"], "unit": row["unit"],
        }])
        try:
            if REVISION_LOG.exists():
                rec = pd.concat([pd.read_parquet(REVISION_LOG), rec], ignore_index=True)
            rec.to_parquet(REVISION_LOG, index=False)
        except Exception:
            pass

    # ---------------------------------------------------------------
    def series(self, metric_id: str, entity: Optional[str] = None) -> pd.DataFrame:
        """지표 시계열을 period 오름차순으로 반환."""
        if self.df.empty:
            return pd.DataFrame(columns=_COLUMNS)
        m = self.df["metric_id"] == metric_id
        if entity is not None:
            m &= self.df["entity"] == entity
        out = self.df[m].copy()
        if out.empty:
            return out
        # 같은 period 에 여러 출처가 있으면 tier 가 낮은(=신뢰도 높은) 쪽을 우선
        out = out.sort_values(["period", "source_tier"]).drop_duplicates(
            subset=["metric_id", "entity", "period"], keep="first")
        return out.sort_values("period").reset_index(drop=True)

    def latest(self, metric_id: str, entity: Optional[str] = None) -> Optional[dict]:
        s = self.series(metric_id, entity)
        if s.empty:
            return None
        return s.iloc[-1].to_dict()

    def entities(self, metric_id: str) -> list[str]:
        if self.df.empty:
            return []
        return sorted(self.df.loc[self.df["metric_id"] == metric_id, "entity"].unique().tolist())

    @property
    def metric_ids(self) -> list[str]:
        if self.df.empty:
            return []
        return sorted(self.df["metric_id"].unique().tolist())
