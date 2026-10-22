"""Strict input validation for the setpoint endpoint.

Validation answers "is this request well-formed and inside the hard bounds?".
It is a different question from "who are you?" (authentication) and "are you
allowed?" (authorization), and from "is this value operationally acceptable?"
(a policy / safety limit). The lesson keeps those four ideas apart.
"""

from __future__ import annotations

import json
import math

from . import config


class ValidationError(Exception):
    """A request was rejected before it could change any state."""

    def __init__(self, status: int, code: str, message: str, requested: float | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.requested = requested


def check_media_type(mimetype: str) -> None:
    if mimetype != "application/json":
        raise ValidationError(
            415, "unsupported_media_type", "Content-Type must be application/json."
        )


def check_size(content_length: int | None) -> None:
    if content_length is not None and content_length > config.MAX_BODY_BYTES:
        raise ValidationError(
            413,
            "payload_too_large",
            f"Request body must be at most {config.MAX_BODY_BYTES} bytes.",
        )


def _reject_constant(name: str):
    # Python's json accepts NaN / Infinity by default; standard JSON does not.
    raise ValueError(f"non-standard JSON constant: {name}")


def parse_setpoint_body(raw: bytes) -> float:
    """Return a finite setpoint within the GLOBAL range, or raise."""
    if len(raw) > config.MAX_BODY_BYTES:
        raise ValidationError(
            413,
            "payload_too_large",
            f"Request body must be at most {config.MAX_BODY_BYTES} bytes.",
        )
    if not raw.strip():
        raise ValidationError(400, "malformed_json", "Request body is empty.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationError(400, "malformed_json", "Body must be UTF-8 encoded JSON.")
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        raise ValidationError(400, "malformed_json", "Body is not valid JSON.")

    if not isinstance(data, dict) or set(data) != {"setpoint_c"}:
        raise ValidationError(
            400,
            "invalid_body",
            'Body must be a JSON object with exactly one key: "setpoint_c".',
        )

    value = data["setpoint_c"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(422, "invalid_value", "setpoint_c must be a JSON number.")
    try:
        number = float(value)
    except OverflowError:
        raise ValidationError(422, "invalid_value", "setpoint_c is not a finite number.")
    if not math.isfinite(number):
        raise ValidationError(422, "invalid_value", "setpoint_c is not a finite number.")

    if number < config.GLOBAL_MIN_C or number > config.GLOBAL_MAX_C:
        raise ValidationError(
            422,
            "out_of_range",
            f"setpoint_c must be between {config.GLOBAL_MIN_C:g} and "
            f"{config.GLOBAL_MAX_C:g} °C (global simulation range).",
            requested=number,
        )
    return number
