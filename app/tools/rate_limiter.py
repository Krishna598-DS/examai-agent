# app/tools/rate_limiter.py
import asyncio
import time
from collections import deque
from app.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Tracks call timestamps in a sliding window.
    If too many calls happen in the window, it waits.

    This is the "sliding window" algorithm — one of the standard
    rate limiting algorithms used in production systems.
    Others include: token bucket, leaky bucket, fixed window.
    Sliding window is accurate but uses more memory.
    Token bucket is the most common in practice (used by AWS, Stripe).

    Args:
        max_calls: Maximum number of calls allowed in the window
        window_seconds: The time window in seconds
    """

    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        # deque with maxlen automatically drops oldest entries
        self.call_times: deque = deque()
        # asyncio.Lock ensures only one coroutine checks/updates at a time
        # Without this, two concurrent requests could both pass the check
        # and both make calls, exceeding the limit
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Wait until a call slot is available.
        Blocks the caller if the rate limit is reached.
        """
        async with self._lock:
            now = time.monotonic()

            # Remove timestamps older than our window
            # monotonic() is better than time() for measuring durations
            # because it never goes backwards (unlike system time which
            # can jump if the clock is adjusted)
            while self.call_times and \
                  now - self.call_times[0] >= self.window_seconds:
                self.call_times.popleft()

            if len(self.call_times) >= self.max_calls:
                # Calculate how long to wait
                oldest_call = self.call_times[0]
                wait_time = self.window_seconds - (now - oldest_call)

                logger.warning(
                    "rate_limit_reached",
                    current_calls=len(self.call_times),
                    max_calls=self.max_calls,
                    wait_seconds=round(wait_time, 2)
                )

                # Release lock while waiting so other coroutines can check
                # (they'll also wait, but this prevents deadlock)
                await asyncio.sleep(wait_time)

            self.call_times.append(time.monotonic())

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        pass


# Module-level rate limiter instances
# Serper free tier: 2500/month ≈ 83/day ≈ 3/hour to be safe in development
# We set 10 per minute as a reasonable development limit
serper_limiter = RateLimiter(max_calls=10, window_seconds=60)

# OpenAI has much higher limits but we still rate limit to control costs
openai_limiter = RateLimiter(max_calls=50, window_seconds=60)
