"""
Retry decorator and utilities for handling transient failures.
"""

import asyncio
import logging
from typing import Any, Callable, Optional, Type, TypeVar
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryError(Exception):
    """Raised when all retry attempts are exhausted"""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        self.message = message
        self.last_exception = last_exception
        super().__init__(message)


def retry_on_exception(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    timeout_seconds: float = 30.0,
    retryable_exceptions: Optional[list[Type[Exception]]] = None,
    non_retryable_exceptions: Optional[list[Type[Exception]]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts (total = 1 + max_attempts)
        backoff_factor: Multiplier for exponential backoff (0.5s, 1s, 2s, etc.)
        timeout_seconds: Total timeout for all attempts combined
        retryable_exceptions: List of exceptions to retry on. If None, retries transient exceptions.
        non_retryable_exceptions: List of exceptions to NOT retry (fail fast)
    
    Example:
        @retry_on_exception(max_attempts=3, backoff_factor=1.0, timeout_seconds=10.0)
        async def call_external_api():
            return await api.request()
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = datetime.now()
            timeout = timedelta(seconds=timeout_seconds)
            last_exception: Optional[Exception] = None

            for attempt in range(1, max_attempts + 2):  # +2 for initial + retries
                try:
                    elapsed = datetime.now() - start_time
                    if elapsed > timeout:
                        raise asyncio.TimeoutError(
                            f"Exceeded total timeout of {timeout_seconds}s after {attempt - 1} attempts"
                        )

                    # Execute the function with remaining timeout
                    remaining_timeout = (timeout - elapsed).total_seconds()
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=max(1.0, remaining_timeout),
                    )

                except Exception as exc:
                    last_exception = exc

                    # Check if this is a non-retryable exception
                    if non_retryable_exceptions:
                        for exc_type in non_retryable_exceptions:
                            if isinstance(exc, exc_type):
                                logger.warning(
                                    f"Non-retryable exception in {func.__name__}: {type(exc).__name__}: {str(exc)}"
                                )
                                raise

                    # Check if this is a retryable exception
                    if retryable_exceptions:
                        is_retryable = any(
                            isinstance(exc, exc_type) for exc_type in retryable_exceptions
                        )
                        if not is_retryable:
                            logger.warning(
                                f"Non-retryable exception in {func.__name__}: {type(exc).__name__}: {str(exc)}"
                            )
                            raise

                    # Check if we have attempts left
                    if attempt >= max_attempts + 1:
                        logger.error(
                            f"All {max_attempts} retry attempts exhausted for {func.__name__}"
                        )
                        raise RetryError(
                            f"Failed after {max_attempts + 1} attempts: {type(exc).__name__}: {str(exc)}",
                            last_exception=exc,
                        ) from exc

                    # Calculate backoff delay
                    delay = backoff_factor * (2 ** (attempt - 1))

                    # Check if we have time for another attempt
                    elapsed = datetime.now() - start_time
                    if elapsed + timedelta(seconds=delay) > timeout:
                        logger.error(
                            f"Timeout exceeded before retry attempt {attempt + 1} in {func.__name__}"
                        )
                        raise asyncio.TimeoutError(
                            f"Exceeded total timeout of {timeout_seconds}s after {attempt} attempts"
                        ) from exc

                    logger.debug(
                        f"Retry attempt {attempt} for {func.__name__} after {delay}s. "
                        f"Error: {type(exc).__name__}: {str(exc)}"
                    )

                    await asyncio.sleep(delay)

        return wrapper

    return decorator
