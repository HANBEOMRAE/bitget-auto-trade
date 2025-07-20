from bitget.client import Client
from app.config import EX_API_KEY, EX_API_SECRET, EX_API_PASSPHRASE
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_bitget_client: Client | None = None

def get_bitget_client() -> Client:
    global _bitget_client
    if _bitget_client is None:
        if not EX_API_KEY or not EX_API_SECRET or not EX_API_PASSPHRASE:
            logger.error("Bitget API 키/시크릿/패스프레이즈가 설정되지 않았습니다.")
            raise RuntimeError("Missing Bitget API credentials.")
        # ✅ 위치 기반 초기화 방식 사용
        _bitget_client = Client(
            EX_API_KEY,
            EX_API_SECRET,
            EX_API_PASSPHRASE,
            use_server_time=False  # 선택 인자, 필요 시 True로 변경
        )
        logger.info("Initialized python-bitget Client.")
    return _bitget_client

