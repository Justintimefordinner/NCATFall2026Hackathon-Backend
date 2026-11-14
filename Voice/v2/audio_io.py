"""
audio_io.py - microphone, speaker and small audio helpers.

Fixes from the first voice project:
  * Mic auto-pick: if no device is given (or the default can't record), use the
    first device that actually has inputs, preferring USB. No more silently
    "listening" to an HDMI output.
  * Clear error when the mic is busy (another program has it open, so it
    disappears from the device list).
  * Mic recovers if the USB stream dies.
  * Playback is resampled to whatever rate the speaker accepts, so TTS never
    fails with "Invalid sample rate".
"""
import queue
import time

import numpy as np
import sounddevice as sd

SR = 16000


# ---------------- helpers ----------------
def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-12)) if len(x) else 0.0


def resample(x, sr_in, sr_out=SR):
    x = np.asarray(x, dtype=np.float32)
    if sr_in == sr_out or len(x) == 0:
        return x
    n = int(round(len(x) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def normalize_level(x, target_rms=0.08):
    """Even out loud/quiet speakers before STT."""
    r = rms(x)
    if r < 1e-5:
        return x
    return np.clip(x * (target_rms / r), -1.0, 1.0).astype(np.float32)


def estimate_floor(x, frame=1600):
    """Noise floor of a clip: median level of its quietest 20 % of frames."""
    n = len(x) // frame
    if n < 2:
        return rms(x)
    lv = np.sqrt((x[: n * frame].reshape(n, frame) ** 2).mean(axis=1))
    lv.sort()
    return float(np.median(lv[: max(1, n // 5)]))


class HighPass:
    """~120 Hz high-pass. Uses scipy if present, else just removes DC."""
    def __init__(self, sr=SR, fc=120.0):
        self.ok = False
        try:
            from scipy.signal import butter, lfilter, lfilter_zi
            self.b, self.a = butter(2, fc / (sr / 2), btype="high")
            self._zi0 = lfilter_zi(self.b, self.a) * 0.0
            self.zi = self._zi0.copy()
            self.lfilter = lfilter
            self.ok = True
        except Exception:
            pass

    def reset(self):
        if self.ok:
            self.zi = self._zi0.copy()

    def __call__(self, x):
        if not self.ok:
            return (x - np.mean(x)).astype(np.float32)
        y, self.zi = self.lfilter(self.b, self.a, x, zi=self.zi)
        return y.astype(np.float32)


# ---------------- device selection ----------------
def list_devices():
    print(sd.query_devices())
    print("\nUse a NAME PIECE, e.g. --device fifine  (numbers can change between boots)")


def _match(device, kind):
    devs = sd.query_devices()
    key = "max_input_channels" if kind == "input" else "max_output_channels"
    if isinstance(device, int) or str(device).isdigit():
        i = int(device)
        if 0 <= i < len(devs) and devs[i][key] > 0:
            return i
        raise RuntimeError(f"Device {i} has no {kind}.")
    want = str(device).lower()
    for i, d in enumerate(devs):
        if d[key] > 0 and want in d["name"].lower():
            return i
    hint = (" If it's plugged in, another program probably has it open "
            "(e.g. the mes-voice service: sudo systemctl stop mes-voice).") if kind == "input" else ""
    raise RuntimeError(f"No {kind} device matching {device!r}.{hint}")


def pick_input(device=None):
    if device not in (None, ""):
        return _match(device, "input")
    devs = sd.query_devices()
    try:
        d = sd.default.device[0]
        if d is not None and d >= 0 and devs[d]["max_input_channels"] > 0:
            return d
    except Exception:
        pass
    inputs = [i for i, d in enumerate(devs) if d["max_input_channels"] > 0]
    if not inputs:
        raise RuntimeError("No microphone found. Plug in the USB mic (run with --devices to check).")
    usb = [i for i in inputs if "usb" in devs[i]["name"].lower()]
    return (usb or inputs)[0]


def pick_output(device=None):
    return None if device in (None, "") else _match(device, "output")


# ---------------- microphone ----------------
class AntiAlias:
    """Low-pass at 7.2 kHz before dropping a 44.1/48 kHz mic to 16 kHz. Without it, hiss and
    fan noise above 8 kHz fold down into the speech band and hurt Moonshine. Keeps filter state
    across chunks so there are no clicks at chunk edges. No-op without scipy or at 16 kHz."""

    def __init__(self, rate, cutoff=7200.0):
        self.sos = None
        if rate <= SR:
            return
        try:
            from scipy.signal import butter, sosfilt, sosfilt_zi
            self.sos = butter(8, cutoff / (rate / 2), btype="low", output="sos")
            self.zi = sosfilt_zi(self.sos) * 0.0
            self.sosfilt = sosfilt
        except Exception:
            self.sos = None

    def __call__(self, x):
        if self.sos is None:
            return x
        y, self.zi = self.sosfilt(self.sos, x, zi=self.zi)
        return y.astype(np.float32)


class Mic:
    """16 kHz mono float32 chunks, whatever rate the hardware really runs at."""

    def __init__(self, device=None, chunk_sec=0.1):
        self.index = pick_input(device)
        self.name = sd.query_devices(self.index)["name"]
        self.chunk_sec = chunk_sec
        self.q = queue.Queue(maxsize=200)
        self.stream = None
        self._open()

    def _open(self):
        rate = SR
        try:
            sd.check_input_settings(device=self.index, channels=1, samplerate=SR, dtype="float32")
        except Exception:
            rate = int(sd.query_devices(self.index, "input")["default_samplerate"])
        self.rate = rate
        self.aa = AntiAlias(rate)
        self.stream = sd.InputStream(device=self.index, channels=1, samplerate=rate, dtype="float32",
                                     blocksize=int(rate * self.chunk_sec), callback=self._cb)
        self.stream.start()
        self.last_chunk = time.time()

    def _cb(self, indata, frames, t, status):
        try:
            self.q.put_nowait(indata[:, 0].copy())
        except queue.Full:
            pass  # we're behind; dropping old audio beats growing latency

    def read(self, timeout=1.0):
        try:
            x = self.q.get(timeout=timeout)
        except queue.Empty:
            if time.time() - self.last_chunk > 3:
                self._recover()
            raise
        self.last_chunk = time.time()
        return resample(self.aa(x), self.rate, SR)

    def _recover(self):
        print("  [mic] no audio for 3 s, reopening the mic...")
        try:
            self.stream.close()
        except Exception:
            pass
        try:
            self._open()
            print(f"  [mic] reopened: {self.name}")
        except Exception as e:
            print(f"  [mic] reopen failed: {e}")
            self.last_chunk = time.time()  # try again in 3 s

    def drain(self):
        while True:
            try:
                self.q.get_nowait()
            except queue.Empty:
                return

    def record(self, seconds):
        self.drain()
        out, need = [], int(seconds * SR)
        while sum(len(c) for c in out) < need:
            try:
                out.append(self.read())
            except queue.Empty:
                continue
        return np.concatenate(out)[:need]

    def close(self):
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass


# ---------------- speaker ----------------
class Player:
    def __init__(self, device=None):
        self.index = pick_output(device)
        info = sd.query_devices(self.index, "output") if self.index is not None else sd.query_devices(kind="output")
        self.name = info["name"]
        self.rate = int(info["default_samplerate"]) or 48000

    def play(self, samples, sr):
        """Blocking. Resamples to the speaker's own rate."""
        if samples is None or len(samples) == 0 or not sr:
            return False
        x = resample(np.asarray(samples, dtype=np.float32), sr, self.rate)
        sd.play(x, self.rate, device=self.index, blocking=True)
        return True
