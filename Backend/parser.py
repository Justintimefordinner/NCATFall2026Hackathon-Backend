"""Transcript -> Command. Pure Python, no Flask imports.

Three passes: normalize, exact phrase match, fuzzy match. The PHRASES table and
NUMBER_WORDS are owned by the voice side (Adan); the matching code lives here.
"""
import difflib
import re

from models import (
    CLEAR_ALERT, SUPERVISOR_CONFIRM, NEXT_PAGE, OPEN_INSTRUCTIONS, PREV_PAGE, SIGN_PAGE, SIGN_STEP, START_LABOR,
    STOP_LABOR, UNKNOWN, Command,
)

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
    SUPERVISOR_CONFIRM: ["supervisor confirm", "supervisor sign off", "inspector sign off"],
    CLEAR_ALERT:       ["clear quality alert", "clear alert", "acknowledge alert"],
}
# checked before the step patterns, so "inspector sign off step 2" isn't a tech sign-off
PRIORITY = (SUPERVISOR_CONFIRM, CLEAR_ALERT)

# "step X done" carries a number, so it is matched with patterns, not the table.
STEP_PATTERNS = [r"\bstep (\d+) (done|complete|finished)\b", r"\bsign off step (\d+)\b",
                 r"\bfinished step (\d+)\b", r"\bstep (\d+)\b"]

FUZZY_CUTOFF = 0.75

# precomputed: longest phrases first within each intent, and a flat phrase -> intent map
_ORDERED = {i: sorted(ps, key=len, reverse=True) for i, ps in PHRASES.items()}
_LOOKUP = {p: i for i, ps in PHRASES.items() for p in ps}


def normalize(text):
    t = re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())
    return " ".join(str(NUMBER_WORDS.get(w, w)) for w in t.split())


def parse(text, confidence=1.0, source="voice", role=None, speaker_score=None):
    cmd = _match(text, confidence, source)
    cmd.role, cmd.speaker_score = role, speaker_score
    return cmd


def _match(text, confidence, source):
    t = normalize(text)
    # 0. supervisor phrases win over step patterns
    for intent in PRIORITY:
        for p in _ORDERED[intent]:
            if re.search(rf"\b{p}\b", t):
                return Command(intent, source, {}, confidence, text)
    # 1. step commands carry a number
    for pat in STEP_PATTERNS:
        if m := re.search(pat, t):
            return Command(SIGN_STEP, source, {"step": int(m.group(1))}, confidence, text)
    # 2. exact phrase anywhere in the utterance ("okay next page please")
    for intent, phrases in _ORDERED.items():
        for p in phrases:
            if re.search(rf"\b{p}\b", t):
                return Command(intent, source, {}, confidence, text)
    # 3. fuzzy match on the whole utterance
    best = difflib.get_close_matches(t, _LOOKUP, n=1, cutoff=FUZZY_CUTOFF)
    if best:
        score = difflib.SequenceMatcher(None, t, best[0]).ratio()
        return Command(_LOOKUP[best[0]], source, {}, confidence * score, text)
    return Command(UNKNOWN, source, {}, 0.0, text)
