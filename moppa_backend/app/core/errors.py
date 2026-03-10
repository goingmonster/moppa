from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        payload["details"] = details
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload("VALIDATION_ERROR", "Request validation failed", exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
            body = exc.detail
        else:
            body = error_payload("HTTP_ERROR", str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, __: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=error_payload("DATA_INTEGRITY_ERROR", "Database integrity constraint violated"),
        )

    @app.exception_handler(DataError)
    async def handle_data_error(_: Request, __: DataError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error_payload("DATA_ERROR", "Invalid data for database operation"),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(_: Request, __: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_payload("DATABASE_ERROR", "Database operation failed"),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_payload("INTERNAL_ERROR", "Internal server error"),
        )
