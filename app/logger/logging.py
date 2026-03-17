import os
import logging
import time
from functools import wraps
from pathlib import Path
from logging.handlers import RotatingFileHandler

# =========================================================================
# File-based logger with Rotation and Backup
# =========================================================================
base_dir = Path(__file__).resolve().parent
log_dir = os.path.join(base_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

log_file_path = os.path.join(log_dir, "app.log")
log_format = "%(asctime)s [%(levelname)s] %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

# Rotation: 3MB per file, max 3 backup files (Total ~12MB storage)
file_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=3 * 1024 * 1024,  # 3 Megabytes
    backupCount=3              # Keep 3 historical log files
)
file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
file_handler.setLevel(logging.INFO)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = []  # Clear any default handlers
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)


# =========================================================================
# @log_execution decorator — auto-logs start, finish, duration, error
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
            # We use logger.error with only the error message to avoid long Tracebacks
            logger.error(f"ERROR in {func.__name__}: {error}")
            raise
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"FINISHED: {func.__name__} in {elapsed_time:.2f}s")
    return wrapper
