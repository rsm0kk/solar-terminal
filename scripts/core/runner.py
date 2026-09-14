# -*- coding: utf-8 -*-
"""수집 러너.

부분 실패를 허용한다. 소스 하나가 죽어도 나머지는 계속 수집하고,
실패한 소스는 마지막 정상 데이터를 유지한 채 stale/error 로 표시된다.
"""
from __future__ import annotations

import datetime as dt
import sys
import traceback
from typing import Any, Optional

from adapters import get_adapter_class

from . import quality
from .config import missing_keys, sources as load_sources
from .model import DataPoint, QualityIssue, SourceStatus
from .store import Store

# 주기별 '다음 예상 갱신일' 간격(일)
NEXT_BY_FREQ = {
    "daily": 1, "business_daily": 1, "weekly": 7,
    "monthly": 31, "quarterly": 92, "yearly": 365, "irregular": 0,
}


class CollectResult:
    def __init__(self):
        self.statuses: list[SourceStatus] = []
        self.issues: list[QualityIssue] = []
        self.filings: list[dict] = []
        self.ppa_deals: list[dict] = []
        self.pipeline: list[dict] = []
        self.merge_stats: dict[str, dict] = {}


def _next_expected(latest: Optional[dt.date], freq: str) -> Optional[str]:
    if latest is None:
        return None
    step = NEXT_BY_FREQ.get(freq, 0)
    if not step:
        return None
    return (latest + dt.timedelta(days=step)).isoformat()


def run_collection(
    store: Store,
    only: Optional[list[str]] = None,
    as_of: Optional[dt.date] = None,
) -> CollectResult:
    """모든 소스를 순회 수집해 store 에 병합한다."""
    cfg_all = load_sources()
    src_cfg: dict[str, Any] = cfg_all.get("sources", {})
    stale_by_freq: dict[str, int] = cfg_all.get("staleness_by_freq", {})
    today = as_of or dt.date.today()
    result = CollectResult()
    now_iso = dt.datetime.now().isoformat(timespec="seconds")

    for source_id, cfg in src_cfg.items():
        if only and source_id not in only:
            continue

        label = cfg.get("label", source_id)
        freq = cfg.get("freq", "daily")
        tier = int(cfg.get("tier", 4))
        stale_days = int(cfg.get("stale_days") or stale_by_freq.get(freq, 30))

        st = SourceStatus(
            source_id=source_id, label=label, state="ok", tier=tier,
            frequency=freq, stale_days=stale_days,
            url=cfg.get("url", ""), signup=cfg.get("signup", ""),
            last_attempt=now_iso,
        )

        # 1) 비활성
        if not cfg.get("enabled", True):
            st.state = "disabled"
            st.message = "sources.yaml 에서 비활성화됨"
            result.statuses.append(st)
            continue

        # 2) 키 확인 — 없으면 수집을 시도조차 하지 않고 기존 데이터를 유지한다
        need = cfg.get("requires") or []
        lack = missing_keys(need)
        if lack:
            st.state = "no_key"
            st.message = f"API 미설정: {', '.join(lack)}"
            if cfg.get("signup"):
                st.message += f" — 발급: {cfg['signup']}"
            _fill_existing(st, store, source_id, cfg, today)
            result.statuses.append(st)
            print(f"  [키없음] {label}: {', '.join(lack)}")
            continue

        # 3) 어댑터 로드
        cls = get_adapter_class(cfg.get("adapter", ""))
        if cls is None:
            st.state = "error"
            st.message = f"어댑터 없음: {cfg.get('adapter')}"
            result.statuses.append(st)
            continue

        # 4) 수집
        try:
            adapter = cls(source_id, cfg)
            points: list[DataPoint] = adapter.collect()

            kept, issues = quality.check_points(points)
            result.issues.extend(issues)
            for w in adapter.warnings:
                result.issues.append(QualityIssue(
                    severity="warn", kind="adapter", metric_id="",
                    source_name=label, detail=w))

            stats = store.merge(kept)
            result.merge_stats[source_id] = stats

            # 어댑터가 시계열 외에 들고 오는 것들
            result.filings.extend(getattr(adapter, "filings", []) or [])
            result.issues.extend(getattr(adapter, "quality_issues", []) or [])
            records = getattr(adapter, "records", []) or []
            if records:
                fname = cfg.get("file", "")
                if "ppa_deals" in fname:
                    result.ppa_deals.extend(records)
                elif "capacity_pipeline" in fname:
                    result.pipeline.extend(records)

            st.points = len(kept)
            st.last_success = now_iso

            if getattr(adapter, "is_empty", False) and not kept:
                st.state = "manual_empty"
                st.message = "템플릿이 비어 있습니다 — 값을 채우면 자동 반영됩니다"
            else:
                _fill_existing(st, store, source_id, cfg, today)
                if st.state == "ok" and adapter.warnings:
                    st.message = adapter.warnings[0][:200]

            emoji = "OK  " if st.state == "ok" else f"{st.state.upper():4}"
            print(f"  [{emoji}] {label}: {len(kept)}점 "
                  f"(신규 {stats['inserted']} / 수정 {stats['revised']})")

        except Exception as e:
            st.state = "error"
            st.message = f"{type(e).__name__}: {str(e)[:300]}"
            _fill_existing(st, store, source_id, cfg, today, keep_error=True)
            result.issues.append(QualityIssue(
                severity="error", kind="fetch", source_name=label,
                detail=st.message))
            print(f"  [FAIL] {label}: {st.message[:160]}")
            if "--traceback" in sys.argv:
                traceback.print_exc(limit=4)

        result.statuses.append(st)

    return result


def _fill_existing(
    st: SourceStatus, store: Store, source_id: str, cfg: dict,
    today: dt.date, keep_error: bool = False,
) -> None:
    """스토어에 남아 있는 이 소스의 최신 데이터로 신선도를 계산한다.

    수집에 실패해도 기존 데이터가 있으면 그 기준일로 stale 여부를 판단한다.
    """
    df = store.df
    if df.empty:
        if not keep_error and st.state == "ok":
            st.state = "error"
            st.message = st.message or "수집된 데이터 없음"
        return

    label = cfg.get("label", source_id)
    # source_name 은 어댑터가 세분화할 수 있어 라벨 접두 매칭도 함께 본다
    mask = df["source_name"].astype(str).str.startswith(str(label).split(" · ")[0][:12])
    sub = df[mask]
    if sub.empty:
        return

    latest_str = str(sub["as_of_date"].max())
    st.latest_as_of = latest_str
    try:
        latest = dt.date.fromisoformat(latest_str)
    except ValueError:
        return

    age = (today - latest).days
    st.age_days = age
    st.next_expected = _next_expected(latest, st.frequency)

    if st.state == "ok" and st.stale_days is not None and age > st.stale_days:
        st.state = "stale"
        st.message = f"최신 데이터가 {age}일 전({latest_str}) — 기준 {st.stale_days}일 초과"
