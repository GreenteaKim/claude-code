"""윌리엄 오닐 CAN SLIM 전략 — 성장주 + 기술적 타이밍"""
from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator

from signals.models import SignalType, StrategySignal
from strategies.base import BaseStrategy


class OneilStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "CAN SLIM"

    @property
    def weight(self) -> float:
        return 0.18

    def analyze(self, df: pd.DataFrame, stock_code: str) -> StrategySignal:
        close = df["Close"]
        volume = df["Volume"]

        score = 0
        details: list[str] = []

        # N — New High: 52주 고점 5% 이내 또는 돌파 (15점)
        high_52w = close.rolling(252).max().iloc[-1]
        cur_close = close.iloc[-1]
        if high_52w and cur_close >= high_52w * 0.95:
            score += 15
            details.append("N:52주 고점 근접")

        # S — Supply/Demand: 50일 평균 거래량 대비 1.5배 이상 (10점)
        vol_ratio_50d = volume.iloc[-1] / volume.rolling(50).mean().iloc[-1]
        if vol_ratio_50d >= 1.5:
            score += 10
            details.append(f"S:거래량 {vol_ratio_50d:.1f}배")

        # L — Leader: 60일 수익률 양호 (15점)
        ret_60d = (cur_close / close.iloc[-61] - 1) if len(close) >= 62 else 0
        if ret_60d > 0.05:
            score += 15
            details.append(f"L:60일 수익률 {ret_60d*100:.1f}%")

        # M — Market Direction: 200일 MA 위 (15점)
        ma200 = close.rolling(200).mean().iloc[-1]
        if ma200 and cur_close > ma200:
            score += 15
            details.append("M:200일 MA 위")

        # I — Institutional: 외국인/기관 순매수 (15점)
        if "ForeignNetBuy" in df.columns:
            foreign_5d = df["ForeignNetBuy"].iloc[-5:]
            if (foreign_5d > 0).all():
                score += 15
                details.append("I:외국인 5일 연속 순매수")

        if "InstitutionNetBuy" in df.columns:
            inst_5d = df["InstitutionNetBuy"].iloc[-5:]
            if (inst_5d > 0).all():
                score += 5
                details.append("I:기관 5일 연속 순매수")

        # C, A 대체: RSI 모멘텀 보정
        rsi = RSIIndicator(close=close, window=14).rsi().iloc[-1]
        if rsi > 60:
            score += 10
            details.append(f"모멘텀 보정(RSI:{rsi:.1f})")

        indicators = {
            "canslim_score": score,
            "52w_high": round(high_52w, 0) if high_52w else None,
            "vol_ratio_50d": round(vol_ratio_50d, 2),
            "rsi_14": round(rsi, 1),
        }

        if score >= 70:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.STRONG_BUY,
                confidence=min(score / 100, 0.9),
                reason=f"CAN SLIM {score}점 ({', '.join(details)})",
                indicators=indicators,
            )

        if score >= 50:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.BUY,
                confidence=score / 100,
                reason=f"CAN SLIM {score}점",
                indicators=indicators,
            )

        if score <= 30:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.SELL,
                confidence=0.6,
                reason=f"CAN SLIM {score}점 — 조건 미달",
                indicators=indicators,
            )

        return StrategySignal(
            strategy_name=self.name,
            signal=SignalType.NEUTRAL,
            confidence=0.4,
            reason=f"CAN SLIM {score}점",
            indicators=indicators,
        )
