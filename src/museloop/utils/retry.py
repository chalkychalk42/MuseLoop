"""Retry utilities using tenacity."""

from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Retry decorator for generation tasks (API calls, model inference)
# Includes rate-limit (429) and transient server errors
retry_generation = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((
        TimeoutError,
        ConnectionError,
        OSError,
        httpx.HTTPStatusError,
    )),
    reraise=True,
)
