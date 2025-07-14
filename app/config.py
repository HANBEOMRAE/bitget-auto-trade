import os
from dotenv import load_dotenv

# .env 환경 변수 로드
load_dotenv()

# 🔐 Bitget API 인증정보
EX_API_KEY = os.getenv("BITGET_API_KEY")
EX_API_SECRET = os.getenv("BITGET_API_SECRET")
EX_API_PASSPHRASE = os.getenv("BITGET_API_PASSPHRASE")

# ⚙️ 시스템 환경 설정
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"         # 드라이런 모드 여부
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", 1.0))            # 신호 체크 간격 (초)
MAX_WAIT = int(os.getenv("MAX_WAIT", 10))                         # 포지션 대기 시간 (초)

# ⚖️ 매매 전략 설정
BUY_PCT = float(os.getenv("BUY_PCT", 0.98))                       # 자본 비율 사용
TRADE_LEVERAGE = float(os.getenv("TRADE_LEVERAGE", 3.0))         # 레버리지 설정
TP_RATIO = float(os.getenv("TP_RATIO", 1.01))                    # 익절 기준 비율
TP_PART_RATIO = float(os.getenv("TP_PART_RATIO", 0.3))           # 1차 익절 비율
SL_RATIO = float(os.getenv("SL_RATIO", 0.99))                    # 손절 기준 비율
