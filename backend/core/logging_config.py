# e:/kaggle hackathon google/metacognition-benchmark/backend/core/logging_config.py
"""
Structured JSON logging configuration for the backend.
"""
import logging
import json
from datetime import datetime
from .config import settings

class JSONFormatter(logging.Formatter):
    """Formatter to output logs in JSON format."""
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logging() -> None:
    """Configures the root logger based on settings."""
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL.upper())

    handler = logging.StreamHandler()
    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(handler)
