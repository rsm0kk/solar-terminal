# -*- coding: utf-8 -*-
"""어댑터 테스트. fixtures 로 오프라인 검증한다 (네트워크 미사용)."""
import datetime as dt
import json
from pathlib import Path

import pytest

from adapters import available, get_adapter_class
from adapters.base import Adapter
from core.store import Store

FIX = Path(__file__).parent / "fixtures"


class TestRegistry:
    def test_모든_소스의_어댑터가_존재한다(self):
        from core.config import sources
        missing = []
        for sid, cfg in sources()["sources"].items():
            name = cfg.get("adapter")
            if name not in available():
                missing.append(f"{sid} → {name}")
        assert not missing, f"레지스트리에 없는 어댑터: {missing}"

    def test_어댑터_클래스_로드(self):
        for name in available():
            cls = get_adapter_class(name)
            assert cls is not None, f"{name} 로드 실패"
            assert issubclass(cls, Adapter)


class TestSchemaGuards:
    """공개 CSV·HTML 구조가 바뀌면 조용히 틀린 값을 넣지 말고 실패해야 한다."""

    def _ad(self):
        return Adapter("t", {"label": "테스트", "tier": 4, "freq": "weekly"})

    def test_필수컬럼_누락시_실패(self):
        ad = self._ad()
        with pytest.raises(ValueError, match="필수 필드 누락"):
            ad.expect_columns(["a", "b"], ["a", "b", "c"], "테스트소스")
        assert ad.warnings

    def test_행수_부족시_실패(self):
        ad = self._ad()
        with pytest.raises(ValueError, match="행 수"):
            ad.expect_min_rows(3, 100, "테스트소스")

    def test_정상이면_통과(self):
        ad = self._ad()
        ad.expect_columns(["a", "b", "c"], ["a", "c"], "테스트소스")
        ad.expect_min_rows(500, 100, "테스트소스")
        assert ad.warnings == []


class TestNaverParsing:
    def test_네이버_시세_리터럴_파싱(self):
        """응답이 JSON 이 아니라 파이썬/JS 리터럴이라 별도 파싱이 필요하다."""
        import ast
        raw = """
 [['날짜', '시가', '고가', '저가', '종가', '거래량', '외국인소진율'],

	["20260701", 231000, 245500, 224500, 240000, 258991, 18.95],
	["20260702", 245000, 252000, 215500, 219000, 255663, 18.46]]
"""
        cleaned = raw.strip().replace("\n", "").replace("\t", "").replace("\r", "")
        data = ast.literal_eval(cleaned)
        assert data[0][0] == "날짜"
        assert len(data) == 3
        assert data[1][4] == 240000


class TestManualCsvTemplates:
    """SAMPLE 행은 절대 대시보드에 들어가면 안 된다."""

    def test_템플릿_5종_존재(self):
        from core.config import MANUAL_DIR
        expected = [
            "solar_supply_chain_prices.csv", "company_kpi_manual.csv",
            "manual_estimates.csv", "ppa_deals_manual.csv",
            "company_capacity_pipeline.csv",
        ]
        for f in expected:
            assert (MANUAL_DIR / f).exists(), f"{f} 없음"

    def test_SAMPLE_행은_제외된다(self):
        from core.config import sources
        cfg = sources()["sources"]["supply_chain_prices"]
        ad = get_adapter_class("manual_csv")("supply_chain_prices", cfg)
        points = ad.collect()
        assert points == [], "SAMPLE 행이 데이터로 들어갔다"
        assert ad.is_empty

    def test_PPA_템플릿도_SAMPLE_제외(self):
        from core.config import sources
        cfg = sources()["sources"]["ppa_deals"]
        ad = get_adapter_class("manual_csv")("ppa_deals", cfg)
        ad.collect()
        assert ad.records == [], "SAMPLE 계약이 레코드로 들어갔다"


class TestStoreContract:
    """스토어의 두 가지 핵심 계약."""

    def _p(self, value, period="2026-07-22", source="A"):
        from core.model import DataPoint
        return DataPoint(
            metric_id="smp_land", entity="KOR", value=value, unit="원/kWh",
            period=period, as_of_date=dt.date(2026, 7, 22),
            fetched_at=dt.datetime(2026, 7, 26), source_name=source,
            source_tier=1, frequency="daily")

    def test_결측이_정상값을_덮어쓰지_않는다(self, tmp_path):
        s = Store(tmp_path / "t.parquet")
        s.merge([self._p(120.0)])
        s.merge([self._p(None)])
        assert s.latest("smp_land", "KOR")["value"] == 120.0

    def test_값이_바뀌면_수정으로_감지(self, tmp_path):
        s = Store(tmp_path / "t.parquet")
        s.merge([self._p(120.0)])
        stats = s.merge([self._p(125.0)])
        assert stats["revised"] == 1
        assert any(i.kind == "revision" for i in s.issues)
        assert s.latest("smp_land", "KOR")["value"] == 125.0

    def test_같은값_재수집은_수정이_아니다(self, tmp_path):
        s = Store(tmp_path / "t.parquet")
        s.merge([self._p(120.0)])
        stats = s.merge([self._p(120.0)])
        assert stats["revised"] == 0
        assert stats["unchanged"] == 1

    def test_출처가_여러개면_tier_높은쪽_채택(self, tmp_path):
        from core.model import DataPoint
        s = Store(tmp_path / "t.parquet")
        low = DataPoint(metric_id="smp_land", entity="KOR", value=140.0, unit="원/kWh",
                        period="2026-07-22", as_of_date=dt.date(2026, 7, 22),
                        fetched_at=dt.datetime(2026, 7, 26), source_name="B",
                        source_tier=5, frequency="daily")
        s.merge([self._p(120.0, source="A"), low])
        assert s.latest("smp_land", "KOR")["value"] == 120.0


class TestRecordsPersistence:
    def test_빈수집은_기존레코드를_지우지_않는다(self, tmp_path, monkeypatch):
        from core import records
        monkeypatch.setattr(records, "PROCESSED_DIR", tmp_path)
        monkeypatch.setattr(records, "_path", lambda kind: tmp_path / records.KINDS[kind][0])

        first = records.merge("filings", [
            {"rcept_no": "1", "date": "20260701", "title": "A"},
            {"rcept_no": "2", "date": "20260702", "title": "B"},
        ])
        assert len(first) == 2

        again = records.merge("filings", [])          # 수집 실패 시나리오
        assert len(again) == 2, "빈 수집이 기존 공시를 지웠다"

        updated = records.merge("filings", [{"rcept_no": "2", "date": "20260702", "title": "B수정"}])
        assert len(updated) == 2
        assert [f for f in updated if f["rcept_no"] == "2"][0]["title"] == "B수정"
