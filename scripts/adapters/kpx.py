# -*- coding: utf-8 -*-
"""전력거래소(KPX) / 공공데이터포털 — SMP·REC·태양광 발전량.

필요: DATA_GO_KR_SERVICE_KEY

2026-07-26 확인 사항 (중요):
  보유 중인 data.go.kr 서비스키는 유효하다 (관세청 API 는 200 정상).
  그런데 KPX API 는 500 을 돌려준다 → 키 문제가 아니라 **해당 API 개별
  '활용신청' 미승인** 상태다. data.go.kr 에서 아래 API 에 활용신청하면
  같은 키로 동작한다. 새 키 발급은 필요 없다.

data.go.kr 은 API 마다 엔드포인트 이름이 제각각이라 후보를 순서대로 시도하고
성공한 것만 채택한다. 실패해도 다른 소스 수집은 계속된다.
"""
from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET
from typing import Any, Optional

from core.config import get_key
from core.http import FetchError, fetch_text
from core.model import DataPoint

from .base import Adapter

CACHE_TTL = 3 * 3600
DAYS_BACK = 120

# (설명, URL, 파라미터빌더, 파서)  — 앞에서부터 시도한다
SMP_CANDIDATES = [
    ("육지 일별 SMP", "https://apis.data.go.kr/B552115/SmpLandPrice/getSmpLandPrice"),
    ("일별 SMP", "https://apis.data.go.kr/B552115/SmpMaxMlt/getSmpMaxMlt"),
    ("시간대별 SMP", "https://apis.data.go.kr/B552115/SmpHm/getSmpHm"),
]
REC_CANDIDATES = [
    ("REC 현물시장", "https://apis.data.go.kr/B552115/RecSpotPrice/getRecSpotPrice"),
    ("REC 거래정보", "https://apis.data.go.kr/B552115/RecTradeInfo/getRecTradeInfo"),
]


class KpxAdapter(Adapter):
    name = "kpx"

    def collect(self) -> list[DataPoint]:
        key = get_key("DATA_GO_KR_SERVICE_KEY")
        if not key:
            raise FetchError("DATA_GO_KR_SERVICE_KEY 미설정")

        points: list[DataPoint] = []
        tried: list[str] = []

        smp = self._try_group(key, SMP_CANDIDATES, self._parse_smp, tried)
        points.extend(smp)
        rec = self._try_group(key, REC_CANDIDATES, self._parse_rec, tried)
        points.extend(rec)

        if not points:
            raise FetchError(
                "KPX: 모든 엔드포인트 실패. data.go.kr 에서 해당 API '활용신청'이 "
                "승인됐는지 확인하세요 (키는 유효함). 시도: " + " | ".join(tried)
            )
        if not smp:
            self.warnings.append("SMP 미수집 — 활용신청 확인 필요")
        if not rec:
            self.warnings.append("REC 미수집 — 활용신청 확인 필요")
        return points

    # ------------------------------------------------------------------
    def _try_group(self, key: str, candidates, parser, tried: list[str]) -> list[DataPoint]:
        end = dt.date.today()
        start = end - dt.timedelta(days=DAYS_BACK)
        for label, url in candidates:
            for params in self._param_variants(key, start, end):
                try:
                    text = fetch_text(url, params=params, cache_ttl=CACHE_TTL, retries=1)
                except Exception as e:
                    tried.append(f"{label}:{type(e).__name__}")
                    continue
                try:
                    pts = parser(text, label, url)
                except Exception as e:
                    tried.append(f"{label}:파싱실패({str(e)[:40]})")
                    continue
                if pts:
                    return pts
                tried.append(f"{label}:빈응답")
        return []

    @staticmethod
    def _param_variants(key: str, start: dt.date, end: dt.date) -> list[dict[str, Any]]:
        """data.go.kr 은 API 마다 파라미터명이 달라 흔한 조합을 순서대로 시도한다."""
        return [
            {"serviceKey": key, "pageNo": 1, "numOfRows": 500, "dataType": "XML",
             "strDate": start.strftime("%Y%m%d"), "endDate": end.strftime("%Y%m%d")},
            {"serviceKey": key, "pageNo": 1, "numOfRows": 500, "dataType": "XML",
             "baseDate": end.strftime("%Y%m%d")},
            {"serviceKey": key, "pageNo": 1, "numOfRows": 500, "dataType": "XML"},
        ]

    # ------------------------------------------------------------------
    @staticmethod
    def _items(text: str) -> list[dict[str, str]]:
        root = ET.fromstring(text)
        code = root.findtext(".//resultCode")
        if code not in (None, "00", "0"):
            raise ValueError(f"resultCode={code} {root.findtext('.//resultMsg')}")
        out = []
        for item in root.iter("item"):
            out.append({child.tag: (child.text or "").strip() for child in item})
        return out

    @staticmethod
    def _first(d: dict[str, str], *names: str) -> Optional[str]:
        for n in names:
            if d.get(n):
                return d[n]
        return None

    @staticmethod
    def _to_date(s: str) -> Optional[dt.date]:
        s = (s or "").strip().replace("-", "").replace("/", "")[:8]
        if len(s) != 8 or not s.isdigit():
            return None
        try:
            return dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    def _parse_smp(self, text: str, label: str, url: str) -> list[DataPoint]:
        pts: list[DataPoint] = []
        for it in self._items(text):
            d = self._to_date(self._first(it, "tradeDay", "baseDate", "tradeDd", "basDt") or "")
            if not d:
                continue
            for field, metric, region in (
                ("smpLand", "smp_land", "육지"),
                ("smpJeju", "smp_jeju", "제주"),
                ("smp", "smp_land", "육지"),
            ):
                raw = it.get(field)
                if not raw:
                    continue
                try:
                    v = float(raw.replace(",", ""))
                except ValueError:
                    continue
                if v <= 0:
                    continue
                pts.append(self.point(
                    metric_id=metric, value=v, unit="원/kWh", currency="KRW",
                    period=d.isoformat(), as_of=d, entity="KOR",
                    frequency="daily", confidence=0.98,
                    source_name=f"전력거래소 · {label}", source_url=url,
                ))
        return pts

    def _parse_rec(self, text: str, label: str, url: str) -> list[DataPoint]:
        pts: list[DataPoint] = []
        for it in self._items(text):
            d = self._to_date(self._first(it, "tradeDay", "baseDate", "tradeDd", "basDt") or "")
            if not d:
                continue
            avg = self._first(it, "avgPrice", "avrgPc", "closPrice", "price")
            vol = self._first(it, "tradeQty", "trqu", "volume")
            if avg:
                try:
                    v = float(avg.replace(",", ""))
                    if v > 0:
                        pts.append(self.point(
                            metric_id="rec_spot_price", value=v, unit="원/REC", currency="KRW",
                            period=d.isoformat(), as_of=d, entity="KOR",
                            frequency="daily", confidence=0.95,
                            source_name=f"전력거래소 · {label}", source_url=url,
                        ))
                except ValueError:
                    pass
            if vol:
                try:
                    v = float(vol.replace(",", ""))
                    if v >= 0:
                        pts.append(self.point(
                            metric_id="rec_spot_volume", value=v, unit="REC",
                            period=d.isoformat(), as_of=d, entity="KOR",
                            frequency="daily", confidence=0.95,
                            source_name=f"전력거래소 · {label}", source_url=url,
                        ))
                except ValueError:
                    pass
        return pts
