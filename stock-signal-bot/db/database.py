"""SQLite 연결 및 테이블 초기화"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH

_CREATE_SIGNAL_HISTORY = """
CREATE TABLE IF NOT EXISTS signal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    ensemble_score REAL NOT NULL,
    strategy_details TEXT NOT NULL,
    price_at_signal REAL NOT NULL,
    volume_at_signal INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_POSITIONS = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    entry_price REAL NOT NULL,
    entry_date TIMESTAMP NOT NULL,
    stop_loss_price REAL NOT NULL,
    status TEXT DEFAULT 'OPEN',
    exit_price REAL,
    exit_date TIMESTAMP,
    exit_reason TEXT
);
"""

_CREATE_DAILY_MARKET_DATA = """
CREATE TABLE IF NOT EXISTS daily_market_data (
    stock_code TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    foreign_net_buy INTEGER,
    institutional_net_buy INTEGER,
    PRIMARY KEY (stock_code, date)
);
"""


def init_db(db_path: str = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(_CREATE_SIGNAL_HISTORY)
        conn.execute(_CREATE_POSITIONS)
        conn.execute(_CREATE_DAILY_MARKET_DATA)
        conn.commit()


@contextmanager
def get_conn(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
