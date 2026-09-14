# -*- coding: utf-8 -*-
"""dashboard.json 조립.

HTML 은 이 JSON 하나만 소비한다. 마크업에 숫자를 하드코딩하지 않는다.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

import pandas as pd

from .config import companies as load_companies, metrics as load_metrics, sources as load_sources
from .model import QualityIssue, SourceStatus
from .store import Store

# 주기별 보관 기간 (HTML 용량 제어)
KEEP_DAYS = {
    "daily": 1100, "business_daily": 1100, "weekly": 1500,
    "monthly": 2600, "quarterly": 3700, "yearly": 9200, "irregular": 3700,
}


def _period_sort_key(p: str) -> str:
    """YYYYQn 을 YYYY-Qn 정렬 가능하게. 나머지는 그대로."""
    if len(p) == 6 and p[4] == "Q":
        return f"{p[:4]}-{int(p[5]):02d}"
    return p


def build_series(store: Store) -> dict[str, Any]:
    """metric_id|entity → 시계열 + 메타데이터."""
    metric_cfg = (load_metrics() or {}).get("metrics", {})
    out: dict[str, Any] = {}
    if store.df.empty:
        return out

    today = dt.date.today()
    df = store.df.copy()
    df["_aod"] = pd.to_datetime(df["as_of_date"], errors="coerce")

    for (metric_id, entity), grp in df.groupby(["metric_id", "entity"], sort=False):
        mcfg = metric_cfg.get(metric_id, {})
        freq = str(grp["frequency"].iloc[-1])
        keep = KEEP_DAYS.get(freq, 1100)
        cutoff = pd.Timestamp(today - dt.timedelta(days=keep))

        g = grp[grp["_aod"].notna() & (grp["_aod"] >= cutoff)]
        if g.empty:
            g = grp.tail(40)

        # 같은 period 에 여러 출처 → tier 낮은(신뢰도 높은) 쪽
        g = g.sort_values(["period", "source_tier"]).drop_duplicates(
            subset=["period"], keep="first")
        g = g.iloc[g["period"].map(_period_sort_key).argsort()]

        points = []
        for _, r in g.iterrows():
            v = r["value"]
            if pd.isna(v):
                continue
            points.append([str(r["period"]), round(float(v), 6)])
        if not points:
            continue

        last = g.iloc[-1]
        out[f"{metric_id}|{entity}"] = {
            "metric_id": metric_id,
            "entity": str(entity),
            "label": mcfg.get("label", metric_id),
            "unit": str(last["unit"]),
            "axis_group": mcfg.get("axis_group", ""),
            "freq": freq,
            "tab": mcfg.get("tab", ""),
            "good": mcfg.get("good", "neutral"),
            "source": str(last["source_name"]),
            "source_url": str(last["source_url"] or ""),
            "tier": int(last["source_tier"]),
            "as_of": str(last["as_of_date"]),
            "is_manual": bool(last["is_manual"]),
            "is_estimate": bool(last["is_estimate"]),
            "note": str(last["note"] or ""),
            "points": points,
        }
    return out


def _changes(points: list, windows: tuple[int, ...] = (1, 4, 13, 52)) -> dict[str, Optional[float]]:
    """관측치 개수 기준 변화율. 주간 데이터면 1=WoW, 4≈1M, 13≈3M, 52≈1Y."""
    out: dict[str, Optional[float]] = {}
    labels = ["last", "m1", "m3", "y1"]
    for label, n in zip(labels, windows):
        if len(points) > n:
            prev = points[-1 - n][1]
            cur = points[-1][1]
            out[label] = round((cur - prev) / abs(prev) * 100, 2) if prev else None
        else:
            out[label] = None
    return out


def build(
    store: Store,
    statuses: list[SourceStatus],
    issues: list[QualityIssue],
    signal_result: dict,
    brief: dict,
    filings: list[dict],
    ppa_deals: list[dict],
    pipeline: list[dict],
    rec_weight: float = 1.0,
) -> dict[str, Any]:
    comp_cfg = load_companies()
    metric_cfg = (load_metrics() or {}).get("metrics", {})
    src_cfg = load_sources()

    series = build_series(store)

    # 시리즈별 변화율 요약 (표에서 바로 씀)
    for key, s in series.items():
        s["changes"] = _changes(s["points"])
        s["latest"] = s["points"][-1][1] if s["points"] else None

    ok = sum(1 for s in statuses if s.state == "ok")
    stale = sum(1 for s in statuses if s.state == "stale")
    err = sum(1 for s in statuses if s.state == "error")
    nokey = sum(1 for s in statuses if s.state == "no_key")
    empty = sum(1 for s in statuses if s.state == "manual_empty")

    from .quality import summarize

    # SAMPLE 행은 어댑터에서 이미 걸렀지만 한 번 더 방어
    ppa_clean = [d for d in ppa_deals if str(d.get("row_type", "")).upper() != "SAMPLE"]
    pipe_clean = [d for d in pipeline if str(d.get("row_type", "")).upper() != "SAMPLE"]

    return {
        "meta": {
            "title": "SOLAR ANALYST TERMINAL",
            "as_of": dt.date.today().isoformat(),
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "rec_weight_default": rec_weight,
            "series_count": len(series),
            "point_count": int(len(store.df)),
            "source_summary": {
                "ok": ok, "stale": stale, "error": err,
                "no_key": nokey, "manual_empty": empty, "total": len(statuses),
            },
            "tier_labels": {str(k): v for k, v in (src_cfg.get("tier_labels") or {}).items()},
        },
        "metrics": metric_cfg,
        "companies": comp_cfg.get("companies", []),
        "exposure_labels": comp_cfg.get("exposure_labels", {}),
        "series": series,
        "signals": signal_result,
        "brief": brief,
        "status": [s.model_dump() for s in statuses],
        "quality": {
            "summary": summarize(issues),
            "issues": [i.model_dump() for i in issues[:400]],
        },
        "filings": sorted(filings, key=lambda f: str(f.get("date", "")), reverse=True)[:250],
        "ppa_deals": ppa_clean,
        "pipeline": pipe_clean,
    }
