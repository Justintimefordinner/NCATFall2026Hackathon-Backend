"""
enroll.py - enroll the SUPERVISOR's voice (team doc: "Supervisor voice confirmation").

Only the supervisor is enrolled. Tech commands work for anyone; the voice
client sends a speaker_score (0-1, how much a voice matches the supervisor)
with every command, and the backend accepts a supervisor challenge only when
that score is at or above its own threshold.

Doc rules this follows:
  * several samples, in the demo room, with the station mic
  * only the speech part of each sample is used (VAD trims silence and room noise)
  * consistency check: samples that don't agree with each other get flagged

  python enroll.py --name justin          # record 4 samples and save
  python enroll.py --name justin --samples 6 --seconds 5
  python enroll.py --test                 # say things, see live scores (find the threshold)
  python enroll.py --show                 # what's enrolled
  python enroll.py --delete

Stop the voice service first so the mic is free:  sudo systemctl stop mes-voice
"""
import argparse
import json
import os
import sys
import time

import numpy as np

import engines as E
import vconfig
from audio_io import SR, HighPass, Mic, list_devices, rms

PROMPTS = [
    "Supervisor confirm. Blue seven, green four, red nine.",
    "Clear quality alert. The quick brown fox jumps over the lazy dog.",
    "Inspector sign off. One, two, three, four, five, six, seven, eight.",
    "This is the supervisor at station one, confirming the inspection.",
    "Acknowledge alert. Orange two, silver five, purple eight.",
    "Supervisor sign off. The torque on bolt six is within spec.",
]


def speech_only(cfg, x):
    """High-pass + VAD, return just the speech (or the raw clip if VAD finds none)."""
    x = HighPass(fc=cfg.HIGHPASS_HZ)(x)
    vad, window = E.load_vad(cfg)
    padded = np.concatenate([x, np.zeros(int(SR * 1.0), np.float32)])
    segs = []
    for i in range(0, len(padded) - window + 1, window):
        vad.accept_waveform(padded[i:i + window])
        while not vad.empty():
            segs.append(np.array(vad.front.samples, dtype=np.float32))
            vad.pop()
    return np.concatenate(segs) if segs else np.zeros(0, np.float32)


def countdown():
    for n in (3, 2, 1):
        print(f"  {n}...", end=" ", flush=True)
        time.sleep(0.6)
    print("TALK")


def record_sample(cfg, mic, ext, seconds, prompt, i, total):
    while True:
        print(f"\nSample {i}/{total}. When it says TALK, read this out loud at normal volume,")
        print(f"from where the supervisor will stand during the demo:\n\n   \"{prompt}\"\n")
        input("  Press Enter when ready... ")
        countdown()
        x = mic.record(seconds)
        sp = speech_only(cfg, x)
        dur, lvl = len(sp) / SR, rms(sp)
        if dur < 1.5:
            print(f"  Only {dur:.1f}s of speech detected (level {rms(x):.4f}). Speak a bit louder/closer. Again.")
            continue
        print(f"  got {dur:.1f}s of speech, level {lvl:.4f}")
        return E.embed(ext, sp)


def enroll(cfg, a):
    ext = E.load_speaker(cfg)
    mic = Mic(a.device if a.device is not None else cfg.MIC_DEVICE)
    print(f"Mic: {mic.name}")
    embs = []
    for i in range(a.samples):
        embs.append(record_sample(cfg, mic, ext, a.seconds, PROMPTS[i % len(PROMPTS)], i + 1, a.samples))
    mic.close()

    embs = np.stack(embs)
    mean = embs.mean(axis=0)
    mean /= np.linalg.norm(mean) + 1e-9
    per = [E.cosine(e, mean) for e in embs]
    consistency = round(float(np.mean(per)), 3)
    print("\nEach sample vs the average voiceprint:")
    for i, s in enumerate(per, 1):
        flag = "   <- odd one out (noise? different voice?)" if s < consistency - 0.1 else ""
        print(f"  sample {i}: {s:.3f}{flag}")
    print(f"Consistency: {consistency}")
    if consistency < 0.6:
        print("!! Low consistency. Re-run with the mic closer and less background noise.")

    os.makedirs(cfg.VOICES_DIR, exist_ok=True)
    np.save(os.path.join(cfg.VOICES_DIR, "supervisor.npy"), mean)
    with open(os.path.join(cfg.VOICES_DIR, "supervisor.json"), "w") as f:
        json.dump({"name": a.name, "samples": len(embs), "seconds": a.seconds,
                   "consistency": consistency, "enrolled": time.strftime("%Y-%m-%d %H:%M"),
                   "mic": mic.name}, f, indent=2)
    print(f"\nSaved supervisor '{a.name}'. Next: python enroll.py --test")
    print("Then restart voice: sudo systemctl restart mes-voice")


def test(cfg, a):
    sup, info = E.load_supervisor(cfg)
    if sup is None:
        sys.exit("No supervisor enrolled. Run: python enroll.py --name <name>")
    ext = E.load_speaker(cfg)
    vad, window = E.load_vad(cfg)
    mic = Mic(a.device if a.device is not None else cfg.MIC_DEVICE)
    hp = HighPass(fc=cfg.HIGHPASS_HZ)
    print(f"Supervisor: {info.get('name')}. Mic: {mic.name}")
    print("Have the supervisor AND other people say a few commands. Each line is one utterance.")
    print("Pick the backend threshold between the supervisor's LOWEST score and everyone else's HIGHEST.")
    print("Doc: set it strict (wrong person let through is worse than asking again). Ctrl+C to stop.\n")
    buf = np.zeros(0, np.float32)
    try:
        while True:
            try:
                buf = np.concatenate([buf, hp(mic.read())])
            except Exception:
                continue
            while len(buf) >= window:
                vad.accept_waveform(buf[:window])
                buf = buf[window:]
            while not vad.empty():
                seg = np.array(vad.front.samples, dtype=np.float32)
                vad.pop()
                if len(seg) / SR < 0.5:
                    continue
                s = E.cosine(E.embed(ext, seg), sup)
                bar = "#" * max(0, int(s * 40))
                print(f"  {s:5.3f} |{bar:<40}| {len(seg)/SR:.1f}s")
    except KeyboardInterrupt:
        print()


def main():
    ap = argparse.ArgumentParser(description="Enroll the supervisor's voice")
    ap.add_argument("--name", default="supervisor")
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--device", help="mic name piece or index")
    ap.add_argument("--test", action="store_true", help="live score vs the enrolled supervisor")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--delete", action="store_true")
    ap.add_argument("--devices", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()
    cfg = vconfig.load(a.set)
    if a.devices:
        return list_devices()
    if a.show:
        _, info = E.load_supervisor(cfg)
        print(json.dumps(info, indent=2) if info else "No supervisor enrolled.")
        return
    if a.delete:
        for f in ("supervisor.npy", "supervisor.json"):
            p = os.path.join(cfg.VOICES_DIR, f)
            if os.path.exists(p):
                os.remove(p)
        print("Supervisor voiceprint deleted.")
        return
    if a.test:
        return test(cfg, a)
    enroll(cfg, a)


if __name__ == "__main__":
    main()
