"""Tiny illustrative cold-room model.

This is a teaching toy, NOT an engineering model. It exists so that the
requested setpoint and the simulated measured temperature are two different
things that change at different speeds.

Model, advanced in fixed 0.5 s steps:

* The room leaks heat toward a warm ambient temperature all the time.
* A thermostat with hysteresis switches a "compressor" on and off around the
  setpoint. While on, it removes heat at a fixed rate.
* Every few minutes a short "defrost" cycle switches the compressor off and
  adds a little heat.
* An alarm becomes active only after the measured value has stayed outside the
  demo range for a short delay.

The simulation advances lazily: it catches up whenever it is read or changed,
using an injectable clock so tests are deterministic. There is no background
thread and nothing here touches files, processes or the network.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from typing import Callable

from . import config

AMBIENT_C = 8.0
LEAK_PER_S = 0.004
COOL_RATE_C_PER_S = 0.30
DEFROST_HEAT_C_PER_S = 0.04
HYSTERESIS_C = 0.5
DEFROST_INTERVAL_S = 300.0
DEFROST_DURATION_S = 15.0
ALARM_DELAY_S = 10.0

STEP_S = 0.5
MAX_CATCHUP_S = 3600.0
SAMPLE_EVERY_S = 2.0
HISTORY_MAX = 150
MODEL_FLOOR_C = -60.0
MODEL_CEILING_C = 25.0


class Simulation:
    """Thread-safe simulated cold room."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._last = clock()
        self._pending = 0.0
        self._sim_time = 0.0
        self._temp = config.INITIAL_TEMP_C
        self._setpoint = config.INITIAL_TEMP_C
        self._compressor = False
        self._defrost_left = 0.0
        self._since_defrost = 0.0
        self._outside_for = 0.0
        self._sample_acc = 0.0
        self._history: deque[tuple[float, float, float]] = deque(maxlen=HISTORY_MAX)
        self._record_sample()

    # -- public API ---------------------------------------------------------

    def set_setpoint(self, value: float) -> float:
        """Set the requested setpoint. Always bounded to the global range."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("setpoint must be a number")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("setpoint must be finite")
        if number < config.GLOBAL_MIN_C or number > config.GLOBAL_MAX_C:
            raise ValueError(
                f"setpoint must be between {config.GLOBAL_MIN_C} and "
                f"{config.GLOBAL_MAX_C} degrees C"
            )
        with self._lock:
            self._advance_locked()
            self._setpoint = number
        return number

    def snapshot(self) -> dict:
        """Return the current state as plain JSON-friendly data."""
        with self._lock:
            self._advance_locked()
            defrosting = self._defrost_left > 0
            if defrosting:
                phase = "defrost"
                next_defrost = 0.0
            else:
                phase = "cooling" if self._compressor else "holding"
                next_defrost = max(0.0, DEFROST_INTERVAL_S - self._since_defrost)

            outside = self._is_outside(self._temp)
            active = outside and self._outside_for >= ALARM_DELAY_S
            kind = None
            if outside:
                kind = "high" if self._temp > config.POLICY_MAX_C else "low"
            return {
                "setpoint_c": round(self._setpoint, 2),
                "measured_c": round(self._temp, 2),
                "compressor_on": self._compressor,
                "phase": phase,
                "next_defrost_in_s": round(next_defrost, 1),
                "sim_time_s": round(self._sim_time, 1),
                "alarm": {
                    "active": active,
                    "pending": outside and not active,
                    "kind": kind if outside else None,
                    "min_c": config.POLICY_MIN_C,
                    "max_c": config.POLICY_MAX_C,
                    "delay_s": ALARM_DELAY_S,
                },
                "history": [list(sample) for sample in self._history],
            }

    # -- internals (lock must be held) ----------------------------------------

    @staticmethod
    def _is_outside(temp: float) -> bool:
        return temp < config.POLICY_MIN_C or temp > config.POLICY_MAX_C

    def _advance_locked(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        self._last = now
        if elapsed <= 0:
            return
        self._pending += min(elapsed, MAX_CATCHUP_S)
        while self._pending >= STEP_S:
            self._pending -= STEP_S
            self._step(STEP_S)

    def _update_defrost(self, dt: float) -> bool:
        if self._defrost_left > 0:
            self._defrost_left -= dt
            if self._defrost_left <= 0:
                self._defrost_left = 0.0
                self._since_defrost = 0.0
                return False
            return True
        self._since_defrost += dt
        if self._since_defrost >= DEFROST_INTERVAL_S:
            self._defrost_left = DEFROST_DURATION_S
            return True
        return False

    def _step(self, dt: float) -> None:
        self._sim_time += dt
        defrosting = self._update_defrost(dt)

        if defrosting:
            self._compressor = False
        elif self._compressor:
            if self._temp <= self._setpoint - HYSTERESIS_C:
                self._compressor = False
        elif self._temp >= self._setpoint + HYSTERESIS_C:
            self._compressor = True

        rate = LEAK_PER_S * (AMBIENT_C - self._temp)
        if self._compressor:
            rate -= COOL_RATE_C_PER_S
        if defrosting:
            rate += DEFROST_HEAT_C_PER_S
        self._temp = min(max(self._temp + rate * dt, MODEL_FLOOR_C), MODEL_CEILING_C)

        if self._is_outside(self._temp):
            self._outside_for += dt
        else:
            self._outside_for = 0.0

        self._sample_acc += dt
        if self._sample_acc >= SAMPLE_EVERY_S:
            self._sample_acc -= SAMPLE_EVERY_S
            self._record_sample()

    def _record_sample(self) -> None:
        self._history.append(
            (round(self._sim_time, 1), round(self._temp, 2), round(self._setpoint, 2))
        )
