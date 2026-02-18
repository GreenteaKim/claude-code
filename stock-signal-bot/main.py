"""엔트리포인트 — APScheduler 기반 자동 실행"""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from config import SCHEDULE, TIMEZONE
from db.database import init_db
from notifications.telegram import send_daily_report, send_error, send_signal, send_stop_loss_alert
from signals.generator import build_daily_report, run_signal_scan
from signals.models import SignalType
from db.signal_history import get_open_positions, close_position
from data.fetcher import get_current_price

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── 스케줄 작업 ─────────────────────────────────────────────────────────────

async def job_signal_scan() -> None:
    """시그널 스캔 → 유효 시그널 Telegram 발송"""
    logger.info("시그널 스캔 시작")
    try:
        signals = run_signal_scan()
        for signal in signals:
            if signal.signal != SignalType.NEUTRAL:
                await send_signal(signal)
        logger.info(f"시그널 스캔 완료: {len(signals)}건")
    except Exception as e:
        logger.error(f"시그널 스캔 오류: {e}")
        await send_error(str(e))


async def job_daily_report() -> None:
    """장 마감 후 종합 리포트"""
    logger.info("일간 리포트 생성 시작")
    try:
        signals = run_signal_scan(notify_neutral=True)
        report = build_daily_report(signals)
        await send_daily_report(report)
        logger.info("일간 리포트 발송 완료")
    except Exception as e:
        logger.error(f"일간 리포트 오류: {e}")
        await send_error(str(e))


async def job_stop_loss_monitor() -> None:
    """장중 5분 간격 손절 모니터링"""
    positions = get_open_positions()
    if not positions:
        return

    for pos in positions:
        code = pos["stock_code"]
        stop_price = pos["stop_loss_price"]
        entry_price = pos["entry_price"]

        try:
            current_price, _ = get_current_price(code)
            if current_price == 0:
                continue

            loss_pct = (current_price - entry_price) / entry_price

            if current_price <= stop_price:
                reason = (
                    f"리버모어/오닐 손절선 도달 "
                    f"({loss_pct*100:.1f}%, 진입가:{entry_price:,.0f}원)"
                )
                close_position(pos["id"], current_price, "STOP_LOSS")
                await send_stop_loss_alert(
                    code,
                    config.TARGETS.get(code, {}).get("name", code),
                    current_price,
                    stop_price,
                    reason,
                )
        except Exception as e:
            logger.error(f"[{code}] 손절 모니터링 오류: {e}")


# ── 스케줄러 설정 ───────────────────────────────────────────────────────────

def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    pre = SCHEDULE["pre_market_scan"]
    scheduler.add_job(
        job_signal_scan,
        CronTrigger(hour=pre["hour"], minute=pre["minute"], timezone=TIMEZONE),
        id="pre_market_scan",
        name="장 시작 전 사전 스캔",
    )

    mo = SCHEDULE["market_open_signal"]
    scheduler.add_job(
        job_signal_scan,
        CronTrigger(hour=mo["hour"], minute=mo["minute"], timezone=TIMEZONE),
        id="market_open_signal",
        name="장 시작 직후 시그널",
    )

    mid = SCHEDULE["midday_check"]
    scheduler.add_job(
        job_signal_scan,
        CronTrigger(hour=mid["hour"], minute=mid["minute"], timezone=TIMEZONE),
        id="midday_check",
        name="점심 중간 점검",
    )

    closing = SCHEDULE["closing_signal"]
    scheduler.add_job(
        job_signal_scan,
        CronTrigger(hour=closing["hour"], minute=closing["minute"], timezone=TIMEZONE),
        id="closing_signal",
        name="장 마감 직전 시그널",
    )

    daily = SCHEDULE["daily_report"]
    scheduler.add_job(
        job_daily_report,
        CronTrigger(hour=daily["hour"], minute=daily["minute"], timezone=TIMEZONE),
        id="daily_report",
        name="일간 종합 리포트",
    )

    # 장중 5분 간격 손절 모니터링 (09:05 ~ 15:30)
    scheduler.add_job(
        job_stop_loss_monitor,
        CronTrigger(
            hour="9-15",
            minute="*/5",
            second=0,
            timezone=TIMEZONE,
        ),
        id="stop_loss_monitor",
        name="손절 모니터링",
    )

    return scheduler


# ── 진입점 ──────────────────────────────────────────────────────────────────

async def main() -> None:
    logger.info("봇 시작 중...")
    init_db()

    scheduler = build_scheduler()
    scheduler.start()
    logger.info("스케줄러 시작 완료")

    # 시작 직후 즉시 1회 스캔
    await job_signal_scan()

    try:
        # asyncio 루프 유지
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("봇 종료")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
