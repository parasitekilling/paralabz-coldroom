"""Host / Origin checks, CORS and response headers (both modes)."""

import pytest

from conftest import BASE


def test_bad_host_is_rejected_for_every_endpoint(either):
    api, token = either
    evil = "http://evil.example:5000"
    for path in ("/", "/api/status", "/api/audit", "/static/app.js"):
        assert api.get(path, base_url=evil).status_code == 403
    r = api.set('{"setpoint_c": -20}', token=token, base_url=evil)
    assert r.status_code == 403
    assert api.setpoint() == -18.0


def test_host_on_wrong_port_is_rejected(either):
    api, _ = either
    assert api.get("/api/status", base_url="http://127.0.0.1:8080").status_code == 403


@pytest.mark.parametrize("origin", ["http://evil.example", "null", "https://127.0.0.1:5000", "http://127.0.0.1:6000"])
def test_foreign_origin_is_rejected_even_with_valid_token(either, origin):
    api, token = either
    r = api.set('{"setpoint_c": -20}', token=token, headers={"Origin": origin})
    assert r.status_code == 403
    assert r.get_json()["error"] == "bad_origin"
    assert api.setpoint() == -18.0


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5000", "http://localhost:5000"])
def test_local_origin_is_accepted(either, origin):
    api, token = either
    r = api.set('{"setpoint_c": -20}', token=token, headers={"Origin": origin})
    assert r.status_code == 200


def test_localhost_host_header_is_accepted(either):
    api, _ = either
    assert api.get("/api/status", base_url="http://localhost:5000").status_code == 200


def test_rejected_guard_attempts_are_audited(protected):
    protected.set('{"setpoint_c": -20}', headers={"Origin": "http://evil.example"})
    latest = protected.get("/api/audit").get_json()["entries"][0]
    assert (latest["action"], latest["outcome"]) == ("request_guard", "bad_origin")


def test_no_cors_headers_anywhere(either):
    api, token = either
    responses = [
        api.get("/", headers={"Origin": BASE}),
        api.get("/api/status", headers={"Origin": BASE}),
        api.get("/api/status", headers={"Origin": "http://evil.example"}),
        api.set('{"setpoint_c": -20}', token=token, headers={"Origin": BASE}),
        api.options(
            "/api/setpoint",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        ),
    ]
    for r in responses:
        assert not [h for h in r.headers.keys() if h.lower().startswith("access-control-")]
    assert responses[-1].status_code == 403  # cross-site preflight is refused outright


def test_security_headers_are_present(either):
    api, _ = either
    r = api.get("/")
    csp = r.headers["Content-Security-Policy"]
    assert "default-src 'none'" in csp and "script-src 'self'" in csp
    assert "connect-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert api.get("/api/status").headers["Cache-Control"] == "no-store"
