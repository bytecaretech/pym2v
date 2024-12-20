"""Utilities for the pym2v package.

This module provides utility functions for the pym2v package.
"""

from typing import Generator

import pandas as pd
from loguru import logger
from tenacity import RetryCallState

from .types import IntInput, TsInput


def _log_retry_attempt(retry_state: RetryCallState):
    """Log retry attempts.

    Args:
        retry_state (RetryCallState): The state of the retry call.
    """
    if retry_state.attempt_number > 1:
        logger.info(
            f"Retrying {retry_state.fn.__name__}: attempt {retry_state.attempt_number}, reason: {retry_state.outcome}"  # type: ignore
        )


def batch_interval(
    start: TsInput, end: TsInput, max_interval: IntInput = "1D"
) -> Generator[tuple[TsInput, TsInput], None, None]:
    """Split the interval between start and end into smaller intervals of at most max_interval.

    Args:
        start (TsInput): The start of the interval.
        end (TsInput): The end of the interval.
        max_interval (IntInput, optional): The maximum size of each smaller interval. Defaults to "1D".

    Yields:
        Generator[tuple[TsInput, TsInput], None, None]: A generator yielding smaller intervals as tuples.
    """
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    max_interval = pd.Timedelta(max_interval)
    left = start

    while left < end:
        right = min(left + max_interval, end)
        yield left, right
        left = right
