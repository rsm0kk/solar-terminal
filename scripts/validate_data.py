# -*- coding: utf-8 -*-
"""데이터 정합성 검사 — 빌드와 별개로 언제든 돌릴 수 있다.

    python scripts/validate_data.py
    python scripts/validate_data.py --strict   # warn 도 실패로 처리

종료코드 0=정상, 1=error 등급 위반 있음
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import quality
from core.config import PUBLIC_DATA_DIR, setup_console, sources as load_sources
from core.store import Store

setup_console()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="warn 도 실패로 처리")
    args = ap.parse_args()

    store = Store()
    print("=" * 66)
    print("  데이터 정합성 검사")
    print("=" * 66)

    if store.df.empty:
        print("\n스토어가 비어 있습니다. 먼저 python scripts/update_all.py 를 실행하세요.")
        return 1

    print(f"\n포인트 {len(store.df):,} / 지표 {store.df['metric_id'].nunique()} "
          f"/ 시리즈 {store.df.groupby(['metric_id','entity']).ngroups}")

    issues = []
    issues += quality.check_series(store.df)
    issues += quality.check_source_conflicts(store.df)

    # 필수 메타데이터 누락 검사 — 출처·기준일 없는 값이 있으면 안 된다
    missing_src = store.df["source_name"].isna() | (store.df["source_name"].astype(str).str.strip() == "")
    missing_date = store.df["as_of_date"].isna()
    missing_unit = store.df["unit"].isna() | (store.df["unit"].astype(str).str.strip() == "")
    for label, mask in (("출처", missing_src), ("기준일", missing_date), ("단위", missing_unit)):
        n = int(mask.sum())
        if n:
            issues.append(quality.QualityIssue(
                severity="error", kind="metadata",
                detail=f"{label} 없는 포인트 {n}건 — 화면에 출처 없는 숫자가 나갈 수 있음"))

    # 미래 날짜 (예보 제외)
    today = dt.date.today()
    future = store.df[
        (store.df["as_of_date"].astype(str) > (today + dt.timedelta(days=1)).isoformat())
        & (~store.df["note"].astype(str).str.contains("forecast", case=False, na=False))
        & (store.df["is_estimate"] != True)  # noqa: E712
    ]
    if len(future):
        issues.append(quality.QualityIssue(
            severity="error", kind="date_reversal",
            detail=f"예보가 아닌데 기준일이 미래인 포인트 {len(future)}건"))

    summary = quality.summarize(issues)
    print(f"\n이슈 {summary['total']}건 — " + ", ".join(
        f"{k} {v}" for k, v in sorted(summary["by_severity"].items())) or "없음")
    for kind, n in sorted(summary["by_kind"].items(), key=lambda x: -x[1]):
        print(f"  {kind:<22} {n}")

    errors = [i for i in issues if i.severity == "error"]
    if errors:
        print(f"\n--- error 등급 {len(errors)}건 ---")
        for i in errors[:20]:
            print(f"  [{i.kind}] {i.metric_id} {i.entity} {i.period}: {i.detail[:130]}")

    # 소스별 신선도
    print("\n--- 소스별 최신 기준일 ---")
    src_cfg = load_sources().get("sources", {})
    stale_map = {c.get("label", k): c.get("stale_days") for k, c in src_cfg.items()}
    grp = store.df.groupby("source_name")["as_of_date"].max().sort_values(ascending=False)
    for name, last in grp.items():
        try:
            age = (today - dt.date.fromisoformat(str(last))).days
        except ValueError:
            continue
        limit = next((v for k, v in stale_map.items() if str(name).startswith(str(k)[:10])), None)
        flag = ""
        if limit and age > limit:
            flag = f"  <-- 지연 (기준 {limit}일)"
        print(f"  {str(name)[:38]:<38} {last}  ({age}일 전){flag}")

    out = PUBLIC_DATA_DIR / "quality_report.json"
    out.write_text(json.dumps({
        "checked_at": dt.datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "issues": [i.model_dump() for i in issues[:400]],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n보고서: {out}")

    if errors:
        return 1
    if args.strict and summary["total"]:
        return 1
    print("\n정합성 검사 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
