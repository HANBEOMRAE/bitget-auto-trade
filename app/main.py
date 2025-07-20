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
    1) 가격 모니터링 스레드 실행
    2) 일일 리포트 스케줄링 (옵션)
    """
    def safe_monitor():
        try:
            start_monitor()
        except Exception:
            logging.getLogger("monitor").exception("Bitget 모니터링 실패")

    thread = threading.Thread(target=safe_monitor, daemon=True)
    thread.start()

    # ✅ 필요 시 일일 리포트 기능 활성화
    # from app.routers.report import report
    # sched = BackgroundScheduler(timezone="Asia/Seoul")
    # sched.add_job(lambda: report(), 'cron', hour=9, minute=0)
    # sched.start()

# ✅ 웹훅 라우터 등록
app.include_router(webhook_router)

@app.get("/health")
def health():
    return {"status": "alive"}

# ✅ 직접 실행 시 (개발/로컬 테스트 용도)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)