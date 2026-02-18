"""래리 윌리엄스 전략 — Williams %R 과매수/과매도 스윙 트레이딩"""
from __future__ import annotations

import pandas as pd
from ta.momentum import WilliamsRIndicator

from signals.models import SignalType, StrategySignal
from strategies.base import BaseStrategy


class WilliamsStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "윌리엄스 %R"

    @property
    def weight(self) -> float:
        return 0.10

    def analyze(self, df: pd.DataFrame, stock_code: str) -> StrategySignal:
        indicator = WilliamsRIndicator(
            high=df["High"], low=df["Low"], close=df["Close"], lbp=14
        )
        willr = indicator.williams_r()
        vol_ratio = df["Volume"] / df["Volume"].rolling(20).mean()

        cur_wr = willr.iloc[-1]
        prev_wr = willr.iloc[-2]
        cur_vol = vol_ratio.iloc[-1]

        indicators = {
            "williams_r": round(cur_wr, 2),
            "volume_ratio": round(cur_vol, 2),
        }

        # 매수: -80 아래에서 위로 크로스업 + 거래량 확인
        if prev_wr < -80 and cur_wr >= -80:
            if cur_vol >= 1.5:
                return StrategySignal(
                    strategy_name=self.name,
                    signal=SignalType.STRONG_BUY,
                    confidence=0.8,
                    reason=f"%R 과매도 반등 + 거래량 {cur_vol:.1f}배",
                    indicators=indicators,
                )
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.BUY,
                confidence=0.6,
                reason=f"%R 과매도 반등 (거래량 부족: {cur_vol:.1f}배)",
                indicators=indicators,
            )

        # 매도: -20 위에서 아래로 크로스다운
        if prev_wr > -20 and cur_wr <= -20:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.SELL,
                confidence=0.7,
                reason="%R 과매수 하락 전환",
                indicators=indicators,
            )

        # 과매수 구간 지속
        if cur_wr > -20:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.NEUTRAL,
                confidence=0.4,
                reason=f"%R 과매수 구간 유지 ({cur_wr:.1f})",
                indicators=indicators,
            )

        # 과매도 구간 지속
        if cur_wr < -80:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.NEUTRAL,
                confidence=0.3,
                reason=f"%R 과매도 대기 중 ({cur_wr:.1f})",
                indicators=indicators,
            )

        return StrategySignal(
            strategy_name=self.name,
            signal=SignalType.NEUTRAL,
            confidence=0.3,
            reason=f"%R 중립 ({cur_wr:.1f})",
            indicators=indicators,
        )
