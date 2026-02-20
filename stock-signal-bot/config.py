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

# ── 스케줄 (KST) ───────────────────────────────────────────────
TIMEZONE = "Asia/Seoul"
SCHEDULE = {
    "pre_market_scan": {"hour": 8, "minute": 30},
    "market_open_signal": {"hour": 9, "minute": 5},
    "midday_check": {"hour": 12, "minute": 30},
    "closing_signal": {"hour": 15, "minute": 20},
    "daily_report": {"hour": 15, "minute": 40},
    "stop_loss_interval_minutes": 5,
    # KOSPI200 스크리닝: 일간리포트 전 09:00, 장중 12:00, 장 마감 15:10
    "kospi200_screening": [
        {"hour": 9, "minute": 0},
        {"hour": 12, "minute": 0},
        {"hour": 15, "minute": 10},
    ],
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

# ── 신규 추천 스크리닝 유니버스 (KOSPI & KOSDAQ 주도주 중심) ───────────────
SCREENING_UNIVERSE: dict[str, str] = {
    # IT/반도체
    "005930": "삼성전자", "000660": "SK하이닉스",
    "042700": "한미반도체", "259960": "크래프톤", "035420": "NAVER",
    "035720": "카카오", "018260": "삼성SDS", "022100": "포스코DX",
    "293490": "카카오게임즈", "112040": "위메이드",
    # 자동차/운수장비
    "005380": "현대차", "000270": "기아", "012330": "현대모비스",
    "028150": "GS건설", "042660": "한화오션", "010140": "삼성중공업",
    # 2차전지/화학/에너지
    "373220": "LG에너지솔루션", "006400": "삼성SDI", "051910": "LG화학",
    "096770": "SK이노베이션", "003670": "포스코퓨처엠", "247540": "에코프로비엠",
    "086520": "에코프로", "066970": "엘앤에프", "005490": "POSCO홀딩스",
    # 바이오/헬스케어
    "207940": "삼성바이오로직스", "068270": "셀트리온", "000100": "유한양행",
    "128940": "한미약품", "196170": "알테오젠", "214150": "클래시스", "145020": "휴젤",
    # 금융/지주
    "105560": "KB금융", "055550": "신한지주", "086790": "하나금융지주",
    "006800": "미래에셋증권", "039490": "키움증권", "032640": "LG유플러스", 
    "017670": "SK텔레콤", "030200": "KT", "033780": "KT&G",
    # 필수소비재/유통/기타
    "051900": "LG생활건강", "090430": "아모레퍼시픽", "028260": "삼성물산",
    "010950": "S-Oil", "018880": "한온시스템", "034020": "두산에너빌리티",
    "011200": "HMM", "023530": "롯데쇼핑"
}

# 스크리닝에서 TARGETS(보유 종목)는 제외
SCREENING_UNIVERSE = {
    k: v for k, v in SCREENING_UNIVERSE.items() if k not in TARGETS
}

# 추천 종목 최대 수
MAX_RECOMMENDATIONS: int = int(os.getenv("MAX_RECOMMENDATIONS", "5"))

# KOSPI200 스크리닝 병렬 워커 수
# 펢뢡 제한 종목(DB IO 많음) → 3개 정도가 안전
SCREENER_WORKERS: int = int(os.getenv("SCREENER_WORKERS", "3"))
