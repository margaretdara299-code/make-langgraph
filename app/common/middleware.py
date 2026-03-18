"""
Request logger middleware — logs every request/response with timing.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("tensaw_skills_studio")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"-> {request.method} {request.url.path} - {response.status_code} in {elapsed_ms:.0f}ms")
            return response
        except Exception as error:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.exception(f"-> {request.method} {request.url.path} - ERROR in {elapsed_ms:.0f}ms")
            raise
