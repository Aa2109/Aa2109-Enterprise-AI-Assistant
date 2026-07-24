import logging
import structlog

logging.basicConfig(level=logging.INFO)

logger = structlog.get_logger()
