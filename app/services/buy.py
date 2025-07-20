import logging
import math
from app.clients.bitget_client import get_bitget_client
from app.config import DRY_RUN, TRADE_LEVERAGE
from app.state import monitor_state

from bitget.apis.mix.v1.mix_account_api import MixAccountApi
from bitget.apis.mix.v1.mix_market_api import MixMarketApi
from bitget.apis.mix.v1.mix_order_api import MixOrderApi

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def round_step_size(value: float, step_size: float, round_up=False) -> float:
    precision = int(round(-math.log10(step_size), 0))
    factor = 10 ** precision
    return math.ceil(value * factor) / factor if round_up else math.floor(value * factor) / factor

def execute_buy(symbol: str) -> dict:
    client = get_bitget_client()

    if DRY_RUN:
        logger.info(f"[DRY_RUN] BUY {symbol}")
        return {"skipped": "dry_run"}

    try:
        # API 객체 초기화
        account_api = MixAccountApi(client)
        market_api = MixMarketApi(client)
        order_api = MixOrderApi(client)

        margin_coin = "USDT"
        product_type = "umcbl"

        # 1. 레버리지 설정
        account_api.set_leverage(symbol, margin_coin, TRADE_LEVERAGE)

        # 2. 잔고 및 마크가격 확인
        account = account_api.get_account(symbol, product_type)
        usdt_balance = float(account["data"]["marginCoinAccount"]["available"])

        price = market_api.get_mark_price(symbol)
        mark_price = float(price["data"]["markPrice"])

        # 3. 주문 수량 계산
        allocation = usdt_balance * 0.98 * TRADE_LEVERAGE
        raw_qty = allocation / mark_price

        # 4. 최소 수량 필터 확인
        info = market_api.get_symbols(product_type)
        sym_info = next(s for s in info["data"] if s["symbol"] == symbol)

        min_qty = float(sym_info["minTradeNum"])
        price_scale = int(sym_info["priceScale"])
        size_scale = int(sym_info["sizeScale"])
        step_size = 10 ** -size_scale
        tick_size = 10 ** -price_scale

        qty = round_step_size(raw_qty, step_size)
        if qty < min_qty:
            logger.warning(f"Qty {qty} < minQty {min_qty}. Skipping BUY.")
            return {"skipped": "quantity_too_low"}

        # 5. 시장가 매수
        order = order_api.place_order(
            symbol=symbol,
            marginCoin=margin_coin,
            size=str(qty),
            side="open_long",
            orderType="market"
        )
        logger.info(f"Market BUY submitted: {order}")

        entry_price = mark_price
        executed_qty = qty
        monitor_state["entry_price"] = entry_price
        logger.info(f"Entry LONG: {executed_qty}@{entry_price}")

        # 6. TP1
        tp1_price = round_step_size(entry_price * 1.003, tick_size, round_up=True)
        tp1_qty   = round_step_size(executed_qty * 0.20, step_size)

        tp1 = order_api.place_plan_order(
            symbol=symbol,
            marginCoin=margin_coin,
            size=str(tp1_qty),
            side="close_long",
            triggerPrice=str(tp1_price),
            executePrice=str(tp1_price),
            triggerType="market_price",
            orderType="market"
        )

        # 7. TP2
        remain_after_tp1 = executed_qty - tp1_qty
        tp2_qty = round_step_size(remain_after_tp1 * 0.50, step_size)
        tp2_price = round_step_size(entry_price * 1.007, tick_size, round_up=True)

        tp2 = order_api.place_plan_order(
            symbol=symbol,
            marginCoin=margin_coin,
            size=str(tp2_qty),
            side="close_long",
            triggerPrice=str(tp2_price),
            executePrice=str(tp2_price),
            triggerType="market_price",
            orderType="market"
        )

        # 8. SL
        sl_price = round_step_size(entry_price * 0.997, tick_size)
        sl = order_api.place_plan_order(
            symbol=symbol,
            marginCoin=margin_coin,
            size=str(executed_qty),
            side="close_long",
            triggerPrice=str(sl_price),
            executePrice=str(sl_price),
            triggerType="market_price",
            orderType="market"
        )

        logger.info(
            f"TP1 @ {tp1_price} x{tp1_qty}, "
            f"TP2 @ {tp2_price} x{tp2_qty}, "
            f"SL @ {sl_price} x{executed_qty}"
        )

        return {
            "buy": {"filled": executed_qty, "entry": entry_price},
            "orders": {
                "tp1": tp1,
                "tp2": tp2,
                "sl":  sl
            }
        }

    except Exception as e:
        logger.exception(f"[BUY ERROR] {symbol}: {e}")
        return {"skipped": "error", "error": str(e)}