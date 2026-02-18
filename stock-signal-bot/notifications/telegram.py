"""Telegram 메시지 포맷팅 및 발송"""
from __future__ import annotations

import logging

import telegram

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from signals.models import DailyReport, EnsembleSignal, SignalType

logger = logging.getLogger(__name__)


def _get_bot() -> telegram.Bot:
    return telegram.Bot(token=TELEGRAM_BOT_TOKEN)


async def send_signal(signal: EnsembleSignal) -> None:
    """매매 시그널 알림 발송"""
    bot = _get_bot()
    message = _format_signal(signal)
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="HTML",
    )
    logger.info(f"[Telegram] 시그널 발송: {signal.stock_name} {signal.signal.name}")


async def send_stop_loss_alert(
    stock_code: str,
    stock_name: str,
    current_price: float,
    stop_price: float,
    reason: str,
) -> None:
    """긴급 손절 알림 발송"""
    bot = _get_bot()
    change = (current_price - stop_price) / stop_price * 100
    message = (
        "🚨 <b>긴급 손절 알림</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ {stock_name} ({stock_code})\n"
        f"💰 현재가: {current_price:,.0f}원 ({change:+.1f}%)\n\n"
        f"⚠️ {reason}\n\n"
        "즉시 매도를 권고합니다.\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="HTML",
    )


async def send_daily_report(report: DailyReport) -> None:
    """장 마감 후 종합 리포트 발송"""
    bot = _get_bot()
    message = _format_daily_report(report)
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="HTML",
    )


async def send_error(error_msg: str) -> None:
    """에러 알림"""
    bot = _get_bot()
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=f"❌ <b>봇 오류</b>\n{error_msg}",
        parse_mode="HTML",
    )


# ── 포맷터 ─────────────────────────────────────────────────────────────────


def _format_signal(signal: EnsembleSignal) -> str:
    chg_arrow = "▲" if signal.change_pct >= 0 else "▼"
    lines = [
        "📊 <b>매매 시그널 알림</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"🏷️ {signal.stock_name} ({signal.stock_code})",
        f"💰 현재가: {signal.price:,.0f}원 ({chg_arrow}{abs(signal.change_pct):.1f}%)",
        "",
        f"{signal.signal.label()} (Score: {signal.ensemble_score:.2f})",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "📋 <b>전략별 시그널:</b>",
    ]

    for i, s in enumerate(signal.strategy_signals):
        prefix = "└" if i == len(signal.strategy_signals) - 1 else "├"
        lines.append(f"  {prefix} {s.strategy_name}: {s.signal.emoji()} {s.signal.name} ({s.reason})")

    # 주요 지표 (첫 번째 전략 지표 표시)
    all_indicators: dict = {}
    for s in signal.strategy_signals:
        all_indicators.update(s.indicators)

    if all_indicators:
        lines += ["", "📈 <b>주요 지표:</b>"]
        for k, v in list(all_indicators.items())[:4]:
            lines.append(f"  ├ {k}: {v}")

    lines.append("")
    lines.append(f"⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')} KST")
    return "\n".join(lines)


def _format_daily_report(report: DailyReport) -> str:
    lines = [
        f"📋 <b>일간 종합 리포트 ({report.date})</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for signal in report.signals:
        chg = signal.change_pct
        arrow = "▲" if chg >= 0 else "▼"
        lines.append(
            f"{signal.stock_name} | {signal.price:,.0f} ({arrow}{abs(chg):.1f}%) "
            f"| {signal.signal.emoji()} {signal.signal.name}"
        )

    if report.kospi:
        chg_arrow = "▲" if (report.kospi_change_pct or 0) >= 0 else "▼"
        lines += [
            "",
            "📊 <b>시장 환경:</b>",
            f"  ├ KOSPI: {report.kospi:,.0f} ({chg_arrow}{abs(report.kospi_change_pct or 0):.1f}%)",
        ]

    return "\n".join(lines)
