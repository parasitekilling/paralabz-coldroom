import pytest
from flask import Flask

import app as cli
from coldroom import config


def test_loopback_constants():
    assert config.HOST == "127.0.0.1"
    assert config.PORT == 5000


@pytest.mark.parametrize(
    "argv",
    [["--host", "0.0.0.0"], ["--port", "8080"], ["--debug"], ["--demo"], ["--insecure"]],
)
def test_parser_has_no_network_or_debug_options_and_no_abbreviations(argv):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(argv)


def _run_main(monkeypatch, argv):
    calls = {}
    captured = {}
    real_create = cli.create_app

    def spy_create(**kwargs):
        captured["app"] = real_create(**kwargs)
        return captured["app"]

    def fake_run(self, host=None, port=None, debug=None, **kwargs):
        calls.update(host=host, port=port, debug=debug, **kwargs)

    monkeypatch.setattr(cli, "create_app", spy_create)
    monkeypatch.setattr(Flask, "run", fake_run)
    cli.main(argv)
    return calls, captured["app"].extensions["coldroom"]


def test_main_binds_loopback_with_debug_and_reloader_off(monkeypatch, capsys):
    calls, _ = _run_main(monkeypatch, [])
    assert calls["host"] == "127.0.0.1"
    assert calls["port"] == 5000
    assert calls["debug"] is False
    assert calls["use_reloader"] is False
    capsys.readouterr()


def test_protected_start_prints_token_to_terminal_only(monkeypatch, capsys, caplog):
    with caplog.at_level("DEBUG"):
        _, ctx = _run_main(monkeypatch, [])
    out = capsys.readouterr().out
    assert "PROTECTED" in out
    assert ctx.token in out
    assert ctx.token not in caplog.text


def test_insecure_start_is_explicit_and_prints_no_token(monkeypatch, capsys):
    _, ctx = _run_main(monkeypatch, ["--demo-insecure"])
    out = capsys.readouterr().out
    assert ctx.mode == "insecure"
    assert "INSECURE TEACHING MODE" in out
    assert "Operator token" not in out
