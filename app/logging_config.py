import sys

from loguru import logger

from app.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    logger.remove()
    logger.add(sys.stdout, level=settings.log_level, serialize=False, enqueue=True)


def get_logger():
    return logger
