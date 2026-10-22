import pytest

from conftest import TOKEN, WRONG_TOKEN

OK_BODY = '{"setpoint_c": -20}'


def test_unauthenticated_change_is_rejected_with_401(protected):
    r = protected.set(OK_BODY)
    assert r.status_code == 401
    assert "Bearer" in r.headers["WWW-Authenticate"]
    assert protected.setpoint() == -18.0


def test_wrong_token_is_rejected(protected):
    r = protected.set(OK_BODY, token=WRONG_TOKEN)
    assert r.status_code == 401
    assert protected.setpoint() == -18.0


@pytest.mark.parametrize(
    "header",
    ["Basic dXNlcjpwYXNz", "Bearer", "Bearer ", "bearer", "", f"Token {TOKEN}", f"Bearer {TOKEN} extra"],
)
def test_malformed_authorization_header_is_rejected(protected, header):
    r = protected.set(OK_BODY, headers={"Authorization": header})
    assert r.status_code == 401
    assert protected.setpoint() == -18.0


def test_token_in_query_string_is_ignored(protected):
    r = protected.post(
        f"/api/setpoint?token={TOKEN}&setpoint_c=-20",
        data=OK_BODY,
        content_type="application/json",
    )
    assert r.status_code == 401
    assert protected.setpoint() == -18.0


def test_valid_token_allows_in_policy_change(protected):
    r = protected.set(OK_BODY, token=TOKEN)
    assert r.status_code == 200
    assert r.get_json() == {"ok": True, "setpoint_c": -20.0, "mode": "protected"}
    assert protected.setpoint() == -20.0


def test_authentication_runs_before_body_parsing(protected):
    # Unauthenticated callers must learn nothing about body handling.
    r = protected.set("{not json", token=None)
    assert r.status_code == 401


def test_no_state_changing_get(protected):
    assert protected.get("/api/setpoint?setpoint_c=-20").status_code == 405
    assert protected.setpoint() == -18.0


def test_lockout_after_repeated_failures(protected, clock):
    for _ in range(5):
        assert protected.set(OK_BODY, token=WRONG_TOKEN).status_code == 401
    r = protected.set(OK_BODY, token=WRONG_TOKEN)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1
    # Even the right token is refused while locked out.
    assert protected.set(OK_BODY, token=TOKEN).status_code == 429
    assert protected.setpoint() == -18.0

    clock.advance(61)
    assert protected.set(OK_BODY, token=TOKEN).status_code == 200


def test_failures_outside_the_window_do_not_accumulate(protected, clock):
    for _ in range(4):
        protected.set(OK_BODY, token=WRONG_TOKEN)
    clock.advance(61)
    for _ in range(4):
        assert protected.set(OK_BODY, token=WRONG_TOKEN).status_code == 401
    assert protected.set(OK_BODY, token=TOKEN).status_code == 200


def test_success_resets_failure_counter(protected):
    for _ in range(4):
        protected.set(OK_BODY, token=WRONG_TOKEN)
    assert protected.set(OK_BODY, token=TOKEN).status_code == 200
    for _ in range(4):
        assert protected.set(OK_BODY, token=WRONG_TOKEN).status_code == 401


def test_lockout_is_per_source_address(protected):
    for _ in range(5):
        protected.set(OK_BODY, token=WRONG_TOKEN)
    other = protected.set(
        OK_BODY, token=TOKEN, environ_base={"REMOTE_ADDR": "127.0.0.2"}
    )
    assert other.status_code == 200
