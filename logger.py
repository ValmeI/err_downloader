from loguru import logger
import sys
import traceback
from pathlib import Path
from types import TracebackType
from typing import Optional, Type


def setup_loguru_logger(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Setup loguru logger with custom format."""
    logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS ZZ}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>{exception}"
    )

    # Always log to stderr (for manual runs)
    logger.add(sys.stderr, level=level, format=log_format, colorize=True, backtrace=True, diagnose=True)

    # Also log to file if specified
    if log_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Add file handler (without colors)
        logger.add(
            log_file,
            level=level,
            format=log_format,
            colorize=False,
            backtrace=True,
            diagnose=True,
            rotation="00:00",  # Rotate at midnight
            retention="14 days",  # Keep logs for 14 days
            compression="gz"  # Compress old logs
        )


def handle_exception(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Optional[TracebackType], stack_row_limit: int = 10) -> None:
    """Global exception handler to catch and log any uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        traceback_string = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback, limit=stack_row_limit))
        logger.error(f"An unhandled exception occurred: {exc_type.__name__}: {exc_value}, traceback: {traceback_string}")


def init_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Initialize logging with exception handling."""
    setup_loguru_logger(level, log_file)
    sys.excepthook = handle_exception
