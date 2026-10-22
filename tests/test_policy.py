import pytest

from conftest import TOKEN


@pytest.mark.parametrize("value", [-25, -25.0, -20, -15, -15.0])
def test_values_inside_policy_are_accepted(protected, value):
    r = protected.set(f'{{"setpoint_c": {value}}}', token=TOKEN)
    assert r.status_code == 200
    assert protected.setpoint() == float(value)


@pytest.mark.parametrize("value", [-25.01, -14.99, -10, 0, 10, -26, -40])
def test_authenticated_out_of_policy_is_rejected(protected, value):
    r = protected.set(f'{{"setpoint_c": {value}}}', token=TOKEN)
    assert r.status_code == 422
    assert r.get_json()["error"] in {"out_of_policy"}
    assert protected.setpoint() == -18.0


def test_out_of_policy_message_calls_it_a_demo_policy(protected):
    r = protected.set('{"setpoint_c": -10}', token=TOKEN)
    assert "demo" in r.get_json()["message"].lower()
    assert "not a universal" in r.get_json()["message"].lower()


def test_status_documents_policy_as_chosen_demo_policy(protected):
    limits = protected.status()["limits"]
    assert limits["policy_enforced"] is True
    assert (limits["policy_min_c"], limits["policy_max_c"]) == (-25.0, -15.0)
    assert "not a universal" in limits["policy_note"]


def test_policy_is_not_enforced_in_insecure_mode_but_global_range_is(insecure):
    assert insecure.status()["limits"]["policy_enforced"] is False
    assert insecure.set('{"setpoint_c": -10}').status_code == 200
    assert insecure.set('{"setpoint_c": 10}').status_code == 200
    assert insecure.set('{"setpoint_c": -40}').status_code == 200
    assert insecure.set('{"setpoint_c": 10.5}').status_code == 422
    assert insecure.set('{"setpoint_c": -40.5}').status_code == 422
    assert insecure.setpoint() == -40.0
