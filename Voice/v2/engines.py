"""
engines.py - loads the offline models (sherpa-onnx) and the TTS.

  VAD      Silero              finds where speech starts and stops
  STT      Moonshine tiny/base speech to text (no confidence score -> send 1.0)
  Speaker  WeSpeaker/TitaNet   voiceprint, compared to the enrolled supervisor
  TTS      Piper, else espeak-ng

Needs sherpa-onnx 1.x. Version 2.x changed the Piper setup and breaks TTS
("phoneme_codepoints is empty..."), so requirements.txt pins <2.
"""
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import wave

import numpy as np

try:
    import sherpa_onnx
except ImportError:
    sys.exit("sherpa-onnx is not installed. Run: pip install -r requirements.txt")

SR = 16000


def sherpa_version():
    return getattr(sherpa_onnx, "__version__", "?")


def _hits(models, pattern, want_dir):
    return sorted(p for p in glob.glob(os.path.join(models, pattern)) if os.path.isdir(p) == want_dir)


def _file(models, pattern, what):
    hits = _hits(models, pattern, False)
    if not hits:
        sys.exit(f"Missing {what} ({pattern}) in {models}. Run Voice/Voice/download_models.sh first.")
    return hits[0]


def _dir(models, pattern, what):
    hits = _hits(models, pattern, True)
    if not hits:
        sys.exit(f"Missing {what} ({pattern}) in {models}. Run Voice/Voice/download_models.sh first.")
    return hits[0]


# ---------------- VAD ----------------
def load_vad(cfg):
    c = sherpa_onnx.VadModelConfig()
    c.silero_vad.model = _file(cfg.MODELS_DIR, "silero_vad.onnx", "Silero VAD")
    c.silero_vad.threshold = float(cfg.VAD_THRESHOLD)
    c.silero_vad.min_silence_duration = float(cfg.VAD_END_SILENCE)
    c.silero_vad.min_speech_duration = float(cfg.VAD_MIN_SPEECH)
    try:
        c.silero_vad.max_speech_duration = float(cfg.VAD_MAX_SPEECH)
    except AttributeError:
        pass
    c.sample_rate = SR
    c.num_threads = 1
    vad = sherpa_onnx.VoiceActivityDetector(c, buffer_size_in_seconds=30)
    return vad, c.silero_vad.window_size


# ---------------- STT ----------------
def load_asr(cfg):
    pattern = f"sherpa-onnx-moonshine-{cfg.ASR_MODEL}*"
    hits = _hits(cfg.MODELS_DIR, pattern, True)
    if not hits:
        any_ = _hits(cfg.MODELS_DIR, "sherpa-onnx-moonshine-*", True)
        if not any_:
            sys.exit(f"No Moonshine model in {cfg.MODELS_DIR}. Run Voice/Voice/download_models.sh")
        print(f"  [stt] no '{cfg.ASR_MODEL}' model found, using {os.path.basename(any_[0])}")
        hits = any_
    mdir = hits[0]
    g = lambda p: _file(mdir, p, f"Moonshine {p}")
    asr = sherpa_onnx.OfflineRecognizer.from_moonshine(
        preprocessor=g("preprocess*.onnx"),
        encoder=g("encode*.onnx"),
        uncached_decoder=g("uncached_decode*.onnx"),
        cached_decoder=g("cached_decode*.onnx"),
        tokens=g("tokens.txt"),
        num_threads=int(cfg.ASR_THREADS),
    )
    return asr, os.path.basename(mdir)


def transcribe(asr, samples):
    s = asr.create_stream()
    s.accept_waveform(SR, samples)
    asr.decode_stream(s)
    return s.result.text.strip()


# ---------------- speaker ID ----------------
def load_speaker(cfg):
    model = _file(cfg.MODELS_DIR, "speaker_*.onnx", "speaker-ID model")
    c = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=model, num_threads=int(cfg.SPEAKER_THREADS))
    if not c.validate():
        sys.exit(f"Bad speaker model config: {model}")
    return sherpa_onnx.SpeakerEmbeddingExtractor(c)


def embed(extractor, samples):
    s = extractor.create_stream()
    s.accept_waveform(SR, samples)
    s.input_finished()
    e = np.array(extractor.compute(s), dtype=np.float32)
    return e / (np.linalg.norm(e) + 1e-9)


def load_supervisor(cfg):
    """(embedding, info) of the enrolled supervisor, or (None, None)."""
    npy = os.path.join(cfg.VOICES_DIR, "supervisor.npy")
    if not os.path.exists(npy):
        return None, None
    meta = os.path.join(cfg.VOICES_DIR, "supervisor.json")
    info = json.load(open(meta)) if os.path.exists(meta) else {}
    return np.load(npy), info


def cosine(a, b):
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))


def load_room(cfg):
    """'Room center': the average voiceprint of this mic + room, from other people's
    samples plus the supervisor's. Subtracting it removes what every voice recorded
    here has in common (mic, room), so only the voice itself is compared.
    Returns (center, n_room_samples) or (None, 0)."""
    room_p = os.path.join(cfg.VOICES_DIR, "room_samples.npy")
    if not os.path.exists(room_p):
        return None, 0
    room = np.load(room_p)
    sup_p = os.path.join(cfg.VOICES_DIR, "supervisor_samples.npy")
    sup_one = os.path.join(cfg.VOICES_DIR, "supervisor.npy")
    sup = np.load(sup_p) if os.path.exists(sup_p) else (np.load(sup_one)[None] if os.path.exists(sup_one) else None)
    allv = room if sup is None else np.concatenate([room, sup])
    return allv.mean(axis=0), len(room)


def speaker_score(emb, supervisor, center=None):
    """Cosine vs the supervisor, room-adjusted when a center is available."""
    if center is None:
        return cosine(emb, supervisor)
    return cosine(emb - center, supervisor - center)


# ---------------- TTS ----------------
class TTS:
    """Piper through sherpa-onnx if it actually produces audio, else espeak-ng, else silent."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.engine = "none"
        self.piper = None
        self.espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        want = (cfg.TTS_ENGINE or "auto").lower() if cfg.USE_TTS else "none"
        if want in ("auto", "piper"):
            try:
                self.piper = self._load_piper()
                x, sr = self._say_piper("ready")
                if len(x) and sr:
                    self.engine = "piper"
                else:
                    print("  [tts] Piper loaded but produced no audio "
                          "(sherpa-onnx 2.x? run: pip install 'sherpa-onnx<2')")
                    self.piper = None
            except SystemExit as e:
                print(f"  [tts] Piper unavailable: {e}")
            except Exception as e:
                print(f"  [tts] Piper failed: {e}")
        if self.engine == "none" and want in ("auto", "espeak"):
            if self.espeak:
                self.engine = "espeak"
            elif want != "none":
                print("  [tts] no espeak-ng either (sudo apt install espeak-ng). Announcements will be printed only.")

    def _load_piper(self):
        vdir = _dir(self.cfg.MODELS_DIR, "vits-piper-*", "Piper voice")
        c = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=_file(vdir, "*.onnx", "Piper .onnx"),
                    lexicon="",
                    tokens=_file(vdir, "tokens.txt", "Piper tokens"),
                    data_dir=_dir(vdir, "espeak-ng-data", "espeak-ng-data"),
                ),
                num_threads=2,
            ),
            max_num_sentences=2,
        )
        return sherpa_onnx.OfflineTts(c)

    def _say_piper(self, text):
        a = self.piper.generate(text, sid=0, speed=float(self.cfg.TTS_SPEED))
        return np.array(a.samples, dtype=np.float32), int(a.sample_rate)

    def _say_espeak(self, text):
        wpm = str(int(160 * float(self.cfg.TTS_SPEED)))
        out = subprocess.run([self.espeak, "-s", wpm, "--stdout", text],
                             capture_output=True, timeout=10).stdout
        with wave.open(io.BytesIO(out)) as w:
            sr, n = w.getframerate(), w.getnframes()
            x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        return x, sr

    def synth(self, text):
        """(samples, sample_rate). Empty array if nothing could be made."""
        try:
            if self.engine == "piper":
                x, sr = self._say_piper(text)
                if len(x):
                    return x, sr
                if self.espeak:
                    return self._say_espeak(text)
            elif self.engine == "espeak":
                return self._say_espeak(text)
        except Exception as e:
            print(f"  [tts] error: {e}")
        return np.zeros(0, np.float32), 0
