"""스탠 와인스타인 전략 — Stage Analysis (4단계 순환)"""
from __future__ import annotations

from enum import Enum

import pandas as pd

from signals.models import SignalType, StrategySignal
from strategies.base import BaseStrategy


class Stage(Enum):
    STAGE_1 = 1  # 바닥 다지기
    STAGE_2 = 2  # 상승 국면
    STAGE_3 = 3  # 천장 형성
    STAGE_4 = 4  # 하락 국면
    UNKNOWN = 0


def _classify_stage(df: pd.DataFrame) -> tuple[Stage, float]:
    """30주(150일) 이동평균 기반 Stage 분류. slope 반환."""
    close = df["Close"]
    ma150 = close.rolling(150).mean()

    if ma150.isna().iloc[-1]:
        return Stage.UNKNOWN, 0.0

    cur_ma = ma150.iloc[-1]
    prev_ma = ma150.iloc[-10]  # 10거래일 전과 비교로 기울기 계산
    slope = (cur_ma - prev_ma) / prev_ma * 100

    cur_close = close.iloc[-1]
    vol = df["Volume"]
    vol_ratio_4w = vol.iloc[-1] / vol.rolling(20).mean().iloc[-1]

    above_ma = cur_close > cur_ma

    if above_ma and slope > 0.1:
        return Stage.STAGE_2, slope
    if above_ma and abs(slope) <= 0.1:
        return Stage.STAGE_1, slope
    if not above_ma and slope > -0.1:
        return Stage.STAGE_3, slope
    return Stage.STAGE_4, slope


class WeinsteinStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "와인스타인 Stage"

    @property
    def weight(self) -> float:
        return 0.15

    def analyze(self, df: pd.DataFrame, stock_code: str) -> StrategySignal:
        close = df["Close"]
        ma150 = close.rolling(150).mean()
        volume = df["Volume"]

        stage, slope = _classify_stage(df)

        # 이전 Stage (5일 전)
        if len(df) >= 155:
            prev_stage, prev_slope = _classify_stage(df.iloc[:-5])
        else:
            prev_stage = Stage.UNKNOWN
            prev_slope = 0.0

        cur_close = close.iloc[-1]
        cur_ma = ma150.iloc[-1]
        vol_ratio_4w = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]

        indicators = {
            "stage": stage.name,
            "ma150": round(cur_ma, 0) if not pd.isna(cur_ma) else None,
            "slope_pct": round(slope, 3),
            "vol_ratio_4w": round(vol_ratio_4w, 2),
        }

        # ── 매수: Stage 1→2 전환 ─────────────────────────
        entering_stage2 = (
            prev_stage in (Stage.STAGE_1, Stage.UNKNOWN)
            and stage == Stage.STAGE_2
        )
        slope_turned_positive = prev_slope <= 0 and slope > 0

        if entering_stage2 or (stage == Stage.STAGE_2 and slope_turned_positive):
            if vol_ratio_4w >= 2.0:
                return StrategySignal(
                    strategy_name=self.name,
                    signal=SignalType.STRONG_BUY,
                    confidence=0.85,
                    reason=f"Stage 2 진입 + 거래량 {vol_ratio_4w:.1f}배",
                    indicators=indicators,
                )
            if vol_ratio_4w >= 1.0:
                return StrategySignal(
                    strategy_name=self.name,
                    signal=SignalType.BUY,
                    confidence=0.65,
                    reason=f"Stage 2 진입 (기울기:{slope:.3f}%)",
                    indicators=indicators,
                )

        # Stage 2 유지 중 (추가 매수 필요 없음 → 관망)
        if stage == Stage.STAGE_2:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.NEUTRAL,
                confidence=0.5,
                reason=f"Stage 2 유지 (보유 중)",
                indicators=indicators,
            )

        # ── 매도: Stage 2→3, 3→4 전환 ──────────────────
        if stage == Stage.STAGE_3:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.SELL,
                confidence=0.65,
                reason=f"Stage 3 진입 (천장 형성)",
                indicators=indicators,
            )

        if stage == Stage.STAGE_4:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.STRONG_SELL,
                confidence=0.80,
                reason=f"Stage 4 진입 (하락 국면)",
                indicators=indicators,
            )

        return StrategySignal(
            strategy_name=self.name,
            signal=SignalType.NEUTRAL,
            confidence=0.3,
            reason=f"Stage 1 관망 (바닥 다지기)",
            indicators=indicators,
        )
