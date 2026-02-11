"""Utilities for the pym2v package."""

from datetime import datetime, timedelta
from typing import Generator

from tenacity import RetryCallState

from .logger import get_logger

logger = get_logger(__name__)


def _log_retry_attempt(retry_state: RetryCallState):
    """Log retry attempts.

    Args:
        retry_state (RetryCallState): The state of the retry call.
    """
    if retry_state.attempt_number > 1:
        logger.info(
            "Retrying %s: attempt %d, reason: %s",
            retry_state.fn.__name__,  # type: ignore
            retry_state.attempt_number,
            retry_state.outcome,
        )


def batch_interval(
    start: datetime, end: datetime, max_interval: timedelta
) -> Generator[tuple[datetime, datetime], None, None]:
    """Split the interval between start and end into smaller intervals of at most max_interval.

    Args:
        start: The start of the interval.
        end: The end of the interval.
        max_interval: The maximum size of each smaller interval.

    Yields:
        Smaller intervals as (start, end) tuples.
    """
    left = start

    while left < end:
        right = min(left + max_interval, end)
        yield left, right
        left = right
