from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from signals.models import StrategySignal


class BaseStrategy(ABC):
    """모든 전략이 상속받는 추상 클래스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """전략 이름 (예: '일목균형표')"""

    @property
    @abstractmethod
    def weight(self) -> float:
        """앙상블 가중치 (합계 1.0)"""

    @abstractmethod
    def analyze(self, df: pd.DataFrame, stock_code: str) -> StrategySignal:
        """
        Args:
            df: OHLCV + 수급 컬럼을 가진 DataFrame
                필수 컬럼: Open, High, Low, Close, Volume
                선택 컬럼: ForeignNetBuy, InstitutionNetBuy
            stock_code: 종목코드

        Returns:
            StrategySignal
        """

    def _safe_analyze(self, df: pd.DataFrame, stock_code: str) -> StrategySignal:
        """에러 발생 시 NEUTRAL 반환"""
        from signals.models import SignalType

        try:
            return self.analyze(df, stock_code)
        except Exception as exc:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.NEUTRAL,
                confidence=0.0,
                reason=f"분석 실패: {exc}",
            )
