"""
FastAPI application factory and configuration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from app.config.settings import get_settings
from app.config.logging import configure_logging
from app.config.middleware import setup_middleware
from app.config.exceptions import app_exception_handler, validation_error_handler, AppException
from app.database.session import init_db, close_db, get_db


# Configure logging before app creation
configure_logging()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        await init_db()
        yield
        # Shutdown
        await close_db()
    
    app = FastAPI(
        title=settings.app_name,
        description="Reconciliation Management System (RMS)",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # Setup middleware
    setup_middleware(app, debug=settings.debug)
    
    # Register exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    
    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check(db = Depends(get_db)):
        """Health check endpoint with database connectivity check"""
        try:
            from sqlalchemy import text
            # Execute simple query to verify database connection
            await db.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        return {
            "status": "healthy",
            "environment": settings.environment,
            "database": db_status
        }
    
    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        """API root endpoint"""
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "docs_url": "/docs",
            "openapi_url": "/openapi.json"
        }
    
    # Register routers (imported here to avoid circular imports at module level)
    from app.tenants.rest.router import router as tenants_router
    from app.invoices.rest.router import router as invoices_router
    from app.bank_transactions.rest.router import router as bank_transactions_router
    from app.reconciliation.rest.router import router as reconciliation_router
    from app.seed.rest.router import router as seed_router
    
    app.include_router(tenants_router, prefix=f"{settings.api_v1_prefix}/tenants")
    app.include_router(invoices_router, prefix=settings.api_v1_prefix)
    app.include_router(bank_transactions_router, prefix=settings.api_v1_prefix)
    app.include_router(reconciliation_router)
    if settings.enable_seed_endpoints:
        app.include_router(seed_router)
    
    # Setup GraphQL endpoint
    from strawberry.fastapi import GraphQLRouter
    from app.graphql.schema import schema
    from app.graphql.context import get_graphql_context
    
    # Create GraphQL router with context getter
    graphql_app = GraphQLRouter(
        schema,
        context_getter=get_graphql_context
    )
    app.include_router(graphql_app, prefix="/graphql", tags=["graphql"])
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
