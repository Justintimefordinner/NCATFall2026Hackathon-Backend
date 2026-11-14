"""
enroll.py - register an operator's voice so the bench can tell people apart.

  python3 enroll.py --name maria --role operator
  python3 enroll.py --name james --role supervisor
  python3 enroll.py --test          # speak, see who it thinks you are + scores
  python3 enroll.py --list

Enroll in the SAME spot and with the SAME mic you'll demo with, ideally with the
real background noise running. That makes the voiceprint much more reliable.
"""
import argparse
import json
import os
import time

import numpy as np

import models as M
from mic import Mic, list_devices

PROMPTS = [
    "Load Alpha. Next step. Inspection pass. Report defect.",
    "Go back. Repeat the step. Pause the order. Resume.",
    "Call supervisor. Release hold. Load Bravo. What step am I on?",
    "Count out loud from one to ten at a normal speaking volume.",
    "Say your name and the name of your team, then say next step twice.",
]


def speech_only(clip, vad, window):
    """Strip silence/noise gaps with the VAD so the voiceprint is pure speech."""
    if hasattr(vad, "reset"):
        vad.reset()
    for i in range(0, len(clip) - window + 1, window):
        vad.accept_waveform(clip[i:i + window])
    vad.flush()
    segs = []
    while not vad.empty():
        segs.append(np.array(vad.front.samples, dtype=np.float32))
        vad.pop()
    return np.concatenate(segs) if segs else np.zeros(0, np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--role", default="operator", choices=["operator", "supervisor"])
    ap.add_argument("--clips", type=int, default=4)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--device", default=None, help="input device index/name (see --devices)")
    ap.add_argument("--devices", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.45)
    a = ap.parse_args()

    if a.devices:
        return list_devices()
    dev = int(a.device) if a.device and a.device.isdigit() else a.device
    os.makedirs(M.VOICES, exist_ok=True)

    if a.list:
        v = M.load_voices()
        names = list(v)
        print("Enrolled:", {n: v[n][1] for n in names} or "nobody yet")
        if len(names) > 1:
            print("\nSimilarity between enrolled voices (lower = easier to tell apart):")
            for i, x in enumerate(names):
                for y in names[i + 1:]:
                    print(f"  {x:>10} vs {y:<10} {float(np.dot(v[x][0], v[y][0])):.3f}")
        return

    ext = M.load_speaker()
    vad, window = M.load_vad(threshold=0.5)
    hp = M.HighPass()
    mic = Mic(dev).start()
    time.sleep(0.3)

    if a.test:
        voices = M.load_voices()
        print("Test mode. Ctrl+C to stop.")
        while True:
            input("\nPress Enter, then talk for 3 seconds...")
            sp = speech_only(hp(mic.record(3.0)), vad, window)
            if len(sp) < M.SR * 0.5:
                print("  (not enough speech heard)")
                continue
            e = M.embed(ext, sp)
            name, best = M.identify(e, voices, a.threshold)
            scores = {n: round(float(np.dot(e, v[0])), 3) for n, v in voices.items()}
            print(f"  -> {name or 'UNKNOWN'}   scores: {scores}")

    if not a.name:
        ap.error("--name is required (or use --test / --list)")
    name = a.name.strip().lower().replace(" ", "_")

    embs = []
    print(f"\nEnrolling '{name}' as {a.role}. {a.clips} clips of {a.seconds:.0f}s each.")
    for i in range(a.clips):
        print(f"\nClip {i + 1}/{a.clips}. Read this in your normal work voice:\n   \"{PROMPTS[i % len(PROMPTS)]}\"")
        input("Press Enter and start talking...")
        sp = speech_only(hp(mic.record(a.seconds)), vad, window)
        if len(sp) < M.SR * 1.0:
            print("  Not enough speech detected - get closer to the mic and try that clip again.")
            sp = speech_only(hp(mic.record(a.seconds)), vad, window)
            if len(sp) < M.SR * 0.8:
                print("  Still too little speech, skipping this clip.")
                continue
        embs.append(M.embed(ext, sp))
        print(f"  ok ({len(sp) / M.SR:.1f}s of speech)")
    mic.stop()

    if len(embs) < 2:
        raise SystemExit("Too few good clips. Run again.")
    consistency = np.mean([float(np.dot(x, y)) for i, x in enumerate(embs) for y in embs[i + 1:]])
    mean = np.mean(embs, axis=0)
    mean /= np.linalg.norm(mean)
    np.save(os.path.join(M.VOICES, f"{name}.npy"), mean)

    roles_path = os.path.join(M.VOICES, "roles.json")
    roles = json.load(open(roles_path)) if os.path.exists(roles_path) else {}
    roles[name] = a.role
    json.dump(roles, open(roles_path, "w"), indent=2)

    print(f"\nSaved {name} ({a.role}). Clip-to-clip consistency: {consistency:.3f} "
          f"(above ~0.6 is good; if low, re-enroll closer to the mic).")
    others = {n: v for n, v in M.load_voices().items() if n != name}
    for n, v in others.items():
        print(f"  similarity to {n}: {float(np.dot(mean, v[0])):.3f}  "
              f"(should be well below the {a.threshold} threshold)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
