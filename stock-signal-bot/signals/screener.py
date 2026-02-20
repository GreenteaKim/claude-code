"""KOSPI200 전체 종목 스크리닝 — 신규 추천 종목 발굴"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import MAX_RECOMMENDATIONS, SCREENING_UNIVERSE, SCREENER_WORKERS
from data.fetcher import get_current_price, get_ohlcv, get_kospi200_tickers
from signals.models import Recommendation, SignalType
from strategies.ensemble import generate_ensemble_signal

logger = logging.getLogger(__name__)

# 추천 대상 시그널 (BUY 이상만)
_BUY_SIGNALS = {SignalType.BUY, SignalType.STRONG_BUY}


import yfinance as yf
from datetime import date, timedelta

def check_global_market_status(ma_period: int = 120) -> tuple[bool, str]:
    """
    한국(KOSPI) 및 글로벌(SPY, QQQ) 지수의 120일 이동평균선(MA)을 확인.
    KOSPI가 강세(>120MA)이면서, SPY나 QQQ 중 하나라도 강세여야 BULL 마켓으로 판단.
    """
    import pandas as pd
    try:
        end_d = date.today()
        start_d = end_d - timedelta(days=300)
        s_date, e_date = start_d.strftime("%Y%m%d"), end_d.strftime("%Y%m%d")
        
        # 1. KOSPI 필터
        krx_df = get_ohlcv("069500") # KODEX200 proxy
        if krx_df.empty:
            # krx로 호출시 069500 (KODEX200) fallback. 안되면 통과
            return True, "KOSPI 데이터 수집 실패 (필터 무시)"
            
        k_close = krx_df["Close"].iloc[-1]
        k_ma = krx_df["Close"].rolling(ma_period).mean().iloc[-1]
        kospi_bull = (k_close > k_ma)
        
        # 2. 글로벌 필터 (SPY, QQQ)
        spy = yf.download("SPY", start=start_d, progress=False)
        qqq = yf.download("QQQ", start=start_d, progress=False)
        
        if spy.empty or qqq.empty:
            return kospi_bull, f"KOSPI > {ma_period}MA: {kospi_bull} (글로벌 데이터 수집 실패)"
            
        def get_close(df):
            if isinstance(df.columns, pd.MultiIndex):
                return df["Close"].iloc[:,0] if "Close" in df.columns else df.iloc[:,0]
            return df["Close"]
            
        spy_c = get_close(spy)
        qqq_c = get_close(qqq)
        
        spy_bull = spy_c.iloc[-1] > spy_c.rolling(ma_period).mean().iloc[-1]
        qqq_bull = qqq_c.iloc[-1] > qqq_c.rolling(ma_period).mean().iloc[-1]
        
        is_bull = kospi_bull and (spy_bull or qqq_bull)
        
        msgs = []
        msgs.append(f"KOSPI {'강세' if kospi_bull else '약세'}")
        msgs.append(f"S&P500 {'강세' if spy_bull else '약세'}")
        msgs.append(f"NASDAQ {'강세' if qqq_bull else '약세'}")
        status_msg = f"{ma_period}일선 기준: " + ", ".join(msgs)
        
        return is_bull, status_msg
        
    except Exception as e:
        logger.warning(f"마켓 필터 오류: {e}")
        return True, "마켓 필터 오류 (필터 무시)"

def run_screening() -> list[Recommendation]:
    """
    KOSPI200 (혹은 정적 유니버스) 전체 종목을 스캔해 BUY 이상 시그널 종목을 반환.
    단, 글로벌 글로벌 마켓 필터가 '약세'를 가리키면 추천 스킵.
    """
    # ── 1. 마켓 상태 확인 ───────────────────────────────────────────────
    import pandas as pd
    is_bull, market_msg = check_global_market_status(120)
    logger.info(f"[screener] 글로벌 마켓 상태 확인: {market_msg}")
    
    if not is_bull:
        logger.info("[screener] 글로벌 연동 120일 MA 약세장 ⚠️ → 현금 관망 모드")
        return [
            Recommendation(
                stock_code="MARKET_WEAK",
                stock_name="⚠️ 관망장세",
                signal=SignalType.NEUTRAL,
                ensemble_score=0.0,
                price=0.0,
                change_pct=0.0,
                top_reasons=[
                    f"글로벌 마켓 연동 필터 발동",
                    market_msg,
                    "시장 약세 국면이므로 안전을 위해 신규 종목 추천을 생략하고 현금 대기(관망)를 권장합니다."
                ]
            )
        ]

    # ── 유니버스 결정 ──────────────────────────────────────────────────────
    try:
        target_universe = get_kospi200_tickers()
    except Exception:
        target_universe = {}
        
    if not target_universe:
        logger.warning("KOSPI200 목록 조회 실패 → config.SCREENING_UNIVERSE 사용")
        target_universe = SCREENING_UNIVERSE
    else:
        logger.info(f"KOSPI200 종목 {len(target_universe)}개 스캔 시작")

    # ── 병렬 스크리닝 ──────────────────────────────────────────────────────
    candidates: list[tuple[float, Recommendation]] = []
    total = len(target_universe)
    done = 0

    with ThreadPoolExecutor(max_workers=SCREENER_WORKERS) as pool:
        futures = {
            pool.submit(_screen_stock, code, name): (code, name)
            for code, name in target_universe.items()
        }
        for future in as_completed(futures):
            code, name = futures[future]
            done += 1
            try:
                rec = future.result()
                if rec and rec.signal in _BUY_SIGNALS:
                    candidates.append((rec.ensemble_score, rec))
                    logger.debug(f"[screener] ✅ {name}({code}) 추천 후보 추가 (score={rec.ensemble_score:.2f})")
            except Exception as e:
                logger.warning(f"[screener] {name}({code}) 분석 실패: {e}")

            if done % 20 == 0 or done == total:
                logger.info(f"[screener] 진행: {done}/{total} 완료, 후보: {len(candidates)}개")

    candidates.sort(key=lambda x: x[0], reverse=True)
    result = [rec for _, rec in candidates[:MAX_RECOMMENDATIONS]]
    
    # 만일 시장은 불(Bull)장이지만 BUY 조건 통과 종목이 없을 때
    if not result:
        result = [
            Recommendation(
                stock_code="NO_TARGET",
                stock_name="추천 종목 없음",
                signal=SignalType.NEUTRAL,
                ensemble_score=0.0, price=0.0, change_pct=0.0,
                top_reasons=[market_msg, "현재 시장 강세 요건은 충족했으나, 알고리즘 매수 기준에 도달한 주도주가 없습니다."]
            )
        ]
        
    logger.info(f"[screener] 스크리닝 완료 → 추천 {len(result)}개 선정")
    return result


def _screen_stock(code: str, name: str) -> Recommendation | None:
    """단일 종목 분석 (ThreadPoolExecutor에서 호출됨)"""
    try:
        df = get_ohlcv(code)
        if df.empty or len(df) < 60:
            return None

        price, change_pct = get_current_price(code)
        if price == 0:
            return None

        # stock_name을 직접 전달해서 TARGETS 조회 없이도 올바른 이름 사용
        ensemble = generate_ensemble_signal(code, df, price, change_pct, stock_name=name)

        # 주요 매수 근거 추출 (BUY+ 시그널을 낸 전략들의 reason)
        top_reasons = [
            f"{s.strategy_name}: {s.reason}"
            for s in ensemble.strategy_signals
            if s.signal in _BUY_SIGNALS
        ][:3]

        return Recommendation(
            stock_code=code,
            stock_name=name,
            signal=ensemble.signal,
            ensemble_score=ensemble.ensemble_score,
            price=price,
            change_pct=change_pct,
            top_reasons=top_reasons,
        )
    except Exception as e:
        logger.debug(f"[screener] {name}({code}) 내부 오류: {e}")
        return None
