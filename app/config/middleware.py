"""
Middleware setup for FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from asgi_correlation_id import CorrelationIdMiddleware


def setup_middleware(app: FastAPI, debug: bool = False):
    """Register middleware in reverse order (inner to outer)"""
    
    # Request ID correlation (innermost - runs first)
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Request-ID",
        generator=lambda: __import__("uuid").uuid4().hex
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if debug else ["http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Gzip compression for responses > 1KB
    app.add_middleware(GZipMiddleware, minimum_size=1024)
