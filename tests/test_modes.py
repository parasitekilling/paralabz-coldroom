import pytest

from coldroom import create_app
from conftest import Api, TOKEN


def test_default_mode_is_protected():
    api = Api(create_app())
    assert api.status()["mode"] == "protected"
    assert api.ctx.token  # a token was generated


def test_protected_page_shows_mode_and_disclaimer(protected):
    html = protected.get("/").get_data(as_text=True)
    assert "MODE: PROTECTED" in html
    assert "INTENTIONALLY MISSING" not in html
    assert (
        "Local educational simulation. No physical devices connected. "
        "Not a reproduction of the French refrigeration attack."
    ) in html


def test_insecure_page_shows_red_warning_and_example_once(insecure):
    html = insecure.get("/").get_data(as_text=True)
    assert "MODE: INSECURE TEACHING MODE" in html
    assert "ACCESS CONTROL IS INTENTIONALLY MISSING" in html
    assert 'role="alert"' in html
    assert html.count("/api/setpoint") == 1  # exactly one example request
    assert "token-input" not in html  # no token UI in insecure mode


def test_insecure_mode_allows_unauthenticated_change_and_logs_it(insecure, caplog):
    with caplog.at_level("INFO"):
        r = insecure.set('{"setpoint_c": -10}')
    assert r.status_code == 200
    assert insecure.setpoint() == -10.0
    assert insecure.status()["access_control_missing"] is True
    latest = insecure.get("/api/audit").get_json()["entries"][0]
    assert (latest["outcome"], latest["requested_c"], latest["mode"]) == ("accepted", -10.0, "insecure")
    assert "INSECURE DEMO MODE" in caplog.text


def test_insecure_mode_has_no_token_and_ignores_auth_header(insecure):
    assert insecure.ctx.token is None
    r = insecure.set('{"setpoint_c": -12}', headers={"Authorization": "Bearer whatever"})
    assert r.status_code == 200


def test_insecure_mode_does_not_rate_limit(insecure):
    for _ in range(20):
        assert insecure.set('{"setpoint_c": -12}').status_code == 200


def test_protected_status_flags(protected):
    s = protected.status()
    assert s["auth_required"] is True
    assert s["access_control_missing"] is False


def test_no_route_can_switch_modes(protected):
    rules = {r.rule for r in protected.app.url_map.iter_rules()}
    assert rules == {"/", "/api/status", "/api/audit", "/api/setpoint", "/static/<path:filename>"}
    for path in ("/api/mode", "/api/config", "/mode", "/admin"):
        for method in ("get", "post", "put"):
            r = getattr(protected._client, method)(path, base_url="http://127.0.0.1:5000")
            assert r.status_code in (404, 405)
    assert protected.status()["mode"] == "protected"


def test_mode_cannot_be_changed_through_setpoint_body(protected):
    r = protected.set('{"setpoint_c": -20, "mode": "insecure"}', token=TOKEN)
    assert r.status_code == 400
    assert protected.status()["mode"] == "protected"


def test_state_is_not_shared_between_app_instances():
    a, b = Api(create_app(operator_token="a" * 40)), Api(create_app(operator_token="b" * 40))
    a.set('{"setpoint_c": -20}', token="a" * 40)
    assert b.setpoint() == -18.0
