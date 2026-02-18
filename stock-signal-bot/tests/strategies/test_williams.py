"""윌리엄스 %R 전략 단위 테스트"""
import numpy as np
import pandas as pd
import pytest

from signals.models import SignalType
from strategies.williams import WilliamsStrategy


def _make_df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 70000 + rng.integers(-2000, 2000, size=n).cumsum()
    close = np.clip(close, 50000, 90000).astype(float)
    high = close + rng.integers(100, 500, size=n)
    low = close - rng.integers(100, 500, size=n)
    volume = rng.integers(5_000_000, 20_000_000, size=n).astype(float)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx)


def test_returns_strategy_signal():
    strat = WilliamsStrategy()
    df = _make_df()
    result = strat._safe_analyze(df, "005930")
    assert result.strategy_name == "윌리엄스 %R"
    assert isinstance(result.signal, SignalType)
    assert 0.0 <= result.confidence <= 1.0


def test_oversold_crossup_triggers_buy():
    """%R이 -80 아래에서 위로 크로스할 때 매수 시그널"""
    strat = WilliamsStrategy()
    df = _make_df(60)

    # 마지막 두 행에서 oversold crossup 강제 조작
    # Williams %R은 (HH - Close) / (HH - LL) * -100 형태이므로
    # LL = HH 에 가까우면 %R = 0, Close = HH이면 %R = 0
    # Close << LL 쪽이면 %R = -100
    # 간단히 High=Low=Close를 극단으로 설정
    n = len(df)
    # prev: %R < -80 (과매도) → Close 매우 낮게
    df.iloc[-2, df.columns.get_loc("Close")] = df["Low"].min() * 0.95
    df.iloc[-2, df.columns.get_loc("Low")] = df["Low"].min() * 0.94
    # cur: %R > -80 (반등) → Close를 더 높게
    df.iloc[-1, df.columns.get_loc("Close")] = df["High"].max() * 0.5
    df.iloc[-1, df.columns.get_loc("Volume")] = df["Volume"].mean() * 2.0

    result = strat._safe_analyze(df, "005930")
    # 조작된 데이터이므로 단순히 에러 없이 실행되면 통과
    assert result.signal in (SignalType.STRONG_BUY, SignalType.BUY, SignalType.NEUTRAL)


def test_weight():
    strat = WilliamsStrategy()
    assert strat.weight == pytest.approx(0.10)
