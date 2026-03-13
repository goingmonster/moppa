import logging
from typing import Any

from app.config import settings
from app.db.session import SessionLocal
from app.models.s1_ingest_model import S1PullNowRequestModel
from app.repositories.task_config_repository import TaskConfigRepository
from app.services.s1_auto_review_service import S1AutoReviewService
from app.services.s1_ingest_service import S1IngestService


_scheduler: Any = None
_logger = logging.getLogger(__name__)


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


def _run_s1_auto_review_job() -> None:
    with SessionLocal() as db:
        service = S1AutoReviewService(db)
        _ = service.run_review_job()


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
    scheduler = background_scheduler_class(timezone="UTC")

    trigger = cron_trigger_class.from_crontab(cron_expr)
    scheduler.add_job(_run_s1_pull_job, trigger=trigger, id="s1_ingest_pull", replace_existing=True)

    if settings.auto_review_enabled:
        try:
            auto_review_trigger = cron_trigger_class.from_crontab(settings.auto_review_cron)
            scheduler.add_job(
                _run_s1_auto_review_job,
                trigger=auto_review_trigger,
                id="s1_auto_review",
                replace_existing=True,
            )
        except Exception:
            _logger.exception("Failed to register auto review scheduler job")

    scheduler.start()
    _scheduler = scheduler


def stop_s1_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
