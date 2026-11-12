"""SpirandeliEmpire OS 3.2 — Sliding Window Rate Limiter"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict
from fastapi import HTTPException, status

_BUCKETS: Dict[str, Deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, max_requests: int = 10, window_seconds: int = 60) -> None:
    """Enforce sliding-window rate limit per IP/key."""
    now = time.monotonic()
    q = _BUCKETS[key]
    cutoff = now - window_seconds
    while q and q[0] < cutoff:
        q.popleft()
    if len(q) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Aguarde alguns instantes antes de tentar novamente.",
        )
    q.append(now)


def reset_rate_limits() -> None:
    _BUCKETS.clear()

