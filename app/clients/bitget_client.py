import logging
from bitget.client import Client
from app.config import EX_API_KEY, EX_API_SECRET, EX_API_PASSPHRASE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_bitget_client: Client | None = None

def get_bitget_client() -> Client:
    """
    Bitget 공식 python-bitget 라이브러리를 사용한 클라이언트 반환
    """
    global _bitget_client
    if _bitget_client is None:
        if not EX_API_KEY or not EX_API_SECRET or not EX_API_PASSPHRASE:
            logger.error("Bitget API 키/시크릿/패스프레이즈가 설정되지 않았습니다.")
            raise RuntimeError("Missing Bitget API credentials.")

        _bitget_client = Client(
            api_key=EX_API_KEY,
            api_secret=EX_API_SECRET,
            passphrase=EX_API_PASSPHRASE,
        )
        logger.info("Initialized python-bitget Client.")

    return _bitget_client