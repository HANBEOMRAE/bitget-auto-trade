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

product_type = "umcbl"
margin_coin = "USDT"

def _wait_for(symbol: str, target_amt: float) -> bool:
    client = get_bitget_client()
    start = time.time()

    while time.time() - start < MAX_WAIT:
        resp = client.mix_account_api.get_account(symbol=symbol, productType=product_type)
        current_amt = float(resp["data"]["total"])

        if target_amt > 0 and current_amt > 0:
            return True
        if target_amt < 0 and current_amt < 0:
            return True
        if target_amt == 0 and current_amt == 0:
            return True

        time.sleep(POLL_INTERVAL)

    logger.warning(f"[SWITCH TIMEOUT] target {target_amt}, current {current_amt}")
    return False


def _cancel_open_reduceonly_orders(symbol: str):
    client = get_bitget_client()
    open_orders = client.mix_order_api.get_all_open_orders(productType=product_type, symbol=symbol)
    for o in open_orders.get("data", []):
        if o.get("reduceOnly"):
            client.mix_order_api.cancel_order(productType=product_type, symbol=symbol, orderId=o["orderId"])
            logger.info(f"[Cleanup] Canceled reduceOnly order: {o['orderId']}")


def switch_position(symbol: str, action: str) -> dict:
    client = get_bitget_client()

    if DRY_RUN:
        logger.info(f"[DRY_RUN] switch_position {action} {symbol}")
        return {"skipped": "dry_run"}

    monitor_state["trade_count"] += 1
    monitor_state["sl_triggered"] = False

    # 현재 보유 포지션 확인
    resp = client.mix_account_api.get_account(symbol=symbol, productType=product_type)
    current_amt = float(resp["data"]["total"])

    # LONG 진입
    if action.upper() == "BUY":
        if current_amt > 0:
            return {"skipped": "already_long"}

        if current_amt < 0:
            qty = abs(current_amt)
            logger.info(f"[Switch] Closing SHORT {qty} @ market for {symbol}")
            client.mix_order_api.place_order(
                symbol=symbol,
                productType=product_type,
                marginCoin=margin_coin,
                size=str(qty),
                side="buy",
                orderType="market",
                reduceOnly=True
            )

            if not _wait_for(symbol, 0.0):
                return {"skipped": "close_failed"}

            if monitor_state.get("sl_triggered"):
                _cancel_open_reduceonly_orders(symbol)

            try:
                entry = monitor_state.get("entry_price", 0.0)
                cur_price = float(client.mix_market_api.get_ticker(symbol=symbol, productType=product_type)["data"]["last"])
                pnl = (cur_price / entry - 1) * 100
                if pnl < 0:
                    monitor_state["sl_count"] += 1
                    monitor_state["daily_pnl"] += pnl
                    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(f"Stop-loss on switch SHORT→LONG: {pnl:.2f}% at {now}")
            except Exception:
                logger.exception("[PNL] SHORT→LONG 손익 계산 실패")

        return execute_buy(symbol)

    # SHORT 진입
    if action.upper() == "SELL":
        if current_amt < 0:
            return {"skipped": "already_short"}

        if current_amt > 0:
            qty = abs(current_amt)
            logger.info(f"[Switch] Closing LONG {qty} @ market for {symbol}")
            client.mix_order_api.place_order(
                symbol=symbol,
                productType=product_type,
                marginCoin=margin_coin,
                size=str(qty),
                side="sell",
                orderType="market",
                reduceOnly=True
            )

            if not _wait_for(symbol, 0.0):
                return {"skipped": "close_failed"}

            if monitor_state.get("sl_triggered"):
                _cancel_open_reduceonly_orders(symbol)

            try:
                entry = monitor_state.get("entry_price", 0.0)
                cur_price = float(client.mix_market_api.get_ticker(symbol=symbol, productType=product_type)["data"]["last"])
                pnl = (entry / cur_price - 1) * 100
                if pnl < 0:
                    monitor_state["sl_count"] += 1
                    monitor_state["daily_pnl"] += pnl
                    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(f"Stop-loss on switch LONG→SHORT: {pnl:.2f}% at {now}")
            except Exception:
                logger.exception("[PNL] LONG→SHORT 손익 계산 실패")

        return execute_sell(symbol)

    logger.error(f"[SWITCH ERROR] Unknown action: {action}")
    return {"skipped": "unknown_action"}