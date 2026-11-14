"""Spoken supervisor challenge: supervisor_confirm / clear_alert -> phrase -> answer."""
import pytest

import config
from models import *
from parser import parse
from state import MES

HIGH, LOW = 0.9, config.SUPERVISOR_VOICE_THRESHOLD - 0.01


def cmd(intent, source="debug", **args):
    return Command(intent, source, args)


def say(m, text, role="supervisor", score=HIGH):
    return m.dispatch(parse(text, 1.0, "voice", role=role, speaker_score=score))


@pytest.fixture
def m():
    m = MES(config.DATA_PATH)
    m.dispatch(cmd(POWER, "panel"))
    m.dispatch(cmd(LISTEN_TOGGLE, "panel"))
    m.dispatch(cmd(START_LABOR))
    return m


@pytest.fixture
def alert(m):
    m.dispatch(cmd(QUALITY_TRIGGER, "supervisor", message="Loose brick"))
    return m


@pytest.fixture
def pending(m):
    m.dispatch(cmd(SIGN_STEP, step=2))
    assert m.pending_inspector == [(1, 2)]
    return m


# ---------- parser ----------
@pytest.mark.parametrize("text,intent", [
    ("supervisor confirm", SUPERVISOR_CONFIRM), ("supervisor sign off", SUPERVISOR_CONFIRM),
    ("inspector sign off", SUPERVISOR_CONFIRM), ("inspector sign off step 2", SUPERVISOR_CONFIRM),
    ("clear quality alert", CLEAR_ALERT), ("clear alert", CLEAR_ALERT),
    ("acknowledge alert", CLEAR_ALERT), ("bench, clear the alert please", UNKNOWN),
    ("sign off step 2", SIGN_STEP),
])
def test_parse_supervisor_phrases(text, intent):
    assert parse(text).intent == intent


def test_parse_carries_speaker_fields():
    c = parse("clear alert", 0.9, "voice", role="supervisor", speaker_score=0.8)
    assert (c.role, c.speaker_score) == ("supervisor", 0.8)


# ---------- clear alert ----------
def test_tech_clear_alert_keeps_refusing(alert):
    r = say(alert, "clear alert", role="operator")
    assert r.message == "Quality alert open. Supervisor must clear it"
    assert alert.challenge is None and alert.quality_alert == "Loose brick"


def test_supervisor_clears_alert_by_voice(alert):
    r = say(alert, "clear quality alert")
    phrase = alert.challenge["phrase"]
    assert r.ok and r.speak and r.message == f"Supervisor, confirm with: {phrase}"
    snap = alert.snapshot()["supervisor_challenge"]
    assert snap["phrase"] == phrase and snap["action"] == "clear_alert"
    r = say(alert, f"bench {phrase}")
    assert r.ok and r.message == "Quality alert cleared"
    assert alert.quality_alert is None and alert.challenge is None
    last = alert.log[-1]
    assert last.source == "supervisor_voice" and last.score == HIGH and last.ok


def test_challenge_accepts_spoken_number_words_or_digits(alert):
    say(alert, "clear alert")
    color, number = alert.challenge["phrase"].split()
    digits = {"two": 2, "three": 3, "five": 5, "six": 6, "seven": 7, "nine": 9, "ten": 10}
    assert say(alert, f"{color} {digits[number]}").ok


# ---------- inspector sign-off ----------
def test_supervisor_confirm_signs_pending_step(pending):
    say(pending, "supervisor confirm")
    assert pending.challenge["action"] == "signoff"
    r = say(pending, pending.challenge["phrase"])
    assert r.message == "Step 2 signed off by supervisor"
    assert pending.signed_by[(1, 2)] == "supervisor" and pending.pending_inspector == []


def test_voice_signoff_can_finish_assembly(pending):
    pending.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN))
    pending.dispatch(cmd(SIGN_PAGE))
    pending.dispatch(cmd(NEXT_PAGE))
    pending.dispatch(cmd(SIGN_STEP, step=1))
    pending.dispatch(cmd(SIGN_STEP, step=2))
    # pretend the last step needs an inspector too
    pending.pages[1]["steps"][2]["inspector_required"] = True
    pending.dispatch(cmd(SIGN_STEP, step=3))
    say(pending, "inspector sign off")
    r = say(pending, pending.challenge["phrase"])
    assert r.message.endswith("Assembly complete") and pending.mode == COMPLETE


def test_supervisor_confirm_with_nothing_pending(m):
    r = say(m, "supervisor confirm")
    assert r.ok is False and r.message == "No step waiting on inspector" and m.challenge is None


def test_supervisor_clear_alert_with_no_alert(m):
    assert say(m, "clear alert").message == "No open quality alert" and m.challenge is None


def test_tech_supervisor_confirm_refused(pending):
    r = say(pending, "supervisor confirm", role="operator")
    assert r.message == "Supervisor must sign off" and pending.challenge is None


# ---------- failed answers close the challenge ----------
def _assert_failed(m, r):
    assert r.ok is False and r.speak and r.message == "Supervisor voice not recognized"
    assert m.challenge is None


def test_wrong_words(alert):
    say(alert, "clear alert")
    _assert_failed(alert, say(alert, "banana split"))
    assert alert.quality_alert == "Loose brick"


def test_low_score(alert):
    say(alert, "clear alert")
    _assert_failed(alert, say(alert, alert.challenge["phrase"], score=LOW))
    assert alert.quality_alert is not None


def test_missing_score(alert):
    say(alert, "clear alert")
    _assert_failed(alert, say(alert, alert.challenge["phrase"], score=None))


def test_tech_voice_with_right_words(alert):
    say(alert, "clear alert")
    _assert_failed(alert, say(alert, alert.challenge["phrase"], role="operator"))
    assert alert.log[-1].source == "supervisor_voice"        # logged as a challenge attempt


def test_any_other_utterance_closes_it(pending):
    say(pending, "supervisor confirm")
    _assert_failed(pending, say(pending, "next page", role="operator"))
    assert pending.page == 1                                 # the utterance did not run


def test_expired_challenge(alert):
    say(alert, "clear alert")
    phrase = alert.challenge["phrase"]
    alert.challenge["expires_at"] -= config.CHALLENGE_TTL + 1
    assert alert.snapshot()["supervisor_challenge"] is None
    r = say(alert, phrase)                                   # too late: just an unknown utterance
    assert r.message == "Try again" and alert.challenge is None
    assert alert.quality_alert is not None


# ---------- interaction with other inputs ----------
def test_non_voice_input_does_not_consume_challenge(alert):
    say(alert, "clear alert")
    alert.dispatch(cmd(LISTEN_TOGGLE, "panel")); alert.dispatch(cmd(LISTEN_TOGGLE, "panel"))
    assert alert.challenge is not None
    assert say(alert, alert.challenge["phrase"]).ok


def test_pin_still_works_during_challenge(alert):
    say(alert, "clear alert")
    assert alert.dispatch(cmd(QUALITY_ACK, "supervisor", pin=config.PIN)).ok
    r = say(alert, alert.challenge["phrase"])                # nothing left to clear
    assert r.message == "No open quality alert"


def test_reset_clears_challenge(alert):
    say(alert, "clear alert")
    alert.dispatch(cmd(RESET, "supervisor"))
    assert alert.challenge is None


def test_log_scores_only_on_voice(alert):
    say(alert, "next page", role="operator", score=0.7)
    assert (alert.log[-1].source, alert.log[-1].score) == ("voice", 0.7)
    say(alert, "clear alert")
    assert (alert.log[-1].source, alert.log[-1].score) == ("supervisor_voice", HIGH)
    alert.dispatch(cmd(LISTEN_TOGGLE, "panel"))
    assert alert.log[-1].score is None


# ---------- HTTP ----------
def test_challenge_over_http():
    from app import app, mes
    mes.reset()
    c = app.test_client()
    post = lambda url, body=None: c.post(url, json=body).get_json()
    post("/api/panel/button", {"id": "power"})
    post("/api/panel/button", {"id": "listen_toggle"})
    post("/api/quality/trigger", {"message": "Loose brick"})
    voice = {"source": "voice", "role": "supervisor", "speaker_score": 0.82}
    r = post("/api/command", {"text": "clear alert", **voice})
    phrase = r["state"]["supervisor_challenge"]["phrase"]
    r = post("/api/command", {"text": phrase, **voice})
    assert r["message"] == "Quality alert cleared" and r["state"]["quality_alert"] is None
    assert r["state"]["last"]["source"] == "supervisor_voice"
    assert r["state"]["last"]["score"] == 0.82
    bad = c.post("/api/command", json={"text": "x", "speaker_score": "loud"})
    assert bad.status_code == 400
