import asyncio
import collections
import time

from datetime import datetime
from types import TracebackType
from typing import Optional, Callable, Awaitable, Any, Type

from ..base_functions.base_functions import logger


class AsyncRateLimiter:
    """
    Provides rate limiting for an operation with a configurable number of requests for a time period.
    """

    __lock: asyncio.Lock
    callback: Optional[Callable[[float], Awaitable[Any]]]
    max_calls: int
    period: float
    calls: collections.deque

    def __init__(
        self,
        max_calls: int,
        period: float = 1.0,
        callback: Optional[Callable[[float], Awaitable[Any]]] = None,
    ):
        if period <= 0:
            raise ValueError("Rate limiting period should be > 0")
        if max_calls <= 0:
            raise ValueError("Rate limiting number of calls should be > 0")
        self.calls = collections.deque()

        self.period = period
        self.max_calls = max_calls
        self.callback = callback
        self.__lock = asyncio.Lock()

    async def __aenter__(self) -> "AsyncRateLimiter":
        async with self.__lock:
            if len(self.calls) >= self.max_calls:
                until = datetime.utcnow().timestamp() + self.period - self._timespan
                if self.callback:
                    asyncio.ensure_future(self.callback(until))
                sleep_time = until - datetime.utcnow().timestamp()
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        async with self.__lock:
            # Store the last operation timestamp.
            self.calls.append(datetime.utcnow().timestamp())

            while self._timespan >= self.period:
                self.calls.popleft()

    @property
    def _timespan(self) -> float:
        return self.calls[-1] - self.calls[0]


async def throttle(self, delay: int, host: str) -> None:
    if delay is None or delay == 0:
        return

    key: Optional[str] = None
    while True:
        if key is None:
            key = f'throttle:{host}'
        now = time.time()
        last = self.throttle_times.get(key, 0.0)
        elapsed = now - last

        if elapsed >= delay:
            self.throttle_times[key] = now
            return

        remaining = delay - elapsed + 0.25

        log_string = f'\nDelaying request to {host} for {remaining:.2f} seconds.'
        # logger.debug(log_string)
        await asyncio.sleep(remaining)
