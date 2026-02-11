"""Logger configuration for the pym2v package."""

import logging
import sys


def get_logger(name: str, level: int | str = logging.INFO) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: The name of the logger (typically __name__).
        level: The logging level. Defaults to INFO.

    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(formatter)

        logger.setLevel(level)
        logger.addHandler(console_handler)
        logger.propagate = False

    return logger
