# app/main.py

from fastapi import FastAPI
from app.routers.webhook import router as webhook_router
import threading
import logging
from app.services.monitor import start_monitor

from apscheduler.schedulers.background import BackgroundScheduler

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

    thread = threading.Thread(target=safe_monitor, daemon=True)
    thread.start()

    # from app.routers.report import report
    # sched = BackgroundScheduler(timezone="Asia/Seoul")
    # sched.add_job(lambda: report(), 'cron', hour=9, minute=0)
    # sched.start()


app.include_router(webhook_router)

@app.get("/health")
def health():
    return {"status": "alive"}


# ✅ FastAPI 앱 실행을 위한 코드 추가 (직접 실행 시에만)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)