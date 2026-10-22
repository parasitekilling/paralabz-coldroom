"""ParaLabz ColdRoom entry point.

    python app.py                  protected mode (default)
    python app.py --demo-insecure  intentionally vulnerable teaching mode

The mode is chosen here, at startup, and cannot be changed while the app runs.
The app always binds to 127.0.0.1:5000. There are deliberately no --host or
--port options, and the debugger/reloader are always off.

Local educational simulation. No physical devices connected.
"""

from __future__ import annotations

import argparse
import logging

from coldroom import config, create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.py",
        description="ParaLabz ColdRoom - local educational IoT access-control simulation.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--demo-insecure",
        action="store_true",
        help=(
            "Start the INTENTIONALLY VULNERABLE teaching mode (no authorization "
            "on the setpoint endpoint). Local use only."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    app = create_app(insecure=args.demo_insecure)
    ctx = app.extensions["coldroom"]
    url = f"http://{config.HOST}:{config.PORT}/"

    print("=" * 66)
    print(" ParaLabz ColdRoom - local educational simulation")
    print(" No physical devices connected.")
    print("=" * 66)
    if ctx.insecure:
        print(" MODE: INSECURE TEACHING MODE (--demo-insecure)")
        print(" Access control on the setpoint endpoint is INTENTIONALLY MISSING.")
        print(" Use on this computer only. Restart without the flag to leave it.")
    else:
        print(" MODE: PROTECTED (default)")
        print(" Operator token (shown ONLY here; do not show this terminal on stream):")
        print(f"   {ctx.token}")
        print(" A new token is generated on every start.")
    print(f" Open: {url}   (loopback only; stop with Ctrl+C)")
    print("=" * 66, flush=True)

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    main()
