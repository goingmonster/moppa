from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.agent_predictions import router as agent_predictions_router
from app.api.api_keys import router as api_keys_router
from app.api.event_filter_rules import router as event_filter_rules_router
from app.api.model_endpoints import router as model_endpoints_router
from app.api.events import router as events_router
from app.api.data_sources import router as data_sources_router
from app.api.health import router as health_router
from app.api.questions import router as questions_router
from app.api.community_predictions import router as community_predictions_router
from app.api.question_comments import router as question_comments_router
from app.api.question_templates import router as question_templates_router
from app.api.s1_ingest import router as s1_ingest_router
from app.api.task_configs import router as task_configs_router
from app.api.tasks import router as tasks_router
from app.config import settings
from app.core import register_exception_handlers
from app.jobs.s1_scheduler import start_s1_scheduler, stop_s1_scheduler
from app.logging_config import configure_logging


configure_logging(settings.log_level, settings.log_file_path)


def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} is running"}


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(events_router)
    app.include_router(auth_router)
    app.include_router(api_keys_router)
    app.include_router(agent_predictions_router)
    app.include_router(data_sources_router)
    app.include_router(event_filter_rules_router)
    app.include_router(model_endpoints_router)
    app.include_router(health_router)
    app.include_router(questions_router)
    app.include_router(community_predictions_router)
    app.include_router(question_comments_router)
    app.include_router(question_templates_router)
    app.include_router(s1_ingest_router)
    app.include_router(task_configs_router)
    app.include_router(tasks_router)
    app.add_api_route("/", root, methods=["GET"], tags=["root"])

    @app.on_event("startup")
    def on_startup() -> None:
        start_s1_scheduler()

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        stop_s1_scheduler()

    register_exception_handlers(app)

    return app


app = create_app()
