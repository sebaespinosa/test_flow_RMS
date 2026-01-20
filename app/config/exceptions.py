"""
Custom exception classes and handlers.
"""

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request


class AppException(HTTPException):
    """Base application exception"""
    
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: dict | None = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class ValidationError(AppException):
    """Validation error (422)"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class NotFoundError(AppException):
    """Resource not found (404)"""
    
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    """Resource conflict, usually for idempotency or duplicate key (409)"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class UnauthorizedError(AppException):
    """Unauthorized access (401)"""
    
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenError(AppException):
    """Forbidden access (403)"""
    
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


# Exception handlers
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle AppException and subclasses"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_type": exc.__class__.__name__
        }
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": str(exc),
            "error_type": "ValidationError"
        }
    )
