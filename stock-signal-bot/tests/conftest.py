import sys
import os

# stock-signal-bot/ 을 sys.path에 추가해 절대 임포트 사용
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 테스트용 더미 환경변수 설정
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test_chat_id")
