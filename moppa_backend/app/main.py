from fastapi import FastAPI

from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.questions import router as questions_router
from app.api.tasks import router as tasks_router
from app.config import settings
from app.core import register_exception_handlers


def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} is running"}


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(events_router)
    app.include_router(health_router)
    app.include_router(questions_router)
    app.include_router(tasks_router)
    app.add_api_route("/", root, methods=["GET"], tags=["root"])
    register_exception_handlers(app)

    return app


app = create_app()
