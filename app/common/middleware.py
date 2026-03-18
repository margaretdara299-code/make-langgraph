import os
import time
import logging
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("tensaw_skills_studio")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Ensure state.error is initialized
        request.state.error = None
        
        # Execute the request pipeline (this includes exception handlers)
        response = await call_next(request)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Check if an error was recorded by the exception handlers
        error = getattr(request.state, "error", None)
        
        if error and response.status_code >= 400:
            # Failure log (Actionable error info)
            tb = getattr(error, "__traceback__", None)
            if tb:
                last_frame = traceback.extract_tb(tb)[-1]
                file_info = f"({os.path.basename(last_frame.filename)}:{last_frame.lineno})"
            else:
                file_info = "(no traceback)"
            
            # Use ERROR level for 500s, WARNING for 4xx
            log_level = logging.ERROR if response.status_code >= 500 else logging.INFO
            logger.log(log_level, f"-> {request.method} {request.url.path} | Status: {response.status_code} | Time: {elapsed_ms:.2f}ms | FAIL: {type(error).__name__}: {str(error)} {file_info}")
        else:
            # Success log (One line only)
            logger.info(f"-> {request.method} {request.url.path} | Status: {response.status_code} | Time: {elapsed_ms:.2f}ms")
            
        return response
