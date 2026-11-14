import pytest

from models import *
from parser import normalize, parse

CASES = [
    # start labor
    ("start labor", START_LABOR, None), ("Start work", START_LABOR, None),
    ("start clock", START_LABOR, None), ("clock in", START_LABOR, None),
    ("okay start labor please", START_LABOR, None),
    # stop labor
    ("stop labor", STOP_LABOR, None), ("stop work", STOP_LABOR, None),
    ("stop clock", STOP_LABOR, None), ("pause labor", STOP_LABOR, None),
    # instructions
    ("open instructions", OPEN_INSTRUCTIONS, None), ("view instructions", OPEN_INSTRUCTIONS, None),
    ("show instructions", OPEN_INSTRUCTIONS, None), ("read ahead", OPEN_INSTRUCTIONS, None),
    # next
    ("next", NEXT_PAGE, None), ("next page", NEXT_PAGE, None), ("go on", NEXT_PAGE, None),
    ("continue", NEXT_PAGE, None), ("forward", NEXT_PAGE, None),
    ("okay next page please", NEXT_PAGE, None), ("go to the next page", NEXT_PAGE, None),
    # previous
    ("previous", PREV_PAGE, None), ("previous page", PREV_PAGE, None),
    ("prior page", PREV_PAGE, None), ("go back", PREV_PAGE, None), ("back", PREV_PAGE, None),
    # sign page
    ("page done", SIGN_PAGE, None), ("sign off page", SIGN_PAGE, None),
    ("page complete", SIGN_PAGE, None), ("all done", SIGN_PAGE, None),
    ("okay page done", SIGN_PAGE, None),
    # sign step
    ("step three done", SIGN_STEP, 3), ("step 3 done", SIGN_STEP, 3),
    ("step 3", SIGN_STEP, 3), ("step three", SIGN_STEP, 3),
    ("sign off step 4", SIGN_STEP, 4), ("sign off step for", SIGN_STEP, 4),
    ("finished step two", SIGN_STEP, 2), ("step to complete", SIGN_STEP, 2),
    ("step one finished", SIGN_STEP, 1), ("Step 10 done.", SIGN_STEP, 10),
    ("step won done", SIGN_STEP, 1), ("step ate done", SIGN_STEP, 8),
    # fuzzy
    ("nxt page", NEXT_PAGE, None), ("stop labour", STOP_LABOR, None),
    ("open instruction", OPEN_INSTRUCTIONS, None),
    # unknown
    ("banana", UNKNOWN, None), ("", UNKNOWN, None), ("what time is lunch", UNKNOWN, None),
]


@pytest.mark.parametrize("text,intent,step", CASES)
def test_parse(text, intent, step):
    c = parse(text)
    assert c.intent == intent and c.args.get("step") == step


def test_parse_keeps_raw_source_confidence():
    c = parse("Next page!", 0.9, "debug")
    assert (c.raw, c.source, c.confidence) == ("Next page!", "debug", 0.9)


def test_fuzzy_scales_confidence():
    c = parse("nxt page", 0.9)
    assert c.intent == NEXT_PAGE and 0.6 < c.confidence < 0.9


def test_unknown_has_zero_confidence():
    assert parse("banana").confidence == 0.0


def test_normalize():
    assert normalize("Step THREE, done!") == "step 3 done"


def test_no_phrase_inside_another_intents_phrase():
    import re
    from parser import PHRASES
    for i, ps in PHRASES.items():
        for j, qs in PHRASES.items():
            if i == j:
                continue
            for p in ps:
                for q in qs:
                    assert not re.search(rf"\b{p}\b", q), f"{p!r} ({i}) is inside {q!r} ({j})"


# ---------- easter egg ----------
@pytest.mark.parametrize("text", ["What do you say to our judges?", "what do you say to the judges",
                                  "bench, say to our judges", "thank the judges",
                                  "what do you say to our judge"])      # fuzzy: STT drops the s
def test_thank_judges(text):
    assert parse(text).intent == THANK_JUDGES
