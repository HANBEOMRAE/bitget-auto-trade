# app/routers/webhook.py

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import DRY_RUN
from app.services.switching import switch_position
from app.state import monitor_state

# 로거 설정
logger = logging.getLogger("webhook")
router = APIRouter()

# 웹훅 수신 데이터 스키마
class AlertPayload(BaseModel):
    symbol: str   # 예: "ETH/USDT"
    action: str   # "BUY" 또는 "SELL"

# 웹훅 수신 엔드포인트
@router.post("/webhook")
async def webhook(payload: AlertPayload):
    sym = payload.symbol.upper().replace("/", "")  # "ETHUSDT" 형식
    action = payload.action.upper()                # "BUY" 또는 "SELL"

    if DRY_RUN:
        logger.info(f"[DRY_RUN] Received {action} for {sym}")
        return {"status": "dry_run", "symbol": sym, "action": action}

    try:
        # Bitget 포지션 스위칭 실행
        res = switch_position(sym, action)

        # 이미 동일 방향 포지션이면 스킵 처리
        if "skipped" in res:
            logger.info(f"Skipped {action} for {sym} - {res['skipped']}")
            return {"status": "skipped", "reason": res["skipped"]}

        # 거래 정보 추출
        info = res.get("buy", {}) if action == "BUY" else res.get("sell", {})
        entry = float(info.get("entry", 0))
        qty   = float(info.get("filled", 0))

        # 유효하지 않은 거래 정보는 무시
        if entry <= 0 or qty <= 0:
            logger.warning(f"[WARNING] Invalid trade info for {sym}: {info}")
            return {
                "status": "error",
                "reason": "Invalid trade data",
                "symbol": sym,
                "action": action,
                "entry": entry,
                "qty": qty
            }

        # 현재 시각
        now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")

        # 모니터 상태 갱신
        monitor_state.update({
            "symbol":         sym,
            "entry_price":    entry,
            "position_qty":   qty,
            "entry_time":     now,
            "first_tp_done":  False,
            "second_tp_done": False,
            "sl_done":        False,
        })

        logger.info(f"[SUCCESS] {action} executed for {sym} @ {entry} qty={qty}")

    except Exception as e:
        logger.exception(f"[ERROR] Exception during {action} for {sym}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")

    return {"status": "ok", "result": res}