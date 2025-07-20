import logging
import math
from app.clients.bitget_client import get_bitget_client
from app.config import DRY_RUN, TRADE_LEVERAGE
from app.state import monitor_state

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def round_step_size(value: float, step_size: float, round_up=False) -> float:
    precision = int(round(-math.log10(step_size), 0))
    factor = 10 ** precision
    return math.ceil(value * factor) / factor if round_up else math.floor(value * factor) / factor


def execute_buy(symbol: str) -> dict:
    client = get_bitget_client()
    margin_coin = "USDT"
    product_type = "umcbl"

    if DRY_RUN:
        logger.info(f"[DRY_RUN] BUY {symbol}")
        return {"skipped": "dry_run"}

    try:
        # 1. 레버리지 설정
        client.mix_account_api.set_leverage(symbol=symbol, marginCoin=margin_coin, leverage=TRADE_LEVERAGE)

        # 2. 잔고 확인
        account = client.mix_account_api.get_account(symbol=symbol, productType=product_type)
        usdt_balance = float(account["data"]["available"])

        # 3. 현재 마크가격 조회
        ticker = client.mix_market_api.get_ticker(productType=product_type, symbol=symbol)
        mark_price = float(ticker["data"]["last"])

        # 4. 심볼 정보 확인
        symbols_info = client.mix_market_api.get_all_symbols(productType=product_type)
        symbol_info = next(item for item in symbols_info["data"] if item["symbol"] == symbol)
        min_qty = float(symbol_info["minTradeNum"])
        tick_size = 10 ** -int(symbol_info["priceScale"])
        step_size = 10 ** -int(symbol_info["sizeScale"])

        # 5. 주문 수량 계산
        alloc = usdt_balance * 0.98 * TRADE_LEVERAGE
        raw_qty = alloc / mark_price
        qty = round_step_size(raw_qty, step_size)
        if qty < min_qty:
            logger.warning(f"BUY Skipped: qty {qty} < min {min_qty}")
            return {"skipped": "qty_too_low"}

        # 6. 시장가 매수
        res = client.mix_order_api.place_order(
            symbol=symbol,
            marginCoin=margin_coin,
            size=str(qty),
            side="open_long",
            orderType="market"
        )
        logger.info(f"[BUY] Market order submitted: {res}")

        # 7. 모니터 상태 갱신
        monitor_state["entry_price"] = mark_price
        monitor_state["position_qty"] = qty

        # 8. 익절, 손절 설정
        tp1_price = round_step_size(mark_price * 1.003, tick_size, round_up=True)
        tp1_qty = round_step_size(qty * 0.2, step_size)

        tp2_price = round_step_size(mark_price * 1.007, tick_size, round_up=True)
        tp2_qty = round_step_size((qty - tp1_qty) * 0.5, step_size)

        sl_price = round_step_size(mark_price * 0.997, tick_size)

        tp1 = client.mix_order_api.place_plan_order(
            symbol=symbol,
            marginCoin=margin_coin,
            size=str(tp1_qty),
            side="close_long",
            orderType="market",
            triggerPrice=str(tp1_price),
            executePrice=str(tp1_price),
            triggerType="market_price"
        )

        tp2 = client.mix_order_api.place_plan_order(
            symbol=symbol,
            marginCoin=margin_coin,
            size=str(tp2_qty),
            side="close_long",
            orderType="market",
            triggerPrice=str(tp2_price),
            executePrice=str(tp2_price),
            triggerType="market_price"
        )

        sl = client.mix_order_api.place_plan_order(
            symbol=symbol,
            marginCoin=margin_coin,
            size=str(qty),
            side="close_long",
            orderType="market",
            triggerPrice=str(sl_price),
            executePrice=str(sl_price),
            triggerType="market_price"
        )

        logger.info(
            f"[TP/SL] TP1: {tp1_price} x{tp1_qty}, TP2: {tp2_price} x{tp2_qty}, SL: {sl_price} x{qty}"
        )

        return {
            "buy": {"filled": qty, "entry": mark_price},
            "orders": {"tp1": tp1, "tp2": tp2, "sl": sl}
        }

    except Exception as e:
        logger.exception(f"[BUY ERROR] {symbol}: {e}")
        return {"skipped": "error", "error": str(e)}