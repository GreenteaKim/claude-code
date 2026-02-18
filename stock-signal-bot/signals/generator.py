"""종목별 시그널 통합 생성"""
from __future__ import annotations

import logging

from config import TARGETS
from data.fetcher import get_current_price, get_ohlcv, get_kospi_data
from db.signal_history import is_duplicate, save_signal
from signals.models import DailyReport, EnsembleSignal, SignalType
from strategies.ensemble import generate_ensemble_signal

logger = logging.getLogger(__name__)


def run_signal_scan(notify_neutral: bool = False) -> list[EnsembleSignal]:
    """
    모든 감시 종목에 대해 시그널 생성.
    중복 시그널은 제외. 결과 리스트 반환.
    """
    results: list[EnsembleSignal] = []

    for code in TARGETS:
        try:
            signal = _analyze_stock(code)
            if signal is None:
                continue

            # NEUTRAL은 기본적으로 저장하지 않고 알림도 안 보냄
            if signal.signal == SignalType.NEUTRAL and not notify_neutral:
                results.append(signal)
                continue

            # 중복 시그널 필터 (6시간 이내 동일 방향)
            if is_duplicate(code, signal.signal, within_hours=6):
                logger.info(f"[{code}] 중복 시그널 무시: {signal.signal.name}")
                continue

            save_signal(signal)
            results.append(signal)

        except Exception as e:
            logger.error(f"[{code}] 시그널 생성 오류: {e}")

    return results


def _analyze_stock(stock_code: str) -> EnsembleSignal | None:
    df = get_ohlcv(stock_code)
    if df.empty or len(df) < 60:
        logger.warning(f"[{stock_code}] 데이터 부족 ({len(df)}일)")
        return None

    price, change_pct = get_current_price(stock_code)
    if price == 0:
        logger.warning(f"[{stock_code}] 현재가 조회 실패")
        return None

    return generate_ensemble_signal(stock_code, df, price, change_pct)


def build_daily_report(signals: list[EnsembleSignal]) -> DailyReport:
    from datetime import date

    kospi, kospi_chg = get_kospi_data()

    return DailyReport(
        date=date.today().isoformat(),
        signals=signals,
        kospi=kospi,
        kospi_change_pct=kospi_chg,
    )
