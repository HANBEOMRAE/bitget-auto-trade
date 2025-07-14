import os
from dotenv import load_dotenv

load_dotenv()

EX_API_KEY = os.getenv("EX_API_KEY")
EX_API_SECRET = os.getenv("EX_API_SECRET")
EX_API_PASSPHRASE = os.getenv("EX_API_PASSPHRASE")

# ✅ 추가해야 할 항목
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", 1.0))   # 기본값 1초
MAX_WAIT = int(os.getenv("MAX_WAIT", 10))                # 기본값 10초
