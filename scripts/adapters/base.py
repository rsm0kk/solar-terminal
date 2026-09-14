# -*- coding: utf-8 -*-
"""어댑터 기반 클래스.

각 소스는 독립 어댑터다. 한 어댑터가 죽어도 나머지 수집은 계속된다.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from core.model import DataPoint


class Adapter:
    """수집기 인터페이스.

    구현체는 collect() 만 채우면 된다. 예외를 던지면 러너가 잡아서
    해당 소스만 error 상태로 기록하고 다음 소스로 넘어간다.
    """

    #: sources.yaml 의 adapter 필드와 매칭되는 이름
    name: str = ""

    def __init__(self, source_id: str, cfg: dict[str, Any]):
        self.source_id = source_id
        self.cfg = cfg
        self.label: str = cfg.get("label", source_id)
        self.tier: int = int(cfg.get("tier", 4))
        self.freq: str = cfg.get("freq", "daily")
        self.url: str = cfg.get("url", "")
        self._fetched_at = dt.datetime.now()
        #: 어댑터가 스키마 변화 등을 감지하면 여기 남긴다 (품질보고서로 나감)
        self.warnings: list[str] = []

    # ------------------------------------------------------------------
    def collect(self) -> list[DataPoint]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    def point(
        self,
        metric_id: str,
        value: Optional[float],
        unit: str,
        period: str,
        as_of: dt.date,
        *,
        entity: str = "GLOBAL",
        currency: Optional[str] = None,
        published_at: Optional[dt.date] = None,
        source_name: Optional[str] = None,
        source_url: Optional[str] = None,
        tier: Optional[int] = None,
        frequency: Optional[str] = None,
        is_estimate: bool = False,
        is_manual: bool = False,
        confidence: float = 1.0,
        note: str = "",
    ) -> DataPoint:
        """소스 기본값을 채워 DataPoint 를 만든다."""
        return DataPoint(
            metric_id=metric_id,
            entity=entity,
            value=value,
            unit=unit,
            currency=currency,
            period=period,
            as_of_date=as_of,
            published_at=published_at,
            fetched_at=self._fetched_at,
            source_name=source_name or self.label,
            source_url=source_url or self.url,
            source_tier=tier if tier is not None else self.tier,
            frequency=frequency or self.freq,
            is_estimate=is_estimate,
            is_manual=is_manual,
            confidence=confidence,
            note=note,
        )

    # ------------------------------------------------------------------
    def expect_columns(self, got: list[str], required: list[str], where: str) -> None:
        """스키마 변화 감지.

        공개 CSV·HTML 표의 구조가 바뀌면 조용히 틀린 값을 넣는 대신 경고를 남긴다.
        """
        missing = [c for c in required if c not in got]
        if missing:
            msg = f"{where}: 필수 필드 누락 {missing} (구조 변경 의심). 실제 필드: {got[:12]}"
            self.warnings.append(msg)
            raise ValueError(msg)

    def expect_min_rows(self, n: int, minimum: int, where: str) -> None:
        if n < minimum:
            msg = f"{where}: 행 수 {n} < 최소 기대치 {minimum} (구조 변경·차단 의심)"
            self.warnings.append(msg)
            raise ValueError(msg)


# 국내 주요 태양광 권역 (일사량·발전여건용)
KR_REGIONS = [
    ("seoul", "서울", 37.5665, 126.9780),
    ("gyeonggi", "경기", 37.4138, 127.5183),
    ("chungnam", "충남", 36.5184, 126.8000),
    ("jeonbuk", "전북", 35.7175, 127.1530),
    ("jeonnam", "전남", 34.8679, 126.9910),
    ("gyeongbuk", "경북", 36.4919, 128.8889),
    ("jeju", "제주", 33.4996, 126.5312),
]

# 글로벌 비교 대상국
COUNTRIES = {
    "KOR": "한국",
    "USA": "미국",
    "CHN": "중국",
    "IND": "인도",
    "DEU": "독일",
    "JPN": "일본",
}

# OWID 는 ISO3 대신 국가명을 쓰는 데이터셋이 있어 양방향 매핑을 둔다
OWID_NAMES = {
    "South Korea": "KOR",
    "United States": "USA",
    "China": "CHN",
    "India": "IND",
    "Germany": "DEU",
    "Japan": "JPN",
    "European Union (27)": "EU27",
}
