"""일간 OHLCV 데이터 SQLite 캐싱"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from db.database import get_conn


def load_cached(stock_code: str, start: date, end: date) -> pd.DataFrame:
    """캐시에서 데이터 로드. 없으면 빈 DataFrame 반환."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT date, open, high, low, close, volume,
                   foreign_net_buy, institutional_net_buy
            FROM daily_market_data
            WHERE stock_code = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
            """,
            (stock_code, start.isoformat(), end.isoformat()),
        ).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df.columns = [c.title() if c in ("open", "high", "low", "close") else c for c in df.columns]
    df.rename(
        columns={
            "volume": "Volume",
            "foreign_net_buy": "ForeignNetBuy",
            "institutional_net_buy": "InstitutionNetBuy",
        },
        inplace=True,
    )
    return df


def save_to_cache(stock_code: str, df: pd.DataFrame) -> None:
    """DataFrame을 캐시에 upsert"""
    if df.empty:
        return

    df2 = df.copy()
    df2.index = pd.to_datetime(df2.index)

    with get_conn() as conn:
        for dt, row in df2.iterrows():
            conn.execute(
                """
                INSERT OR REPLACE INTO daily_market_data
                    (stock_code, date, open, high, low, close, volume,
                     foreign_net_buy, institutional_net_buy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stock_code,
                    dt.strftime("%Y-%m-%d"),
                    row.get("Open"),
                    row.get("High"),
                    row.get("Low"),
                    row.get("Close"),
                    row.get("Volume"),
                    row.get("ForeignNetBuy"),
                    row.get("InstitutionNetBuy"),
                ),
            )


def missing_dates(
    stock_code: str, start: date, end: date
) -> tuple[date | None, date | None]:
    """캐시에 없는 날짜 범위 반환 (start, end). 모두 있으면 (None, None)."""
    cached = load_cached(stock_code, start, end)
    if cached.empty:
        return start, end

    cached_dates = set(cached.index.date)
    # 간단 체크: 가장 최근 캐시 날짜 이후가 빠져있는지 확인
    last_cached = max(cached_dates)
    if last_cached < end:
        return last_cached + timedelta(days=1), end

    return None, None
