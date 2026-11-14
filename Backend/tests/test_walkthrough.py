"""The demo, scripted. This is the spec in code."""
import config
from models import *
from state import MES


def cmd(intent, source="debug", **args):
    return Command(intent, source, args)


def test_demo_walkthrough():
    m = MES(config.DATA_PATH)
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
    assert m.signed_by[(1, 2)] == "supervisor"
    assert m.dispatch(cmd(PREV_PAGE)).message == "No previous page"
    assert m.dispatch(cmd(SIGN_PAGE)).message == "Page 1 signed off"
    assert m.snapshot()["page"]["all_signed"] is True
    assert m.page == 1                                # page done does not auto-advance
    assert m.dispatch(cmd(NEXT_PAGE)).message == "Page 2"
    assert m.dispatch(cmd(NEXT_PAGE)).message == "No next page"
    r = m.dispatch(cmd(SIGN_PAGE))
    assert r.message == "Page 2 signed off. Assembly complete" and m.mode == COMPLETE
    assert m.dispatch(cmd(STOP_LABOR)).message == "Labor stopped. Operation complete"
    assert m.mode == COMPLETE
    snap = m.snapshot()
    assert snap["progress"] == {"signed": 6, "total": 6}
    assert snap["labor"]["running"] is False
