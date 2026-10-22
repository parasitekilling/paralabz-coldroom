"""Bounded in-memory audit log.

Entries hold only: timestamp, action, outcome, requested value and mode.
Secrets (the operator token, supplied tokens, Authorization headers) are never
passed in here. The log lives in memory, is capped, and is lost on restart.
"""

from __future__ import annotations

import logging
import math
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Callable

from . import config

logger = logging.getLogger("coldroom.audit")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog:
    def __init__(
        self,
        max_entries: int = config.AUDIT_MAX_ENTRIES,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._entries: deque[dict] = deque(maxlen=max_entries)
        self._lock = threading.Lock()
        self._now = now

    def record(self, action: str, outcome: str, requested_c: object, mode: str) -> None:
        requested = None
        if (
            isinstance(requested_c, (int, float))
            and not isinstance(requested_c, bool)
            and math.isfinite(requested_c)
        ):
            requested = round(float(requested_c), 3)
        entry = {
            "timestamp": self._now().isoformat(timespec="seconds"),
            "action": action,
            "outcome": outcome,
            "requested_c": requested,
            "mode": mode,
        }
        with self._lock:
            self._entries.append(entry)
        logger.info(
            "audit action=%s outcome=%s requested_c=%s mode=%s",
            action,
            outcome,
            requested,
            mode,
        )

    def entries(self) -> list[dict]:
        """Newest first."""
        with self._lock:
            return list(reversed(self._entries))
