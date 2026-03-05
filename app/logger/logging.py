import os
import logging
import time
from functools import wraps
from pathlib import Path

# =========================================================================
# File-based logger (same pattern as ml-ar-management-api)
# =========================================================================
base_dir = Path(__file__).resolve().parent
log_dir = os.path.join(base_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(log_dir, "app.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
logging.getLogger().addHandler(console_handler)

logger = logging.getLogger(__name__)


# =========================================================================
# @log_execution decorator — auto-logs start, finish, duration, exceptions
# =========================================================================
def log_execution(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"STARTED: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as error:
            logger.exception(f"EXCEPTION in {func.__name__}: {error}")
            raise
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"FINISHED: {func.__name__} in {elapsed_time:.2f}s")
    return wrapper
