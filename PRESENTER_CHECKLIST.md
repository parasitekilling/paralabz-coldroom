# ParaLabz #03 presenter checklist

## Before going live
- [ ] Python installed; folder opened in VS Code; first run done once (Flask installed).
- [ ] Browser zoom 100%, window 1920x1080, page loads at <http://127.0.0.1:5000/>.
- [ ] Stream capture = **browser window only**. The terminal (it shows the operator token) is **not** captured.
- [ ] Other apps, notifications and tabs hidden.
- [ ] Optional: run the tests once (`Terminal > Run Task > ColdRoom: run tests`).

## Part 1 - insecure teaching mode (`start-insecure.bat`)
- [ ] Read the disclaimer aloud; point at the red warning and the mode badge.
- [ ] Task 1-2: local address `127.0.0.1:5000`; open `/api/status`.
- [ ] Task 3: run the one demo request (`curl.exe` in PowerShell). Show it is accepted.
- [ ] Task 4: requested setpoint jumped; measured value drifts slowly; alarm appears after ~40-60 s.
- [ ] Say: only authorization is missing here; validation and range limits still apply.

## Part 2 - protected mode (stop with Ctrl+C, `start-protected.bat`)
- [ ] Task 5: mode is chosen at startup; no button or endpoint switches it.
- [ ] Task 6: same request -> HTTP 401. (Five failures in a minute locks you out: do not spam it.)
- [ ] Task 7: copy the token privately, paste into the operator panel, apply `-20` -> accepted.
- [ ] Task 8: apply `-10` with the token -> 422 `out_of_policy`. Say the range is a chosen demo policy.
- [ ] Show the audit log: attempts recorded, no secrets.
- [ ] Task 9: authentication vs authorization vs input validation vs operational safety limits.

## Say clearly
- Teaching model, not production-secure, not a pentest qualification.
- No real device, no real attack reproduced, nothing exposed to the internet.

## After the stream
- [ ] Ctrl+C in the terminal. Close the terminal (token was only ever there).
- [ ] Reset = restart: fresh -18 °C, empty log, new token (see README).
