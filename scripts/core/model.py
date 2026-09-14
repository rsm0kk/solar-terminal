# -*- coding: utf-8 -*-
"""데이터 포인트 모델.

모든 수집 결과는 DataPoint 로 정규화된다. 출처·기준일·단위 없이 저장되는
값은 존재할 수 없다 — 화면에 '출처 없는 숫자'가 나가지 않게 하는 1차 방어선이다.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Frequency = Literal[
    "daily", "business_daily", "weekly", "monthly",
    "quarterly", "yearly", "irregular",
]

# period 형식: 2026-07-26 / 2026-07 / 2026Q2 / 2026
_PERIOD_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?|Q[1-4])?$")


class DataPoint(BaseModel):
    """정규화된 단일 관측치."""

    metric_id: str
    entity: str = "GLOBAL"          # 국가코드(KOR/USA) 또는 기업id(oci/hanwha)
    value: Optional[float] = None   # None = 결측(수집 실패와 구분됨)
    unit: str
    currency: Optional[str] = None

    period: str                     # 관측 대상 기간
    as_of_date: dt.date             # 이 값이 대표하는 날짜
    published_at: Optional[dt.date] = None   # 원 출처가 발표한 날짜
    fetched_at: dt.datetime         # 우리가 수집한 시각

    source_name: str
    source_url: str = ""
    source_tier: int = Field(ge=1, le=6)
    frequency: Frequency

    is_estimate: bool = False
    is_manual: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    revision_id: str = ""

    note: str = ""

    model_config = {"extra": "forbid"}

    @field_validator("period")
    @classmethod
    def _check_period(cls, v: str) -> str:
        if not _PERIOD_RE.match(v):
            raise ValueError(f"period 형식 오류: {v!r} (허용: YYYY, YYYY-MM, YYYY-MM-DD, YYYYQn)")
        return v

    @field_validator("value")
    @classmethod
    def _check_finite(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("value 가 NaN/Inf")
        return float(v)

    @model_validator(mode="after")
    def _fill_revision(self):
        if not self.revision_id:
            object.__setattr__(self, "revision_id", self.content_hash())
        return self

    # ---- 키 ----
    @property
    def series_key(self) -> str:
        return f"{self.metric_id}|{self.entity}"

    @property
    def point_key(self) -> str:
        """중복 판단키. 같은 키의 값이 바뀌면 '과거 데이터 수정'으로 감지한다."""
        return f"{self.metric_id}|{self.entity}|{self.period}|{self.source_name}"

    def content_hash(self) -> str:
        raw = f"{self.point_key}|{self.value}|{self.unit}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    # ---- 직렬화 ----
    def to_row(self) -> dict[str, Any]:
        d = self.model_dump()
        d["as_of_date"] = self.as_of_date.isoformat()
        d["published_at"] = self.published_at.isoformat() if self.published_at else None
        d["fetched_at"] = self.fetched_at.isoformat(timespec="seconds")
        return d

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "DataPoint":
        r = dict(row)
        if isinstance(r.get("as_of_date"), str):
            r["as_of_date"] = dt.date.fromisoformat(r["as_of_date"])
        if isinstance(r.get("published_at"), str):
            r["published_at"] = dt.date.fromisoformat(r["published_at"])
        if isinstance(r.get("fetched_at"), str):
            r["fetched_at"] = dt.datetime.fromisoformat(r["fetched_at"])
        return cls(**r)


class SourceStatus(BaseModel):
    """소스별 수집 결과. status.json 으로 나가고 '데이터 상태' 탭에 그대로 표시된다."""

    source_id: str
    label: str
    state: Literal["ok", "stale", "error", "no_key", "disabled", "manual_empty"]
    tier: int
    frequency: str
    points: int = 0
    last_success: Optional[str] = None    # ISO datetime
    last_attempt: Optional[str] = None
    latest_as_of: Optional[str] = None    # 원 데이터 기준일
    next_expected: Optional[str] = None
    stale_days: Optional[int] = None
    age_days: Optional[int] = None
    message: str = ""
    url: str = ""
    signup: str = ""

    @property
    def is_healthy(self) -> bool:
        return self.state in ("ok", "manual_empty", "disabled")


class QualityIssue(BaseModel):
    """품질검사 위반. quality_report.json 으로 나간다."""

    severity: Literal["error", "warn", "info"]
    kind: str                  # duplicate / date_reversal / spike / unit / negative / revision / conflict
    metric_id: str = ""
    entity: str = ""
    period: str = ""
    source_name: str = ""
    detail: str = ""
    dropped: bool = False      # 해당 포인트를 버렸는지
