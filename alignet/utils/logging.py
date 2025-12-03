import os
import logging
from logging.handlers import RotatingFileHandler

EVENTS_LEVEL_NUM = 38
DEFAULT_LOG_BACKUP_COUNT = 10

logger = None

def get_logger(full_path="logs"):
    global logger
    if logger is not None:
        return logger

    os.makedirs(full_path, exist_ok=True)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.info(f"Setting up events logger {__name__} for {full_path}")

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        os.path.join(full_path, "events.log"),
        maxBytes=1024 * 1024 * 50, # 10MB
        backupCount=DEFAULT_LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    #console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    return logger
