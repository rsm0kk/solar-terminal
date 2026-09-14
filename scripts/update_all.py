# -*- coding: utf-8 -*-
"""태양광 대시보드 — 수집·정규화·검증·빌드 전체 파이프라인.

    python scripts/update_all.py
    python scripts/update_all.py --as-of 2026-07-26
    python scripts/update_all.py --only owid_solar,ember_monthly
    python scripts/update_all.py --no-render        # JSON 까지만
    python scripts/update_all.py --traceback        # 실패 시 스택 출력

부분 실패를 허용한다. 소스 하나가 죽어도 나머지는 수집되고,
실패한 소스는 마지막 정상 데이터를 유지한 채 상태만 error/stale 로 바뀐다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

# scripts/ 를 임포트 경로에 넣는다 (core, adapters)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import dashboard, derive, quality, records, signals as signal_engine
from core.brief import BriefBuilder
from core.config import (OUT_DIR, PUBLIC_DATA_DIR, metrics as load_metrics,
                         setup_console)
from core.runner import run_collection
from core.store import Store

setup_console()


def log(msg: str = "") -> None:
    print(msg, flush=True)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str),
                    encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="태양광 대시보드 데이터 갱신 및 빌드")
    ap.add_argument("--as-of", type=str, default=None, help="기준일 YYYY-MM-DD")
    ap.add_argument("--only", type=str, default=None, help="특정 소스만 (쉼표 구분)")
    ap.add_argument("--no-render", action="store_true", help="HTML 빌드 생략")
    ap.add_argument("--no-fetch", action="store_true", help="수집 생략, 저장된 데이터로 빌드만")
    ap.add_argument("--traceback", action="store_true", help="실패 시 스택 출력")
    args = ap.parse_args()

    as_of = dt.date.fromisoformat(args.as_of) if args.as_of else dt.date.today()
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    t0 = time.time()

    log("=" * 70)
    log(f"  SOLAR ANALYST TERMINAL — 데이터 갱신  (기준일 {as_of})")
    log("=" * 70)

    store = Store()
    log(f"\n[1/6] 저장된 데이터 로드: {len(store.df):,}포인트")

    # ---------------- 수집 ----------------
    if args.no_fetch:
        log("\n[2/6] 수집 생략 (--no-fetch)")
        from core.runner import CollectResult
        result = CollectResult()
    else:
        log("\n[2/6] 소스 수집")
        result = run_collection(store, only=only, as_of=as_of)

    # 소스 상태도 보관한다. --no-fetch 로 다시 빌드했다고 해서
    # '데이터 상태' 탭이 텅 비면 화면이 실제 상황을 잘못 알려주게 된다.
    if result.statuses:
        records.save_statuses([s.model_dump() for s in result.statuses])
    else:
        from core.model import SourceStatus
        restored = []
        for row in records.load_statuses():
            try:
                restored.append(SourceStatus(**row))
            except Exception:
                continue
        result.statuses = restored
        if restored:
            log(f"  직전 수집 상태 복원: {len(restored)}개 소스")

    # 공시·PPA·파이프라인은 시계열이 아니라 별도 저장한다.
    # 수집이 비어도(--no-fetch, DART 실패) 기존 데이터가 사라지면 안 된다.
    result.filings = records.merge("filings", result.filings)
    result.ppa_deals = records.merge("ppa_deals", result.ppa_deals)
    result.pipeline = records.merge("pipeline", result.pipeline)
    log(f"  레코드 유지: 공시 {len(result.filings)} / PPA {len(result.ppa_deals)} / 파이프라인 {len(result.pipeline)}")

    # ---------------- 파생지표 ----------------
    log("\n[3/6] 파생지표 계산")
    rec_weight = float((load_metrics() or {}).get("rec_weight_default", 1.0))
    derived = derive.compute(store, rec_weight=rec_weight)
    if derived:
        kept, issues = quality.check_points(derived)
        result.issues.extend(issues)
        stats = store.merge(kept)
        log(f"  파생 {len(kept)}점 (신규 {stats['inserted']} / 수정 {stats['revised']})")
    else:
        log("  계산 가능한 파생지표 없음 (입력 지표 미수집)")

    # ---------------- 품질검사 ----------------
    log("\n[4/6] 품질검사")
    result.issues.extend(store.issues)
    result.issues.extend(quality.check_series(store.df))
    result.issues.extend(quality.check_source_conflicts(store.df))
    summary = quality.summarize(result.issues)
    log(f"  이슈 {summary['total']}건 "
        f"(error {summary['by_severity'].get('error', 0)} / "
        f"warn {summary['by_severity'].get('warn', 0)} / "
        f"info {summary['by_severity'].get('info', 0)})")
    for kind, n in sorted(summary["by_kind"].items(), key=lambda x: -x[1])[:6]:
        log(f"    - {kind}: {n}")

    store.save()
    log(f"  스토어 저장: {len(store.df):,}포인트")

    # ---------------- 시그널·브리핑 ----------------
    log("\n[5/6] 시그널 엔진 · 아침 브리핑")
    sig = signal_engine.evaluate(store, ref_date=as_of)
    used = len(sig.get("signals", {}))
    log(f"  평가된 시그널 {used}개 / 제외 {len(sig.get('excluded', {}))}개")
    for cid, c in (sig.get("companies") or {}).items():
        log(f"    {cid:<8} {c['total']:+6.2f} ({c['verdict']}) "
            f"전주대비 {c['delta']:+.2f} · 지표 {c['signals_used']}개")

    brief = BriefBuilder(store, sig, result.statuses).build(result.filings, result.ppa_deals)
    for line in brief["headline"]:
        log(f"  · {line}")

    # ---------------- 빌드 ----------------
    log("\n[6/6] JSON · HTML 빌드")
    payload = dashboard.build(
        store, result.statuses, result.issues, sig, brief,
        result.filings, result.ppa_deals, result.pipeline, rec_weight=rec_weight,
    )

    write_json(PUBLIC_DATA_DIR / "dashboard.json", payload)
    write_json(PUBLIC_DATA_DIR / "status.json", {
        "as_of": as_of.isoformat(),
        "generated_at": payload["meta"]["generated_at"],
        "summary": payload["meta"]["source_summary"],
        "sources": payload["status"],
    })
    write_json(PUBLIC_DATA_DIR / "quality_report.json", payload["quality"])
    write_json(PUBLIC_DATA_DIR / "morning_brief.json", brief)

    size = (PUBLIC_DATA_DIR / "dashboard.json").stat().st_size
    log(f"  dashboard.json  {size/1024:,.0f} KB / 시리즈 {payload['meta']['series_count']}개")

    if not args.no_render:
        try:
            from core.render import render_html
            out_path = render_html(payload)
            log(f"  HTML  {out_path}  ({out_path.stat().st_size/1024:,.0f} KB)")
        except Exception as e:
            log(f"  [FAIL] HTML 빌드 실패: {type(e).__name__}: {e}")
            if args.traceback:
                import traceback
                traceback.print_exc()

    # ---------------- 요약 ----------------
    s = payload["meta"]["source_summary"]
    log("\n" + "=" * 70)
    log(f"  완료 {time.time()-t0:.1f}s — 정상 {s['ok']} / 지연 {s['stale']} / "
        f"오류 {s['error']} / 키없음 {s['no_key']} / 미입력 {s['manual_empty']}")
    log("=" * 70)

    # 핵심 소스가 전부 죽으면 CI 실패로 알린다
    critical = {"owid_solar", "ember_monthly", "naver_stock", "dart"}
    dead = {st.source_id for st in result.statuses
            if st.state == "error" and st.source_id in critical}
    if dead and not args.no_fetch:
        log(f"\n[경고] 핵심 소스 실패: {', '.join(sorted(dead))}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
