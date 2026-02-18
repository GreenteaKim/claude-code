"""존 볼린저 전략 — 밴드폭 수축(Squeeze) 후 상단 돌파"""
from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

from signals.models import SignalType, StrategySignal
from strategies.base import BaseStrategy

_SQUEEZE_WINDOW = 126  # 약 6개월


class BollingerStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "볼린저 밴드"

    @property
    def weight(self) -> float:
        return 0.12

    def analyze(self, df: pd.DataFrame, stock_code: str) -> StrategySignal:
        bb = BollingerBands(close=df["Close"], window=20, window_dev=2)
        rsi_ind = RSIIndicator(close=df["Close"], window=14)

        upper = bb.bollinger_hband()
        lower = bb.bollinger_lband()
        mid = bb.bollinger_mavg()
        rsi = rsi_ind.rsi()

        bandwidth = (upper - lower) / mid
        percent_b = (df["Close"] - lower) / (upper - lower)

        # 6개월 기준 BandWidth 백분위
        bw_pct = bandwidth.rolling(_SQUEEZE_WINDOW).rank(pct=True)

        cur_bw_pct = bw_pct.iloc[-1]
        prev_bw_pct = bw_pct.iloc[-2]
        cur_pb = percent_b.iloc[-1]
        cur_rsi = rsi.iloc[-1]
        cur_close = df["Close"].iloc[-1]
        cur_mid = mid.iloc[-1]

        indicators = {
            "bandwidth_percentile": round(cur_bw_pct, 2),
            "percent_b": round(cur_pb, 2),
            "rsi_14": round(cur_rsi, 1),
        }

        was_squeeze = prev_bw_pct < 0.2
        is_upper_breakout = cur_pb > 1.0

        # 매수: Squeeze 이후 상단 돌파 + RSI 50 이상
        if was_squeeze and is_upper_breakout and cur_rsi > 50:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.STRONG_BUY,
                confidence=0.8,
                reason=f"Squeeze 돌파 (BW분위:{cur_bw_pct:.2f}, %B:{cur_pb:.2f}, RSI:{cur_rsi:.1f})",
                indicators=indicators,
            )

        # 매수 약신호: Squeeze 중 상단 근접
        if cur_bw_pct < 0.2 and cur_pb > 0.8 and cur_rsi > 50:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.BUY,
                confidence=0.5,
                reason="Squeeze 진행 중 상단 근접",
                indicators=indicators,
            )

        # 매도: 상단에서 중심선 아래로 하락
        if percent_b.iloc[-2] > 0.5 and cur_close < cur_mid:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.SELL,
                confidence=0.6,
                reason=f"중심선 하향 이탈 (%B:{cur_pb:.2f})",
                indicators=indicators,
            )

        # 손절: 하단 밴드 하향 이탈
        if cur_pb < 0:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.STRONG_SELL,
                confidence=0.7,
                reason=f"하단 밴드 이탈 (%B:{cur_pb:.2f})",
                indicators=indicators,
            )

        return StrategySignal(
            strategy_name=self.name,
            signal=SignalType.NEUTRAL,
            confidence=0.3,
            reason=f"볼린저 중립 (%B:{cur_pb:.2f})",
            indicators=indicators,
        )
