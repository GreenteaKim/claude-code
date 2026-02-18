"""pykrx 기반 주가/거래량/수급 데이터 수집 (캐시 우선)"""
from __future__ import annotations

import time
from datetime import date, timedelta

import pandas as pd
from pykrx import stock as krx

from config import LOOKBACK_DAYS
from data.cache import load_cached, missing_dates, save_to_cache
from db.database import init_db


def get_ohlcv(
    stock_code: str,
    end_date: date | None = None,
    lookback_days: int = LOOKBACK_DAYS,
) -> pd.DataFrame:
    """
    종목 OHLCV + 수급(외국인/기관 순매수) DataFrame 반환.
    캐시 우선, 없는 날짜만 pykrx로 수집.

    컬럼: Open, High, Low, Close, Volume, ForeignNetBuy, InstitutionNetBuy
    인덱스: datetime
    """
    init_db()

    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)

    # 캐시 확인
    fetch_start, fetch_end = missing_dates(stock_code, start_date, end_date)

    if fetch_start and fetch_end:
        _fetch_and_cache(stock_code, fetch_start, fetch_end)

    df = load_cached(stock_code, start_date, end_date)
    return df


def get_current_price(stock_code: str) -> tuple[float, float]:
    """(현재가, 전일 대비 등락률%) 반환"""
    today = date.today().strftime("%Y%m%d")
    try:
        df = krx.get_market_ohlcv_by_date(today, today, stock_code)
        if df.empty:
            # 장 마감/휴장 시 최근 거래일 데이터 사용
            recent = get_ohlcv(stock_code, lookback_days=5)
            if recent.empty:
                return 0.0, 0.0
            last = recent.iloc[-1]
            prev = recent.iloc[-2] if len(recent) >= 2 else recent.iloc[-1]
            price = float(last["Close"])
            change_pct = (last["Close"] - prev["Close"]) / prev["Close"] * 100
            return price, round(change_pct, 2)

        price = float(df["종가"].iloc[-1])
        change_pct = float(df["등락률"].iloc[-1]) if "등락률" in df.columns else 0.0
        return price, round(change_pct, 2)
    except Exception:
        recent = get_ohlcv(stock_code, lookback_days=5)
        if recent.empty:
            return 0.0, 0.0
        last = recent.iloc[-1]
        prev = recent.iloc[-2] if len(recent) >= 2 else recent.iloc[-1]
        price = float(last["Close"])
        change_pct = (last["Close"] - prev["Close"]) / prev["Close"] * 100
        return price, round(change_pct, 2)


def get_kospi_data() -> tuple[float, float]:
    """(KOSPI 현재지수, 등락률%) 반환"""
    today = date.today().strftime("%Y%m%d")
    try:
        df = krx.get_index_ohlcv_by_date(today, today, "1001")  # KOSPI
        if df.empty:
            return 0.0, 0.0
        price = float(df["종가"].iloc[-1])
        change_pct = float(df["등락률"].iloc[-1]) if "등락률" in df.columns else 0.0
        return price, round(change_pct, 2)
    except Exception:
        return 0.0, 0.0


# ── 내부 함수 ──────────────────────────────────────────────────────────────


def _fetch_and_cache(
    stock_code: str, start: date, end: date
) -> None:
    """pykrx 호출 → SQLite 캐시 저장"""
    fmt_start = start.strftime("%Y%m%d")
    fmt_end = end.strftime("%Y%m%d")

    try:
        # OHLCV
        ohlcv = krx.get_market_ohlcv_by_date(fmt_start, fmt_end, stock_code)
        time.sleep(0.3)  # pykrx 호출 속도 제한

        # 외국인/기관 순매수
        trading = krx.get_market_trading_value_by_date(
            fmt_start, fmt_end, stock_code
        )
        time.sleep(0.3)
    except Exception as e:
        print(f"[fetcher] {stock_code} 데이터 수집 실패: {e}")
        return

    if ohlcv.empty:
        return

    # 컬럼명 표준화
    ohlcv = ohlcv.rename(
        columns={
            "시가": "Open",
            "고가": "High",
            "저가": "Low",
            "종가": "Close",
            "거래량": "Volume",
        }
    )

    if not trading.empty:
        ohlcv["ForeignNetBuy"] = trading.get("외국인합계", 0)
        ohlcv["InstitutionNetBuy"] = trading.get("기관합계", 0)

    save_to_cache(stock_code, ohlcv[["Open", "High", "Low", "Close", "Volume",
                                     "ForeignNetBuy", "InstitutionNetBuy"]])
