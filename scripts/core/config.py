# -*- coding: utf-8 -*-
"""경로·설정·API 키 로딩."""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# scripts/core/config.py → 프로젝트 루트는 2단계 위
ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
HISTORY_DIR = DATA_DIR / "history"
MANUAL_DIR = DATA_DIR / "manual"
PUBLIC_DATA_DIR = ROOT / "public" / "data"
OUT_DIR = ROOT / "out"
CACHE_DIR = DATA_DIR / ".cache"

for _d in (RAW_DIR, PROCESSED_DIR, HISTORY_DIR, MANUAL_DIR, PUBLIC_DATA_DIR, OUT_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def setup_console() -> None:
    """Windows 콘솔이 cp949 라서 한글·em-dash 출력 시 죽는 문제 방지."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


@lru_cache(maxsize=None)
def load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"설정 파일 없음: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def sources() -> dict[str, Any]:
    return load_yaml("sources.yaml")


def companies() -> dict[str, Any]:
    return load_yaml("companies.yaml")


def metrics() -> dict[str, Any]:
    return load_yaml("metrics.yaml")


def signals() -> dict[str, Any]:
    return load_yaml("signals.yaml")


# ------------------------------------------------------------------
# API 키
# ------------------------------------------------------------------
# 우선순위: 환경변수 → .env → (마이그레이션 편의) 전력기기 대시보드의 secrets.json
# 키는 코드·HTML 어디에도 하드코딩하지 않는다.
_ENV_CACHE: dict[str, str] | None = None

# 전력기기 프로젝트의 secrets.json 을 그대로 재사용한다.
# 두 대시보드가 키를 공유하므로 사용자가 파일 하나만 관리하면 된다.
# (.env 를 만들면 그쪽이 우선한다)
_LEGACY_KEY_MAP = {
    "DART_API_KEY": "DART_KEY",
    "FRED_API_KEY": "FRED_KEY",
    "DATA_GO_KR_SERVICE_KEY": "CUSTOMS_KEY",
    "EIA_API_KEY": "EIA_KEY",
    "CENSUS_API_KEY": "CENSUS_KEY",
    "ECOS_API_KEY": "ECOS_KEY",
}


def _load_dotenv() -> dict[str, str]:
    global _ENV_CACHE
    if _ENV_CACHE is not None:
        return _ENV_CACHE
    out: dict[str, str] = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    _ENV_CACHE = out
    return out


def _load_legacy_secrets() -> dict[str, str]:
    """이전 전력기기 프로젝트의 secrets.json 재사용 (있을 때만)."""
    import json
    for cand in (
        ROOT.parent / "전력기기 대쉬보드" / "secrets.json",
        ROOT / "secrets.json",
    ):
        try:
            if cand.exists():
                return json.loads(cand.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


def get_key(name: str) -> str:
    """API 키 조회. 없으면 빈 문자열 (예외를 던지지 않는다)."""
    v = os.environ.get(name)
    if v and v.strip():
        return v.strip()
    v = _load_dotenv().get(name)
    if v and v.strip():
        return v.strip()
    legacy_name = _LEGACY_KEY_MAP.get(name)
    if legacy_name:
        v = _load_legacy_secrets().get(legacy_name)
        if v and v.strip():
            return v.strip()
    return ""


def has_keys(names: list[str]) -> bool:
    return all(get_key(n) for n in names)


def missing_keys(names: list[str]) -> list[str]:
    return [n for n in names if not get_key(n)]
