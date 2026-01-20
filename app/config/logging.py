"""
Logging configuration using loguru.
"""

import sys
from pathlib import Path
from loguru import logger as _logger
from app.config.settings import get_settings


def configure_logging():
    """Configure loguru with console and file handlers"""
    settings = get_settings()
    
    # Remove default handler
    _logger.remove()
    
    # Console handler
    _logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level
    )
    
    # File handler (create logs directory if needed)
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    _logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="500 MB",
        retention="7 days"
    )


def get_logger(name: str):
    """Get a logger instance for a module"""
    return _logger.bind(request_id=None).bind(module=name)
