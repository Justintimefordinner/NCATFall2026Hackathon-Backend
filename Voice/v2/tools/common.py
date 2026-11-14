"""Shared bits for the test tools: paths, WAV I/O, the command list."""
import csv
import os
import sys
import wave

import numpy as np

TOOLS = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(TOOLS)
if V2 not in sys.path:
    sys.path.insert(0, V2)

TESTSET = os.path.join(V2, "testset")
MANIFEST = os.path.join(TESTSET, "manifest.csv")
FIELDS = ["file", "speaker", "condition", "expected"]

# Every command and variant from the team doc's "Voice commands" table.
# Numbers are mixed between words and digits on purpose; Moonshine writes either.
PHRASES = [
    "start labor", "start work", "start clock", "clock in",
    "stop labor", "stop work", "stop clock", "pause labor",
    "open instructions", "view instructions", "show instructions", "read ahead",
    "step one done", "step two done", "step three done", "step four done",
    "sign off step five", "step six complete", "finished step seven", "step eight done",
    "page done", "sign off page", "page complete", "all done",
    "previous", "previous page", "prior page", "go back", "back",
    "next", "next page", "go on", "continue", "forward",
    "supervisor confirm", "supervisor sign off", "inspector sign off", "inspector confirm",
    "clear quality alert", "clear alert", "acknowledge alert", "acknowledge quality alert",
]


def read_wav(path):
    """Mono float32 at 16 kHz from a 16-bit WAV (any rate / channels)."""
    from audio_io import SR, resample
    with wave.open(path) as w:
        sr, ch, n, width = w.getframerate(), w.getnchannels(), w.getnframes(), w.getsampwidth()
        raw = w.readframes(n)
    if width != 2:
        raise ValueError(f"{path}: only 16-bit WAV supported")
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return resample(x, sr, SR)


def write_wav(path, x, sr=16000):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    y = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(y.tobytes())


def read_manifest(path=MANIFEST):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def append_manifest(row, path=MANIFEST):
    new = not os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def load_phrases(path=None):
    if not path:
        return list(PHRASES)
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]
