import logging
from bitget.client import Client
from app.config import EX_API_KEY, EX_API_SECRET, EX_API_PASSPHRASE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_bitget_client: Client | None = None  # Python 3.10 이상 OK

def get_bitget_client() -> Client:
    global _bitget_client

    if _bitget_client is None:
        missing = []
        if not EX_API_KEY:
            missing.append("EX_API_KEY")
        if not EX_API_SECRET:
            missing.append("EX_API_SECRET")
        if not EX_API_PASSPHRASE:
            missing.append("EX_API_PASSPHRASE")

        if missing:
            logger.error(f"Bitget API 설정 누락: {', '.join(missing)}")
            raise RuntimeError(f"Bitget API 설정 누락: {', '.join(missing)}")

        # ✅ use_server_time=True 권장 (타임오프셋 문제 방지)
        _bitget_client = Client(
            EX_API_KEY,
            EX_API_SECRET,
            EX_API_PASSPHRASE,
            use_server_time=True
        )
        logger.info("✅ Bitget Client 초기화 완료")

    return _bitget_client