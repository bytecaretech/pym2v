from typing import Generator

import pandas as pd
from loguru import logger
from tenacity import RetryCallState

from .types import IntInput, TsInput


def log_retry_attempt(retry_state: RetryCallState):
    if retry_state.attempt_number > 1:
        logger.info(
            f"Retrying {retry_state.fn.__name__}: attempt {retry_state.attempt_number}, reason: {retry_state.outcome}"
        )


def batch_interval(
    start: TsInput, end: TsInput, max_interval: IntInput = "1D"
) -> Generator[tuple[TsInput, TsInput], None, None]:
    """
    Split the interval between start and end into smaller intervals of at most max_interval.
    """
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    max_interval = pd.Timedelta(max_interval)
    left = start

    while left < end:
        right = min(left + max_interval, end)
        yield left, right
        left = right
