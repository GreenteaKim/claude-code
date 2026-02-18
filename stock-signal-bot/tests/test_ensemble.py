"""앙상블 시그널 테스트"""
import numpy as np
import pandas as pd
import pytest

from signals.models import SignalType
from strategies.ensemble import _apply_consensus_filter, generate_ensemble_signal
from signals.models import StrategySignal


def _make_df(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(99)
    close = np.linspace(60000, 80000, n).astype(float) + rng.integers(-1000, 1000, size=n)
    high = close + 500
    low = close - 500
    vol = np.ones(n) * 12_000_000
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close, "Volume": vol}, index=idx)


def test_generate_ensemble_returns_signal():
    df = _make_df(300)
    result = generate_ensemble_signal("005930", df, 75000.0, 1.2)
    assert result.stock_code == "005930"
    assert isinstance(result.signal, SignalType)
    assert len(result.strategy_signals) == 7
    assert -2.0 <= result.ensemble_score <= 2.0


def test_consensus_filter_strong_buy_with_2_strong_sells():
    """STRONG_BUY 점수지만 STRONG_SELL 2개 → NEUTRAL 강등"""
    signals = [
        StrategySignal(strategy_name="A", signal=SignalType.STRONG_SELL, reason=""),
        StrategySignal(strategy_name="B", signal=SignalType.STRONG_SELL, reason=""),
        StrategySignal(strategy_name="C", signal=SignalType.STRONG_BUY, reason=""),
    ]
    result = _apply_consensus_filter(1.5, signals)
    assert result == SignalType.NEUTRAL


def test_consensus_filter_strong_sell_with_2_strong_buys():
    """STRONG_SELL 점수지만 STRONG_BUY 2개 → NEUTRAL 강등"""
    signals = [
        StrategySignal(strategy_name="A", signal=SignalType.STRONG_BUY, reason=""),
        StrategySignal(strategy_name="B", signal=SignalType.STRONG_BUY, reason=""),
        StrategySignal(strategy_name="C", signal=SignalType.STRONG_SELL, reason=""),
    ]
    result = _apply_consensus_filter(-1.5, signals)
    assert result == SignalType.NEUTRAL


def test_weights_sum_to_one():
    """7개 전략 가중치 합계 = 1.0"""
    from strategies.ensemble import _STRATEGIES
    total = sum(s.weight for s in _STRATEGIES)
    assert total == pytest.approx(1.0, abs=0.01)
