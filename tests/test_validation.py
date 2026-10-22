"""Input validation, run against BOTH modes."""

import pytest


def _send(either, body, content_type="application/json"):
    api, token = either
    return api, api.set(body, token=token, content_type=content_type)


@pytest.mark.parametrize(
    "body,status,error",
    [
        (b"{", 400, "malformed_json"),
        (b"", 400, "malformed_json"),
        (b"   ", 400, "malformed_json"),
        (b"\xff\xfe\x00", 400, "malformed_json"),
        (b'{"setpoint_c": NaN}', 400, "malformed_json"),
        (b'{"setpoint_c": Infinity}', 400, "malformed_json"),
        (b'{"setpoint_c": -Infinity}', 400, "malformed_json"),
        (b"[" * 900, 400, "malformed_json"),
        (b"[-20]", 400, "invalid_body"),
        (b"-20", 400, "invalid_body"),
        (b'"-20"', 400, "invalid_body"),
        (b"{}", 400, "invalid_body"),
        (b'{"temp": -20}', 400, "invalid_body"),
        (b'{"setpoint_c": -20, "extra": 1}', 400, "invalid_body"),
        (b'{"setpoint_c": "-20"}', 422, "invalid_value"),
        (b'{"setpoint_c": null}', 422, "invalid_value"),
        (b'{"setpoint_c": true}', 422, "invalid_value"),
        (b'{"setpoint_c": [1]}', 422, "invalid_value"),
        (b'{"setpoint_c": 1e999}', 422, "invalid_value"),
        (b'{"setpoint_c": -1e999}', 422, "invalid_value"),
        (b'{"setpoint_c": 1' + b"0" * 400 + b"}", 422, "invalid_value"),
        (b'{"setpoint_c": 50}', 422, "out_of_range"),
        (b'{"setpoint_c": -100}', 422, "out_of_range"),
        (b'{"setpoint_c": 10.01}', 422, "out_of_range"),
    ],
)
def test_bad_bodies_are_rejected_without_changing_state(either, body, status, error):
    api, r = _send(either, body)
    assert r.status_code == status
    assert r.get_json()["error"] == error
    assert api.setpoint() == -18.0


@pytest.mark.parametrize(
    "content_type",
    [None, "text/plain", "application/x-www-form-urlencoded", "application/xml", "text/json"],
)
def test_wrong_content_type_is_415(either, content_type):
    api, r = _send(either, b'{"setpoint_c": -20}', content_type=content_type)
    assert r.status_code == 415
    assert api.setpoint() == -18.0


def test_json_with_charset_parameter_is_accepted(either):
    api, r = _send(either, b'{"setpoint_c": -20}', content_type="application/json; charset=utf-8")
    assert r.status_code == 200
    assert api.setpoint() == -20.0


def test_oversized_request_is_413(either):
    api, r = _send(either, b'{"setpoint_c": -20}' + b" " * 2000)
    assert r.status_code == 413
    assert r.get_json()["error"] == "payload_too_large"
    assert api.setpoint() == -18.0


def test_error_responses_are_json_not_tracebacks(either):
    api, _ = either
    for path in ("/nope", "/api/nope"):
        r = api.get(path)
        assert r.status_code == 404
        assert r.get_json()["ok"] is False
    r = api.post("/api/status")
    assert r.status_code == 405
    assert "Traceback" not in r.get_data(as_text=True)
