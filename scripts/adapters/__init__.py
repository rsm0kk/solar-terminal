# -*- coding: utf-8 -*-
"""어댑터 레지스트리.

sources.yaml 의 `adapter:` 값 → 구현 클래스 매핑.
임포트 자체가 실패해도(선택적 의존성 등) 전체가 죽지 않게 지연 로딩한다.
"""
from __future__ import annotations

import importlib
from typing import Optional, Type

from .base import Adapter

# adapter 이름 → (모듈, 클래스)
_REGISTRY: dict[str, tuple[str, str]] = {
    "owid": (".owid", "OwidAdapter"),
    "ember": (".ember", "EmberAdapter"),
    "openmeteo": (".openmeteo", "OpenMeteoAdapter"),
    "nasa_power": (".nasa_power", "NasaPowerAdapter"),
    "naver_stock": (".naver_stock", "NaverStockAdapter"),
    "dart": (".dart", "DartAdapter"),
    "fred": (".fred", "FredAdapter"),
    "eia": (".eia", "EiaAdapter"),
    "kpx": (".kpx", "KpxAdapter"),
    "manual_csv": (".manual_csv", "ManualCsvAdapter"),
}


def get_adapter_class(name: str) -> Optional[Type[Adapter]]:
    entry = _REGISTRY.get(name)
    if not entry:
        return None
    module_name, class_name = entry
    try:
        mod = importlib.import_module(module_name, package=__name__)
        return getattr(mod, class_name)
    except Exception as e:  # noqa: BLE001 — 어댑터 하나의 문제로 전체를 막지 않는다
        print(f"  [주의] 어댑터 로드 실패 {name}: {type(e).__name__}: {e}")
        return None


def available() -> list[str]:
    return sorted(_REGISTRY)


__all__ = ["Adapter", "get_adapter_class", "available"]
