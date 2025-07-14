import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.clients.bitget_client import get_bitget_client
from app.config import DRY_RUN, POLL_INTERVAL, MAX_WAIT
from app.services.buy import execute_buy
from app.services.sell import execute_sell
from app.state import monitor_state

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def _wait_for(symbol: str, target_amt: float) -> bool:
    client = get_bitget_client()
    start = time.time()
    current = None

    while time.time() - start < MAX_WAIT:
        positions = client.mix_get_account(symbol=symbol, productType="umcbl")
        current = next((float(p["holdVol"]) for p in positions["data"] if p["symbol"] == symbol), 0.0)

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
    client = get_bitget_client()
    orders = client.mix_get_all_open_orders(productType="umcbl", symbol=symbol)
    for order in orders.get("data", []):
        if order.get("reduceOnly"):
            client.mix_cancel_order(symbol=symbol, orderId=order["orderId"], productType="umcbl")
            logger.info(f"[Cleanup] Canceled reduceOnly order {order['orderId']}")

def switch_position(symbol: str, action: str) -> dict:
    client = get_bitget_client()

    if DRY_RUN:
        logger.info(f"[DRY_RUN] switch_position {action} {symbol}")
        return {"skipped": "dry_run"}

    monitor_state["trade_count"] += 1
    monitor_state["sl_triggered"] = False

    account_info = client.mix_get_account(symbol=symbol, productType="umcbl")
    current_amt = next((float(p["holdVol"]) for p in account_info["data"] if p["symbol"] == symbol), 0.0)

    if action.upper() == "BUY":
        if current_amt > 0:
            return {"skipped": "already_long"}

        if current_amt < 0:
            qty = abs(current_amt)
            logger.info(f"Closing SHORT {qty} @ market for {symbol}")
            client.mix_place_order(
                symbol=symbol,
                productType="umcbl",
                orderType="market",
                side="buy",
                size=str(qty),
                reduceOnly=True
            )
            if not _wait_for(symbol, 0.0):
                return {"skipped": "close_failed"}

            if monitor_state.get("sl_triggered", False):
                logger.info(f"[Switch] SL-triggered close → cleaning up TP/SL")
                _cancel_open_reduceonly_orders(symbol)

            try:
                entry = monitor_state.get("entry_price", 0.0)
                ticker = client.mix_get_ticker(symbol=symbol, productType="umcbl")
                cur_price = float(ticker["data"]["last"])
                pnl = (cur_price / entry - 1) * 100
                if pnl < 0:
                    monitor_state["sl_count"] += 1
                    monitor_state["daily_pnl"] += pnl
                    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(f"Stop-loss on switch SHORT→LONG: {pnl:.2f}% at {now}")
            except Exception:
                logger.exception("Failed to calc SL PnL on short close")

        return execute_buy(symbol)

    if action.upper() == "SELL":
        if current_amt < 0:
            return {"skipped": "already_short"}

        if current_amt > 0:
            qty = abs(current_amt)
            logger.info(f"Closing LONG {qty} @ market for {symbol}")
            client.mix_place_order(
                symbol=symbol,
                productType="umcbl",
                orderType="market",
                side="sell",
                size=str(qty),
                reduceOnly=True
            )
            if not _wait_for(symbol, 0.0):
                return {"skipped": "close_failed"}

            if monitor_state.get("sl_triggered", False):
                logger.info(f"[Switch] SL-triggered close → cleaning up TP/SL")
                _cancel_open_reduceonly_orders(symbol)

            try:
                entry = monitor_state.get("entry_price", 0.0)
                ticker = client.mix_get_ticker(symbol=symbol, productType="umcbl")
                cur_price = float(ticker["data"]["last"])
                pnl = (entry / cur_price - 1) * 100
                if pnl < 0:
                    monitor_state["sl_count"] += 1
                    monitor_state["daily_pnl"] += pnl
                    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(f"Stop-loss on switch LONG→SHORT: {pnl:.2f}% at {now}")
            except Exception:
                logger.exception("Failed to calc SL PnL on long close")

        return execute_sell(symbol)

    logger.error(f"Unknown action for switch: {action}")
    return {"skipped": "unknown_action"}
