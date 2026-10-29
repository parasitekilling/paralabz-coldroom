# Security Assessment Report: ColdRoom

## Executive Summary
This report documents a source-assisted assessment of the ColdRoom Flask application. The assessment verified the behavior of an intentionally vulnerable endpoint and compared it against the app's protected-mode defenses. 

**Note:** This is a local educational simulation used to demonstrate security concepts. No real-world production systems were tested.

## Scope & Environment
- **Target:** Local ColdRoom Flask app (`127.0.0.1:5000`)
- **Mode:** Insecure Teaching Mode vs. Protected Mode
- **Tools Used:** Burp Suite, Python, VS Code

## Findings

### 1. Missing Authorization on Setpoint Endpoint
- **Severity:** High (In teaching context)
- **Description:** The `/api/setpoint` endpoint accepts POST requests without requiring an authorization token when running in insecure teaching mode. 
- **Evidence:** 
  - A Burp Suite intercepted `POST` request with body `{"setpoint_c": -20}` returns `HTTP 200 OK`.
- **Defense Comparison:** In Protected Mode, the app enforces a Bearer token check. The identical request without a token returns `HTTP 401 Unauthorized`.

### 2. Command Injection in Ping Endpoint
- **Severity:** Critical (In teaching context)
- **Description:** The `/api/ping` endpoint passes user input directly to the OS shell via `os.popen()`.
- **Evidence:** 
  - Injecting a shell command via the `host` parameter executes system commands (see `ATTACKS.md` for the payload).
- **Defense Comparison:** Protected mode uses strict regex validation and `subprocess.run()` to prevent shell execution.

## Conclusion
The lab successfully demonstrates the difference between input validation and authorization, and the dangers of passing unvalidated user input to the OS shell. All tests were conducted locally and safely.