# app/main.py

from fastapi import FastAPI
from app.routers.webhook import router as webhook_router
import threading
import logging
from app.services.monitor import start_monitor

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from zoneinfo import ZoneInfo

app = FastAPI()

@app.on_event("startup")
def on_startup():
    """
    앱 기동 시:
    1) 모니터 스레드 실행 (Bitget용)
    2) 매일 KST 09:00에 일일 리포트 출력 (옵션)
    """
    def safe_monitor():
        try:
            start_monitor()
        except Exception:
            logging.getLogger("monitor").exception("Bitget 모니터링 실패")
    
    # 백그라운드 모니터링 스레드 시작
    thread = threading.Thread(target=safe_monitor, daemon=True)
    thread.start()

    # APScheduler로 일일 리포트 실행 예약 (원할 경우 사용)
    # from app.routers.report import report
    # sched = BackgroundScheduler(timezone="Asia/Seoul")
    # sched.add_job(lambda: report(), 'cron', hour=9, minute=0)
    # sched.start()

# 웹훅 라우터 등록 (TradingView 신호 처리)
app.include_router(webhook_router)

# 헬스체크 API
@app.get("/health")
def health():
    return {"status": "alive"}
