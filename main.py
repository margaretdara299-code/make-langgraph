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
from app.skill.controller import router as skill_router, version_router
from app.action.controller import router as action_router, designer_router
from app.connector.controller import router as connector_router
from app.category.controller import router as category_router
from app.capability.controller import router as capability_router
from app.engine.controller import router as engine_router
from app.claims.controller import router as claims_router
from fastapi import APIRouter


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
# Health Check & Docs
# =========================================================================
@application.get("/health", tags=["Health"])
def health_check():
    return build_success_response("Healthy", {"time": generate_utc_timestamp()})

from fastapi.responses import HTMLResponse

@application.get("/api-client", include_in_schema=False)
def scalar_html():
    html_content = """
    <!doctype html>
    <html>
      <head>
        <title>Tensaw API Client</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
          body { margin: 0; padding: 0; }
        </style>
      </head>
      <body>
        <!-- Use unpkg CDN to bypass potential jsdelivr blocks -->
        <script id="api-reference" data-url="/openapi.json"></script>
        <script src="https://unpkg.com/@scalar/api-reference"></script>
      </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# =========================================================================
# Register Routers under /api/v1
# =========================================================================
api_v1 = APIRouter(prefix="/api/v1")

# Resource-based routers
api_v1.include_router(skill_router)
api_v1.include_router(version_router)
api_v1.include_router(action_router)
api_v1.include_router(connector_router)
api_v1.include_router(category_router)
api_v1.include_router(capability_router)
api_v1.include_router(engine_router)
api_v1.include_router(claims_router)

# Special purpose routers
api_v1.include_router(designer_router)

# Mount parent router to application
application.include_router(api_v1)


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
