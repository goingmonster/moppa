from fastapi import APIRouter

from app.db.session import ping_db


router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Health check")
def health_check() -> dict[str, str | bool]:
    database_ok = ping_db()
    return {
        "status": "ok" if database_ok else "degraded",
        "database": database_ok,
    }
