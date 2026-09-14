# -*- coding: utf-8 -*-
"""데이터 품질 검사.

원칙: 의심스러우면 '버리기'보다 '표시하기'. 진짜 급등락은 실제로 일어난다.
명백한 오류(단위 불일치, 불가능한 음수, 미래 날짜)만 드롭한다.
"""
from __future__ import annotations

import datetime as dt
import statistics
from collections import defaultdict
from typing import Iterable

import pandas as pd

from .model import DataPoint, QualityIssue

# 음수가 될 수 없는 지표 (가격·물량·용량·발전량)
NON_NEGATIVE_HINTS = (
    "price", "capacity", "generation", "shipment", "volume", "revenue",
    "smp", "rec", "ghi", "sunshine", "close", "market_cap", "mw", "twh",
)
# 음수가 정상인 지표 (프리미엄·스프레드·이익·편차)
NEGATIVE_OK = (
    "premium", "spread", "profit", "dev_pct", "margin", "net_debt", "change",
)

# 주기별 '비정상 급등락' 경고 임계치 (%)
SPIKE_THRESHOLD = {
    "daily": 60.0,
    "business_daily": 40.0,
    "weekly": 45.0,
    "monthly": 90.0,
    "quarterly": 200.0,
    "yearly": 300.0,
    "irregular": 500.0,
}
# 이걸 넘으면 단위오류로 보고 드롭 (예: 원/kWh 가 갑자기 1000배)
ABSURD_MULTIPLE = 50.0

# 본질적으로 변동성이 큰 지표 — 급등락·배수 검사를 적용하지 않는다.
# 흐린 날 일조 0.03h → 맑은 날 11.9h 는 날씨지 단위 오류가 아니고,
# 거래량은 원래 일별로 몇 배씩 움직인다. 여기에 경고를 달면 진짜 오류가 묻힌다.
VOLATILE_METRICS = {
    "ghi_daily", "sunshine_hours", "ghi_normal_dev_pct",
    "trade_volume", "rec_spot_volume",
}
# 서로 다른 모델·관측으로 산출되어 출처 간 괴리가 정상인 지표
MODELED_METRICS = {"ghi_daily", "sunshine_hours"}

CONFLICT_THRESHOLD_PCT = 5.0
CONFLICT_THRESHOLD_MODELED_PCT = 60.0


def _non_negative(metric_id: str) -> bool:
    mid = metric_id.lower()
    if any(h in mid for h in NEGATIVE_OK):
        return False
    return any(h in mid for h in NON_NEGATIVE_HINTS)


def check_points(points: Iterable[DataPoint]) -> tuple[list[DataPoint], list[QualityIssue]]:
    """수집 직후 포인트 단위 검사. (통과 포인트, 이슈목록) 반환."""
    pts = list(points)
    issues: list[QualityIssue] = []
    kept: list[DataPoint] = []
    today = dt.date.today()

    seen: dict[str, DataPoint] = {}
    unit_by_series: dict[str, str] = {}

    for p in pts:
        # 1) 중복 제거 — 같은 point_key 가 한 수집에 두 번 나오면 뒤엣것만
        if p.point_key in seen:
            issues.append(QualityIssue(
                severity="info", kind="duplicate", metric_id=p.metric_id,
                entity=p.entity, period=p.period, source_name=p.source_name,
                detail="동일 수집분 내 중복 — 마지막 값만 사용", dropped=True,
            ))
            kept = [x for x in kept if x.point_key != p.point_key]
        seen[p.point_key] = p

        # 2) 미래 날짜 (일사량 '예보'는 예외)
        is_forecast = "forecast" in p.note.lower() or p.is_estimate
        if p.as_of_date > today + dt.timedelta(days=1) and not is_forecast:
            issues.append(QualityIssue(
                severity="error", kind="date_reversal", metric_id=p.metric_id,
                entity=p.entity, period=p.period, source_name=p.source_name,
                detail=f"기준일이 미래: {p.as_of_date}", dropped=True,
            ))
            continue

        # 3) 발표일이 기준일보다 앞서면 역전
        if p.published_at and p.published_at < p.as_of_date - dt.timedelta(days=400):
            issues.append(QualityIssue(
                severity="warn", kind="date_reversal", metric_id=p.metric_id,
                entity=p.entity, period=p.period, source_name=p.source_name,
                detail=f"발표일({p.published_at})이 기준일({p.as_of_date})보다 지나치게 이름",
            ))

        # 4) 불가능한 음수
        if p.value is not None and p.value < 0 and _non_negative(p.metric_id):
            issues.append(QualityIssue(
                severity="error", kind="negative", metric_id=p.metric_id,
                entity=p.entity, period=p.period, source_name=p.source_name,
                detail=f"음수가 될 수 없는 지표에 음수: {p.value}", dropped=True,
            ))
            continue

        # 5) 시리즈 내 단위 일관성
        sk = p.series_key
        if sk in unit_by_series and unit_by_series[sk] != p.unit:
            issues.append(QualityIssue(
                severity="error", kind="unit", metric_id=p.metric_id,
                entity=p.entity, period=p.period, source_name=p.source_name,
                detail=f"같은 시리즈에 단위 혼재: {unit_by_series[sk]} vs {p.unit}", dropped=True,
            ))
            continue
        unit_by_series[sk] = p.unit

        # 6) 통화 표기 검증 — 통화 단위인데 currency 가 비면 경고
        if any(c in p.unit for c in ("USD", "KRW", "RMB", "EUR", "원")) and not p.currency:
            issues.append(QualityIssue(
                severity="info", kind="unit", metric_id=p.metric_id,
                entity=p.entity, period=p.period, source_name=p.source_name,
                detail=f"통화 단위({p.unit})인데 currency 미기재",
            ))

        kept.append(p)

    return kept, issues


def check_series(df: pd.DataFrame) -> list[QualityIssue]:
    """스토어 전체에 대한 시계열 검사 (급등락·날짜역전)."""
    issues: list[QualityIssue] = []
    if df.empty:
        return issues

    for (metric_id, entity), grp in df.groupby(["metric_id", "entity"], sort=False):
        g = grp.sort_values("period")
        vals = pd.to_numeric(g["value"], errors="coerce")
        freq = str(g["frequency"].iloc[-1]) if "frequency" in g else "daily"
        thr = SPIKE_THRESHOLD.get(freq, 100.0)

        # 변동성이 본질인 지표는 급등락·배수 검사를 건너뛴다 (날짜역전 검사는 유지)
        skip_spike = str(metric_id) in VOLATILE_METRICS

        # 배수 검사의 기준 스케일 — 직전까지 본 값들의 중앙값(확장 윈도우).
        # 전체 시리즈 중앙값을 쓰면 이상치 자신이 기준을 오염시킨다
        # (120 → 120,000 두 점만 있으면 중앙값이 60,060 이 되어 오류를 놓친다).
        seen_abs: list[float] = []

        prev_v = None
        prev_period = None
        for period, v, unit, src in zip(g["period"], vals, g["unit"], g["source_name"]):
            if pd.isna(v):
                continue
            if not skip_spike and prev_v is not None and prev_v != 0:
                ratio = abs(v / prev_v) if prev_v else 0
                pct = (v - prev_v) / abs(prev_v) * 100
                # 0 부근을 지나가거나 부호가 뒤집히면 배수는 의미가 없다 → 단위검사 생략
                # (영업이익 -74억 → -4,897억 은 66배지만 단위 오류가 아니라 실제 대규모 손실)
                scale = statistics.median(seen_abs) if len(seen_abs) >= 2 else 0.0
                near_zero = scale > 0 and abs(prev_v) < scale * 0.1
                sign_flip = (prev_v < 0) != (v < 0)
                if near_zero or sign_flip:
                    pass
                elif ratio >= ABSURD_MULTIPLE or (ratio > 0 and ratio <= 1 / ABSURD_MULTIPLE):
                    issues.append(QualityIssue(
                        severity="error", kind="unit", metric_id=str(metric_id),
                        entity=str(entity), period=str(period), source_name=str(src),
                        detail=(f"{prev_period}→{period} 값이 {ratio:.0f}배 변동 "
                                f"({prev_v}→{v} {unit}). 단위 오류 의심"),
                    ))
                elif abs(pct) > thr:
                    issues.append(QualityIssue(
                        severity="warn", kind="spike", metric_id=str(metric_id),
                        entity=str(entity), period=str(period), source_name=str(src),
                        detail=f"{prev_period}→{period} {pct:+.1f}% 급변 ({prev_v}→{v} {unit})",
                    ))
            seen_abs.append(abs(float(v)))
            prev_v, prev_period = v, period

        # 날짜 역전: period 순서와 as_of_date 순서가 어긋나는 경우
        try:
            aod = pd.to_datetime(g["as_of_date"], errors="coerce")
            if aod.notna().sum() > 2 and not aod.is_monotonic_increasing:
                issues.append(QualityIssue(
                    severity="warn", kind="date_reversal", metric_id=str(metric_id),
                    entity=str(entity), detail="period 순서와 as_of_date 순서 불일치",
                ))
        except Exception:
            pass

    return issues


def check_source_conflicts(df: pd.DataFrame) -> list[QualityIssue]:
    """같은 지표·기간을 서로 다른 출처가 다르게 보고하는 경우.

    임의 합성하지 않는다 — tier 가 높은 출처를 메인으로 쓰고 충돌 사실만 기록한다.
    """
    issues: list[QualityIssue] = []
    if df.empty:
        return issues

    grp = df.groupby(["metric_id", "entity", "period"], sort=False)
    for (metric_id, entity, period), g in grp:
        if g["source_name"].nunique() < 2:
            continue
        vals = pd.to_numeric(g["value"], errors="coerce").dropna()
        if len(vals) < 2:
            continue
        lo, hi = vals.min(), vals.max()
        if lo == 0:
            continue
        diff_pct = (hi - lo) / abs(lo) * 100

        # 위성·기상모델 산출값은 출처가 다르면 원래 갈린다. 임계치를 높이고
        # 경고가 아닌 참고(info)로 남긴다 — 진짜 오류를 묻지 않기 위해서다.
        modeled = str(metric_id) in MODELED_METRICS
        threshold = CONFLICT_THRESHOLD_MODELED_PCT if modeled else CONFLICT_THRESHOLD_PCT
        if diff_pct <= threshold:
            continue

        winner = g.sort_values("source_tier").iloc[0]
        others = ", ".join(
            f"{r['source_name']}={r['value']}" for _, r in g.iterrows()
            if r["source_name"] != winner["source_name"]
        )
        issues.append(QualityIssue(
            severity="info" if modeled else "warn",
            kind="conflict", metric_id=str(metric_id),
            entity=str(entity), period=str(period),
            source_name=str(winner["source_name"]),
            detail=(f"출처 간 {diff_pct:.1f}% 불일치. "
                    f"메인={winner['source_name']}({winner['value']}), 기타: {others}"
                    + (" (모델 산출값이라 괴리가 정상 범위)" if modeled else "")),
        ))
    return issues


def check_quarterly_conversion(
    cumulative: dict[str, float], standalone: dict[str, float], label: str = ""
) -> list[QualityIssue]:
    """누적 → 단독분기 변환 검증.

    같은 연도의 단독분기 합이 연간 누적과 일치해야 한다.
    재무상태표 항목에는 적용하지 않는다(분기말 잔액이므로 누적 개념이 없음).
    """
    issues: list[QualityIssue] = []
    by_year: dict[str, list[str]] = defaultdict(list)
    for q in standalone:
        by_year[q[:4]].append(q)

    for year, quarters in by_year.items():
        if len(quarters) < 4:
            continue
        s = sum(standalone[q] for q in quarters)
        annual = cumulative.get(f"{year}Q4")
        if annual is None:
            continue
        if abs(annual) < 1e-9:
            continue
        gap = abs(s - annual) / abs(annual) * 100
        if gap > 1.0:
            issues.append(QualityIssue(
                severity="error", kind="quarterly_conversion",
                metric_id=label, period=f"{year}",
                detail=f"단독분기 합({s:,.1f}) ≠ 연간누적({annual:,.1f}), 괴리 {gap:.2f}%",
            ))
    return issues


def summarize(issues: list[QualityIssue]) -> dict:
    by_kind: dict[str, int] = defaultdict(int)
    by_sev: dict[str, int] = defaultdict(int)
    for i in issues:
        by_kind[i.kind] += 1
        by_sev[i.severity] += 1
    return {
        "total": len(issues),
        "by_severity": dict(by_sev),
        "by_kind": dict(by_kind),
        "dropped": sum(1 for i in issues if i.dropped),
    }
