import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

EVENTS_LEVEL_NUM = 38
DEFAULT_LOG_BACKUP_COUNT = 10
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB

logger = None


def _timestamp_namer(default_name):
    """
    Custom namer function for RotatingFileHandler.
    Converts backup file names from index-based to timestamp-based format.
    
    RotatingFileHandler creates backup files with format: base.log.1, base.log.2, etc.
    This function converts them to: base_YYYY-MM-DD_HH-MM-SS.log
    
    Example:
        events.log.1 -> events_2025-12-30_14-30-00.log
        events.log.2 -> events_2025-12-30_15-45-00.log
    """
    # Extract directory and base filename
    directory = os.path.dirname(default_name)
    base_name = os.path.basename(default_name)
    
    # RotatingFileHandler creates files like: events.log.1, events.log.2, etc.
    # Split by '.' to separate base name and index
    parts = base_name.split('.')
    
    if len(parts) >= 3:
        # Format: events.log.1
        # parts = ['events', 'log', '1']
        base_parts = parts[:-1]  # ['events', 'log']
        index = parts[-1]  # '1'
        
        # Reconstruct base name without index: events.log
        base = '.'.join(base_parts)
        
        # Generate timestamp for the backup file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Convert to readable format: events_YYYY-MM-DD_HH-MM-SS.log
        # Remove .log extension from base
        if base.endswith('.log'):
            base_without_ext = base[:-4]  # 'events'
            new_name = f"{base_without_ext}_{timestamp}.log"
        else:
            # If no .log extension, just add timestamp
            new_name = f"{base}_{timestamp}.log"
        
        return os.path.join(directory, new_name)
    
    # Fallback: return original name if format doesn't match
    return default_name


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
    
    # Use RotatingFileHandler with size-based rotation (10MB)
    # Custom namer will convert backup files to timestamp-based names
    # This will create files like: events.log, events_2025-12-30_14-30-00.log, etc.
    log_file_path = os.path.join(full_path, "events.log")
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=DEFAULT_MAX_BYTES,  # 10MB
        backupCount=DEFAULT_LOG_BACKUP_COUNT,
        encoding='utf-8',
    )
    
    # Set custom namer to use timestamp-based naming instead of index-based
    file_handler.namer = _timestamp_namer
    
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    #console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    return logger
