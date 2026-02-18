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
