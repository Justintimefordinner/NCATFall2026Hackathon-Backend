"""
models.py - loads the offline sherpa-onnx models and shared audio helpers.

  ASR      : Moonshine tiny (int8)       -> speech to text
  VAD      : Silero VAD                  -> finds where speech starts/stops
  Speaker  : WeSpeaker ResNet34 / TitaNet -> voice fingerprint (who is talking)
  TTS      : Piper (en_US amy low)       -> bench talks back (see tts.py)
"""
import glob
import json
import os
import sys

import numpy as np

try:
    import sherpa_onnx
except ImportError:
    sys.exit("sherpa-onnx is not installed. Run: pip install -r requirements.txt")

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")
VOICES = os.path.join(HERE, "voices")
SR = 16000
THREADS = 2


def _one(pattern, what):
    hits = sorted(glob.glob(os.path.join(MODELS, pattern), recursive=True))
    if not hits:
        sys.exit(f"Missing {what} ({pattern}) in {MODELS}. Run ./download_models.sh first.")
    return hits[0]


def load_vad(threshold=0.5):
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = _one("silero_vad.onnx", "VAD model")
    cfg.silero_vad.threshold = threshold          # higher = less sensitive to noise
    cfg.silero_vad.min_silence_duration = 0.35    # end of utterance after 350 ms quiet
    cfg.silero_vad.min_speech_duration = 0.25     # ignore clicks / bangs shorter than this
    try:
        cfg.silero_vad.max_speech_duration = 8.0  # commands are short; cut off long chatter
    except AttributeError:
        pass
    cfg.sample_rate = SR
    cfg.num_threads = 1
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=30)
    return vad, cfg.silero_vad.window_size


def _dir(pattern, what):
    hits = sorted(p for p in glob.glob(os.path.join(MODELS, pattern)) if os.path.isdir(p))
    if not hits:
        sys.exit(f"Missing {what} ({pattern}) in {MODELS}. Run ./download_models.sh first.")
    return hits[0]


def load_asr():
    mdir = _dir("sherpa-onnx-moonshine-*", "Moonshine model dir")
    g = lambda p: _one(os.path.join(os.path.basename(mdir), p), f"Moonshine {p}")
    return sherpa_onnx.OfflineRecognizer.from_moonshine(
        preprocessor=g("preprocess*.onnx"),
        encoder=g("encode*.onnx"),
        uncached_decoder=g("uncached_decode*.onnx"),
        cached_decoder=g("cached_decode*.onnx"),
        tokens=g("tokens.txt"),
        num_threads=THREADS,
    )


def transcribe(asr, samples):
    s = asr.create_stream()
    s.accept_waveform(SR, samples)
    asr.decode_stream(s)
    return s.result.text.strip()


def load_speaker():
    model = _one("speaker_*.onnx", "speaker-ID model")
    cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=model, num_threads=THREADS)
    if not cfg.validate():
        sys.exit(f"Bad speaker model config: {model}")
    return sherpa_onnx.SpeakerEmbeddingExtractor(cfg)


def embed(extractor, samples):
    s = extractor.create_stream()
    s.accept_waveform(SR, samples)
    s.input_finished()
    e = np.array(extractor.compute(s), dtype=np.float32)
    return e / (np.linalg.norm(e) + 1e-9)


def tts_voice_name(voice=None):
    """Which Piper voice load_tts() will use, e.g. 'en_US-amy-low'."""
    return os.path.basename(_tts_dir(voice))[len("vits-piper-"):]


def _tts_dir(voice=None):
    # pick a voice with --voice or PIPER_VOICE (e.g. en_US-amy-medium); default: amy-low if present
    voice = voice or os.environ.get("PIPER_VOICE")
    if voice:
        return _dir(f"vits-piper-{voice}*", f"Piper voice {voice}")
    default = os.path.join(MODELS, "vits-piper-en_US-amy-low")
    return default if os.path.isdir(default) else _dir("vits-piper-*", "Piper voice dir")


def load_tts(voice=None):
    vdir = _tts_dir(voice)
    base = os.path.basename(vdir)
    onnx = [p for p in glob.glob(os.path.join(vdir, "*.onnx"))]
    if not onnx:
        sys.exit(f"No .onnx in {vdir}")
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=onnx[0],
                lexicon="",
                tokens=_one(os.path.join(base, "tokens.txt"), "Piper tokens"),
                data_dir=_one(os.path.join(base, "espeak-ng-data"), "espeak-ng-data"),
            ),
            num_threads=THREADS,
        ),
        max_num_sentences=2,
    )
    return sherpa_onnx.OfflineTts(cfg)


# ---------- enrolled voices ----------

def load_voices():
    """Returns {name: (embedding, role)}."""
    roles_path = os.path.join(VOICES, "roles.json")
    roles = json.load(open(roles_path)) if os.path.exists(roles_path) else {}
    out = {}
    for f in glob.glob(os.path.join(VOICES, "*.npy")):
        name = os.path.splitext(os.path.basename(f))[0]
        out[name] = (np.load(f), roles.get(name, "operator"))
    return out


def identify(emb, voices, threshold, margin=0.05):
    """Cosine match against enrolled voices. Returns (name|None, best_score)."""
    if not voices:
        return None, 0.0
    scores = sorted(((float(np.dot(emb, v[0])), n) for n, v in voices.items()), reverse=True)
    best, name = scores[0]
    second = scores[1][0] if len(scores) > 1 else -1.0
    if best >= threshold and (best - second) >= margin:
        return name, round(best, 3)
    return None, round(best, 3)


# ---------- audio helpers ----------

def resample(x, sr_in, sr_out=SR):
    if sr_in == sr_out:
        return x.astype(np.float32)
    n = int(round(len(x) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


class HighPass:
    """~120 Hz high-pass to cut motor hum / fan rumble. Uses scipy if present."""
    def __init__(self, sr=SR, fc=120.0):
        self.ok = False
        try:
            from scipy.signal import butter, lfilter_zi, lfilter
            self.b, self.a = butter(2, fc / (sr / 2), btype="high")
            self.zi = lfilter_zi(self.b, self.a) * 0.0
            self.lfilter = lfilter
            self.ok = True
        except Exception:
            pass

    def __call__(self, x):
        if not self.ok:
            return x - np.mean(x)
        y, self.zi = self.lfilter(self.b, self.a, x, zi=self.zi)
        return y.astype(np.float32)


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-12))


def normalize_level(x, target_rms=0.08):
    r = rms(x)
    if r < 1e-5:
        return x
    y = x * (target_rms / r)
    return np.clip(y, -1.0, 1.0).astype(np.float32)
