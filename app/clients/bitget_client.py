import logging
from app.config import EX_API_KEY, EX_API_SECRET, EX_API_PASSPHRASE
from bitget.client.mix.mix_account import MixAccountClient
from bitget.client.mix.mix_order import MixOrderClient
from bitget.client.mix.mix_position import MixPositionClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_mix_account_client: MixAccountClient | None = None
_mix_order_client: MixOrderClient | None = None
_mix_position_client: MixPositionClient | None = None

def get_mix_account_client() -> MixAccountClient:
    global _mix_account_client
    if _mix_account_client is None:
        if not EX_API_KEY or not EX_API_SECRET or not EX_API_PASSPHRASE:
            logger.error("Bitget API 키가 설정되지 않았습니다.")
            raise RuntimeError("Missing Bitget API credentials.")
        _mix_account_client = MixAccountClient(EX_API_KEY, EX_API_SECRET, EX_API_PASSPHRASE, use_server_time=True)
        logger.info("MixAccountClient initialized.")
    return _mix_account_client

def get_mix_order_client() -> MixOrderClient:
    global _mix_order_client
    if _mix_order_client is None:
        _mix_order_client = MixOrderClient(EX_API_KEY, EX_API_SECRET, EX_API_PASSPHRASE, use_server_time=True)
        logger.info("MixOrderClient initialized.")
    return _mix_order_client

def get_mix_position_client() -> MixPositionClient:
    global _mix_position_client
    if _mix_position_client is None:
        _mix_position_client = MixPositionClient(EX_API_KEY, EX_API_SECRET, EX_API_PASSPHRASE, use_server_time=True)
        logger.info("MixPositionClient initialized.")
    return _mix_position_client