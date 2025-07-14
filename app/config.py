import os
from dotenv import load_dotenv

load_dotenv()

EX_API_KEY = os.getenv("EX_API_KEY")
EX_API_SECRET = os.getenv("EX_API_SECRET")
EX_API_PASSPHRASE = os.getenv("EX_API_PASSPHRASE")

# DRY_RUN 설정
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# 대기 시간 설정
POLL_INTERVAL = 1
MAX_WAIT = 30
