# Flask API and State Machine: Programming Plan

Nov 13, 2026 · @Jeffrey Justin Wright

The backend is one Flask process on the Pi 5 that owns all MES state. Every input (voice, ESP32 panel, supervisor screen) becomes a `Command`, goes through one `dispatch()` function, and the resulting state is pushed to every client. The parser and state machine are pure Python with no Flask imports, so they can be built and tested before any other part exists. Full system design: [Voice MES Assistant: Project Documentation](https://claude.ai/artifact/Af4fE4PpXvxauDnV7H44fa).

## Module layout

Dependencies only point down this table: `app.py` imports everything, `state.py` and `parser.py` import nothing from Flask.

| File | Owns | Imports |
| --- | --- | --- |
| `app.py` | Flask app, HTTP routes, `/ws/ui` and `/ws/panel`, serving `frontend/dist/` | everything below |
| `hub.py` | Set of connected sockets, `broadcast()`, panel heartbeat thread | `state.py` (for snapshots) |
| `state.py` | `MES` class: runtime state, `dispatch()`, `snapshot()`, `lights()` | `models.py` |
| `parser.py` | `parse(text, confidence) -> Command` | `models.py` |
| `models.py` | `Command`, `Result`, `LogEntry` dataclasses, intent names, mode names | nothing |
| `config.py` | `PIN`, `CONFIDENCE_THRESHOLD`, data file path, port | nothing |
| `data/op10.json` | Instruction pages for the Lego build |  |
| `tests/` | Parser tests, walkthrough test | `state.py`, `parser.py` |
| `tools/` | `fake_panel.py`, `repl.py` | HTTP / WebSocket only |

Voice (Adan) runs as a separate process and only talks to the backend over HTTP and `/ws/ui`. It never imports backend code.

## Data model

Every input becomes a `Command`; every handled command returns a `Result`. Instruction data is read-only JSON loaded at startup; runtime state lives on the `MES` object.

```python
# models.py
from dataclasses import dataclass, field
import time

# modes
IDLE, ARRIVED, VIEWING, WORKING, COMPLETE = "idle", "arrived", "viewing", "working", "complete"

# tech intents (voice / debug box)
START_LABOR, STOP_LABOR, OPEN_INSTRUCTIONS = "start_labor", "stop_labor", "open_instructions"
NEXT_PAGE, PREV_PAGE = "next_page", "prev_page"
SIGN_STEP, SIGN_PAGE, UNKNOWN = "sign_step", "sign_page", "unknown"
# panel intents
POWER, LISTEN_TOGGLE = "power", "listen_toggle"
# supervisor intents
INSPECTOR_SIGNOFF, QUALITY_TRIGGER, QUALITY_ACK, RESET = (
    "inspector_signoff", "quality_trigger", "quality_ack", "reset")

SUPERVISOR_INTENTS = {INSPECTOR_SIGNOFF, QUALITY_TRIGGER, QUALITY_ACK, RESET}
BLOCKED_BY_ALERT = {SIGN_STEP, SIGN_PAGE, NEXT_PAGE, PREV_PAGE}

@dataclass
class Command:
    intent: str
    source: str                 # "voice" | "debug" | "panel" | "supervisor"
    args: dict = field(default_factory=dict)   # {"step": 3}, {"pin": "1234"}, {"message": "..."}
    confidence: float = 1.0
    raw: str = ""               # original text, for the log

@dataclass
class Result:
    ok: bool
    message: str                # spoken, shown on screen, logged
    speak: bool = True          # False for silent results (wrong PIN, ignored voice)

@dataclass
class LogEntry:
    ts: float
    source: str
    input: str
    ok: bool
    message: str
```

Instruction data (`data/op10.json`), unchanged from the project doc:

```json
{
  "work_order": "WO-1001", "part_rev": "B", "serial": "SN-0042",
  "operation": "Op 10: Base assembly",
  "pages": [
    {"number": 1, "title": "Base plate", "steps": [
      {"number": 1, "text": "Place 2x8 grey plate", "image": "p1s1.jpg", "inspector_required": false},
      {"number": 2, "text": "Attach 2x2 red brick at corner", "image": "p1s2.jpg", "inspector_required": true}
    ]}
  ]
}
```

Runtime state on `MES` (internal; clients only ever see `snapshot()`):

| Field | Type | Notes |
| --- | --- | --- |
| `mode` | str | One of the five modes, starts `idle` |
| `listening` | bool | Flipped by the Listen button |
| `page` | int | 1-based, current page |
| `signed` | `set[tuple[int, int]]` | `(page, step)` pairs signed off |
| `signed_by` | `dict[tuple, str]` | `"tech"` or `"supervisor"`, for the log and screen |
| `pending_inspector` | `list[tuple[int, int]]` | Inspector steps the tech tried to sign, oldest first |
| `quality_alert` | `str or None` | Alert message while open |
| `labor_started_at` | `float or None` | `time.time()` when the clock started |
| `labor_accum` | float | Seconds from earlier runs of the clock |
| `log` | `list[LogEntry]` | Every input, capped at 200 |

Store the labor clock as a start timestamp plus accumulated seconds, not a ticking counter. `labor_seconds = labor_accum + (now - labor_started_at)` while running, so no timer thread is needed.

## State machine

`dispatch()` is the only way state changes. It runs the order of checks, then hands off to one small handler per intent. The transition tables in the project doc are the spec; each row there should map to one branch here and one test.

```python
# state.py
import json, threading, time
from models import *
import config

class MES:
    def __init__(self, data_path):
        self.data_path = data_path
        self.lock = threading.Lock()
        self.reset()

    # ---------- entry point ----------
    def dispatch(self, cmd: Command) -> Result:
        with self.lock:
            res = self._check(cmd)
            self._log(cmd, res)
            return res

    def _check(self, cmd):
        # 1. voice while listening is off: ignore
        if cmd.source == "voice" and not self.listening:
            return Result(False, "Ignored, listening off", speak=False)
        # 2. unknown or low confidence
        if cmd.intent == UNKNOWN or cmd.confidence < config.CONFIDENCE_THRESHOLD:
            return Result(False, "Try again")
        # 3. idle only accepts power, listen, reset
        if self.mode == IDLE and cmd.intent not in (POWER, LISTEN_TOGGLE, RESET):
            return Result(False, "Press power to start", speak=False)
        # 4. supervisor inputs work in any mode
        if cmd.intent in SUPERVISOR_INTENTS:
            return self._supervisor(cmd)
        # 5. open quality alert blocks sign-offs and page changes
        if self.quality_alert and cmd.intent in BLOCKED_BY_ALERT:
            return Result(False, "Quality alert open. Supervisor must clear it")
        # 6. transition table
        handler = getattr(self, "_on_" + cmd.intent, None)
        if handler is None:
            return Result(False, "Try again")
        return handler(cmd)

    # ---------- panel ----------
    def _on_power(self, cmd):
        if self.mode != IDLE:
            return Result(True, "Already on", speak=False)
        self.mode = ARRIVED
        return Result(True, "Incomplete operation. Start labor or open instructions?")

    def _on_listen_toggle(self, cmd):
        self.listening = not self.listening
        return Result(True, "Listening on" if self.listening else "Listening off")

    # ---------- labor ----------
    def _on_start_labor(self, cmd):
        if self.mode == WORKING:
            return Result(False, "Labor already running")
        if self.mode == COMPLETE:
            return Result(False, "Operation already complete")
        self.mode = WORKING            # from ARRIVED or VIEWING
        self.labor_started_at = time.time()
        return Result(True, "Labor started")

    def _on_stop_labor(self, cmd):
        if self.labor_started_at is None:
            return Result(False, "Labor is not running")
        self.labor_accum += time.time() - self.labor_started_at
        self.labor_started_at = None
        if self.mode == COMPLETE:
            return Result(True, "Labor stopped. Operation complete")
        self.mode = VIEWING
        return Result(True, "Labor stopped. Operation incomplete")

    def _on_open_instructions(self, cmd):
        if self.mode != ARRIVED:
            return Result(True, f"Page {self.page}")   # already open, just confirm
        self.mode = VIEWING
        return Result(True, "Instructions open")

    # ---------- navigation ----------
    def _on_next_page(self, cmd):
        if self.mode == ARRIVED:
            return Result(False, "Say start labor or open instructions")
        if self.page >= len(self.pages):
            return Result(False, "No next page")
        self.page += 1
        return Result(True, f"Page {self.page}")

    def _on_prev_page(self, cmd):
        if self.mode == ARRIVED:
            return Result(False, "Say start labor or open instructions")
        if self.page <= 1:
            return Result(False, "No previous page")
        self.page -= 1
        return Result(True, f"Page {self.page}")

    # ---------- sign-offs ----------
    def _on_sign_step(self, cmd):
        if (r := self._can_sign()): return r
        n = cmd.args["step"]
        step = self._step(self.page, n)
        if step is None:
            return Result(False, f"No step {n} on this page")
        key = (self.page, n)
        if key in self.signed:
            return Result(False, f"Step {n} already signed off")
        if step["inspector_required"]:
            if key not in self.pending_inspector:
                self.pending_inspector.append(key)
            return Result(False, "This step requires supervisor sign-off")
        self._sign(key, "tech")
        return self._after_sign(Result(True, f"Step {n} signed off"))

    def _on_sign_page(self, cmd):
        if (r := self._can_sign()): return r
        held = []
        for step in self.pages[self.page - 1]["steps"]:
            key = (self.page, step["number"])
            if key in self.signed: continue
            if step["inspector_required"]:
                held.append(step["number"])
                if key not in self.pending_inspector:
                    self.pending_inspector.append(key)
            else:
                self._sign(key, "tech")
        msg = f"Page {self.page} signed off"
        if held:
            msg += ". Step " + ", ".join(map(str, held)) + " needs supervisor sign-off"
        return self._after_sign(Result(True, msg))

    def _can_sign(self):
        if self.mode == ARRIVED:
            return Result(False, "Say start labor or open instructions")
        if self.mode == VIEWING:
            return Result(False, "Start labor before signing off")
        if self.mode == COMPLETE:
            return Result(False, "Operation already complete")
        return None

    def _after_sign(self, res):
        if len(self.signed) == self.total_steps:
            self.mode = COMPLETE
            res.message += ". Assembly complete"
        return res

    # ---------- supervisor ----------
    def _supervisor(self, cmd):
        if cmd.intent == RESET:
            self.reset()
            return Result(True, "Demo reset", speak=False)
        if cmd.intent == QUALITY_TRIGGER:
            self.quality_alert = cmd.args["message"]
            return Result(True, f"Quality alert: {self.quality_alert}")
        if cmd.args.get("pin") != config.PIN:
            return Result(False, "Wrong PIN", speak=False)
        if cmd.intent == QUALITY_ACK:
            if not self.quality_alert:
                return Result(False, "No open quality alert", speak=False)
            self.quality_alert = None
            return Result(True, "Quality alert cleared")
        if cmd.intent == INSPECTOR_SIGNOFF:
            if not self.pending_inspector:
                return Result(False, "No step waiting on inspector", speak=False)
            key = self._pick_pending(cmd.args)   # (page, step) if given, else oldest
            self.pending_inspector.remove(key)
            self._sign(key, "supervisor")
            return self._after_sign(Result(True, f"Step {key[1]} signed off by supervisor"))
```

Still to write: `reset()` (reload JSON, set every field to its start value), `_step()`, `_sign()`, `_pick_pending()`, `_log()`, `total_steps`, `snapshot()` and `lights()`. `_log()` appends a `LogEntry` with `cmd.raw` or the intent name as `input`.

Three details that matter:

- **`_after_sign` runs on every sign path**, including supervisor sign-off, so a supervisor PIN on the last inspector step finishes the assembly.
- **Supervisor sign-off is not blocked by a quality alert.** Check 4 runs before check 5. If the team wants alerts to block inspector sign-offs too, add a check inside `_supervisor`.
- **Keep `dispatch` fast.** No network or audio calls inside the lock. `app.py` broadcasts after `dispatch` returns.

## Parser

`parse()` turns a transcript into a `Command` in three passes: normalize, exact phrase match, then fuzzy match. Adan owns the `PHRASES` table and number words; you own the matching code. Use `difflib` from the standard library so there's nothing extra to install.

```python
# parser.py
import re, difflib
from models import *

NUMBER_WORDS = {"one": 1, "won": 1, "two": 2, "to": 2, "too": 2, "three": 3, "four": 4,
                "for": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ate": 8,
                "nine": 9, "ten": 10}

PHRASES = {
    START_LABOR:       ["start labor", "start work", "start clock", "clock in"],
    STOP_LABOR:        ["stop labor", "stop work", "stop clock", "pause labor"],
    OPEN_INSTRUCTIONS: ["open instructions", "view instructions", "show instructions", "read ahead"],
    NEXT_PAGE:         ["next", "next page", "go on", "continue", "forward"],
    PREV_PAGE:         ["previous", "previous page", "prior page", "go back", "back"],
    SIGN_PAGE:         ["page done", "sign off page", "page complete", "all done"],
}
# step X done: matched with patterns, not the table
STEP_PATTERNS = [r"step (\d+) (done|complete|finished)", r"sign off step (\d+)",
                 r"finished step (\d+)", r"step (\d+)"]

FUZZY_CUTOFF = 0.75

def normalize(text):
    t = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    words = [str(NUMBER_WORDS.get(w, w)) for w in t.split()]
    return " ".join(words)

def parse(text, confidence=1.0, source="voice"):
    t = normalize(text)
    # 1. step commands carry a number
    for pat in STEP_PATTERNS:
        if m := re.search(pat, t):
            return Command(SIGN_STEP, source, {"step": int(m.group(1))}, confidence, text)
    # 2. exact phrase anywhere in the utterance ("okay next page please")
    for intent, phrases in PHRASES.items():
        for p in sorted(phrases, key=len, reverse=True):
            if re.search(rf"\b{p}\b", t):
                return Command(intent, source, {}, confidence, text)
    # 3. fuzzy match on the whole utterance
    lookup = {p: i for i, ps in PHRASES.items() for p in ps}
    best = difflib.get_close_matches(t, lookup, n=1, cutoff=FUZZY_CUTOFF)
    if best:
        score = difflib.SequenceMatcher(None, t, best[0]).ratio()
        return Command(lookup[best[0]], source, {}, confidence * score, text)
    return Command(UNKNOWN, source, {}, 0.0, text)
```

Watch for these when testing:

- **Phrase order matters.** "Stop labor" contains no other phrase, but "next page" contains "next". Check longer phrases first within each intent and make sure no phrase in one intent is inside a phrase of another.
- **"Back" and "continue" are short and common.** If they misfire in noise, drop them from exact match and leave them to fuzzy.
- **Number homophones** ("to", "for", "won") only matter right after "step". If they cause false positives elsewhere, convert number words only inside step patterns.
- **Final confidence** is the STT confidence times the fuzzy score. `dispatch()` compares it to `config.CONFIDENCE_THRESHOLD` (start at 0.6 and tune on the floor).

## Flask API and WebSockets

Every route does the same three things: build a `Command`, call `mes.dispatch()`, then `hub.publish(result)`. Routes hold no rules.

| Endpoint | Method | Body | Used by | Builds |
| --- | --- | --- | --- | --- |
| `/api/command` | POST | `{"text": "step three done", "confidence": 0.82, "source": "voice"}` | Voice process, debug box, `repl.py` | `parse(text, confidence, source)` |
| `/api/inspector/signoff` | POST | `{"pin": "1234", "page": 1, "step": 2}` (page and step optional) | Supervisor screen | `INSPECTOR_SIGNOFF` |
| `/api/quality/trigger` | POST | `{"message": "Bolt 6 not torqued to spec"}` | Supervisor screen | `QUALITY_TRIGGER` |
| `/api/quality/acknowledge` | POST | `{"pin": "1234"}` | Supervisor screen | `QUALITY_ACK` |
| `/api/reset` | POST | none | Us | `RESET` |
| `/api/state` | GET | none | Debugging, curl | Returns `snapshot()` |
| `/ws/ui` | WebSocket | none sent | Tech screen, supervisor screen, voice process | Receives `state` and `announce` messages |
| `/ws/panel` | WebSocket | `hello`, `button` | ESP32 | `button` id becomes `POWER` or `LISTEN_TOGGLE` |
| `/api/panel/button`, `/api/panel/lights` | POST / GET | `{"id": "power"}` | ESP32 fallback | Same as `/ws/panel` |
| `/tech`, `/supervisor`, `/` | GET |  | Browsers | `frontend/dist/index.html` |

Every POST returns `{"ok": bool, "message": str, "state": snapshot}` with HTTP 200, even when `ok` is false. A blocked command is a normal result, not an error. Use 400 only for malformed JSON.

### Messages pushed on `/ws/ui`

```json
{"type": "state",
 "operation": {"work_order": "WO-1001", "part_rev": "B", "serial": "SN-0042",
               "operation": "Op 10: Base assembly", "operator": "J. Wright", "page_count": 4},
 "mode": "working", "listening": true,
 "labor": {"running": true, "seconds": 312},
 "page": {"number": 1, "title": "Base plate", "steps": [
   {"number": 1, "text": "Place 2x8 grey plate", "image": "/static/img/p1s1.jpg",
    "inspector_required": false, "signed": true, "signed_by": "tech", "pending_inspector": false}]},
 "pending_inspector": [{"page": 1, "step": 2}],
 "progress": {"signed": 5, "total": 18},
 "quality_alert": null,
 "last": {"ts": 1731556800, "source": "voice", "input": "step one done", "ok": true, "message": "Step 1 signed off"},
 "log": []}

{"type": "announce", "message": "Step 1 signed off"}
```

`log` carries the newest 50 entries. Send `announce` only when `result.speak` is true; the voice process speaks it.

### `hub.py`

```python
import json, threading, time

class Hub:
    def __init__(self, mes):
        self.mes, self.ui, self.panels = mes, set(), set()
        self.lock = threading.Lock()

    def publish(self, result=None):
        snap = json.dumps({"type": "state", **self.mes.snapshot()})
        lights = json.dumps({"type": "lights", **self.mes.lights()})
        msgs = [snap]
        if result and result.speak:
            msgs.append(json.dumps({"type": "announce", "message": result.message}))
        self._send(self.ui, msgs)
        self._send(self.panels, [lights])

    def _send(self, clients, msgs):
        with self.lock:
            for ws in list(clients):
                try:
                    for m in msgs: ws.send(m)
                except Exception:
                    clients.discard(ws)     # dead socket, drop it

    def heartbeat(self):                    # run in a daemon thread
        while True:
            time.sleep(1)
            self._send(self.panels, [json.dumps({"type": "lights", **self.mes.lights()})])
```

### `app.py` sketch

```python
from flask import Flask, request, jsonify, send_from_directory
from flask_sock import Sock

app = Flask(__name__, static_folder=None)
sock = Sock(app)
mes = MES(config.DATA_PATH)
hub = Hub(mes)

def run(cmd):
    res = mes.dispatch(cmd)
    hub.publish(res)
    return jsonify(ok=res.ok, message=res.message, state=mes.snapshot())

@app.post("/api/command")
def command():
    b = request.get_json(force=True)
    return run(parse(b["text"], b.get("confidence", 1.0), b.get("source", "debug")))

@app.post("/api/quality/trigger")
def quality_trigger():
    return run(Command(QUALITY_TRIGGER, "supervisor", {"message": request.json["message"]}))

@sock.route("/ws/ui")
def ws_ui(ws):
    hub.ui.add(ws)
    ws.send(json.dumps({"type": "state", **mes.snapshot()}))
    while True:
        ws.receive()        # clients don't send anything; this blocks until disconnect

@sock.route("/ws/panel")
def ws_panel(ws):
    hub.panels.add(ws)
    while True:
        msg = json.loads(ws.receive())
        if msg["type"] == "button":
            res = mes.dispatch(Command(msg["id"], "panel", raw=msg["id"]))
            hub.publish(res)

if __name__ == "__main__":
    threading.Thread(target=hub.heartbeat, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)
```

**Threading:** `threaded=True` gives each request and socket its own thread. `MES.lock` serializes state changes and `Hub.lock` serializes sends, so two threads never write to one socket at once. Never hold `MES.lock` while sending.

## Build plan

Eight milestones, in order. Each one ends with something you can run, so you always have a working fallback if time runs out. Times are rough targets for the 4-hour rule.

- [ ] **M1. Skeleton (30 min).** `models.py`, `config.py`, `data/op10.json` with 2 pages of placeholder steps (one `inspector_required`). Done when: `python -c "from state import MES; MES('data/op10.json')"` runs.
- [ ] **M2. State machine core (1.5 h).** `reset`, `dispatch`, `_check`, labor, navigation, sign-offs, `_after_sign`. Done when: the walkthrough test passes using `Command` objects directly, no parser.
- [ ] **M3. Supervisor paths (45 min).** Quality trigger, acknowledge, inspector sign-off, wrong PIN, reset. Done when: tests for alert blocking and supervisor finishing the assembly pass.
- [ ] **M4. Parser (1 h).** `normalize`, phrase table, step patterns, fuzzy. Done when: a table test of 30+ phrasings (every variant in the doc, plus "step 3" vs "step three") passes.
- [ ] **M5. HTTP API (45 min).** `app.py` with every POST route and `/api/state`. Done when: `repl.py` can drive the whole walkthrough against a running server.
- [ ] **M6. `/ws/ui` broadcast (45 min).** `hub.py`, snapshot on connect and on every change, `announce` messages. Done when: `wscat -c ws://localhost:5000/ws/ui` shows a new state after each `repl.py` command. Tell Chiloh and Adan it's live.
- [ ] **M7. `/ws/panel` (45 min).** Button handling, lights on change, 1 s heartbeat, HTTP fallback routes. Done when: `fake_panel.py` sees lights change and Micah's ESP32 connects.
- [ ] **M8. Integration on the Pi (1 h+).** Hotspot, serve `frontend/dist/`, real voice process, real panel. Done when: the full demo walkthrough runs end to end with no laptop shortcuts.

Before M2 ends, commit `fixtures/state_idle.json`, `state_working.json`, and `state_alert.json` (real `snapshot()` output) so Chiloh can build the screens against them.

## Testing without the other parts

The walkthrough test is the spec in code: it scripts the demo and asserts on state after each step. Run it with `pytest` after every change.

```python
# tests/test_walkthrough.py
from state import MES
from models import *
import config

def cmd(intent, source="debug", **args):
    return Command(intent, source, args)

def test_demo_walkthrough():
    m = MES("data/op10.json")
    assert m.dispatch(cmd(SIGN_STEP, step=1)).ok is False          # idle ignores it
    assert "Incomplete operation" in m.dispatch(cmd(POWER, "panel")).message
    assert m.dispatch(cmd(NEXT_PAGE)).message == "Say start labor or open instructions"
    m.dispatch(cmd(OPEN_INSTRUCTIONS));               assert m.mode == VIEWING
    assert m.dispatch(cmd(SIGN_STEP, step=1)).message == "Start labor before signing off"
    m.dispatch(cmd(START_LABOR));                     assert m.mode == WORKING
    m.dispatch(cmd(SIGN_STEP, step=1));               assert (1, 1) in m.signed
    r = m.dispatch(cmd(SIGN_STEP, step=2))            # inspector step
    assert r.message == "This step requires supervisor sign-off" and (1, 2) in m.pending_inspector
    m.dispatch(cmd(QUALITY_TRIGGER, "supervisor", message="Bolt 6 not torqued"))
    assert m.dispatch(cmd(NEXT_PAGE)).message.startswith("Quality alert open")
    assert m.dispatch(cmd(QUALITY_ACK, "supervisor", pin="0000")).ok is False
    m.dispatch(cmd(QUALITY_ACK, "supervisor", pin=config.PIN)); assert m.quality_alert is None
    m.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN)); assert (1, 2) in m.signed
    assert m.dispatch(cmd(PREV_PAGE)).message == "No previous page"
    # ... sign the remaining pages, last one returns "Assembly complete", mode == COMPLETE
    assert m.dispatch(cmd(STOP_LABOR)).message == "Labor stopped. Operation complete"
```

Add one small test per row of the transition tables in the project doc (already signed, no step X, stop labor when not running, voice ignored while listening is off). Add a parser table test:

```python
@pytest.mark.parametrize("text,intent,step", [
    ("next page", NEXT_PAGE, None), ("prior page", PREV_PAGE, None),
    ("step three done", SIGN_STEP, 3), ("sign off step 4", SIGN_STEP, 4),
    ("okay page done", SIGN_PAGE, None), ("banana", UNKNOWN, None),
])
def test_parse(text, intent, step):
    c = parse(text)
    assert c.intent == intent and c.args.get("step") == step
```

### Fake clients (`tools/`)

| Tool | Stands in for | What it does |
| --- | --- | --- |
| `repl.py` | Voice process, debug box | Reads lines from stdin, POSTs each to `/api/command`, prints `message` |
| `fake_panel.py` | ESP32 | Connects to `/ws/panel` with the `websockets` package, sends `hello`, maps keys `p` and `l` to `power` and `listen_toggle`, prints every `lights` message |
| `wscat -c ws://localhost:5000/ws/ui` | Tech and supervisor screens | Prints every `state` and `announce` push |
| `curl -X POST localhost:5000/api/quality/trigger -H 'Content-Type: application/json' -d '{"message":"test"}'` | Supervisor screen | Same for the other supervisor routes |

With these four you can run the entire demo from a terminal before anyone else's part works.

## Open decisions

The code above assumes the first answer in each line. Each one is a one-line change.

- [ ] Should a quality alert block supervisor inspector sign-off too? (assumed no)
- [ ] Should "page done" auto-advance to the next page? (no, should display banner on screen that all steps are complete)
- [ ] Should finishing the operation stop the labor clock automatically? (assumed no; ask judges)
- [ ] Should a wrong PIN be spoken on the tech side, or only shown on the supervisor screen? (assumed screen only)
- [ ] Should a voice command while listening is off be logged on the supervisor screen? (assumed yes, marked ignored)
- [ ] Supervisor PIN value and where it lives (assumed one hard-coded `config.PIN`)
