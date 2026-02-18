"""시그널 이력 저장/조회 및 중복 방지"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from db.database import get_conn
from signals.models import EnsembleSignal, SignalType


def save_signal(signal: EnsembleSignal, volume: int | None = None) -> int:
    strategy_details = json.dumps(
        [
            {
                "name": s.strategy_name,
                "signal": s.signal.name,
                "reason": s.reason,
                "indicators": s.indicators,
            }
            for s in signal.strategy_signals
        ],
        ensure_ascii=False,
    )

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO signal_history
                (stock_code, stock_name, signal_type, ensemble_score,
                 strategy_details, price_at_signal, volume_at_signal)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.stock_code,
                signal.stock_name,
                signal.signal.name,
                signal.ensemble_score,
                strategy_details,
                signal.price,
                volume,
            ),
        )
        return cur.lastrowid


def is_duplicate(
    stock_code: str,
    signal_type: SignalType,
    within_hours: int = 6,
) -> bool:
    """최근 N시간 내 동일 종목·동일 방향 시그널이 있으면 True"""
    cutoff = datetime.now() - timedelta(hours=within_hours)
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM signal_history
            WHERE stock_code = ?
              AND signal_type = ?
              AND created_at >= ?
            """,
            (stock_code, signal_type.name, cutoff.isoformat()),
        ).fetchone()
        return row["cnt"] > 0


def get_recent_signals(stock_code: str, limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM signal_history
            WHERE stock_code = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (stock_code, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def save_position(
    stock_code: str,
    entry_price: float,
    stop_loss_price: float,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO positions (stock_code, entry_price, entry_date, stop_loss_price)
            VALUES (?, ?, ?, ?)
            """,
            (stock_code, entry_price, datetime.now().isoformat(), stop_loss_price),
        )
        return cur.lastrowid


def get_open_positions() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM positions WHERE status = 'OPEN'"
        ).fetchall()
        return [dict(r) for r in rows]


def close_position(
    position_id: int,
    exit_price: float,
    exit_reason: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE positions
            SET status = 'CLOSED', exit_price = ?, exit_date = ?, exit_reason = ?
            WHERE id = ?
            """,
            (exit_price, datetime.now().isoformat(), exit_reason, position_id),
        )
