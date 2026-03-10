from typing import Any

from app.config import settings
from app.db.session import SessionLocal
from app.models.s1_ingest_model import S1PullNowRequestModel
from app.repositories.task_config_repository import TaskConfigRepository
from app.services.s1_ingest_service import S1IngestService


_scheduler: Any = None


def _resolve_pull_cron() -> str:
    with SessionLocal() as db:
        config = TaskConfigRepository(db).get_by_task_type("s1_ingest_pull")
    if config is not None:
        raw = config.value.get("main_cron")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return "0 * * * *"


def _run_s1_pull_job() -> None:
    with SessionLocal() as db:
        service = S1IngestService(db)
        _ = service.run_pull_job(S1PullNowRequestModel(source_system=settings.source_system_name))


def start_s1_scheduler() -> None:
    global _scheduler
    if not settings.scheduler_enabled:
        return
    if _scheduler is not None and _scheduler.running:
        return
    background_module = __import__("apscheduler.schedulers.background", fromlist=["BackgroundScheduler"])
    cron_module = __import__("apscheduler.triggers.cron", fromlist=["CronTrigger"])
    background_scheduler_class = getattr(background_module, "BackgroundScheduler")
    cron_trigger_class = getattr(cron_module, "CronTrigger")
    cron_expr = _resolve_pull_cron()
    trigger = cron_trigger_class.from_crontab(cron_expr)
    scheduler = background_scheduler_class(timezone="UTC")
    scheduler.add_job(_run_s1_pull_job, trigger=trigger, id="s1_ingest_pull", replace_existing=True)
    scheduler.start()
    _scheduler = scheduler


def stop_s1_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
