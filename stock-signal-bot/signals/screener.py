"""KOSPI 주요 종목 스크리닝 — 신규 추천 종목 발굴"""
from __future__ import annotations

import logging
import time

from config import MAX_RECOMMENDATIONS, SCREENING_UNIVERSE
from data.fetcher import get_current_price, get_ohlcv
from signals.models import Recommendation, SignalType
from strategies.ensemble import generate_ensemble_signal

logger = logging.getLogger(__name__)

# 추천 대상 시그널 (BUY 이상만)
_BUY_SIGNALS = {SignalType.BUY, SignalType.STRONG_BUY}


def run_screening() -> list[Recommendation]:
    """
    SCREENING_UNIVERSE 전체를 스캔해 BUY 이상 시그널 종목을
    앙상블 스코어 기준 내림차순으로 반환 (최대 MAX_RECOMMENDATIONS개).
    """
    candidates: list[tuple[float, Recommendation]] = []

    for code, name in SCREENING_UNIVERSE.items():
        try:
            rec = _screen_stock(code, name)
            if rec and rec.signal in _BUY_SIGNALS:
                candidates.append((rec.ensemble_score, rec))
            time.sleep(0.2)  # pykrx 속도 제한
        except Exception as e:
            logger.warning(f"[screener] {name}({code}) 분석 실패: {e}")

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [rec for _, rec in candidates[:MAX_RECOMMENDATIONS]]


def _screen_stock(code: str, name: str) -> Recommendation | None:
    df = get_ohlcv(code)
    if df.empty or len(df) < 60:
        return None

    price, change_pct = get_current_price(code)
    if price == 0:
        return None

    ensemble = generate_ensemble_signal(code, df, price, change_pct)

    # 주요 매수 근거 추출 (BUY+ 시그널을 낸 전략들의 reason)
    top_reasons = [
        f"{s.strategy_name}: {s.reason}"
        for s in ensemble.strategy_signals
        if s.signal in _BUY_SIGNALS
    ][:3]

    return Recommendation(
        stock_code=code,
        stock_name=name,
        signal=ensemble.signal,
        ensemble_score=ensemble.ensemble_score,
        price=price,
        change_pct=change_pct,
        top_reasons=top_reasons,
    )
