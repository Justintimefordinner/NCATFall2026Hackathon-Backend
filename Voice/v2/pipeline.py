"""
pipeline.py - the part of the voice chain that turns one speech segment into
a transcript plus a speaker score. The live client AND the test tools use this
same code, so a score from tools/score.py describes what the demo will do.

  segment -> loudness gate -> [speaker score || Moonshine STT] -> Result

Speaker scoring runs in parallel with STT, so it adds almost no latency.
Per the team doc, the speaker score never blocks anything here: tech commands
work for anyone, and the backend compares speaker_score to its own strict
threshold only for supervisor actions.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np

import engines as E
from audio_io import SR, HighPass, estimate_floor, normalize_level, rms


@dataclass
class Result:
    dur: float = 0.0
    level: float = 0.0
    floor: float = 0.0
    passed: bool = False
    reason: str = ""
    text: str = ""
    stt_ms: int = 0
    spk: float = None
    timings: dict = field(default_factory=dict)

    @property
    def snr(self):
        return self.level / max(self.floor, 1e-9)

    def head(self):
        return f"[{self.dur:.1f}s lvl {self.level:.4f} = {self.snr:.1f}x room]"

    def summary(self):
        if not self.passed:
            return f"{self.head()} DROPPED: {self.reason}"
        spk = "-" if self.spk is None else f"{self.spk:.2f}"
        return f'{self.head()} spk={spk} stt={self.stt_ms}ms  "{self.text}"'


class Pipeline:
    def __init__(self, cfg, asr, speaker=None, supervisor=None):
        self.cfg = cfg
        self.asr = asr
        self.speaker = speaker
        self.supervisor = supervisor
        self.pool = ThreadPoolExecutor(max_workers=1)

    def _score(self, seg):
        return E.cosine(E.embed(self.speaker, seg), self.supervisor)

    def process(self, seg, floor):
        c = self.cfg
        r = Result(dur=len(seg) / SR, level=rms(seg), floor=floor)
        if r.dur < c.MIN_SEGMENT_SEC:
            r.reason = f"too short ({r.dur:.2f}s)"
            return r
        if c.USE_GATE:
            if r.level < floor * c.GATE_SNR:
                r.reason = f"too quiet vs room (needs {c.GATE_SNR}x)"
                return r
            if r.level < c.GATE_MIN_RMS:
                r.reason = f"too quiet (below {c.GATE_MIN_RMS})"
                return r

        fut = None
        if c.USE_SPEAKER_ID and self.speaker is not None and self.supervisor is not None:
            fut = self.pool.submit(self._score, seg)

        t0 = time.perf_counter()
        text = E.transcribe(self.asr, normalize_level(seg))
        r.stt_ms = int((time.perf_counter() - t0) * 1000)
        if fut is not None:
            try:
                r.spk = round(fut.result(timeout=2), 3)
            except Exception:
                r.spk = None
        r.timings["after_stt_ms"] = int((time.perf_counter() - t0) * 1000)

        if not text.strip(" .,!?-"):
            r.reason = "no words"
            return r
        r.text = text
        r.passed = True
        return r


# ---------------- offline (test tools) ----------------
def segments_from_clip(cfg, samples, vad=None, window=512):
    """Same front end as live: high-pass, then VAD. Returns (segments, floor)."""
    x = np.asarray(samples, dtype=np.float32)
    if cfg.USE_HIGHPASS:
        x = HighPass(fc=cfg.HIGHPASS_HZ)(x)
    floor = max(estimate_floor(x), cfg.NOISE_FLOOR_MIN)
    if not cfg.USE_VAD or vad is None:
        return [x], floor
    if hasattr(vad, "reset"):
        vad.reset()
    padded = np.concatenate([x, np.zeros(int(SR * (cfg.VAD_END_SILENCE + 0.6)), np.float32)])
    segs = []
    for i in range(0, len(padded) - window + 1, window):
        vad.accept_waveform(padded[i:i + window])
        while not vad.empty():
            segs.append(np.array(vad.front.samples, dtype=np.float32))
            vad.pop()
    if hasattr(vad, "flush"):
        vad.flush()
        while not vad.empty():
            segs.append(np.array(vad.front.samples, dtype=np.float32))
            vad.pop()
    return segs, floor
