"""
Test plan step 2 - record the test set: every command and variant, 2-3 team
voices, once clean and once with factory noise playing at a realistic volume.
Every later change gets scored on exactly this audio (tools/score.py).

  python tools/record_testset.py --speaker adan --condition clean
  python tools/record_testset.py --speaker adan --condition noise
  python tools/record_testset.py --speaker micah --condition noise --phrases my_list.txt

Files go to testset/<speaker>/<condition>/ and are listed in testset/manifest.csv.
Stand where the tech stands while building (risk plan: "works seated, fails while building").
Stop the voice service first so the mic is free: sudo systemctl stop mes-voice
"""
import argparse
import os
import re
import time

from common import TESTSET, append_manifest, load_phrases, write_wav  # noqa: E402
import vconfig
from audio_io import Mic, rms


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speaker", required=True)
    ap.add_argument("--condition", required=True, help="clean or noise (any label works)")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--phrases", help="text file, one phrase per line (default: the doc's command table)")
    ap.add_argument("--device")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()
    cfg = vconfig.load(a.set)

    phrases = load_phrases(a.phrases)
    mic = Mic(a.device if a.device is not None else cfg.MIC_DEVICE)
    print(f"Mic: {mic.name}. {len(phrases)} phrases, {a.seconds:.0f}s each.")
    print("For each: press Enter, wait for GO, say the phrase once, naturally.")
    print("Type r + Enter to redo the last one, s + Enter to skip, q + Enter to quit.\n")

    i, saved = 0, 0
    while i < len(phrases):
        p = phrases[i]
        cmd = input(f"[{i + 1}/{len(phrases)}] \"{p}\"  (Enter) ").strip().lower()
        if cmd == "q":
            break
        if cmd == "s":
            i += 1
            continue
        if cmd == "r" and i > 0:
            i -= 1
            continue
        time.sleep(0.2)
        print("   GO")
        x = mic.record(a.seconds)
        lvl = rms(x)
        warn = "  (very quiet - check the mic)" if lvl < 0.003 else ""
        rel = os.path.join(a.speaker, a.condition, f"{i + 1:02d}_{slug(p)}.wav")
        write_wav(os.path.join(TESTSET, rel), x)
        append_manifest({"file": rel, "speaker": a.speaker, "condition": a.condition, "expected": p})
        print(f"   saved {rel}  level {lvl:.4f}{warn}")
        saved += 1
        i += 1
    mic.close()
    print(f"\nSaved {saved} clips. Score them with: python tools/score.py")


if __name__ == "__main__":
    main()
