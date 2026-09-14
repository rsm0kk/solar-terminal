# -*- coding: utf-8 -*-
"""파생지표 계산.

원칙:
  - 입력이 없으면 파생값을 만들지 않는다 (0 이나 추정으로 채우지 않는다).
  - 통화를 환산하면 환산에 쓴 환율의 '기준일'을 note 에 반드시 남긴다.
  - 파생값은 is_estimate=True 로 표시해 원 관측치와 구분한다.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import pandas as pd

from .config import PROCESSED_DIR, metrics as load_metrics
from .model import DataPoint
from .store import Store

DERIVED_SOURCE = "파생계산"
MAX_FX_GAP_DAYS = 7      # 이보다 오래된 환율로는 환산하지 않는다


def _fx_lookup(store: Store, metric_id: str) -> list[tuple[dt.date, float]]:
    df = store.series(metric_id, "KOR" if metric_id == "usd_krw" else "USA")
    if df.empty:
        df = store.series(metric_id)
    out: list[tuple[dt.date, float]] = []
    for _, r in df.iterrows():
        try:
            out.append((dt.date.fromisoformat(str(r["as_of_date"])), float(r["value"])))
        except (ValueError, TypeError):
            continue
    return sorted(out)


def _fx_on(fx: list[tuple[dt.date, float]], target: dt.date) -> Optional[tuple[float, dt.date]]:
    """target 이전의 가장 가까운 환율. 너무 오래됐으면 None."""
    best = None
    for d, v in fx:
        if d <= target:
            best = (v, d)
        else:
            break
    if best is None:
        return None
    if (target - best[1]).days > MAX_FX_GAP_DAYS:
        return None
    return best


def _point(metric_id: str, value: float, unit: str, period: str, as_of: dt.date,
           entity: str, freq: str, note: str, currency: Optional[str] = None,
           confidence: float = 0.85) -> DataPoint:
    return DataPoint(
        metric_id=metric_id, entity=entity, value=value, unit=unit, currency=currency,
        period=period, as_of_date=as_of, fetched_at=dt.datetime.now(),
        source_name=DERIVED_SOURCE, source_url="", source_tier=6,
        frequency=freq, is_estimate=True, confidence=confidence, note=note,
    )


def _as_map(store: Store, metric_id: str, entity: Optional[str] = None) -> dict[str, tuple[float, dt.date, str]]:
    """period → (value, as_of, unit)"""
    df = store.series(metric_id, entity)
    out: dict[str, tuple[float, dt.date, str]] = {}
    for _, r in df.iterrows():
        try:
            out[str(r["period"])] = (
                float(r["value"]),
                dt.date.fromisoformat(str(r["as_of_date"])),
                str(r["unit"]),
            )
        except (ValueError, TypeError):
            continue
    return out


# ----------------------------------------------------------------------
def compute(store: Store, rec_weight: float = 1.0) -> list[DataPoint]:
    out: list[DataPoint] = []
    out += _poly_premium(store)
    out += _cell_module_spread(store)
    out += _us_china_module_premium(store)
    out += _smp_rec_revenue(store, rec_weight)
    out += _op_margin(store)
    out += _ghi_vs_normal(store)
    return out


# ----------------------------------------------------------------------
def _poly_premium(store: Store) -> list[DataPoint]:
    """비중국산 폴리실리콘 프리미엄 (%). 중국가(RMB/kg)를 USD 로 환산해 비교."""
    china = _as_map(store, "poly_price_china_dense")
    nonchina = _as_map(store, "poly_price_nonchina")
    if not china or not nonchina:
        return []
    fx = _fx_lookup(store, "usd_cny")
    if not fx:
        return []

    out: list[DataPoint] = []
    for period, (nc_val, nc_date, nc_unit) in nonchina.items():
        cn = china.get(period)
        if not cn:
            continue
        cn_val, cn_date, cn_unit = cn
        if "RMB" not in cn_unit or "USD" not in nc_unit:
            continue
        rate = _fx_on(fx, cn_date)
        if rate is None:
            continue
        cny_per_usd, fx_date = rate
        cn_usd = cn_val / cny_per_usd
        if cn_usd <= 0:
            continue
        premium = (nc_val - cn_usd) / cn_usd * 100
        out.append(_point(
            "nonchina_poly_premium", round(premium, 2), "%", period, nc_date,
            "GLOBAL", "weekly",
            note=(f"중국 {cn_val} RMB/kg → {cn_usd:.2f} USD/kg 환산 "
                  f"(환율 {cny_per_usd:.4f} CNY/USD, 기준일 {fx_date.isoformat()}) "
                  f"vs 비중국 {nc_val} USD/kg"),
        ))
    return out


def _cell_module_spread(store: Store) -> list[DataPoint]:
    """셀→모듈 스프레드 (USD/W). 셀가(RMB/W)를 USD 로 환산."""
    cell = _as_map(store, "cell_price_topcon_m10")
    module = _as_map(store, "module_price_china_fob")
    if not cell or not module:
        return []
    fx = _fx_lookup(store, "usd_cny")
    if not fx:
        return []

    out: list[DataPoint] = []
    for period, (m_val, m_date, m_unit) in module.items():
        c = cell.get(period)
        if not c:
            continue
        c_val, c_date, c_unit = c
        if "RMB" not in c_unit or "USD" not in m_unit:
            continue
        rate = _fx_on(fx, c_date)
        if rate is None:
            continue
        cny_per_usd, fx_date = rate
        c_usd = c_val / cny_per_usd
        out.append(_point(
            "cell_module_spread", round(m_val - c_usd, 4), "USD/W", period, m_date,
            "GLOBAL", "weekly", currency="USD",
            note=(f"모듈 {m_val} USD/W − 셀 {c_val} RMB/W({c_usd:.4f} USD/W 환산, "
                  f"환율 기준일 {fx_date.isoformat()})"),
        ))
    return out


def _us_china_module_premium(store: Store) -> list[DataPoint]:
    us = _as_map(store, "module_price_us_ddp")
    cn = _as_map(store, "module_price_china_fob")
    if not us or not cn:
        return []
    out: list[DataPoint] = []
    for period, (u_val, u_date, u_unit) in us.items():
        c = cn.get(period)
        if not c or c[0] <= 0:
            continue
        if u_unit != c[2]:
            continue          # 단위가 다르면 계산하지 않는다
        out.append(_point(
            "us_china_module_premium", round((u_val - c[0]) / c[0] * 100, 2), "%",
            period, u_date, "GLOBAL", "weekly",
            note=f"미국 DDP {u_val} vs 중국 FOB {c[0]} ({u_unit})",
        ))
    return out


def _smp_rec_revenue(store: Store, rec_weight: float) -> list[DataPoint]:
    """SMP + REC 환산수익 (원/kWh).

    1 REC = 1MWh 단순 환산 → 원/kWh 로 만들려면 1000 으로 나눈다.
    실제 계약수익이 아니라 시장가격 기반 참고치다.
    """
    smp = _as_map(store, "smp_land", "KOR")
    rec = _as_map(store, "rec_spot_price", "KOR")
    if not smp or not rec:
        return []
    out: list[DataPoint] = []
    for period, (s_val, s_date, _u) in smp.items():
        r = rec.get(period)
        if not r:
            continue
        total = s_val + (r[0] * rec_weight / 1000.0)
        out.append(_point(
            "smp_rec_revenue", round(total, 2), "원/kWh", period, s_date,
            "KOR", "daily", currency="KRW",
            note=(f"SMP {s_val} + REC {r[0]}원/REC × 가중치 {rec_weight} ÷ 1000. "
                  f"1REC=1MWh 단순환산, 시장가격 기반 참고치 (실제 계약수익 아님)"),
        ))
    return out


def _op_margin(store: Store) -> list[DataPoint]:
    out: list[DataPoint] = []
    for entity in store.entities("revenue_q"):
        rev = _as_map(store, "revenue_q", entity)
        op = _as_map(store, "op_profit_q", entity)
        for period, (r_val, r_date, _u) in rev.items():
            o = op.get(period)
            if not o or r_val == 0:
                continue
            out.append(_point(
                "op_margin_q", round(o[0] / r_val * 100, 2), "%", period, r_date,
                entity, "quarterly",
                note=f"영업이익 {o[0]} / 매출 {r_val} (십억원)",
            ))
    return out


def _ghi_vs_normal(store: Store) -> list[DataPoint]:
    """최근 7일·30일 일사량의 평년 대비 편차 (%)."""
    normals_file = PROCESSED_DIR / "ghi_normals.json"
    if not normals_file.exists():
        return []
    import json
    try:
        normals = json.loads(normals_file.read_text(encoding="utf-8"))
    except Exception:
        return []

    today = dt.date.today()
    out: list[DataPoint] = []

    for region, meta in normals.items():
        monthly = meta.get("monthly") or {}
        df = store.series("ghi_daily", region)
        if df.empty:
            continue
        # 예보분은 제외하고 실측만 사용
        obs = df[df["is_estimate"] != True]  # noqa: E712
        if obs.empty:
            continue
        obs = obs.copy()
        obs["_d"] = pd.to_datetime(obs["as_of_date"], errors="coerce")
        obs = obs[obs["_d"].notna()].sort_values("_d")

        for win in (7, 30):
            cutoff = pd.Timestamp(today - dt.timedelta(days=win))
            recent = obs[obs["_d"] >= cutoff]
            if len(recent) < max(3, win // 3):
                continue
            actual = pd.to_numeric(recent["value"], errors="coerce").mean()
            # 해당 기간에 걸친 월들의 평년값 평균
            months = {f"{d.month:02d}" for d in recent["_d"]}
            norm_vals = [monthly[m] for m in months if m in monthly]
            if not norm_vals or actual != actual:
                continue
            normal = sum(norm_vals) / len(norm_vals)
            if normal <= 0:
                continue
            dev = (actual - normal) / normal * 100
            last_date = recent["_d"].max().date()
            out.append(_point(
                "ghi_normal_dev_pct", round(dev, 2), "%",
                last_date.isoformat(), last_date, region, "daily",
                note=(f"최근 {win}일 평균 {actual:.2f} MJ/m2 vs NASA POWER 평년 "
                      f"{normal:.2f} MJ/m2 ({win}일 창)"),
                confidence=0.75,
            ))
    return out
