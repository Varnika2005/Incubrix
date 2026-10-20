import re
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code.upper()
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}

def sanitize_message(msg: str) -> str:
    """Strip local filesystem paths and internal stack trace snippets from error messages."""
    if not msg:
        return "An error occurred."
    # Remove Windows/Unix absolute file paths
    msg = re.sub(r"[A-Za-z]:\\[\w\-\\]+", "[path]", msg)
    msg = re.sub(r"/(?:[a-zA-Z0-9_\-\.]+/)+[a-zA-Z0-9_\-\.]+", "[path]", msg)
    return msg

def format_error_payload(code: str, message: str, retryable: bool = False, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cleaned = sanitize_message(message)
    return {
        "error": {
            "code": code.upper(),
            "message": cleaned,
            "retryable": retryable,
            "details": details or {}
        },
        "detail": cleaned
    }

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_payload(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            details=exc.details
        )
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Map common status codes to standard error codes
    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "PAYLOAD_TOO_LARGE",
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_MEDIA_TYPE",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
        status.HTTP_502_BAD_GATEWAY: "BAD_GATEWAY",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    
    # If detail is already formatted as dict with error or details
    detail_str = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    retryable = exc.status_code in (status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_502_BAD_GATEWAY, status.HTTP_503_SERVICE_UNAVAILABLE)
    
    headers = getattr(exc, "headers", None) or {}
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_payload(code=code, message=detail_str, retryable=retryable),
        headers=headers
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    cleaned_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        cleaned_errors.append({
            "field": loc,
            "message": err.get("msg", "Invalid input"),
            "type": err.get("type", "value_error")
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_payload(
            code="VALIDATION_ERROR",
            message="Request body or query parameters failed schema validation.",
            retryable=False,
            details={"validation_errors": cleaned_errors}
        )
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Do not expose internal details in 500 error
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_payload(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred while processing the request.",
            retryable=False,
            details={}
        )
    )
