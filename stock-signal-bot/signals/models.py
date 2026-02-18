from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SignalType(Enum):
    STRONG_BUY = 2
    BUY = 1
    NEUTRAL = 0
    SELL = -1
    STRONG_SELL = -2

    def label(self) -> str:
        return {
            SignalType.STRONG_BUY: "🔴 강력 매수",
            SignalType.BUY: "🟠 매수",
            SignalType.NEUTRAL: "⚪ 관망",
            SignalType.SELL: "🔵 매도",
            SignalType.STRONG_SELL: "🔵 강력 매도",
        }[self]

    def emoji(self) -> str:
        return {
            SignalType.STRONG_BUY: "🟢",
            SignalType.BUY: "🟢",
            SignalType.NEUTRAL: "⚪",
            SignalType.SELL: "🔴",
            SignalType.STRONG_SELL: "🔴",
        }[self]


class StrategySignal(BaseModel):
    strategy_name: str
    signal: SignalType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    indicators: dict = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class EnsembleSignal(BaseModel):
    stock_code: str
    stock_name: str
    signal: SignalType
    ensemble_score: float
    strategy_signals: list[StrategySignal]
    price: float
    change_pct: float
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"arbitrary_types_allowed": True}


class PositionStatus(BaseModel):
    """보유 포지션 현황"""
    stock_code: str
    stock_name: str
    entry_price: float
    current_price: float
    change_pct: float       # 당일 등락률
    pnl_pct: float          # 매수가 대비 수익률
    signal: SignalType

    model_config = {"arbitrary_types_allowed": True}


class Recommendation(BaseModel):
    """신규 추천 종목"""
    stock_code: str
    stock_name: str
    signal: SignalType
    ensemble_score: float
    price: float
    change_pct: float
    top_reasons: list[str]  # 주요 매수 근거

    model_config = {"arbitrary_types_allowed": True}


class DailyReport(BaseModel):
    date: str
    signals: list[EnsembleSignal]
    positions: list[PositionStatus] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    kospi: Optional[float] = None
    kospi_change_pct: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
