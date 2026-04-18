"""Shared logging utilities for worker services."""

from __future__ import annotations

import logging


def configure_worker_logging(
    *,
    logger_name: str,
    log_level: str,
    console_log_level: str,
    log_file: str | None,
) -> logging.Logger:
    """Configure console/file logging with separate verbosity levels."""

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, console_log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    worker_logger = logging.getLogger(logger_name)
    worker_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    return worker_logger


def short_error(exc: BaseException) -> str:
    """Return a compact one-line error summary."""

    message = str(getattr(exc, "orig", exc))
    message = message.split("[parameters:", 1)[0]
    message = message.split("(Background on this error at:", 1)[0]
    message = message.replace("\n", " ").strip()
    if not message:
        message = exc.__class__.__name__
    return f"{exc.__class__.__name__}: {message}"
