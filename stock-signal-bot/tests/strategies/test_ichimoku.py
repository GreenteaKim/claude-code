"""일목균형표 전략 단위 테스트"""
import numpy as np
import pandas as pd
import pytest

from signals.models import SignalType
from strategies.ichimoku import IchimokuStrategy, _ichimoku


def _make_df(n: int = 120, trend: str = "up") -> pd.DataFrame:
    rng = np.random.default_rng(7)
    if trend == "up":
        close = np.linspace(60000, 80000, n) + rng.integers(-500, 500, size=n)
    else:
        close = np.linspace(80000, 60000, n) + rng.integers(-500, 500, size=n)
    close = close.astype(float)
    high = close + rng.integers(100, 600, size=n)
    low = close - rng.integers(100, 600, size=n)
    volume = rng.integers(5_000_000, 20_000_000, size=n).astype(float)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx)


def test_ichimoku_columns():
    df = _make_df(120)
    ichi = _ichimoku(df)
    assert set(ichi.columns) >= {"tenkan", "kijun", "senkou_a", "senkou_b", "chikou"}


def test_returns_valid_signal():
    strat = IchimokuStrategy()
    df = _make_df(120)
    result = strat._safe_analyze(df, "005930")
    assert isinstance(result.signal, SignalType)
    assert result.strategy_name == "일목균형표"


def test_weight():
    strat = IchimokuStrategy()
    assert strat.weight == pytest.approx(0.20)


def test_uptrend_tends_buy():
    """강한 상승 추세에서 BUY 계열 시그널 비율이 높아야 함"""
    strat = IchimokuStrategy()
    signals = []
    for seed in range(5):
        rng = np.random.default_rng(seed)
        close = np.linspace(50000, 90000, 130).astype(float) + rng.integers(-200, 200, size=130)
        high = close + 300
        low = close - 300
        vol = np.ones(130) * 10_000_000
        idx = pd.date_range("2023-01-01", periods=130, freq="B")
        df = pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close, "Volume": vol}, index=idx)
        sig = strat._safe_analyze(df, "005930")
        signals.append(sig.signal.value)

    avg = sum(signals) / len(signals)
    assert avg >= 0  # 상승 추세에서는 평균적으로 중립 이상이어야 함
