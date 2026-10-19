"""RFC 9457 problem details for every error the API returns."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"

_TITLES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Validation Error",
    429: "Too Many Requests",
    500: "Internal Server Error",
}


class ProblemError(Exception):
    """Raised by services and routers; rendered as application/problem+json."""

    status: int = 400
    code: str = "bad_request"

    def __init__(
        self,
        detail: str,
        *,
        status: int | None = None,
        code: str | None = None,
        errors: list[dict[str, Any]] | None = None,
        extra: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        if status is not None:
            self.status = status
        if code is not None:
            self.code = code
        self.errors = errors or []
        self.extra = extra or {}
        self.headers = headers


class Unauthorized(ProblemError):
    status = 401
    code = "unauthorized"


class Forbidden(ProblemError):
    status = 403
    code = "forbidden"


class NotFound(ProblemError):
    status = 404
    code = "not_found"


class Conflict(ProblemError):
    status = 409
    code = "conflict"


class ValidationFailed(ProblemError):
    status = 422
    code = "validation_error"


class RateLimited(ProblemError):
    status = 429
    code = "rate_limited"


def problem_response(
    status: int,
    detail: str,
    *,
    code: str,
    errors: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://radicle.dev/problems/{code}",
        "title": _TITLES.get(status, "Error"),
        "status": status,
        "detail": detail,
        "errors": errors or [],
    }
    body.update(extra or {})
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem(_: Request, exc: ProblemError) -> JSONResponse:
        return problem_response(
            exc.status,
            exc.detail,
            code=exc.code,
            errors=exc.errors,
            extra=exc.extra,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(p) for p in err["loc"] if p != "body"),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        summary = "; ".join(f"{e['field']}: {e['message']}" for e in errors)
        return problem_response(
            422, f"Invalid request. {summary}", code="validation_error", errors=errors
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else _TITLES.get(exc.status_code, "")
        return problem_response(
            exc.status_code,
            detail,
            code=f"http_{exc.status_code}",
            headers=dict(exc.headers) if exc.headers else None,
        )
