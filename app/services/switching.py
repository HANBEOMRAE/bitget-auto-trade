# app/services/switching.py

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

    while time.time() - start < MAX_WAIT:
        pos_info = client.mix_get_single_position(productType="umcbl", symbol=symbol)
        pos_amt = float(pos_info["total"] or 0)

        if target_amt == 0 and pos_amt == 0:
            return True
        if target_amt > 0 and pos_amt > 0:
            return True
        if target_amt < 0 and pos_amt < 0:
            return True

        time.sleep(POLL_INTERVAL)

    logger.warning(f"[SWITCH] Timeout waiting for position: target={target_amt}, current={pos_amt}")
    return False

def switch_position(symbol: str, action: str) -> dict:
    client = get_bitget_client()

    if DRY_RUN:
        logger.info(f"[DRY_RUN] switch_position {action} {symbol}")
        return {"skipped": "dry_run"}

    monitor_state["trade_count"] += 1
    monitor_state["sl_triggered"] = False

    pos_info = client.mix_get_single_position(productType="umcbl", symbol=symbol)
    current_amt = float(pos_info["total"] or 0)

    if action.upper() == "BUY":
        if current_amt > 0:
            return {"skipped": "already_long"}

        if current_amt < 0:
            qty = abs(current_amt)
            logger.info(f"[SWITCH] Closing SHORT {qty} of {symbol}")
            client.mix_place_order(
                symbol=symbol,
                marginCoin="USDT",
                size=str(qty),
                side="close_short",
                orderType="market"
            )
            if not _wait_for(symbol, 0.0):
                return {"skipped": "close_failed"}

            try:
                entry = monitor_state.get("entry_price", 0.0)
                cur_price = float(client.mix_get_market_price(symbol=symbol)["price"])
                pnl = (cur_price / entry - 1) * 100
                if pnl < 0:
                    monitor_state["sl_count"] += 1
                    monitor_state["daily_pnl"] += pnl
                    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(f"[SWITCH] SL-triggered SHORT→LONG: {pnl:.2f}% at {now}")
            except Exception:
                logger.exception("SL PnL 계산 실패")

        return execute_buy(symbol)

    if action.upper() == "SELL":
        if current_amt < 0:
            return {"skipped": "already_short"}

        if current_amt > 0:
            qty = current_amt
            logger.info(f"[SWITCH] Closing LONG {qty} of {symbol}")
            client.mix_place_order(
                symbol=symbol,
                marginCoin="USDT",
                size=str(qty),
                side="close_long",
                orderType="market"
            )
            if not _wait_for(symbol, 0.0):
                return {"skipped": "close_failed"}

            try:
                entry = monitor_state.get("entry_price", 0.0)
                cur_price = float(client.mix_get_market_price(symbol=symbol)["price"])
                pnl = (entry / cur_price - 1) * 100
                if pnl < 0:
                    monitor_state["sl_count"] += 1
                    monitor_state["daily_pnl"] += pnl
                    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(f"[SWITCH] SL-triggered LONG→SHORT: {pnl:.2f}% at {now}")
            except Exception:
                logger.exception("SL PnL 계산 실패")

        return execute_sell(symbol)

    logger.error(f"[SWITCH] Unknown action: {action}")
    return {"skipped": "unknown_action"}
