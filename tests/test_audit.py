import math

from coldroom.audit import AuditLog
from conftest import TOKEN


def test_log_is_bounded_and_newest_first():
    log = AuditLog(max_entries=5)
    for i in range(20):
        log.record("set_setpoint", "accepted", float(-i), "protected")
    entries = log.entries()
    assert len(entries) == 5
    assert entries[0]["requested_c"] == -19.0
    assert entries[-1]["requested_c"] == -15.0


def test_requested_value_is_sanitised():
    log = AuditLog()
    for bad in (math.nan, math.inf, "not a number", None, True, [1]):
        log.record("set_setpoint", "invalid_value", bad, "protected")
    assert all(e["requested_c"] is None for e in log.entries())


def test_entry_has_timestamp_action_outcome_value_mode():
    log = AuditLog()
    log.record("set_setpoint", "accepted", -20, "protected")
    entry = log.entries()[0]
    assert set(entry) == {"timestamp", "action", "outcome", "requested_c", "mode"}
    assert entry["timestamp"].endswith("+00:00")


def test_api_audit_is_bounded_under_spam(insecure):
    for _ in range(250):
        insecure.set("{bad")
    data = insecure.get("/api/audit").get_json()
    assert len(data["entries"]) == data["max_entries"] == 100


def test_audit_records_each_kind_of_outcome(protected):
    protected.set('{"setpoint_c": -20}')  # 401
    protected.set('{"setpoint_c": -10}', token=TOKEN)  # 422 policy
    protected.set("{bad", token=TOKEN)  # 400
    protected.set('{"setpoint_c": -22}', token=TOKEN)  # ok
    outcomes = [e["outcome"] for e in protected.get("/api/audit").get_json()["entries"]]
    assert outcomes == ["accepted", "malformed_json", "out_of_policy", "unauthorized"]
