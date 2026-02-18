"""일목균형표 전략 — 삼역호전/삼역역전"""
from __future__ import annotations

import pandas as pd

from signals.models import SignalType, StrategySignal
from strategies.base import BaseStrategy


def _ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    high, low, close = df["High"], df["Low"], df["Close"]

    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    # 후행스팬: 현재 종가를 26일 뒤에 표시 → 과거 26일치 비교용으로 shift(-26) 사용
    chikou = close.shift(-26)

    return pd.DataFrame({
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
    }, index=df.index)


class IchimokuStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "일목균형표"

    @property
    def weight(self) -> float:
        return 0.20

    def analyze(self, df: pd.DataFrame, stock_code: str) -> StrategySignal:
        ichi = _ichimoku(df)

        # 현재 기준 지표 (최신)
        tenkan = ichi["tenkan"].iloc[-1]
        kijun = ichi["kijun"].iloc[-1]
        price = df["Close"].iloc[-1]

        # 구름대: senkou_a/b는 26일 선행이므로 현재 구름 = iloc[-1]
        cloud_a = ichi["senkou_a"].iloc[-1]
        cloud_b = ichi["senkou_b"].iloc[-1]
        cloud_top = max(cloud_a, cloud_b)
        cloud_bottom = min(cloud_a, cloud_b)

        # 후행스팬 조건: 현재 종가 vs 26일 전 종가
        chikou_price = df["Close"].iloc[-1]   # 현재 종가 = 후행스팬
        price_26ago = df["Close"].iloc[-27] if len(df) >= 27 else None

        indicators = {
            "tenkan": round(tenkan, 0),
            "kijun": round(kijun, 0),
            "cloud_top": round(cloud_top, 0),
            "cloud_bottom": round(cloud_bottom, 0),
            "price": round(price, 0),
        }

        # ── 삼역호전 조건 ───────────────────────────────
        c1_buy = tenkan > kijun                          # 전환선 > 기준선
        c2_buy = price_26ago is not None and chikou_price > price_26ago  # 후행스팬 > 26일 전 주가
        c3_buy = price > cloud_top                       # 주가 구름 위
        yang_cloud = cloud_a > cloud_b                   # 양운

        buy_count = sum([c1_buy, c2_buy, c3_buy])

        if buy_count == 3:
            sig = SignalType.STRONG_BUY if yang_cloud else SignalType.BUY
            return StrategySignal(
                strategy_name=self.name,
                signal=sig,
                confidence=0.9 if yang_cloud else 0.75,
                reason=f"삼역호전{'(양운)' if yang_cloud else '(음운)'}",
                indicators=indicators,
            )

        # ── 삼역역전 조건 ───────────────────────────────
        c1_sell = tenkan < kijun
        c2_sell = price_26ago is not None and chikou_price < price_26ago
        c3_sell = price < cloud_bottom
        yin_cloud = cloud_a < cloud_b

        sell_count = sum([c1_sell, c2_sell, c3_sell])

        if sell_count == 3:
            sig = SignalType.STRONG_SELL if yin_cloud else SignalType.SELL
            return StrategySignal(
                strategy_name=self.name,
                signal=sig,
                confidence=0.9 if yin_cloud else 0.75,
                reason=f"삼역역전{'(음운)' if yin_cloud else '(양운)'}",
                indicators=indicators,
            )

        # 부분 시그널 (2개 조건)
        if buy_count == 2:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.BUY,
                confidence=0.5,
                reason=f"매수 조건 {buy_count}/3 충족",
                indicators=indicators,
            )

        if sell_count == 2:
            return StrategySignal(
                strategy_name=self.name,
                signal=SignalType.SELL,
                confidence=0.5,
                reason=f"매도 조건 {sell_count}/3 충족 (비중 50% 축소 경고)",
                indicators=indicators,
            )

        return StrategySignal(
            strategy_name=self.name,
            signal=SignalType.NEUTRAL,
            confidence=0.3,
            reason=f"조건 미충족 (매수:{buy_count}/3, 매도:{sell_count}/3)",
            indicators=indicators,
        )
