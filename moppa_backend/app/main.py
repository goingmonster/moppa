from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="MOPPA Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(health_router)

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {"message": "MOPPA Backend is running"}

    return app


app = create_app()
