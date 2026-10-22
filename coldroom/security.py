"""Authentication helpers for protected mode.

Small, honest building blocks for a teaching model:

* a random operator token,
* a constant-time token comparison,
* a Host / Origin allowlist check,
* an in-memory limiter for repeated failed authentication.

The limiter slows down guessing from one source address. It does NOT protect
against a distributed attack, and on loopback every local client shares the
same source address.
"""

from __future__ import annotations

import hmac
import secrets
import threading
import time
from collections import deque
from typing import Callable

from . import config


def generate_token() -> str:
    """256 bits of randomness, URL-safe."""
    return secrets.token_urlsafe(32)


def extract_bearer(header_value: str | None) -> str | None:
    """Return the token from 'Authorization: Bearer <token>', else None."""
    if not header_value or len(header_value) > config.MAX_AUTH_HEADER_CHARS:
        return None
    parts = header_value.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        return None
    return parts[1]


def token_matches(expected: str | None, supplied: str) -> bool:
    if not expected:
        return False
    return hmac.compare_digest(
        expected.encode("utf-8", "replace"), supplied.encode("utf-8", "replace")
    )


def check_host_and_origin(host: str | None, origin: str | None) -> str | None:
    """Return an error code if Host/Origin are not the local app, else None."""
    if host is None or host.lower() not in config.ALLOWED_HOSTS:
        return "bad_host"
    if origin is not None and origin.lower() not in config.ALLOWED_ORIGINS:
        return "bad_origin"
    return None


class RateLimiter:
    """Lock a source address out after repeated failed authentication."""

    def __init__(
        self,
        max_failures: int = config.RATE_MAX_FAILURES,
        window_s: float = config.RATE_WINDOW_S,
        lockout_s: float = config.RATE_LOCKOUT_S,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 256,
    ) -> None:
        self._max_failures = max_failures
        self._window_s = window_s
        self._lockout_s = lockout_s
        self._clock = clock
        self._max_keys = max_keys
        self._lock = threading.Lock()
        self._failures: dict[str, deque[float]] = {}
        self._locked_until: dict[str, float] = {}

    def locked_for(self, key: str) -> float:
        """Seconds of lockout remaining for this key (0 if not locked)."""
        with self._lock:
            until = self._locked_until.get(key)
            if until is None:
                return 0.0
            remaining = until - self._clock()
            if remaining <= 0:
                del self._locked_until[key]
                return 0.0
            return remaining

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            attempts = self._failures.setdefault(key, deque())
            while attempts and now - attempts[0] > self._window_s:
                attempts.popleft()
            attempts.append(now)
            if len(attempts) >= self._max_failures:
                self._locked_until[key] = now + self._lockout_s
                del self._failures[key]
            self._prune_locked()

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def _prune_locked(self) -> None:
        # Keep memory bounded even if many distinct keys show up.
        while len(self._failures) > self._max_keys:
            self._failures.pop(next(iter(self._failures)))
        while len(self._locked_until) > self._max_keys:
            self._locked_until.pop(next(iter(self._locked_until)))
