# -*- coding: utf-8 -*-
"""시계열이 아닌 레코드(공시·PPA계약·파이프라인)의 영속 저장.

시계열은 store.py 가 맡지만 공시 목록 같은 레코드는 별도다.
이것들도 '수집 실패 시 마지막 정상 데이터 유지' 계약을 지켜야 한다.
수집이 비었다고 화면에서 사라지면 안 된다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from .config import PROCESSED_DIR

# 종류 → (파일명, 중복 판단키, 정렬키)
KINDS = {
    "filings": ("filings.json", ("rcept_no",), "date"),
    "ppa_deals": ("ppa_deals.json", ("announced_date", "buyer", "developer", "solar_mw"), "announced_date"),
    "pipeline": ("pipeline.json", ("company_id", "asset_name", "stage"), None),
}
# 오래된 공시는 무한정 쌓지 않는다
MAX_KEEP = {"filings": 800, "ppa_deals": 4000, "pipeline": 2000}


STATUS_FILE = PROCESSED_DIR / "source_status.json"


def _path(kind: str) -> Path:
    return PROCESSED_DIR / KINDS[kind][0]


def save_statuses(rows: list[dict]) -> None:
    """소스 상태를 보관한다. --no-fetch 로 다시 빌드해도 상태가 사라지지 않게."""
    try:
        STATUS_FILE.write_text(
            json.dumps(rows, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    except Exception:
        pass


def load_statuses() -> list[dict]:
    if not STATUS_FILE.exists():
        return []
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def load(kind: str) -> list[dict]:
    p = _path(kind)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _key(rec: dict, fields: tuple[str, ...]) -> tuple:
    return tuple(str(rec.get(f, "")).strip() for f in fields)


def merge(kind: str, incoming: Iterable[dict]) -> list[dict]:
    """기존 레코드와 병합해 저장하고 병합 결과를 돌려준다.

    수집분이 비어 있으면 기존 데이터를 그대로 유지한다 (덮어쓰지 않는다).
    """
    _fname, keyfields, sortkey = KINDS[kind]
    existing = load(kind)
    incoming = [r for r in (incoming or []) if isinstance(r, dict)]

    if not incoming:
        return existing

    by_key: dict[tuple, dict] = {_key(r, keyfields): r for r in existing}
    for r in incoming:
        by_key[_key(r, keyfields)] = r        # 같은 키는 최신 수집분으로 갱신

    merged = list(by_key.values())
    if sortkey:
        merged.sort(key=lambda r: str(r.get(sortkey, "")), reverse=True)
    merged = merged[: MAX_KEEP.get(kind, 2000)]

    try:
        _path(kind).write_text(
            json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    return merged
