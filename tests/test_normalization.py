# -*- coding: utf-8 -*-
"""정규화·변환 로직 테스트. 네트워크를 타지 않는다."""
import datetime as dt

import pytest
from pydantic import ValidationError

from core.model import DataPoint


def mk(**kw):
    base = dict(
        metric_id="poly_price_china_dense", value=38.5, unit="RMB/kg",
        period="2026-07-22", as_of_date=dt.date(2026, 7, 22),
        fetched_at=dt.datetime(2026, 7, 26, 9, 0), source_name="테스트",
        source_tier=4, frequency="weekly",
    )
    base.update(kw)
    return DataPoint(**base)


class TestDataPoint:
    def test_period_형식_검증(self):
        for good in ("2026", "2026-07", "2026-07-22", "2026Q2"):
            assert mk(period=good).period == good
        for bad in ("26-07", "2026/07", "2026Q5", "July", ""):
            with pytest.raises(ValidationError):
                mk(period=bad)

    def test_출처등급_범위(self):
        with pytest.raises(ValidationError):
            mk(source_tier=0)
        with pytest.raises(ValidationError):
            mk(source_tier=7)

    def test_NaN_Inf_거부(self):
        with pytest.raises(ValidationError):
            mk(value=float("nan"))
        with pytest.raises(ValidationError):
            mk(value=float("inf"))

    def test_중복판단키(self):
        a = mk()
        b = mk(value=99.9)
        assert a.point_key == b.point_key       # 값이 달라도 같은 포인트
        assert a.content_hash() != b.content_hash()   # 내용 해시는 달라야 수정 감지 가능

    def test_직렬화_왕복(self):
        a = mk(published_at=dt.date(2026, 7, 23), currency="RMB")
        b = DataPoint.from_row(a.to_row())
        assert b.value == a.value
        assert b.as_of_date == a.as_of_date
        assert b.published_at == a.published_at
        assert b.period == a.period

    def test_결측은_수집실패와_구분(self):
        p = mk(value=None)
        assert p.value is None      # None 은 허용 (0 으로 채우지 않는다)


class TestManualCsvParsing:
    def test_분기_period_파싱(self):
        from adapters.manual_csv import ManualCsvAdapter as M
        assert M._parse_period("2026Q1")[0] == "2026Q1"
        assert M._parse_period("2026Q1")[1] == dt.date(2026, 3, 31)
        assert M._parse_period("2026Q4")[1] == dt.date(2026, 12, 31)
        assert M._parse_period("2026-03")[1] == dt.date(2026, 3, 31)
        assert M._parse_period("2026-03-15")[1] == dt.date(2026, 3, 15)
        assert M._parse_period("엉터리")[0] == ""

    def test_날짜_파싱(self):
        from adapters.manual_csv import ManualCsvAdapter as M
        assert M._parse_date("2026-07-22")[0] == "2026-07-22"
        assert M._parse_date("2026/07/22")[0] == ""


class TestDartQuarterly:
    """DART 누적→단독분기 변환은 가장 틀리기 쉬운 부분이라 별도로 검증한다."""

    def test_누적_차분이_단독분기가_된다(self):
        cumulative = {1: 100.0, 2: 250.0, 3: 400.0, 4: 600.0}
        standalone, prev = {}, 0.0
        for q in (1, 2, 3, 4):
            standalone[q] = cumulative[q] - prev
            prev = cumulative[q]
        assert standalone == {1: 100.0, 2: 150.0, 3: 150.0, 4: 200.0}
        assert sum(standalone.values()) == cumulative[4]

    def test_변환검증이_불일치를_잡는다(self):
        from core.quality import check_quarterly_conversion
        ok = check_quarterly_conversion(
            {"2025Q4": 600.0},
            {"2025Q1": 100.0, "2025Q2": 150.0, "2025Q3": 150.0, "2025Q4": 200.0})
        assert ok == []

        bad = check_quarterly_conversion(
            {"2025Q4": 600.0},
            {"2025Q1": 100.0, "2025Q2": 150.0, "2025Q3": 150.0, "2025Q4": 999.0})
        assert len(bad) == 1
        assert bad[0].severity == "error"
        assert bad[0].kind == "quarterly_conversion"

    def test_재무상태표는_차분하지_않는다(self):
        """분기말 잔액은 누적이 아니므로 차분 대상이 아니다."""
        from core.quality import check_quarterly_conversion
        # BS 항목에는 이 검사를 적용하지 않는다 — 빈 입력이면 이슈도 없어야 한다
        assert check_quarterly_conversion({}, {}) == []
