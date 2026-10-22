# ParaLabz ColdRoom

> Local educational simulation. No physical devices connected.
> Not a reproduction of the French refrigeration attack.

A small, **local-only** teaching app for *ParaLabz #03* (IoT access control and defensive engineering). It simulates a pixel-art cold room and lets you compare two ways of running the same "change the setpoint" endpoint:

| Mode | How to start | What it teaches |
|---|---|---|
| **Protected** (default) | `python app.py` | token authentication, input validation, an operating-policy limit, rate limiting, audit log |
| **Insecure teaching mode** | `python app.py --demo-insecure` | what *missing authorization* on one endpoint looks like |

It is a **beginner teaching model**. It is not production-secure and not a pentest qualification.

## Scope

- Nothing here connects to a physical device, a manufacturer controller, or any public target.
- No exploit, no scanner, no brute-force tool, no credential list.
- No CDNs, external APIs, analytics, telemetry, Docker or cloud. Local assets only.
- Binds to `127.0.0.1:5000` only. There is no `--host`/`--port` option. Debug mode and the reloader are always off.
- The mode is fixed at startup. **No endpoint can change it; you must restart.**
- The simulation is illustrative (a thermostat with leakage and a periodic defrost), not engineering-accurate.

## Quick start on Windows 11 + VS Code (lightest path)

You need only **Python 3.10+** from python.org (a normal per-user install, no admin needed) and VS Code. No Docker, no Node.

1. Unzip/copy the folder, then in VS Code: **File > Open Folder** and pick `paralabz-coldroom`.
2. Easiest: double-click **`start-protected.bat`** (or **`start-insecure.bat`**) in Explorer. The first run creates a local `.venv` and installs Flask (a few seconds); later runs start instantly.
3. Or use the VS Code terminal (**Terminal > New Terminal**, PowerShell):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py                 # protected
.\.venv\Scripts\python.exe app.py --demo-insecure # insecure teaching mode
```

   Using the `.venv\Scripts\python.exe` path directly avoids PowerShell's script-execution policy; you do not need to "activate" anything.
4. Or use the VS Code task menu: **Terminal > Run Task...** and choose *ColdRoom: protected* or *ColdRoom: INSECURE teaching mode* (after step 3's install once).
5. Open <http://127.0.0.1:5000/>. In protected mode, copy the **operator token** printed in the terminal.

Stop with **Ctrl+C**.

## Quick start on Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py                  # protected
.venv/bin/python app.py --demo-insecure  # insecure teaching mode
```

## The one demo request

Run from the project folder. In Windows PowerShell type `curl.exe` instead of `curl` (PowerShell's `curl` is a different command).

```
curl -X POST http://127.0.0.1:5000/api/setpoint -H "Content-Type: application/json" --data-binary "@demo/setpoint.json"
```

The file `demo/setpoint.json` contains `{"setpoint_c": -10}`.

- **Insecure mode:** accepted (HTTP 200). The requested setpoint jumps to -10 °C at once, the *measured* value climbs gradually, and the alarm appears after it leaves the demo range for ~10 s.
- **Protected mode:** rejected with **HTTP 401** (no token). With a token, -10 °C is still rejected (HTTP 422 `out_of_policy`) because it is outside the demo policy.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | the UI |
| GET | `/api/status` | mode, limits, requested setpoint, measured temperature, alarm, history |
| GET | `/api/audit` | bounded audit log (no secrets) |
| POST | `/api/setpoint` | body `{"setpoint_c": <number>}`, `Content-Type: application/json`, max 1024 bytes |

Protected mode requires `Authorization: Bearer <operator token>` on `POST /api/setpoint`.

Status codes: `200` ok, `400` malformed JSON / wrong shape, `401` missing or bad token, `403` bad Host/Origin, `413` body too large, `415` wrong content type, `422` invalid value, outside the global range (-40 to +10 °C), or (protected) outside the demo policy, `429` too many failed attempts.

Check order in protected mode: Host/Origin, lockout, authentication, content type and size, JSON shape and value, global range, then the demo policy.

## Protected mode details

- A random 256-bit operator token is generated at every start and **printed only to the terminal**. It is never in a URL, a response, the page source, logs or the audit log. In the UI you paste it into the operator panel, where it is held in a JavaScript variable only (reloading the page forgets it).
- Demo policy: **-25 to -15 °C**. This is a range chosen for the lesson. It is **not** a universal food-safety or refrigeration requirement.
- Five failed authentications within 60 s lock the source address out for 60 s (HTTP 429).
- Host and Origin must be the local app (`127.0.0.1:5000` or `localhost:5000`); no CORS headers are sent; a strict Content-Security-Policy is set. These reduce DNS-rebinding and cross-site attacks on a localhost service.
- The audit log is in memory, capped at 100 entries, and records timestamp, action, outcome, requested value and mode.

In **insecure mode** the same Host/Origin, size, content-type, JSON and range checks still apply. Only authorization (and the operating policy) is removed, and a red warning is shown.

## Learning tasks

They are also in the UI's learning panel.

1. Read the scope and identify the local address (`http://127.0.0.1:5000`).
2. Inspect `/api/status`.
3. Insecure mode: change the setpoint without authorization (the demo request).
4. Observe requested vs simulated measured temperature.
5. Restart in protected mode.
6. Confirm the same unauthenticated change is rejected (401).
7. Authenticate (token in the operator panel) and make an allowed change (e.g. -20).
8. Confirm an authenticated out-of-policy change (e.g. -10) is rejected (422).
9. Explain authentication vs authorization vs input validation vs operational safety limits.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

(Linux: `.venv/bin/python -m pip install -r requirements-dev.txt && .venv/bin/python -m pytest -q`.) Tests cover authentication, rate limiting, policy limits, malformed input, Host/Origin and CORS, the simulation model, audit bounds and secret handling.

## Safe operation

- Keep it on loopback. Do **not** expose it to a network, forward its port, tunnel it, or put it behind a proxy. This project gives no instructions for that and is not designed for it.
- The operator token is shown in the terminal. **Do not capture the terminal on stream**; capture the browser window only. If the token is exposed, restart the app (a new token is generated).
- Any program running on the same computer can reach `127.0.0.1:5000`. Run it on a machine you control.
- Use insecure mode only for the demonstration, then restart in protected mode.

## Reset procedure

All state is in memory; nothing is written to disk.

1. Press **Ctrl+C** in the terminal (or close the terminal window / VS Code task panel).
2. Start the app again. This restores: temperature and setpoint -18 °C, empty audit log, cleared rate-limit counters, and a **new** operator token.
3. Reload the browser tab (this clears the in-memory token and learning checkboxes).
4. If port 5000 is busy: Windows `Get-NetTCPConnection -LocalPort 5000`, Linux `ss -ltnp | grep 5000`; stop that program. The port cannot be changed.
5. Full clean: delete the `.venv` folder and reinstall.

## Known limitations (honest list)

- Flask's development server over plain HTTP; the token travels unencrypted over loopback. Not a production setup.
- One shared operator token: no users, roles, token expiry or revocation besides restarting.
- The rate limiter is in memory and per source address. On loopback every local client shares one address, so a local program can lock the operator out. It does **not** protect against distributed attacks, and it only slows guessing of a token that is already infeasible to guess.
- `GET /api/status` and `GET /api/audit` need no token (they contain no secrets, but anyone local can read them).
- No CSRF tokens; protection relies on Origin/Host checks, the JSON content-type requirement and the absence of CORS.
- The audit log is in memory, capped, lost on restart, and not tamper-evident.
- Anything that can read this computer's memory, terminal, or the process can read the token.
- The model is illustrative. At a setpoint near the top of the demo range, a normal defrost cycle can briefly trigger the alarm.
- The pixel-art UI was written to the spec but not reviewed in a browser by the author of this code; check it on your own screen before streaming.

## Advanced Lab (Pentesting)

This repository includes an intentionally vulnerable mode for practicing web exploitation (Command Injection and Missing Authorization). 

To begin the walkthrough, read [ATTACKS.md](ATTACKS.md). 

**Goal:** Exploit the insecure mode to read `flag.txt`. Then verify how Protected Mode blocks the same attacks using strict input validation and safe subprocess execution.

**Note:** This lab is strictly for local IoT access control training. Do not expose it to a public network.

## Project Tree

```text
paralabz-coldroom/
├── app.py                      entry point (CLI: --demo-insecure only)
├── requirements.txt            Flask
├── requirements-dev.txt        + pytest
├── pytest.ini
├── start-protected.bat         double-click start (Windows)
├── start-insecure.bat          double-click start, insecure teaching mode
├── PRESENTER_CHECKLIST.md
├── README.md
├── ATTACKS.md                  pentesting walkthrough
├── SECURITY.md                 local-only safety policy
├── flag.txt                    CTF flag for the lab
├── .gitignore
├── .vscode/tasks.json          VS Code run/test tasks
├── demo/setpoint.json          body of the one demo request
├── coldroom/
│   ├── __init__.py             app factory, Host/Origin guard, headers
│   ├── config.py               ranges, limits, text
│   ├── routes.py               endpoints
│   ├── security.py             token, Host/Origin check, rate limiter
│   ├── validation.py           strict request parsing
│   ├── simulation.py           illustrative cold-room model
│   ├── audit.py                bounded audit log
│   ├── templates/index.html
│   └── static/{app.js,style.css}
└── tests/                      pytest suite
