"""HTTP routes.

There is intentionally NO route that changes the application mode. The mode is
fixed when the process starts (see app.py).

Endpoints:
    GET  /               the single-page UI
    GET  /api/status     current mode, limits and simulated state
    GET  /api/audit      bounded audit log (no secrets)
    POST /api/setpoint   change the simulated setpoint (JSON body)
"""

from __future__ import annotations

import os
import subprocess
import sys
import re
import logging
import math
from flask import request, jsonify, current_app
from flask import Blueprint, current_app, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from . import config
from .security import extract_bearer, token_matches
from .validation import (
    ValidationError,
    check_media_type,
    check_size,
    parse_setpoint_body,
)

bp = Blueprint("main", __name__)
logger = logging.getLogger("coldroom.routes")

ACTION = "set_setpoint"


def _ctx():
    return current_app.extensions["coldroom"]


def error_response(status: int, code: str, message: str, headers: dict | None = None):
    response = jsonify({"ok": False, "error": code, "message": message})
    response.status_code = status
    for name, value in (headers or {}).items():
        response.headers[name] = value
    return response


def _reject(ctx, outcome, status, message, requested=None, headers=None):
    ctx.audit.record(ACTION, outcome, requested, ctx.mode)
    return error_response(status, outcome, message, headers)


def _read_setpoint() -> float:
    check_media_type(request.mimetype)
    check_size(request.content_length)
    try:
        raw = request.get_data(cache=False)
    except RequestEntityTooLarge:
        raise ValidationError(
            413,
            "payload_too_large",
            f"Request body must be at most {config.MAX_BODY_BYTES} bytes.",
        )
    return parse_setpoint_body(raw)


@bp.get("/")
def index():
    ctx = _ctx()
    return render_template(
        "index.html",
        mode=ctx.mode,
        insecure=ctx.insecure,
        disclaimer=config.DISCLAIMER,
        policy_note=config.POLICY_NOTE,
        model_note=config.MODEL_NOTE,
        example_command=config.EXAMPLE_COMMAND,
        global_min=config.GLOBAL_MIN_C,
        global_max=config.GLOBAL_MAX_C,
        policy_min=config.POLICY_MIN_C,
        policy_max=config.POLICY_MAX_C,
    )


@bp.get("/api/status")
def status():
    ctx = _ctx()
    limits = {
        "global_min_c": config.GLOBAL_MIN_C,
        "global_max_c": config.GLOBAL_MAX_C,
        "alarm_min_c": config.POLICY_MIN_C,
        "alarm_max_c": config.POLICY_MAX_C,
        "policy_enforced": not ctx.insecure,
    }
    if not ctx.insecure:
        limits["policy_min_c"] = config.POLICY_MIN_C
        limits["policy_max_c"] = config.POLICY_MAX_C
        limits["policy_note"] = config.POLICY_NOTE
    return jsonify(
        {
            "app": "ParaLabz ColdRoom",
            "mode": ctx.mode,
            "auth_required": not ctx.insecure,
            "access_control_missing": ctx.insecure,
            "disclaimer": config.DISCLAIMER,
            "model_note": config.MODEL_NOTE,
            "limits": limits,
            "simulation": ctx.simulation.snapshot(),
        }
    )


@bp.get("/api/audit")
def audit():
    ctx = _ctx()
    return jsonify(
        {"entries": ctx.audit.entries(), "max_entries": config.AUDIT_MAX_ENTRIES}
    )


@bp.post("/api/setpoint")
def set_setpoint():
    ctx = _ctx()
    key = request.remote_addr or "unknown"

    if not ctx.insecure:
        # 1. Throttle repeated failures from the same source address.
        remaining = ctx.limiter.locked_for(key)
        if remaining > 0:
            return _reject(
                ctx,
                "rate_limited",
                429,
                "Too many failed authentication attempts. Try again later.",
                headers={"Retry-After": str(max(1, math.ceil(remaining)))},
            )
        # 2. Authentication happens BEFORE the body is even parsed.
        supplied = extract_bearer(request.headers.get("Authorization"))
        if supplied is None or not token_matches(ctx.token, supplied):
            ctx.limiter.record_failure(key)
            return _reject(
                ctx,
                "unauthorized",
                401,
                "Authentication required: send 'Authorization: Bearer <operator token>'.",
                headers={"WWW-Authenticate": 'Bearer realm="coldroom"'},
            )
        ctx.limiter.record_success(key)

    # 3. Input validation (shape, type, finite, global simulation range).
    try:
        value = _read_setpoint()
    except ValidationError as exc:
        return _reject(ctx, exc.code, exc.status, exc.message, requested=exc.requested)

    # 4. Operational policy limit (protected mode only).
    if not ctx.insecure and not (config.POLICY_MIN_C <= value <= config.POLICY_MAX_C):
        return _reject(
            ctx,
            "out_of_policy",
            422,
            f"Setpoint is outside the demo operating policy "
            f"({config.POLICY_MIN_C:g} to {config.POLICY_MAX_C:g} °C). "
            "This is a chosen demo policy, not a universal requirement.",
            requested=value,
        )

    ctx.simulation.set_setpoint(value)
    ctx.audit.record(ACTION, "accepted", value, ctx.mode)
    if ctx.insecure:
        logger.warning(
            "INSECURE DEMO MODE: simulated setpoint changed to %.1f C with no "
            "authorization (intentional teaching flaw).",
            value,
        )
    return jsonify({"ok": True, "setpoint_c": value, "mode": ctx.mode})

@bp.route('/api/ping', methods=['GET'])
def ping():
    host = request.args.get('host', '127.0.0.1')
    
    # BULLETPROOF CHECK: Look directly at the terminal command
    is_insecure = '--demo-insecure' in sys.argv

    if is_insecure:
        # VULNERABLE: Command Injection
        cmd = f"ping -n 1 {host}" if os.name == 'nt' else f"ping -c 1 {host}"
        try:
            output = os.popen(cmd).read()
            return jsonify({"status": "success", "output": output})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        # SECURE: Input validation
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
             return jsonify({"error": "Invalid IP address format"}), 400
        try:
            cmd = ["ping", "-n", "1", host] if os.name == 'nt' else ["ping", "-c", "1", host]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return jsonify({"status": "success", "output": result.stdout})
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Request timed out"}), 408