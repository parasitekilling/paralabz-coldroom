@echo off
rem ParaLabz ColdRoom - INTENTIONALLY VULNERABLE teaching mode. Local use only.
rem First run creates a local .venv and installs Flask (small, no admin rights).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating local virtual environment...
  py -3 -m venv .venv || python -m venv .venv
)
".venv\Scripts\python.exe" -c "import flask" 2>nul || ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
".venv\Scripts\python.exe" app.py --demo-insecure
pause
