# app/tools/retry.py
import asyncio
import random
from typing import TypeVar, Callable, Any
from functools import wraps
from app.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


async def with_retry(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
    **kwargs
) -> Any:
    """
    Execute an async function with exponential backoff retry logic.

    Args:
        func: The async function to retry
        *args: Positional arguments to pass to func
        max_retries: Maximum number of retry attempts
        base_delay: Starting delay in seconds
        max_delay: Maximum delay cap in seconds
        retryable_exceptions: Only retry on these exception types
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value of func on success

    Raises:
        The last exception if all retries are exhausted
    """
    last_exception = None

    for attempt in range(max_retries + 1):  # +1 for the initial attempt
        try:
            if attempt > 0:
                # Calculate exponential backoff
                # 2^attempt gives: 2, 4, 8, 16...
                delay = min(base_delay * (2 ** attempt), max_delay)

                # Add jitter: random value between 0 and 30% of delay
                # This spreads retries from multiple clients
                jitter = random.uniform(0, delay * 0.3)
                total_delay = delay + jitter

                logger.warning(
                    "retry_attempt",
                    attempt=attempt,
                    max_retries=max_retries,
                    delay_seconds=round(total_delay, 2),
                    error=str(last_exception)
                )

                await asyncio.sleep(total_delay)

            return await func(*args, **kwargs)

        except retryable_exceptions as e:
            last_exception = e

            # Don't retry on the last attempt
            if attempt == max_retries:
                logger.error(
                    "retry_exhausted",
                    attempts=max_retries + 1,
                    final_error=str(e)
                )
                raise

    raise last_exception


def retryable(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,)
):
    """
    Decorator version of with_retry.
    Apply to any async function to make it automatically retry on failure.

    Usage:
        @retryable(max_retries=3, base_delay=1.0)
        async def my_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await with_retry(
                func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
        return wrapper
    return decorator
