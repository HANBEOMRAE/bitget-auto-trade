# app/services/monitor.py

import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from app.clients.bitget_client import get_bitget_client
from app.state import monitor_state
from app.config import POLL_INTERVAL

logger = logging.getLogger("monitor")
logger.setLevel(logging.INFO)


def _poll_price_loop():
    client = get_bitget_client()
    symbol = monitor_state.get("symbol")

    if not symbol:
        logger.warning("모니터 시작 전 symbol이 설정되지 않았습니다.")
        return

    while True:
        try:
            qty = monitor_state.get("position_qty", 0)
            entry_price = monitor_state.get("entry_price", 0)

            if qty > 0 and entry_price > 0:
                ticker = client.mix_get_market_price(symbol=symbol)
                current_price = float(ticker["price"])
                pnl = (current_price / entry_price - 1) * 100
                now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")

                monitor_state.update({
                    "current_price": current_price,
                    "pnl": pnl,
                    "last_checked": now
                })

                logger.info(f"[{now}] {symbol} 현재가: {current_price}, 수익률: {pnl:.2f}%")

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            logger.exception(f"가격 모니터링 중 오류 발생: {e}")
            time.sleep(POLL_INTERVAL)


def start_monitor():
    logger.info("Bitget 가격 모니터 시작")
    from threading import Thread
    thread = Thread(target=_poll_price_loop, daemon=True)
    thread.start()
