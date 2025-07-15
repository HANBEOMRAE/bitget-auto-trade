import logging
from bitget.client import Client
from app.config import EX_API_KEY, EX_API_SECRET, EX_API_PASSPHRASE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 싱글톤으로 Bitget Client 인스턴스 관리
_bitget_client: Client | None = None

def get_bitget_client() -> Client:
    """
    실거래용 Bitget Client를 반환합니다.
    EX_API_KEY/EX_API_SECRET/EX_API_PASSPHRASE 환경변수가 설정되어 있지 않으면 에러를 발생시킵니다.
    """
    global _bitget_client

    if _bitget_client is None:
        if not EX_API_KEY or not EX_API_SECRET or not EX_API_PASSPHRASE:
            logger.error("Bitget API 키/시크릿/패스프레이즈가 .env에 설정되지 않았습니다.")
            raise RuntimeError("Missing Bitget API credentials.")

        # base_url 제거 (이 인자는 지원되지 않음)
        _bitget_client = Client(
            EX_API_KEY,
            EX_API_SECRET,
            EX_API_PASSPHRASE,
            use_server_time=True
        )
        logger.info("Initialized live Bitget Client.")

    return _bitget_client