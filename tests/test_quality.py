# -*- coding: utf-8 -*-
"""품질검사 테스트 — 오탐과 미탐을 모두 막는다."""
import datetime as dt

import pandas as pd

from core import quality
from core.model import DataPoint


def mk(metric_id="module_price_us_ddp", value=0.31, unit="USD/W",
       period="2026-07-22", as_of=None, entity="USA", **kw):
    return DataPoint(
        metric_id=metric_id, entity=entity, value=value, unit=unit, period=period,
        as_of_date=as_of or dt.date(2026, 7, 22),
        fetched_at=dt.datetime(2026, 7, 26), source_name=kw.pop("source", "테스트"),
        source_tier=kw.pop("tier", 4), frequency=kw.pop("freq", "weekly"), **kw)


class TestPointChecks:
    def test_미래날짜_드롭(self):
        future = dt.date.today() + dt.timedelta(days=30)
        kept, issues = quality.check_points([mk(as_of=future, period=future.isoformat())])
        assert kept == []
        assert any(i.kind == "date_reversal" and i.dropped for i in issues)

    def test_일사량_예보는_미래여도_통과(self):
        future = dt.date.today() + dt.timedelta(days=5)
        p = mk(metric_id="ghi_daily", unit="MJ/m2", entity="seoul", freq="daily",
               as_of=future, period=future.isoformat(), is_estimate=True, note="forecast")
        kept, _ = quality.check_points([p])
        assert len(kept) == 1

    def test_가격에_음수는_드롭(self):
        kept, issues = quality.check_points([mk(value=-0.5)])
        assert kept == []
        assert any(i.kind == "negative" for i in issues)

    def test_프리미엄에_음수는_정상(self):
        """비중국 프리미엄·스프레드는 음수가 될 수 있다."""
        kept, _ = quality.check_points([
            mk(metric_id="nonchina_poly_premium", value=-12.0, unit="%", entity="GLOBAL")])
        assert len(kept) == 1

    def test_영업이익_적자는_정상(self):
        kept, _ = quality.check_points([
            mk(metric_id="op_profit_q", value=-490.0, unit="십억원",
               period="2025Q4", entity="hanwha", freq="quarterly")])
        assert len(kept) == 1

    def test_시리즈내_단위혼재_드롭(self):
        a = mk(period="2026-07-15", unit="USD/W")
        b = mk(period="2026-07-22", unit="RMB/W")
        kept, issues = quality.check_points([a, b])
        assert len(kept) == 1
        assert any(i.kind == "unit" and i.dropped for i in issues)

    def test_동일수집분_중복제거(self):
        a = mk(value=0.30)
        b = mk(value=0.31)          # 같은 point_key
        kept, issues = quality.check_points([a, b])
        assert len(kept) == 1
        assert kept[0].value == 0.31        # 마지막 값 채택
        assert any(i.kind == "duplicate" for i in issues)


def _df(rows):
    return pd.DataFrame(rows)


class TestSeriesChecks:
    def test_급등락_경고(self):
        df = _df([
            dict(metric_id="module_price_us_ddp", entity="USA", period="2026-07-15",
                 value=0.31, unit="USD/W", source_name="t", frequency="weekly",
                 as_of_date="2026-07-15", source_tier=4),
            dict(metric_id="module_price_us_ddp", entity="USA", period="2026-07-22",
                 value=0.62, unit="USD/W", source_name="t", frequency="weekly",
                 as_of_date="2026-07-22", source_tier=4),
        ])
        issues = quality.check_series(df)
        assert any(i.kind == "spike" for i in issues)

    def test_일사량은_급등락_경고를_내지_않는다(self):
        """흐린 날 0.03h → 맑은 날 11.9h 는 날씨지 오류가 아니다."""
        rows = []
        for i, v in enumerate([9.5, 0.03, 11.9, 0.1, 10.2]):
            d = f"2026-07-{15+i:02d}"
            rows.append(dict(metric_id="sunshine_hours", entity="chungnam", period=d,
                             value=v, unit="h", source_name="Open-Meteo",
                             frequency="daily", as_of_date=d, source_tier=2))
        issues = quality.check_series(_df(rows))
        assert [i for i in issues if i.kind in ("spike", "unit")] == []

    def test_거래량도_급등락_예외(self):
        rows = []
        for i, v in enumerate([150000, 900000, 120000]):
            d = f"2026-07-{20+i:02d}"
            rows.append(dict(metric_id="trade_volume", entity="oci", period=d,
                             value=v, unit="주", source_name="네이버", frequency="business_daily",
                             as_of_date=d, source_tier=4))
        assert [i for i in quality.check_series(_df(rows)) if i.kind == "spike"] == []

    def test_단위오류급_배수는_잡는다(self):
        df = _df([
            dict(metric_id="smp_land", entity="KOR", period="2026-07-20", value=120.0,
                 unit="원/kWh", source_name="t", frequency="daily",
                 as_of_date="2026-07-20", source_tier=1),
            dict(metric_id="smp_land", entity="KOR", period="2026-07-21", value=120000.0,
                 unit="원/kWh", source_name="t", frequency="daily",
                 as_of_date="2026-07-21", source_tier=1),
        ])
        issues = quality.check_series(df)
        assert any(i.kind == "unit" and i.severity == "error" for i in issues)


class TestConflicts:
    def test_출처충돌_기록하되_합성하지_않는다(self):
        df = _df([
            dict(metric_id="smp_land", entity="KOR", period="2026-07-22", value=120.0,
                 unit="원/kWh", source_name="A", frequency="daily",
                 as_of_date="2026-07-22", source_tier=1),
            dict(metric_id="smp_land", entity="KOR", period="2026-07-22", value=140.0,
                 unit="원/kWh", source_name="B", frequency="daily",
                 as_of_date="2026-07-22", source_tier=4),
        ])
        issues = quality.check_source_conflicts(df)
        assert len(issues) == 1
        assert issues[0].kind == "conflict"
        assert issues[0].source_name == "A"      # tier 가 높은(숫자 작은) 쪽이 메인

    def test_기상모델_괴리는_참고등급(self):
        df = _df([
            dict(metric_id="ghi_daily", entity="seoul", period="2026-05-27", value=5.87,
                 unit="MJ/m2", source_name="NASA POWER", frequency="daily",
                 as_of_date="2026-05-27", source_tier=1),
            dict(metric_id="ghi_daily", entity="seoul", period="2026-05-27", value=2.08,
                 unit="MJ/m2", source_name="Open-Meteo", frequency="daily",
                 as_of_date="2026-05-27", source_tier=2),
        ])
        issues = quality.check_source_conflicts(df)
        assert all(i.severity == "info" for i in issues)
