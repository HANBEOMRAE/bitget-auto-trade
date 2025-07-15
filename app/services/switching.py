import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.clients.bitget_client import (
    get_mix_account_client,
    get_mix_order_client,
    get_mix_position_client
)
from app.config import DRY_RUN, POLL_INTERVAL, MAX_WAIT
from app.services.buy import execute_buy
from app.services.sell import execute_sell
from app.state import monitor_state

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PRODUCT_TYPE = "umcbl"

def _wait_for(symbol: str, target_amt: float) -> bool:
    position_client = get_mix_position_client()
    start = time.time()
    current = 0.0

    while time.time() - start < MAX_WAIT:
        data = position_client.get_position(symbol=symbol, productType=PRODUCT_TYPE)
        positions = data.get("data", [])
        for p in positions:
            if p.get("symbol") == symbol:
                current = float(p.get("holdVol", 0))
                break

        if target_amt > 0 and current > 0:
            return True
        if target_amt < 0 and current < 0:
            return True
        if target_amt == 0 and current == 0:
            return True

        time.sleep(POLL_INTERVAL)

    logger.warning(f"Switch timeout: target {target_amt}, current {current}")
    return False

def _cancel_open_reduceonly_orders(symbol: str):
    order_client = get_mix_order_client()
    orders = order_client.get_all_open_orders(productType=PRODUCT_TYPE, symbol=symbol)
    for order in orders.get("data", []):
        if order.get("reduceOnly"):
            order_client.cancel_order(symbol=symbol, orderId=order["orderId"], productType=PRODUCT_TYPE)
            logger.info(f"[Cleanup] Canceled reduceOnly order {order['orderId']}")

def switch_position(symbol: str, action: str) -> dict:
    account_client = get_mix_account_client()
    order_client = get_mix_order_client()
    position_client = get_mix_position_client()

    if DRY_RUN:
        logger.info(f"[DRY_RUN] switch_position {action} {symbol}")
        return {"skipped": "dry_run"}

    monitor_state["trade_count"] += 1
    monitor_state["sl_triggered"] = False

    acc_data = account_client.get_account(symbol=symbol, productType=PRODUCT_TYPE)
    current_amt = next((float(p["marginAmount"]) for p in acc_data["data"] if p["symbol"] == symbol), 0.0)

    if action.upper() == "BUY":
        if current_amt > 0:
            return {"skipped": "already_long"}

        if current_amt < 0:
            qty = abs(current_amt)
            logger.info(f"Closing SHORT {qty} @ market for {symbol}")
            order_client.place_market_order(
                symbol=symbol,
                productType=PRODUCT_TYPE,
                marginCoin="USDT",
                size=str(qty),
                side="buy",
                reduceOnly=True
            )
            if not _wait_for(symbol, 0.0):
                return {"skipped": "close_failed"}

            if monitor_state.get("sl_triggered", False):
                logger.info(f"[Switch] SL-triggered close → cleaning up TP/SL")
                _cancel_open_reduceonly_orders(symbol)

        return execute_buy(symbol)

    if action.upper() == "SELL":
        if current_amt < 0:
            return {"skipped": "already_short"}

        if current_amt > 0:
            qty = abs(current_amt)
            logger.info(f"Closing LONG {qty} @ market for {symbol}")
            order_client.place_market_order(
                symbol=symbol,
                productType=PRODUCT_TYPE,
                marginCoin="USDT",
                size=str(qty),
                side="sell",
                reduceOnly=True
            )
            if not _wait_for(symbol, 0.0):
                return {"skipped": "close_failed"}

            if monitor_state.get("sl_triggered", False):
                logger.info(f"[Switch] SL-triggered close → cleaning up TP/SL")
                _cancel_open_reduceonly_orders(symbol)

        return execute_sell(symbol)

    logger.error(f"Unknown action for switch: {action}")
    return {"skipped": "unknown_action"}