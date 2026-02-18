"""앙상블 시그널 — 7개 전략 가중 합산"""
from __future__ import annotations

import pandas as pd

from config import (
    ENSEMBLE_BUY_THRESHOLD,
    ENSEMBLE_SELL_THRESHOLD,
    ENSEMBLE_STRONG_BUY_THRESHOLD,
    ENSEMBLE_STRONG_SELL_THRESHOLD,
    TARGETS,
)
from signals.models import EnsembleSignal, SignalType, StrategySignal
from strategies.base import BaseStrategy
from strategies.bollinger import BollingerStrategy
from strategies.elder import ElderStrategy
from strategies.ichimoku import IchimokuStrategy
from strategies.livermore import LivermoreStrategy
from strategies.oneil import OneilStrategy
from strategies.weinstein import WeinsteinStrategy
from strategies.williams import WilliamsStrategy

_STRATEGIES: list[BaseStrategy] = [
    IchimokuStrategy(),
    OneilStrategy(),
    WeinsteinStrategy(),
    ElderStrategy(),
    BollingerStrategy(),
    LivermoreStrategy(),
    WilliamsStrategy(),
]


def generate_ensemble_signal(
    stock_code: str,
    df: pd.DataFrame,
    price: float,
    change_pct: float,
) -> EnsembleSignal:
    """
    1. 각 전략 시그널(-2 ~ +2) 수집
    2. 가중 합산
    3. 컨센서스 필터 적용
    4. 최종 EnsembleSignal 반환
    """
    strategy_signals: list[StrategySignal] = []

    for strategy in _STRATEGIES:
        sig = strategy._safe_analyze(df, stock_code)
        strategy_signals.append(sig)

    # 가중 합산
    weighted_score = sum(
        sig.signal.value * strategy.weight
        for sig, strategy in zip(strategy_signals, _STRATEGIES)
    )

    # 컨센서스 필터
    final_signal = _apply_consensus_filter(weighted_score, strategy_signals)

    stock_name = TARGETS.get(stock_code, {}).get("name", stock_code)

    return EnsembleSignal(
        stock_code=stock_code,
        stock_name=stock_name,
        signal=final_signal,
        ensemble_score=round(weighted_score, 3),
        strategy_signals=strategy_signals,
        price=price,
        change_pct=change_pct,
    )


def _apply_consensus_filter(
    score: float, signals: list[StrategySignal]
) -> SignalType:
    strong_buys = sum(1 for s in signals if s.signal == SignalType.STRONG_BUY)
    strong_sells = sum(1 for s in signals if s.signal == SignalType.STRONG_SELL)

    if score >= ENSEMBLE_STRONG_BUY_THRESHOLD:
        # 강력 매수인데 STRONG_SELL이 2개 이상 → 관망 강등
        if strong_sells >= 2:
            return SignalType.NEUTRAL
        return SignalType.STRONG_BUY

    if score >= ENSEMBLE_BUY_THRESHOLD:
        return SignalType.BUY

    if score <= ENSEMBLE_STRONG_SELL_THRESHOLD:
        if strong_buys >= 2:
            return SignalType.NEUTRAL
        return SignalType.STRONG_SELL

    if score <= ENSEMBLE_SELL_THRESHOLD:
        return SignalType.SELL

    return SignalType.NEUTRAL
