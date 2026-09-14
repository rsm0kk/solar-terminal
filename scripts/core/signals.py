# -*- coding: utf-8 -*-
"""시그널 엔진.

각 지표의 변화율을 -2 ~ +2 로 점수화하고 기업별 가중합을 낸다.
결과는 숫자 하나로 단정하지 않는다 — 총점, 전주대비 변화, 점수를 움직인
상위 지표, 데이터가 오래돼 제외된 지표, 신뢰도를 함께 낸다.

LLM 을 호출하지 않는다. 전부 규칙 기반이다.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

import pandas as pd

from .config import metrics as load_metrics, signals as load_signals
from .store import Store

WINDOW_DAYS = {"dod": 1, "wow": 7, "mom": 30, "qoq": 92, "yoy": 365}


def _series_points(store: Store, metric_id: str, entity: Optional[str]) -> list[tuple[dt.date, float]]:
    df = store.series(metric_id, entity)
    if df.empty:
        return []
    out: list[tuple[dt.date, float]] = []
    for _, r in df.iterrows():
        try:
            out.append((dt.date.fromisoformat(str(r["as_of_date"])), float(r["value"])))
        except (ValueError, TypeError):
            continue
    return sorted(out)


def _latest_before(pts: list[tuple[dt.date, float]], ref: dt.date) -> Optional[tuple[dt.date, float]]:
    best = None
    for d, v in pts:
        if d <= ref:
            best = (d, v)
        else:
            break
    return best


def _pct_change(pts: list[tuple[dt.date, float]], ref: dt.date, window: str) -> Optional[dict]:
    """window 기준 변화율(%). 계산 불가면 None."""
    cur = _latest_before(pts, ref)
    if cur is None:
        return None
    cur_date, cur_val = cur

    if window == "level":
        # 이미 편차·비율 지표인 경우 값 자체를 점수화한다
        return {"pct": cur_val, "current": cur_val, "prev": None,
                "as_of": cur_date, "prev_date": None}

    days = WINDOW_DAYS.get(window, 7)
    target = cur_date - dt.timedelta(days=days)
    # target 이전의 가장 가까운 관측치 (없으면 계산 포기)
    prev = _latest_before(pts, target)
    if prev is None:
        return None
    prev_date, prev_val = prev
    if prev_date == cur_date or prev_val == 0:
        return None
    # 너무 먼 과거와 비교하지 않는다 (window 의 3배까지만 허용)
    if (cur_date - prev_date).days > days * 3 + 3:
        return None

    return {
        "pct": (cur_val - prev_val) / abs(prev_val) * 100,
        "current": cur_val, "prev": prev_val,
        "as_of": cur_date, "prev_date": prev_date,
    }


def _score(pct: float, thresholds: list[float]) -> int:
    t1, t2, t3, t4 = thresholds
    if pct < t1:
        return -2
    if pct < t2:
        return -1
    if pct < t3:
        return 0
    if pct < t4:
        return 1
    return 2


def _entity_for(metric_id: str, metric_cfg: dict) -> Optional[str]:
    """지표별 기본 엔티티. 국내지표는 KOR, 미국지표는 USA, 나머지는 전체."""
    if metric_id.startswith("us_"):
        return "USA"
    tab = (metric_cfg.get(metric_id) or {}).get("tab")
    if tab == "korea":
        return "KOR"
    return None


def evaluate(store: Store, ref_date: Optional[dt.date] = None) -> dict[str, Any]:
    cfg = load_signals()
    metric_cfg = (load_metrics() or {}).get("metrics", {})
    sig_defs: dict[str, dict] = cfg.get("signals", {})
    weights: dict[str, dict] = cfg.get("weights", {})
    bands: list = cfg.get("verdict_bands", [])
    conf_cfg: dict = cfg.get("confidence", {})
    tier_score: dict = {int(k): float(v) for k, v in (conf_cfg.get("tier_score") or {}).items()}
    min_signals = int(conf_cfg.get("min_signals", 3))

    today = ref_date or dt.date.today()
    prev_ref = today - dt.timedelta(days=7)

    evaluated: dict[str, dict] = {}
    excluded: dict[str, str] = {}

    for sid, sd in sig_defs.items():
        metric_id = sd.get("metric", "")
        mcfg = metric_cfg.get(metric_id) or {}
        entity = _entity_for(metric_id, metric_cfg)

        pts = _series_points(store, metric_id, entity)
        if not pts:
            pts = _series_points(store, metric_id, None)
        if not pts:
            excluded[sid] = "데이터 없음"
            continue

        window = sd.get("window", "wow")
        chg = _pct_change(pts, today, window)
        if chg is None:
            excluded[sid] = "비교 기준 시점 데이터 부족"
            continue

        age = (today - chg["as_of"]).days
        max_age = int(sd.get("max_age_days", 30))
        if age > max_age:
            excluded[sid] = f"데이터가 {age}일 전 (기준 {max_age}일 초과)"
            continue

        thresholds = sd.get("thresholds") or [-5, -1, 1, 5]
        score = _score(chg["pct"], thresholds)

        # 전주 시점 점수 (전주 대비 변화 산출용)
        prev_chg = _pct_change(pts, prev_ref, window)
        prev_score = _score(prev_chg["pct"], thresholds) if prev_chg else score

        # 신뢰도: 출처 등급 × 신선도
        latest_row = store.latest(metric_id, entity) or store.latest(metric_id)
        tier = int(latest_row.get("source_tier", 4)) if latest_row else 4
        freshness = max(0.3, 1.0 - (age / max(max_age, 1)) * 0.5)
        conf = tier_score.get(tier, 0.7) * freshness

        evaluated[sid] = {
            "label": sd.get("label", sid),
            "metric_id": metric_id,
            "score": score,
            "prev_score": prev_score,
            "pct": round(chg["pct"], 2),
            "current": chg["current"],
            "prev": chg["prev"],
            "unit": mcfg.get("unit", ""),
            "window": window,
            "as_of": chg["as_of"].isoformat(),
            "age_days": age,
            "tier": tier,
            "confidence": round(conf, 3),
            "rationale": sd.get("rationale", ""),
            "is_manual": bool(latest_row.get("is_manual")) if latest_row else False,
        }

    # ---- 기업별 집계 ----
    companies: dict[str, Any] = {}
    for cid, wmap in weights.items():
        total = prev_total = 0.0
        contribs: list[dict] = []
        conf_num = conf_den = 0.0
        used = 0

        for sid, w in wmap.items():
            w = float(w)
            if w == 0:
                continue
            ev = evaluated.get(sid)
            if ev is None:
                continue
            contribution = ev["score"] * w
            total += contribution
            prev_total += ev["prev_score"] * w
            conf_num += ev["confidence"] * abs(w)
            conf_den += abs(w)
            used += 1
            contribs.append({
                "signal": sid, "label": ev["label"], "score": ev["score"],
                "weight": w, "contribution": round(contribution, 2),
                "pct": ev["pct"], "unit": ev["unit"], "window": ev["window"],
                "as_of": ev["as_of"], "rationale": ev["rationale"],
            })

        # 가중치 총합으로 정규화 (기업 간 비교 가능하게)
        wsum = sum(abs(float(w)) for w in wmap.values() if float(w) != 0) or 1.0
        norm_total = total / wsum * 5.0
        norm_prev = prev_total / wsum * 5.0

        verdict = "판단보류"
        if used >= min_signals:
            for lo, hi, label in bands:
                if lo <= norm_total < hi:
                    verdict = label
                    break

        contribs.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        companies[cid] = {
            "total": round(norm_total, 2),
            "prev_total": round(norm_prev, 2),
            "delta": round(norm_total - norm_prev, 2),
            "verdict": verdict,
            "signals_used": used,
            "min_signals": min_signals,
            "confidence": round(conf_num / conf_den, 3) if conf_den else 0.0,
            "top_drivers": contribs[:3],
            "all_drivers": contribs,
            "excluded": [
                {"signal": s, "label": sig_defs.get(s, {}).get("label", s), "reason": r}
                for s, r in excluded.items() if s in wmap and float(wmap[s]) != 0
            ],
        }

    return {
        "as_of": today.isoformat(),
        "signals": evaluated,
        "excluded": excluded,
        "companies": companies,
        "disclaimer": "시그널 점수는 방향성 참고치이며 실적 확정치가 아닙니다.",
    }
