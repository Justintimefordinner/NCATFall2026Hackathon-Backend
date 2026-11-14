"""Shared data types and names. Imports nothing from the project."""
from dataclasses import dataclass, field

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

PANEL_INTENTS = {POWER, LISTEN_TOGGLE}
SUPERVISOR_INTENTS = {INSPECTOR_SIGNOFF, QUALITY_TRIGGER, QUALITY_ACK, RESET}
BLOCKED_BY_ALERT = {SIGN_STEP, SIGN_PAGE, NEXT_PAGE, PREV_PAGE}


@dataclass
class Command:
    intent: str
    source: str                                 # "voice" | "debug" | "panel" | "supervisor"
    args: dict = field(default_factory=dict)    # {"step": 3}, {"pin": "1234"}, {"message": "..."}
    confidence: float = 1.0
    raw: str = ""                               # original text, for the log


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
