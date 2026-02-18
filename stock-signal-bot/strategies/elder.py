"""알렉산더 엘더 Triple Screen 전략 — 3개 시간 프레임 다중 필터"""
from __future__ import annotations

import pandas as pd
from ta.momentum import StochasticOscillator
from ta.trend import MACD

from signals.models import SignalType, StrategySignal
from strategies.base import BaseStrategy


def _resample_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """일봉 데이터를 주봉으로 리샘플링"""
    df2 = df.copy()
    df2.index = pd.to_datetime(df2.index)
    return df2.resample("W-FRI").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()


class ElderStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "엘더 Triple Screen"

    @property
    def weight(self) -> float:
        return 0.15

    def analyze(self, df: pd.DataFrame, stock_code: str) -> StrategySignal:
        # ── Screen 1: 주봉 MACD 히스토그램 방향 ─────────
        weekly = _resample_weekly(df)
        if len(weekly) < 30:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                reason="주봉 데이터 부족",
            )

        w_macd_ind = MACD(close=weekly["Close"], window_slow=26, window_fast=12, window_sign=9)
        w_hist = w_macd_ind.macd_diff()

        cur_w_hist = w_hist.iloc[-1]
        prev_w_hist = w_hist.iloc[-2]
        weekly_bullish = cur_w_hist > prev_w_hist

        # ── Screen 2: 일봉 Force Index(2) ───────────────
        raw_fi = df["Close"].diff() * df["Volume"]
        force_index_2 = raw_fi.ewm(span=2, adjust=False).mean()

        # Stochastic(5,3)
        stoch_ind = StochasticOscillator(
            high=df["High"], low=df["Low"], close=df["Close"], window=5, smooth_window=3
        )
        stoch_k = stoch_ind.stoch().iloc[-1]

        cur_fi = force_index_2.iloc[-1]
        prev_high = df["High"].iloc[-2]
        prev_low = df["Low"].iloc[-2]
        cur_close = df["Close"].iloc[-1]

        indicators = {
            "weekly_macd_hist": round(cur_w_hist, 2),
            "weekly_bullish": weekly_bullish,
            "force_index_2": round(cur_fi, 0),
            "stoch_k": round(stoch_k, 1),
        }

        if weekly_bullish:
            screen2_buy = cur_fi < 0
            screen3_buy = cur_close > prev_high

            if screen2_buy and screen3_buy:
                return StrategySignal(
                    strategy_name=self.name,
                    signal=SignalType.STRONG_BUY,
                    confidence=0.85,
                    reason=f"Triple Screen 매수 완성 (주봉↑, FI:{cur_fi:.0f}, 전고돌파)",
                    indicators=indicators,
                )

            if screen2_buy:
                return StrategySignal(
                    strategy_name=self.name,
                    signal=SignalType.BUY,
                    confidence=0.60,
                    reason=f"Screen 1,2 통과 — 전고가({prev_high:.0f}) 돌파 대기",
                    indicators=indicators,
                )
        else:
            screen2_sell = cur_fi > 0
            screen3_sell = cur_close < prev_low

            if screen2_sell and screen3_sell:
                return StrategySignal(
                    strategy_name=self.name,
                    signal=SignalType.STRONG_SELL,
                    confidence=0.85,
                    reason=f"Triple Screen 매도 완성 (주봉↓, FI:{cur_fi:.0f}, 전저이탈)",
                    indicators=indicators,
                )

            if screen2_sell:
                return StrategySignal(
                    strategy_name=self.name,
                    signal=SignalType.SELL,
                    confidence=0.55,
                    reason="Screen 1,2 매도 통과",
                    indicators=indicators,
                )

        return StrategySignal(
            strategy_name=self.name,
            signal=SignalType.NEUTRAL,
            confidence=0.3,
            reason="Triple Screen 조건 미충족",
            indicators=indicators,
        )
