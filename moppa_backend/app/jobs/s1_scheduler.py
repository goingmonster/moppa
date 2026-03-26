import logging
from typing import Any

from app.config import settings
from app.db.session import SessionLocal
from app.models.s1_ingest_model import S1PullNowRequestModel
from app.repositories.task_config_repository import TaskConfigRepository
from app.services.auto_question_service import AutoQuestionService
from app.services.question_expiry_service import QuestionExpiryService
from app.services.question_location_analysis_service import QuestionLocationAnalysisService
from app.services.s1_auto_review_service import S1AutoReviewService
from app.services.s1_ingest_service import S1IngestService
from app.services.tavily_ingest_service import TavilyIngestService


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


def _run_auto_question_job() -> None:
    with SessionLocal() as db:
        service = AutoQuestionService(db)
        _ = service.run_auto_question_job()


def _run_question_location_analysis_job() -> None:
    with SessionLocal() as db:
        service = QuestionLocationAnalysisService(db)
        _ = service.run_location_analysis_job()


def _run_tavily_ingest_job() -> None:
    with SessionLocal() as db:
        service = TavilyIngestService(db)
        _ = service.run_ingest_job()


def _run_question_expiry_job() -> None:
    with SessionLocal() as db:
        service = QuestionExpiryService(db)
        _ = service.run_expiry_check_job()


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

    if settings.tavily_ingest_enabled:
        try:
            tavily_trigger = cron_trigger_class.from_crontab(settings.tavily_ingest_cron)
            scheduler.add_job(
                _run_tavily_ingest_job,
                trigger=tavily_trigger,
                id="tavily_ingest",
                replace_existing=True,
            )
        except Exception:
            _logger.exception("Failed to register Tavily ingest scheduler job")

    if settings.auto_question_enabled:
        try:
            auto_question_trigger = cron_trigger_class.from_crontab(settings.auto_question_cron)
            scheduler.add_job(
                _run_auto_question_job,
                trigger=auto_question_trigger,
                id="auto_question",
                replace_existing=True,
            )
        except Exception:
            _logger.exception("Failed to register auto question scheduler job")

    if settings.question_location_analysis_enabled:
        try:
            question_location_trigger = cron_trigger_class.from_crontab(settings.question_location_analysis_cron)
            scheduler.add_job(
                _run_question_location_analysis_job,
                trigger=question_location_trigger,
                id="question_location_analysis",
                replace_existing=True,
            )
        except Exception:
            _logger.exception("Failed to register question location analysis scheduler job")

    if settings.question_expiry_enabled:
        try:
            expiry_trigger = cron_trigger_class.from_crontab(settings.question_expiry_cron)
            scheduler.add_job(
                _run_question_expiry_job,
                trigger=expiry_trigger,
                id="question_expiry",
                replace_existing=True,
            )
        except Exception:
            _logger.exception("Failed to register question expiry scheduler job")

    scheduler.start()
    _scheduler = scheduler


def stop_s1_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
