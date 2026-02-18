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
    bot = _get_bot()
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=_format_signal(signal),
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
    bot = _get_bot()
    change = (current_price - stop_price) / stop_price * 100
    msg = (
        "🚨 <b>긴급 손절 알림</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ {stock_name} ({stock_code})\n"
        f"💰 현재가: {current_price:,.0f}원 ({change:+.1f}%)\n\n"
        f"⚠️ {reason}\n\n"
        "즉시 매도를 권고합니다.\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="HTML")


async def send_daily_report(report: DailyReport) -> None:
    bot = _get_bot()
    messages = _format_daily_report(report)
    for msg in messages:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="HTML")


async def send_error(error_msg: str) -> None:
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
        lines.append(f"  {prefix} {s.strategy_name}: {s.signal.emoji()} {s.reason}")

    lines.append(f"\n⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')} KST")
    return "\n".join(lines)


def _format_daily_report(report: DailyReport) -> list[str]:
    """리포트를 여러 메시지로 분리 반환 (Telegram 4096자 제한 대응)"""
    messages = []

    # ── 1. 보유 포지션 현황 ──────────────────────────────
    if report.positions:
        lines = [
            f"💼 <b>보유 포지션 현황 ({report.date})</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        for p in report.positions:
            pnl_arrow = "▲" if p.pnl_pct >= 0 else "▼"
            day_arrow = "▲" if p.change_pct >= 0 else "▼"
            stop_loss_pct = -7.0  # 오닐 기준
            is_danger = p.pnl_pct <= stop_loss_pct
            danger_mark = " ⚠️ 손절 주의!" if is_danger else ""

            lines += [
                f"🏷️ <b>{p.stock_name}</b> ({p.stock_code}){danger_mark}",
                f"  현재가: {p.current_price:,.0f}원 ({day_arrow}{abs(p.change_pct):.1f}%)",
                f"  매수가: {p.entry_price:,.0f}원",
                f"  수익률: {pnl_arrow}{abs(p.pnl_pct):.2f}%",
                f"  시그널: {p.signal.label()}",
                "",
            ]
        messages.append("\n".join(lines))

    # ── 2. 전략 시그널 요약 ─────────────────────────────
    if report.signals:
        lines = [
            f"📊 <b>전략 시그널 요약 ({report.date})</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        for s in report.signals:
            arrow = "▲" if s.change_pct >= 0 else "▼"
            lines.append(
                f"{s.signal.emoji()} <b>{s.stock_name}</b> | "
                f"{s.price:,.0f}원 ({arrow}{abs(s.change_pct):.1f}%) | "
                f"Score: {s.ensemble_score:.2f}"
            )
            # 전략별 상세
            buy_strategies = [
                f"    ├ {st.strategy_name}: {st.reason}"
                for st in s.strategy_signals
                if st.signal.value > 0
            ]
            if buy_strategies:
                lines += buy_strategies

            lines.append("")

        if report.kospi:
            arrow = "▲" if (report.kospi_change_pct or 0) >= 0 else "▼"
            lines += [
                "📈 <b>시장 환경:</b>",
                f"  KOSPI: {report.kospi:,.0f} ({arrow}{abs(report.kospi_change_pct or 0):.1f}%)",
            ]
        messages.append("\n".join(lines))

    # ── 3. 신규 추천 종목 ───────────────────────────────
    if report.recommendations:
        lines = [
            "🔍 <b>신규 추천 종목 (투자 거장 앙상블)</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        for i, r in enumerate(report.recommendations, 1):
            arrow = "▲" if r.change_pct >= 0 else "▼"
            lines += [
                f"{i}. {r.signal.emoji()} <b>{r.stock_name}</b> ({r.stock_code})",
                f"   현재가: {r.price:,.0f}원 ({arrow}{abs(r.change_pct):.1f}%)",
                f"   앙상블 스코어: {r.ensemble_score:.2f} | {r.signal.label()}",
            ]
            for reason in r.top_reasons:
                lines.append(f"   • {reason}")
            lines.append("")

        messages.append("\n".join(lines))

    if not messages:
        messages.append(
            f"📋 <b>일간 리포트 ({report.date})</b>\n\n분석할 데이터가 없습니다."
        )

    return messages
