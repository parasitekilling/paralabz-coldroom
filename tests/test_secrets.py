import json
import pathlib

from coldroom import create_app
from conftest import TOKEN, WRONG_TOKEN, Api

STATIC = pathlib.Path(__file__).resolve().parents[1] / "coldroom" / "static"


def _exercise(api):
    """Touch every endpoint, with good and bad credentials; return all response text."""
    seen = []
    for path in ("/", "/api/status", "/api/audit", "/static/app.js", "/static/style.css"):
        r = api.get(path)
        seen.append(r.get_data(as_text=True) + str(r.headers))
    attempts = [
        api.set('{"setpoint_c": -20}', token=TOKEN),
        api.set('{"setpoint_c": -20}', token=WRONG_TOKEN),
        api.set('{"setpoint_c": -5}', token=TOKEN),
        api.set("{bad", token=TOKEN),
        api.set('{"setpoint_c": -20}'),
    ]
    for r in attempts:
        seen.append(r.get_data(as_text=True) + str(r.headers))
    seen.append(json.dumps(api.get("/api/audit").get_json()))
    return "\n".join(seen)


def test_token_never_appears_in_any_response_or_header(protected):
    blob = _exercise(protected)
    assert TOKEN not in blob
    assert WRONG_TOKEN not in blob


def test_token_never_appears_in_logs_or_audit(protected, caplog):
    with caplog.at_level("DEBUG"):
        _exercise(protected)
    assert TOKEN not in caplog.text
    assert WRONG_TOKEN not in caplog.text
    audit_dump = json.dumps(protected.ctx.audit.entries())
    assert TOKEN not in audit_dump and WRONG_TOKEN not in audit_dump
    assert "Authorization" not in audit_dump


def test_audit_entries_have_only_the_documented_fields(protected):
    protected.set('{"setpoint_c": -20}', token=TOKEN)
    protected.set('{"setpoint_c": -20}')
    for entry in protected.ctx.audit.entries():
        assert set(entry) == {"timestamp", "action", "outcome", "requested_c", "mode"}


def test_context_repr_does_not_leak_token(protected):
    assert TOKEN not in repr(protected.ctx)


def test_generated_tokens_are_long_and_unique():
    a = create_app().extensions["coldroom"].token
    b = create_app().extensions["coldroom"].token
    assert a != b
    assert len(a) >= 40 and len(b) >= 40


def test_frontend_never_persists_or_url_encodes_the_token():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    for forbidden in ("localStorage", "sessionStorage", "document.cookie", "indexedDB", "?token", "innerHTML"):
        assert forbidden not in js
    assert "operatorToken" in js  # held in a plain in-memory variable


def test_no_external_resources_anywhere():
    import re

    root = pathlib.Path(__file__).resolve().parents[1] / "coldroom"
    pattern = re.compile(r"https?://([^/\s\"'<>):]+)")
    for path in list(root.rglob("*.js")) + list(root.rglob("*.css")) + list(root.rglob("*.html")):
        for host in pattern.findall(path.read_text(encoding="utf-8")):
            assert host in {"127.0.0.1", "localhost"}, f"{path.name}: {host}"
