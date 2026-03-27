"""
Tensaw Skills Studio API — Application entry point.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.common.middleware import RequestLoggerMiddleware
from app.common.utils import generate_utc_timestamp
from app.common.response import build_success_response
from app.core.config import app_config, server_config
from app.core.lifespan import lifespan
from app.logger.logging import logger

# Feature routers
from app.skill.controller import router as skill_router
from app.action.controller import router as action_router
from app.connector.controller import router as connector_router
from app.category.controller import router as category_router
from app.capability.controller import router as capability_router
from app.engine.controller import router as engine_router
from app.claims.controller import router as claims_router


# =========================================================================
# Application
# =========================================================================
application = FastAPI(
    title=app_config.TITLE,
    version=app_config.VERSION,
    lifespan=lifespan,
)

# =========================================================================
# Middleware
# =========================================================================
application.add_middleware(RequestLoggerMiddleware)
application.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# Global Exception Handlers — all errors return envelope format
# =========================================================================
@application.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    """Store for middleware and return envelope."""
    request.state.error = exc
    if isinstance(exc.detail, dict) and "status" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": False, "message": str(exc.detail), "data": None},
    )


@application.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    """Store for middleware and return simple message."""
    request.state.error = exc
    return JSONResponse(
        status_code=422,
        content={"status": False, "message": "Invalid request", "data": None},
    )


@application.exception_handler(Exception)
async def handle_unexpected_error(request: Request, error: Exception):
    """Store for middleware and return generic error."""
    request.state.error = error
    return JSONResponse(
        status_code=500,
        content={"status": False, "message": "Internal error", "data": None},
    )


# =========================================================================
# Health Check
# =========================================================================
@application.get("/health", tags=["Health"])
def health_check():
    return build_success_response("Healthy", {"time": generate_utc_timestamp()})


# =========================================================================
# Register Routers
# =========================================================================
application.include_router(skill_router)
application.include_router(action_router)
application.include_router(connector_router)
application.include_router(category_router)
application.include_router(capability_router)
application.include_router(engine_router)
application.include_router(claims_router)


# =========================================================================
# Run
# =========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:application",
        host=server_config.HOST,
        port=server_config.PORT,
        reload=server_config.RELOAD,
    )
