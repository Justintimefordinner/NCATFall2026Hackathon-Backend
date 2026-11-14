"""Writes real snapshot() output to fixtures/ so the frontend can build against it.
  python tools/make_fixtures.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config  # noqa: E402
from models import *  # noqa: E402,F403
from state import MES  # noqa: E402

OUT = os.path.join(config.BASE_DIR, "fixtures")


def write(name, m):
    with open(os.path.join(OUT, name), "w") as f:
        json.dump({"type": "state", **m.snapshot()}, f, indent=2)
        f.write("\n")
    print("wrote fixtures/" + name)


def main():
    os.makedirs(OUT, exist_ok=True)
    m = MES(config.DATA_PATH)
    write("state_idle.json", m)

    m.dispatch(Command(POWER, "panel", raw="power"))
    m.dispatch(Command(LISTEN_TOGGLE, "panel", raw="listen_toggle"))
    m.dispatch(Command(START_LABOR, "voice", raw="start labor"))
    m.labor_started_at -= 312                       # look like 5 minutes in
    m.dispatch(Command(SIGN_STEP, "voice", {"step": 1}, raw="step one done"))
    m.dispatch(Command(SIGN_STEP, "voice", {"step": 2}, raw="step two done"))
    write("state_working.json", m)

    m.dispatch(Command(QUALITY_TRIGGER, "supervisor", {"message": "Bolt 6 not torqued to spec"},
                       raw="quality alert: Bolt 6 not torqued to spec"))
    m.dispatch(Command(NEXT_PAGE, "voice", raw="next page"))
    write("state_alert.json", m)


if __name__ == "__main__":
    main()
