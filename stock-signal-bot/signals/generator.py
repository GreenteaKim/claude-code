"""종목별 시그널 통합 생성"""
from __future__ import annotations

import logging
from datetime import date

from config import MY_POSITIONS, TARGETS
from data.fetcher import get_current_price, get_ohlcv, get_kospi_data
from db.signal_history import is_duplicate, save_signal
from signals.models import (
    DailyReport, EnsembleSignal, PositionStatus, SignalType
)
from strategies.ensemble import generate_ensemble_signal

logger = logging.getLogger(__name__)


def run_signal_scan(notify_neutral: bool = False) -> list[EnsembleSignal]:
    """
    보유 종목(TARGETS) 시그널 생성.
    중복 시그널 제외. 결과 리스트 반환.
    """
    results: list[EnsembleSignal] = []

    for code in TARGETS:
        try:
            signal = _analyze_stock(code)
            if signal is None:
                continue

            if signal.signal == SignalType.NEUTRAL and not notify_neutral:
                results.append(signal)
                continue

            if is_duplicate(code, signal.signal, within_hours=6):
                logger.info(f"[{code}] 중복 시그널 무시: {signal.signal.name}")
                continue

            save_signal(signal)
            results.append(signal)

        except Exception as e:
            logger.error(f"[{code}] 시그널 생성 오류: {e}")

    return results


def build_position_status(signals: list[EnsembleSignal]) -> list[PositionStatus]:
    """보유 포지션별 현재가 수익률 계산"""
    if not MY_POSITIONS:
        return []

    sig_map = {s.stock_code: s for s in signals}
    positions: list[PositionStatus] = []

    for code, entry_price in MY_POSITIONS.items():
        target = TARGETS.get(code, {})
        name = target.get("name", code)

        sig = sig_map.get(code)
        if sig:
            current_price = sig.price
            change_pct = sig.change_pct
            signal = sig.signal
        else:
            current_price, change_pct = get_current_price(code)
            signal = SignalType.NEUTRAL

        pnl_pct = (current_price - entry_price) / entry_price * 100 if entry_price else 0.0

        positions.append(PositionStatus(
            stock_code=code,
            stock_name=name,
            entry_price=entry_price,
            current_price=current_price,
            change_pct=change_pct,
            pnl_pct=round(pnl_pct, 2),
            signal=signal,
        ))

    return positions


def build_daily_report(
    signals: list[EnsembleSignal],
    run_screener: bool = True,
) -> DailyReport:
    from signals.screener import run_screening

    kospi, kospi_chg = get_kospi_data()
    positions = build_position_status(signals)

    recommendations = []
    if run_screener:
        logger.info("신규 종목 스크리닝 시작...")
        recommendations = run_screening()
        logger.info(f"스크리닝 완료: {len(recommendations)}개 추천 종목")

    return DailyReport(
        date=date.today().isoformat(),
        signals=signals,
        positions=positions,
        recommendations=recommendations,
        kospi=kospi,
        kospi_change_pct=kospi_chg,
    )


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
