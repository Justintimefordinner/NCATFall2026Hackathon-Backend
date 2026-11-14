"""One small test per transition-table row."""
import pytest

import config
from models import *
from state import MES


def cmd(intent, source="debug", **args):
    return Command(intent, source, args)


@pytest.fixture
def m():
    return MES(config.DATA_PATH)


@pytest.fixture
def working(m):
    m.dispatch(cmd(POWER, "panel"))
    m.dispatch(cmd(START_LABOR))
    return m


# ---------- gatekeeping ----------
def test_voice_ignored_while_listening_off_but_logged(m):
    m.dispatch(cmd(POWER, "panel"))
    r = m.dispatch(Command(START_LABOR, "voice", raw="start labor"))
    assert r.ok is False and r.speak is False and m.mode == ARRIVED
    assert m.log[-1].message == "Ignored, listening off" and m.log[-1].input == "start labor"


def test_voice_accepted_while_listening_on(m):
    m.dispatch(cmd(POWER, "panel"))
    m.dispatch(cmd(LISTEN_TOGGLE, "panel"))
    assert m.dispatch(Command(START_LABOR, "voice")).ok and m.mode == WORKING


def test_low_confidence_is_try_again(m):
    m.dispatch(cmd(POWER, "panel"))
    r = m.dispatch(Command(START_LABOR, "debug", confidence=config.CONFIDENCE_THRESHOLD - 0.01))
    assert r.message == "Try again" and m.mode == ARRIVED


def test_unknown_is_try_again(working):
    assert working.dispatch(cmd(UNKNOWN)).message == "Try again"


def test_idle_only_accepts_power_and_reset(m):
    r = m.dispatch(cmd(START_LABOR))
    assert r.message == "Press power to start" and m.mode == IDLE
    r = m.dispatch(cmd(LISTEN_TOGGLE, "panel"))           # listen is ignored in standby
    assert r.ok is False and not r.speak and m.listening is False
    assert m.lights()["listening"] is False
    assert m.dispatch(cmd(QUALITY_TRIGGER, "supervisor", message="x")).ok is False


def test_power_twice(m):
    m.dispatch(cmd(POWER, "panel"))
    r = m.dispatch(cmd(POWER, "panel"))
    assert r.ok and r.message == "Already on" and not r.speak


# ---------- labor ----------
def test_start_labor_twice(working):
    assert working.dispatch(cmd(START_LABOR)).message == "Labor already running"


def test_stop_labor_when_not_running(m):
    m.dispatch(cmd(POWER, "panel"))
    assert m.dispatch(cmd(STOP_LABOR)).message == "Labor is not running"


def test_stop_labor_goes_to_viewing_and_keeps_time(working):
    working.labor_started_at -= 10          # pretend 10 s passed
    r = working.dispatch(cmd(STOP_LABOR))
    assert r.message == "Labor stopped. Operation incomplete" and working.mode == VIEWING
    assert working.snapshot()["labor"] == {"running": False, "seconds": 10}
    working.dispatch(cmd(START_LABOR))
    working.labor_started_at -= 5
    assert working.snapshot()["labor"]["seconds"] == 15


def test_open_instructions_when_already_open(working):
    assert working.dispatch(cmd(OPEN_INSTRUCTIONS)).message == "Page 1"
    assert working.mode == WORKING


# ---------- navigation ----------
def test_page_bounds(working):
    working.dispatch(cmd(SIGN_STEP, step=2))
    working.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN))
    assert working.dispatch(cmd(PREV_PAGE)).message == "No previous page"
    assert working.dispatch(cmd(NEXT_PAGE)).message == "Page 2"
    assert working.dispatch(cmd(NEXT_PAGE)).message == "No next page"
    assert working.dispatch(cmd(PREV_PAGE)).message == "Page 1"


def test_navigation_allowed_while_viewing(m):
    m.dispatch(cmd(POWER, "panel"))
    m.dispatch(cmd(OPEN_INSTRUCTIONS))
    assert m.dispatch(cmd(NEXT_PAGE)).ok and m.page == 2


# ---------- sign-offs ----------
def test_sign_in_arrived(m):
    m.dispatch(cmd(POWER, "panel"))
    assert m.dispatch(cmd(SIGN_STEP, step=1)).message == "Say start labor or open instructions"


def test_already_signed(working):
    working.dispatch(cmd(SIGN_STEP, step=1))
    assert working.dispatch(cmd(SIGN_STEP, step=1)).message == "Step 1 already signed off"


def test_no_such_step(working):
    assert working.dispatch(cmd(SIGN_STEP, step=9)).message == "No step 9 on this page"


def test_inspector_step_not_queued_twice(working):
    working.dispatch(cmd(SIGN_STEP, step=2))
    working.dispatch(cmd(SIGN_STEP, step=2))
    working.dispatch(cmd(SIGN_PAGE))
    assert working.pending_inspector == [(1, 2)]


def test_sign_page_stops_at_inspector_step(working):
    r = working.dispatch(cmd(SIGN_PAGE))
    assert r.message == "Signed off through step 1. Step 2 needs supervisor sign-off"
    assert working.signed == {(1, 1)} and working.pending_inspector == [(1, 2)]
    assert working.snapshot()["page"]["all_signed"] is False


def test_sign_page_first_step_is_inspector(m, tmp_path):
    import json
    data = json.load(open(config.DATA_PATH))
    data["pages"][0]["steps"][0]["inspector_required"] = True
    path = tmp_path / "op.json"
    path.write_text(json.dumps(data))
    m = MES(str(path))
    m.dispatch(cmd(POWER, "panel")); m.dispatch(cmd(START_LABOR))
    r = m.dispatch(cmd(SIGN_PAGE))
    assert r.ok is False and r.message == "Step 1 needs supervisor sign-off"
    assert m.signed == set() and m.pending_inspector == [(1, 1)]


# ---------- inspector gate: can't move past an unsigned inspector step ----------
def test_cannot_sign_step_after_inspector_step(working):
    working.dispatch(cmd(SIGN_STEP, step=1))
    r = working.dispatch(cmd(SIGN_STEP, step=3))          # skipped inspector step 2
    assert r.ok is False and r.message == "Step 2 needs supervisor sign-off before you continue"
    assert (1, 3) not in working.signed
    assert working.pending_inspector == [(1, 2)]           # queued for the supervisor


def test_pending_inspector_step_still_blocks(working):
    working.dispatch(cmd(SIGN_STEP, step=2))               # tech claims it, supervisor hasn't signed
    assert working.dispatch(cmd(SIGN_STEP, step=3)).ok is False
    working.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN))
    assert working.dispatch(cmd(SIGN_STEP, step=3)).message == "Step 3 signed off"


def test_cannot_go_to_next_page_while_working(working):
    r = working.dispatch(cmd(NEXT_PAGE))
    assert r.ok is False and r.message == "Step 2 needs supervisor sign-off before the next page"
    assert working.page == 1 and working.pending_inspector == [(1, 2)]
    working.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN))
    assert working.dispatch(cmd(NEXT_PAGE)).message == "Page 2"


def test_read_ahead_then_sign_later_page_is_blocked(m):
    m.dispatch(cmd(POWER, "panel"))
    m.dispatch(cmd(OPEN_INSTRUCTIONS))
    assert m.dispatch(cmd(NEXT_PAGE)).ok                   # reading ahead is allowed
    m.dispatch(cmd(START_LABOR))
    r = m.dispatch(cmd(SIGN_STEP, step=1))
    assert r.message == "Page 1 step 2 needs supervisor sign-off before you continue"
    assert m.dispatch(cmd(SIGN_PAGE)).ok is False and m.signed == set()


def test_steps_before_inspector_step_are_not_gated(working):
    assert working.dispatch(cmd(SIGN_STEP, step=1)).ok


def test_sign_after_complete(working):
    _finish(working)
    assert working.dispatch(cmd(SIGN_STEP, step=1)).message == "Operation already complete"
    assert working.dispatch(cmd(START_LABOR)).message == "Operation already complete"


def _finish(m):
    m.dispatch(cmd(SIGN_PAGE))                     # stops at inspector step 2
    m.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN))
    m.dispatch(cmd(SIGN_PAGE))                     # now signs step 3
    m.dispatch(cmd(NEXT_PAGE))
    m.dispatch(cmd(SIGN_PAGE))
    assert m.mode == COMPLETE


# ---------- supervisor ----------
def test_alert_blocks_sign_and_navigation(working):
    working.dispatch(cmd(QUALITY_TRIGGER, "supervisor", message="Bad brick"))
    for c in (cmd(SIGN_STEP, step=1), cmd(SIGN_PAGE), cmd(NEXT_PAGE), cmd(PREV_PAGE)):
        assert working.dispatch(c).message == "Quality alert open. Supervisor must clear it"
    assert working.signed == set()
    assert working.dispatch(cmd(STOP_LABOR)).ok          # labor is not blocked


def test_wrong_pin_is_silent(working):
    working.dispatch(cmd(QUALITY_TRIGGER, "supervisor", message="x"))
    r = working.dispatch(cmd(QUALITY_ACK, "supervisor", pin="0000"))
    assert r.message == "Wrong PIN" and r.speak is False and working.quality_alert == "x"


def test_ack_with_no_alert(working):
    assert working.dispatch(cmd(QUALITY_ACK, "supervisor", pin=config.PIN)).message == \
        "No open quality alert"


def test_inspector_signoff_with_nothing_pending(working):
    r = working.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN))
    assert r.message == "No step waiting on inspector"


def test_inspector_signoff_specific_step(working):
    working.dispatch(cmd(SIGN_STEP, step=2))
    r = working.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN, page=1, step=3))
    assert r.ok is False and working.pending_inspector == [(1, 2)]
    r = working.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN, page=1, step=2))
    assert r.message == "Step 2 signed off by supervisor"


def test_inspector_signoff_not_blocked_by_alert(working):
    working.dispatch(cmd(SIGN_STEP, step=2))
    working.dispatch(cmd(QUALITY_TRIGGER, "supervisor", message="x"))
    assert working.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN)).ok


def test_supervisor_finishes_assembly(working):
    # make the very last step the inspector step, so the supervisor's PIN finishes it
    import json, tempfile, os
    data = json.load(open(config.DATA_PATH))
    for p in data["pages"]:
        for s in p["steps"]:
            s["inspector_required"] = False
    data["pages"][-1]["steps"][-1]["inspector_required"] = True
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(data, f)
    m = MES(f.name); os.unlink(f.name)
    m.dispatch(cmd(POWER, "panel")); m.dispatch(cmd(START_LABOR))
    m.dispatch(cmd(SIGN_PAGE)); m.dispatch(cmd(NEXT_PAGE)); m.dispatch(cmd(SIGN_PAGE))
    assert m.mode == WORKING and m.pending_inspector == [(2, 3)]
    r = m.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN))
    assert r.message == "Step 3 signed off by supervisor. Assembly complete"
    assert m.mode == COMPLETE


def test_reset(working):
    working.dispatch(cmd(SIGN_STEP, step=1))
    working.dispatch(cmd(QUALITY_TRIGGER, "supervisor", message="x"))
    r = working.dispatch(cmd(RESET, "supervisor"))
    assert r.ok and not r.speak
    assert working.mode == IDLE and working.signed == set() and working.quality_alert is None
    assert working.labor_started_at is None and working.labor_accum == 0


# ---------- views ----------
def test_log_cap(m):
    for _ in range(config.LOG_CAP + 20):
        m.dispatch(cmd(LISTEN_TOGGLE, "panel"))
    assert len(m.log) == config.LOG_CAP
    assert len(m.snapshot()["log"]) == config.LOG_SENT


def test_lights(working):
    assert working.lights() == {"power": True, "listening": False, "labor": True,
                                "alert": False, "inspector": False, "complete": False}
    working.dispatch(cmd(SIGN_STEP, step=2))
    assert working.lights()["inspector"] is True
    working.dispatch(cmd(INSPECTOR_SIGNOFF, "supervisor", pin=config.PIN))
    assert working.lights()["inspector"] is False


# ---------- power off (long press) ----------
def test_power_off_goes_to_standby_and_keeps_progress(working):
    working.dispatch(cmd(LISTEN_TOGGLE, "panel"))
    working.dispatch(cmd(SIGN_STEP, step=1))
    working.labor_started_at -= 30
    r = working.dispatch(cmd(POWER_OFF, "panel"))
    assert r.ok and r.message == "Station off"
    assert working.mode == IDLE and working.listening is False
    assert working.snapshot()["labor"] == {"running": False, "seconds": 30}
    assert (1, 1) in working.signed
    # while off, the tech can't do anything but power on
    assert working.dispatch(cmd(START_LABOR)).message == "Press power to start"
    r = working.dispatch(cmd(POWER, "panel"))
    assert r.message == "Incomplete operation. Start labor or open instructions?"
    assert working.mode == ARRIVED and (1, 1) in working.signed


def test_power_off_when_already_off(m):
    r = m.dispatch(cmd(POWER_OFF, "panel"))
    assert r.ok and r.message == "Already off" and not r.speak and m.mode == IDLE


def test_power_off_closes_supervisor_challenge(working):
    working.dispatch(cmd(SIGN_STEP, step=2))
    working.challenge = {"phrase": "red two", "action": "signoff", "expires_at": 1e18}
    working.dispatch(cmd(POWER_OFF, "panel"))
    assert working.challenge is None and working.pending_inspector == [(1, 2)]


def test_power_on_after_finishing_resumes_complete(working):
    _finish(working)
    working.dispatch(cmd(POWER_OFF, "panel"))
    assert working.dispatch(cmd(POWER, "panel")).message == "Operation complete"
    assert working.mode == COMPLETE
