"""MES state machine. Pure Python, no Flask imports.

dispatch() is the only way state changes. snapshot() and lights() are the only
views clients ever see.
"""
import json
import threading
import time

import config
from models import (
    ARRIVED, BLOCKED_BY_ALERT, COMPLETE, IDLE, INSPECTOR_SIGNOFF, LISTEN_TOGGLE,
    POWER, QUALITY_ACK, QUALITY_TRIGGER, RESET, SUPERVISOR_INTENTS, UNKNOWN,
    VIEWING, WORKING, Command, LogEntry, Result,
)


class MES:
    def __init__(self, data_path=config.DATA_PATH):
        self.data_path = data_path
        self.lock = threading.Lock()
        self.reset()

    # ---------- setup ----------
    def reset(self):
        """Reload instruction data and put every runtime field back to its start value."""
        with open(self.data_path) as f:
            self.data = json.load(f)
        self.pages = self.data["pages"]
        self.total_steps = sum(len(p["steps"]) for p in self.pages)

        self.mode = IDLE
        self.listening = False
        self.page = 1
        self.signed = set()             # {(page, step)}
        self.signed_by = {}             # {(page, step): "tech" | "supervisor"}
        self.pending_inspector = []     # [(page, step)], oldest first
        self.quality_alert = None
        self.labor_started_at = None
        self.labor_accum = 0.0
        self.log = []

    # ---------- entry point ----------
    def dispatch(self, cmd: Command) -> Result:
        with self.lock:
            res = self._check(cmd)
            self._log(cmd, res)
            return res

    def _check(self, cmd):
        # 1. voice while listening is off: ignore (still logged)
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
        if (r := self._can_sign()):
            return r
        n = cmd.args.get("step")
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
        if (r := self._can_sign()):
            return r
        held = []
        for step in self.pages[self.page - 1]["steps"]:
            key = (self.page, step["number"])
            if key in self.signed:
                continue
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
            self.quality_alert = cmd.args.get("message") or "Quality alert"
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
            key = self._pick_pending(cmd.args)
            if key is None:
                return Result(False, "That step is not waiting on inspector", speak=False)
            self.pending_inspector.remove(key)
            self._sign(key, "supervisor")
            return self._after_sign(Result(True, f"Step {key[1]} signed off by supervisor"))
        return Result(False, "Try again")

    # ---------- helpers ----------
    def _step(self, page, n):
        if not 1 <= page <= len(self.pages):
            return None
        for step in self.pages[page - 1]["steps"]:
            if step["number"] == n:
                return step
        return None

    def _sign(self, key, by):
        self.signed.add(key)
        self.signed_by[key] = by

    def _pick_pending(self, args):
        """(page, step) from args if both given, else the oldest pending step."""
        page, step = args.get("page"), args.get("step")
        if page is None or step is None:
            return self.pending_inspector[0]
        key = (int(page), int(step))
        return key if key in self.pending_inspector else None

    def _log(self, cmd, res):
        self.log.append(LogEntry(time.time(), cmd.source, cmd.raw or cmd.intent,
                                 res.ok, res.message))
        if len(self.log) > config.LOG_CAP:
            del self.log[:-config.LOG_CAP]

    def _labor_seconds(self):
        secs = self.labor_accum
        if self.labor_started_at is not None:
            secs += time.time() - self.labor_started_at
        return int(secs)

    # ---------- views ----------
    def snapshot(self):
        """Everything the screens need, as plain JSON-able data."""
        with self.lock:
            page = self.pages[self.page - 1]
            steps = []
            for s in page["steps"]:
                key = (self.page, s["number"])
                steps.append({
                    "number": s["number"],
                    "text": s["text"],
                    "image": f"/static/img/{s['image']}" if s.get("image") else None,
                    "inspector_required": s["inspector_required"],
                    "signed": key in self.signed,
                    "signed_by": self.signed_by.get(key),
                    "pending_inspector": key in self.pending_inspector,
                })
            d = self.data
            return {
                "operation": {
                    "work_order": d.get("work_order"),
                    "part_rev": d.get("part_rev"),
                    "serial": d.get("serial"),
                    "operation": d.get("operation"),
                    "operator": d.get("operator"),
                    "page_count": len(self.pages),
                },
                "mode": self.mode,
                "listening": self.listening,
                "labor": {"running": self.labor_started_at is not None,
                          "seconds": self._labor_seconds()},
                "page": {
                    "number": page["number"],
                    "title": page["title"],
                    "steps": steps,
                    "all_signed": all(s["signed"] for s in steps),
                },
                "pending_inspector": [{"page": p, "step": s} for p, s in self.pending_inspector],
                "progress": {"signed": len(self.signed), "total": self.total_steps},
                "quality_alert": self.quality_alert,
                "last": vars(self.log[-1]).copy() if self.log else None,
                "log": [vars(e).copy() for e in self.log[-config.LOG_SENT:]],
            }

    def lights(self):
        """Panel LED states for the ESP32."""
        with self.lock:
            return {
                "power": self.mode != IDLE,
                "listening": self.listening,
                "labor": self.labor_started_at is not None,
                "alert": self.quality_alert is not None,
                "complete": self.mode == COMPLETE,
            }
