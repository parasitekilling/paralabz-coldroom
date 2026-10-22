"""ParaLabz ColdRoom: a local-only educational IoT access-control simulation.

No physical device is ever contacted. The application mode is chosen once, when
the app object is created, and cannot be changed while it runs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from . import config
from .audit import AuditLog
from .routes import bp, error_response
from .security import RateLimiter, check_host_and_origin, generate_token
from .simulation import Simulation

CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'"
)


@dataclass
class ColdRoomContext:
    mode: str
    simulation: Simulation
    audit: AuditLog
    limiter: RateLimiter
    # repr=False so the token can never leak through an accidental print/log.
    token: str | None = field(default=None, repr=False)

    @property
    def insecure(self) -> bool:
        return self.mode == config.MODE_INSECURE


def create_app(
    *,
    insecure: bool = False,
    operator_token: str | None = None,
    clock: Callable[[], float] | None = None,
) -> Flask:
    """Build the app. ``insecure`` is fixed for the life of the process.

    ``operator_token`` and ``clock`` exist so tests are deterministic.
    """
    clock = clock or time.monotonic
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_BODY_BYTES
    app.json.sort_keys = False

    mode = config.MODE_INSECURE if insecure else config.MODE_PROTECTED
    token = None if insecure else (operator_token or generate_token())
    ctx = ColdRoomContext(
        mode=mode,
        simulation=Simulation(clock=clock),
        audit=AuditLog(),
        limiter=RateLimiter(clock=clock),
        token=token,
    )
    app.extensions["coldroom"] = ctx
    app.register_blueprint(bp)

    @app.before_request
    def guard_host_and_origin():
        problem = check_host_and_origin(
            request.headers.get("Host"), request.headers.get("Origin")
        )
        if problem is None:
            return None
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            ctx.audit.record("request_guard", problem, None, ctx.mode)
        return error_response(
            403, problem, "Request rejected: Host/Origin is not the local ColdRoom app."
        )

    @app.after_request
    def add_security_headers(response):
        # Deliberately NO Access-Control-* headers: no CORS.
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(Exception)
    def handle_error(exc):
        if isinstance(exc, HTTPException):
            code = (exc.name or "error").lower().replace(" ", "_")
            response = jsonify(
                {"ok": False, "error": code, "message": exc.description or exc.name}
            )
            response.status_code = exc.code or 500
            allowed = getattr(exc, "valid_methods", None)
            if allowed:
                response.headers["Allow"] = ", ".join(allowed)
            return response
        # Never return tracebacks or internals to the client.
        app.logger.error("Unhandled %s in request handler", type(exc).__name__)
        return error_response(500, "internal_error", "Internal server error.")

    return app
