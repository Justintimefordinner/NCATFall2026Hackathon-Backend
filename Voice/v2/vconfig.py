"""
vconfig.py - every voice setting in ONE place.

Risk plan: "Tune all thresholds together in the demo room with noise playing;
keep them in one config file" and "Every stage has an on/off switch in config
so a bad stage can be cut in seconds."

Three ways to change a value (later wins):
  1. Edit the defaults below.
  2. Put overrides in voice_config.json next to this file, e.g.
        {"VAD_THRESHOLD": 0.6, "USE_GATE": false}
  3. On the command line:  python client.py --set GATE_SNR=3 --set USE_GATE=false
"""
import json
import os
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- backend ----------------
BACKEND = "localhost:5000"     # Flask host:port. 10.42.0.1:5000 if voice runs on another device.

# ---------------- stage switches ----------------
USE_HIGHPASS = True            # 120 Hz high-pass (machine rumble, mains hum)
USE_VAD = True                 # Silero VAD: STT only ever sees speech
USE_GATE = True                # loudness gate: drops far-away talkers
USE_SPEAKER_ID = True          # scores the voice vs the enrolled SUPERVISOR. Never blocks tech commands.
USE_ROOM_ADJUST = True         # subtract the room/mic "center" (enroll.py --room) before scoring
USE_TTS = True                 # speak backend announcements
USE_ECHO_FILTER = True         # drop transcripts that repeat what the bench just said

# ---------------- audio devices ----------------
MIC_DEVICE = None              # name piece ("fifine") or index. None = auto-pick a mic.
SPEAKER_DEVICE = None          # name piece or index. None = system default output.
HIGHPASS_HZ = 120.0

# ---------------- VAD (Silero) ----------------
VAD_THRESHOLD = 0.5            # 0-1, higher = needs clearer speech (raise in loud rooms)
VAD_END_SILENCE = 0.35         # seconds of quiet that ends a command (doc: tune 0.30-0.50)
VAD_MIN_SPEECH = 0.25          # ignore bangs/clicks shorter than this
VAD_MAX_SPEECH = 6.0           # commands are short; cut off long chatter

# ---------------- loudness gate ----------------
GATE_SNR = 2.5                 # speech must be this many x louder than the room
GATE_MIN_RMS = 0.004           # and at least this loud in absolute terms
NOISE_FLOOR_START = 0.005      # starting guess; adapts while nobody is talking
NOISE_FLOOR_MIN = 0.001        # floor can't drop below this (a dead-quiet mic won't make the gate meaningless)
MIN_SEGMENT_SEC = 0.3

# ---------------- STT (Moonshine via sherpa-onnx) ----------------
ASR_MODEL = "tiny"             # "tiny" (fast) or "base" (more accurate, slower). See get_base_model.sh
ASR_THREADS = 2
CONFIDENCE = 1.0               # Moonshine gives no score -> send 1.0, backend's fuzzy threshold decides

# ---------------- speaker ID ----------------
SPEAKER_THREADS = 1

# ---------------- TTS ----------------
TTS_ENGINE = "auto"            # "auto" (Piper, else espeak-ng), "piper", "espeak", "none"
TTS_SPEED = 1.1
TTS_TAIL = 0.4                 # keep the mic muted this long after the bench stops talking
TTS_VOICE = None               # Piper voice, e.g. "en_US-lessac-medium". None = amy-low
TTS_LEAD_IN = 0.3              # silence before speech after idle (Bluetooth speaker wake-up)
TTS_PLAYER = "sounddevice"     # or "aplay" (then SPEAKER_DEVICE is an ALSA name like plughw:2,0)
TTS_PRERENDER = True           # cache common phrases at startup (Voice/Voice/tts_cache)
GREETING = "MES activated"     # said once when ready; "" to turn off
ECHO_WINDOW = 1.5              # seconds after the bench stops talking during which echoes are checked
ECHO_SIMILARITY = 0.8          # real echoes score 0.84+; "step three done" vs "step three signed off" is 0.72

# ---------------- paths ----------------
MODELS_DIR = os.path.join(HERE, "..", "Voice", "models")   # reuses Adan's downloaded models
VOICES_DIR = os.path.join(HERE, "voices")                  # supervisor voiceprint (git-ignored)
LOG_DIR = os.path.join(HERE, "logs")
OVERRIDES_FILE = os.path.join(HERE, "voice_config.json")


def _parse(value, current):
    v = value.strip()
    low = v.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("none", "null", ""):
        return None
    if isinstance(current, bool):
        return low == "1"
    for conv in (int, float):
        try:
            return conv(v)
        except ValueError:
            pass
    return v


def load(sets=()):
    """Defaults <- voice_config.json <- --set KEY=VALUE. Returns a namespace."""
    cfg = {k: v for k, v in globals().items() if k.isupper()}
    if os.path.exists(OVERRIDES_FILE):
        with open(OVERRIDES_FILE) as f:
            for k, v in json.load(f).items():
                if k not in cfg:
                    print(f"  [config] unknown key in voice_config.json: {k}")
                cfg[k] = v
    for s in sets or ():
        if "=" not in s:
            raise SystemExit(f"--set needs KEY=VALUE, got {s!r}")
        k, v = s.split("=", 1)
        k = k.strip().upper()
        if k not in cfg:
            print(f"  [config] unknown key: {k}")
        cfg[k] = _parse(v, cfg.get(k))
    for k in ("MODELS_DIR", "VOICES_DIR", "LOG_DIR"):
        cfg[k] = os.path.abspath(os.path.expanduser(cfg[k]))
    return SimpleNamespace(**cfg)


def stages(cfg):
    """One-line summary for logs."""
    names = [("highpass", cfg.USE_HIGHPASS), ("vad", cfg.USE_VAD), ("gate", cfg.USE_GATE),
             ("speaker", cfg.USE_SPEAKER_ID), ("tts", cfg.USE_TTS), ("echo", cfg.USE_ECHO_FILTER)]
    return " ".join(f"{n}={'on' if on else 'OFF'}" for n, on in names)
