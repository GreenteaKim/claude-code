import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]

# ── 감시 종목 ──────────────────────────────────────────
TARGETS: dict[str, dict] = {
    "005930": {"name": "삼성전자", "sector": "반도체"},
    "000660": {"name": "SK하이닉스", "sector": "반도체"},
    "402340": {"name": "SK스퀘어", "sector": "지주회사"},
}

# ── 앙상블 임계값 ───────────────────────────────────────
ENSEMBLE_BUY_THRESHOLD: float = float(os.getenv("ENSEMBLE_BUY_THRESHOLD", "0.6"))
ENSEMBLE_STRONG_BUY_THRESHOLD: float = float(os.getenv("ENSEMBLE_STRONG_BUY_THRESHOLD", "1.2"))
ENSEMBLE_SELL_THRESHOLD: float = float(os.getenv("ENSEMBLE_SELL_THRESHOLD", "-0.6"))
ENSEMBLE_STRONG_SELL_THRESHOLD: float = float(os.getenv("ENSEMBLE_STRONG_SELL_THRESHOLD", "-1.2"))

# ── 손절 설정 ───────────────────────────────────────────
LIVERMORE_STOP_LOSS_PCT: float = float(os.getenv("LIVERMORE_STOP_LOSS_PCT", "0.08"))
ONEIL_STOP_LOSS_PCT: float = float(os.getenv("ONEIL_STOP_LOSS_PCT", "0.07"))

# ── 데이터 기간 ─────────────────────────────────────────
LOOKBACK_DAYS: int = int(os.getenv("LOOKBACK_DAYS", "400"))  # 여유있게 400일
WEEKLY_LOOKBACK_WEEKS: int = int(os.getenv("WEEKLY_LOOKBACK_WEEKS", "60"))

# ── 스케줄 (KST) ───────────────────────────────────────
TIMEZONE = "Asia/Seoul"
SCHEDULE = {
    "pre_market_scan": {"hour": 8, "minute": 30},
    "market_open_signal": {"hour": 9, "minute": 5},
    "midday_check": {"hour": 12, "minute": 30},
    "closing_signal": {"hour": 15, "minute": 20},
    "daily_report": {"hour": 15, "minute": 40},
    "stop_loss_interval_minutes": 5,
}

# ── DB ─────────────────────────────────────────────────
DB_PATH = "signals.db"

# ── 보유 포지션 (.env에서 POSITION_{코드}_ENTRY=평균매수가 형식으로 입력) ──
def _load_positions() -> dict[str, float]:
    positions = {}
    for code in TARGETS:
        val = os.getenv(f"POSITION_{code}_ENTRY")
        if val:
            try:
                positions[code] = float(val)
            except ValueError:
                pass
    return positions

MY_POSITIONS: dict[str, float] = _load_positions()  # {종목코드: 평균매수가}

# ── 신규 추천 스크리닝 유니버스 (KOSPI 주요 30종목) ────────────────────────
SCREENING_UNIVERSE: dict[str, str] = {
    # 반도체·IT
    "000660": "SK하이닉스",
    "005930": "삼성전자",
    "066570": "LG전자",
    "034730": "SK",
    "036570": "엔씨소프트",
    # 2차전지·전기차
    "373220": "LG에너지솔루션",
    "006400": "삼성SDI",
    "051910": "LG화학",
    "247540": "에코프로비엠",
    "086520": "에코프로",
    # 자동차
    "005380": "현대차",
    "000270": "기아",
    "012330": "현대모비스",
    # 바이오·헬스케어
    "207940": "삼성바이오로직스",
    "068270": "셀트리온",
    "326030": "SK바이오팜",
    "091990": "셀트리온헬스케어",
    # 금융
    "105560": "KB금융",
    "055550": "신한지주",
    "086790": "하나금융지주",
    "316140": "우리금융지주",
    # 통신·플랫폼
    "035420": "NAVER",
    "035720": "카카오",
    "017670": "SK텔레콤",
    "030200": "KT",
    # 에너지·화학
    "010950": "S-Oil",
    "011170": "롯데케미칼",
    # 유통·소비
    "069960": "현대백화점",
    "023530": "롯데쇼핑",
    # 철강·소재
    "005490": "POSCO홀딩스",
}

# 스크리닝에서 TARGETS(보유 종목)는 제외
SCREENING_UNIVERSE = {
    k: v for k, v in SCREENING_UNIVERSE.items() if k not in TARGETS
}

# 추천 종목 최대 수
MAX_RECOMMENDATIONS: int = int(os.getenv("MAX_RECOMMENDATIONS", "5"))
