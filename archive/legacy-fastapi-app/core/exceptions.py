"""
Typed error hierarchy and global exception handlers.
Every error is typed, logged, and returns a consistent JSON response format.
Resolves Bug #8 (unsafe error handling) and provides consistent API error responses.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppError(Exception):
    """Base application error. All custom errors should inherit from this."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": resource_id},
        )


class ValidationError(AppError):
    """Input validation failed."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class UnauthorizedError(AppError):
    """Authentication required or failed."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message=message, code="UNAUTHORIZED", status_code=401)


class ForbiddenError(AppError):
    """User lacks permission for this action."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class ConflictError(AppError):
    """Resource conflicts with existing state."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details,
        )


class FileTooLargeError(AppError):
    """Uploaded file exceeds size limit."""

    def __init__(self, size: int, limit: int) -> None:
        super().__init__(
            message=f"File size {size} bytes exceeds limit of {limit} bytes",
            code="FILE_TOO_LARGE",
            status_code=413,
            details={"size": size, "limit": limit},
        )


class UnsupportedMediaTypeError(AppError):
    """Uploaded file type is not supported."""

    def __init__(self, content_type: str) -> None:
        super().__init__(
            message=f"Unsupported media type: {content_type}",
            code="UNSUPPORTED_MEDIA_TYPE",
            status_code=415,
            details={"content_type": content_type},
        )


class JobAlreadyRunningError(AppError):
    """Job is already in progress and cannot be restarted."""

    def __init__(self, job_id: str) -> None:
        super().__init__(
            message=f"Job {job_id} is already running",
            code="JOB_ALREADY_RUNNING",
            status_code=409,
            details={"job_id": job_id},
        )


class AudioExtractionError(AppError):
    """ffmpeg audio extraction failed."""

    def __init__(self, stderr: str) -> None:
        super().__init__(
            message="Audio extraction failed",
            code="AUDIO_EXTRACTION_ERROR",
            status_code=500,
            details={"stderr": stderr[:500]},  # Truncate to avoid huge logs
        )


class TranscriptionError(AppError):
    """Whisper transcription failed."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            message="Transcription failed",
            code="TRANSCRIPTION_ERROR",
            status_code=500,
            details={"detail": detail},
        )


class LLMAnalysisError(AppError):
    """LLM API call failed."""

    def __init__(self, detail: str, provider: str = "") -> None:
        super().__init__(
            message="LLM analysis failed",
            code="LLM_ANALYSIS_ERROR",
            status_code=502,
            details={"detail": detail, "provider": provider},
        )


class ServiceUnavailableError(AppError):
    """A dependency service is unavailable."""

    def __init__(self, service: str) -> None:
        super().__init__(
            message=f"Service unavailable: {service}",
            code="SERVICE_UNAVAILABLE",
            status_code=503,
            details={"service": service},
        )


def _error_response(
    code: str,
    message: str,
    status_code: int,
    request: Request,
    details: Optional[dict[str, Any]] = None,
) -> JSONResponse:
    """Build a consistent JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "meta": {
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    from app.core.logging import get_logger
    log = get_logger("exceptions")

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            log.error("app_error", error=exc.message, code=exc.code, path=request.url.path)
        else:
            log.warning("app_error", error=exc.message, code=exc.code, path=request.url.path)
        return _error_response(exc.code, exc.message, exc.status_code, request, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        log.warning("validation_error", errors=exc.errors(), path=request.url.path)
        return _error_response(
            "VALIDATION_ERROR",
            "Request validation failed",
            422,
            request,
            {"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        log.error(
            "unexpected_error",
            error=str(exc),
            exc_info=exc,
            path=request.url.path,
        )
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred",
            500,
            request,
        )
