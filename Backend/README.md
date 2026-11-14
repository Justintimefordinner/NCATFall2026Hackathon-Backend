# Voice MES Backend

Flask + WebSocket backend that owns all MES state. Design: `Flask API and State Machine Programming Plan.md`.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q            # parser, transitions, walkthrough, HTTP API
.venv/bin/python app.py        # serves on 0.0.0.0:5000
```

## Running everything (from the repo root)

```bash
npm start        # Pi / demo: backend on :5000 serves the screens; frontend edits rebuild automatically
npm run dev      # laptop: Vite dev server on :5173 with hot reload, proxying to :5000
```

Ctrl+C stops everything. A backend left over from an earlier run is stopped automatically, and backend `.py` or `data/op10.json` edits restart the backend on their own (state resets when it does). Same as `./start.sh` / `./start.sh dev`.

## Driving it without the other parts

```bash
.venv/bin/python tools/repl.py                  # type "start labor", "step one done", ":power", ":alert loose brick", ":ack 1234"
.venv/bin/python tools/fake_panel.py            # p = power, l = listen; prints lights
wscat -c ws://localhost:5000/ws/ui              # watch state / announce pushes
.venv/bin/python tools/make_fixtures.py         # regenerate fixtures/state_*.json for the frontend
```

## Settings (env vars, see `config.py`)

`MES_PIN` (default `1234`), `MES_CONFIDENCE` (`0.6`), `MES_PORT` (`5000`), `MES_SUPERVISOR_VOICE` (`0.65`), `MES_DATA`, `MES_FRONTEND_DIST` (default `../Frontend/dist`).

## Contract notes for clients

- Every POST returns `{"ok", "message", "state"}` with HTTP 200, even when `ok` is false. 400 only for malformed JSON.
- `/ws/ui` pushes `{"type": "state", ...snapshot}` on connect and after every change, plus `{"type": "announce", "message", "priority"}` when the result should be spoken. `priority`: 1 quality alert (interrupts speech), 2 confirmation (default), 3 info.
- `POST /api/speak {"text", "priority"?}` makes the bench say something without changing state (supervisor screen, testers, faked demo alerts). `priority` defaults to 3. The line is added to the log with `source: "speak"`.
- `/ws/panel` pushes `{"type": "lights", "power", "listening", "labor", "alert", "inspector", "complete"}` on connect, on hello, and after every command. No periodic heartbeat: the panel should treat the WebSocket connection itself as "Pi alive". `GET /api/panel/status` shows the running code version and how many panels are connected. `inspector` is true while any step waits on supervisor sign-off.
- Panel button ids: `power` (short press: standby -> on), `power_off` (long press: back to standby, mode `idle`; progress, alerts and the labor total are kept, the clock and listening stop), `listen_toggle` (ignored in standby).
- `state.page.all_signed` is true when every step on the current page is signed (use it for the "page complete" banner; "page done" does not auto-advance).
- `state.log` is the newest 50 entries, oldest first.
- Voice POSTs to `/api/command` may include `role` and `speaker_score` (the voice client sends both). A supervisor saying "supervisor confirm" / "clear alert" opens `state.supervisor_challenge = {phrase, action, expires_at}` and announces "Supervisor, confirm with: <phrase>". The next utterance must contain the phrase, come from `role: "supervisor"` with `speaker_score >= MES_SUPERVISOR_VOICE` (0.65), and arrive within 15 s; otherwise it announces "Supervisor voice not recognized". The PIN routes are unchanged.
- Log entries carry `score` (speaker score, voice only); supervisor speech and challenge answers are logged with `source: "supervisor_voice"`.
- Step images are served from `data/img/` at `/static/img/<file>`.
