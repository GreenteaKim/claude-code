"""제시 리버모어 전략 — 피벗 포인트 돌파 추세 추종"""
from __future__ import annotations

import pandas as pd

from signals.models import SignalType, StrategySignal
from strategies.base import BaseStrategy


class LivermoreStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "리버모어"

    @property
    def weight(self) -> float:
        return 0.10

    def analyze(self, df: pd.DataFrame, stock_code: str) -> StrategySignal:
        close = df["Close"]
        high = df["High"]
        volume = df["Volume"]

        # 52주 신고가 / 20일 롤링 고점
        high_52w = close.rolling(252).max()
        high_20d = high.rolling(20).max()

        # 20일 고점 대비 pullback %
        rolling_peak = close.rolling(20).max()
        pullback_pct = (close - rolling_peak) / rolling_peak

        # 연속 양봉 카운터
        consecutive_bull = _count_consecutive_bull(df)

        # 거래량 비율 (20일 평균 대비)
        vol_ratio = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]

        cur_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        cur_52h = high_52w.iloc[-1]
        cur_20h = high_20d.iloc[-2]  # 전일 기준 20일 고점
        pullback = pullback_pct.iloc[-1]

        indicators = {
            "52w_high": round(cur_52h, 0),
            "20d_high": round(cur_20h, 0),
            "pullback_pct": round(pullback * 100, 2),
            "consecutive_bull": consecutive_bull,
            "volume_ratio": round(vol_ratio, 2),
        }

        # ── 매수 조건 ───────────────────────────────────
        # 1) 20일 고점 상향 돌파
        breakout_20d = prev_close <= cur_20h and cur_close > cur_20h
        # 2) 52주 신고가 돌파
        breakout_52w = cur_close >= cur_52h * 0.99  # 1% 이내 근접도 포함

        if breakout_52w and vol_ratio >= 1.5:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.STRONG_BUY,
                confidence=0.85,
                reason=f"52주 신고가 돌파 (거래량 {vol_ratio:.1f}배)",
                indicators=indicators,
            )

        if breakout_20d and pullback > -0.10 and vol_ratio >= 1.2:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.BUY,
                confidence=0.7,
                reason=f"20일 고점 돌파 + pullback {pullback*100:.1f}%",
                indicators=indicators,
            )

        if consecutive_bull >= 3 and vol_ratio >= 1.5:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.BUY,
                confidence=0.6,
                reason=f"{consecutive_bull}일 연속 양봉 + 거래량 급증",
                indicators=indicators,
            )

        # ── 매도/손절 조건 ──────────────────────────────
        # 10일 이동평균선 하향 이탈
        ma10 = close.rolling(10).mean()
        if prev_close >= ma10.iloc[-2] and cur_close < ma10.iloc[-1]:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.SELL,
                confidence=0.7,
                reason="10일 MA 하향 이탈",
                indicators=indicators,
            )

        return StrategySignal(
            strategy_name=self.name,
            signal=SignalType.NEUTRAL,
            confidence=0.3,
            reason="돌파 미확인",
            indicators=indicators,
        )


def _count_consecutive_bull(df: pd.DataFrame) -> int:
    """연속 양봉(종가 > 시가) 일수 계산"""
    count = 0
    for i in range(len(df) - 1, max(len(df) - 10, -1), -1):
        if df["Close"].iloc[i] > df["Open"].iloc[i]:
            count += 1
        else:
            break
    return count
