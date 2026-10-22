"""Central constants for ParaLabz ColdRoom.

Everything that defines the lesson (ranges, limits, text) lives here so the
simulation, the API and the tests all agree on the same numbers.

This is a local educational simulation. It never talks to a physical device.
"""

from __future__ import annotations

# --- Network binding -------------------------------------------------------
# Deliberately constants, not command-line options or environment variables.
HOST = "127.0.0.1"
PORT = 5000

# Host / Origin allowlists used to reduce DNS-rebinding and cross-site abuse
# of a localhost service by a malicious web page.
ALLOWED_HOSTS = frozenset({f"{HOST}:{PORT}", f"localhost:{PORT}"})
ALLOWED_ORIGINS = frozenset({f"http://{host}" for host in ALLOWED_HOSTS})

# --- Modes -------------------------------------------------------------------
MODE_PROTECTED = "protected"
MODE_INSECURE = "insecure"

# --- Temperature ranges (degrees Celsius) ------------------------------------
# Global demonstration range: the hard bound in BOTH modes.
GLOBAL_MIN_C = -40.0
GLOBAL_MAX_C = 10.0

# Example operational policy, enforced in protected mode only. It is a range
# chosen for this lesson. It is NOT a food-safety or refrigeration standard.
POLICY_MIN_C = -25.0
POLICY_MAX_C = -15.0

INITIAL_TEMP_C = -18.0

# --- Request limits ----------------------------------------------------------
MAX_BODY_BYTES = 1024
MAX_AUTH_HEADER_CHARS = 512

# --- Audit log ----------------------------------------------------------------
AUDIT_MAX_ENTRIES = 100

# --- Failed-authentication limiter (protected mode) --------------------------
RATE_MAX_FAILURES = 5
RATE_WINDOW_S = 60.0
RATE_LOCKOUT_S = 60.0

# --- Text shown to the audience ----------------------------------------------
DISCLAIMER = (
    "Local educational simulation. No physical devices connected. "
    "Not a reproduction of the French refrigeration attack."
)

POLICY_NOTE = (
    "The -25 to -15 °C range is an example policy chosen for this demo. "
    "It is not a universal food-safety or refrigeration requirement."
)

MODEL_NOTE = (
    "Illustrative model only: a simple thermostat with leakage toward a warm "
    "room and a periodic defrost. It is not engineering-accurate and must not "
    "be used to reason about real refrigeration equipment."
)

# The one and only example request used in the demo (run from the project
# folder; in Windows PowerShell type curl.exe instead of curl).
EXAMPLE_COMMAND = (
    'curl -X POST http://127.0.0.1:5000/api/setpoint '
    '-H "Content-Type: application/json" '
    '--data-binary "@demo/setpoint.json"'
)
