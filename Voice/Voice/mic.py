"""mic.py - USB mic input that always hands back 16 kHz mono float32 chunks."""
import queue

import numpy as np
import sounddevice as sd

from models import SR, resample


class Mic:
    def __init__(self, device=None, chunk_sec=0.1):
        self.q = queue.Queue()
        self.device = device
        rate = SR
        try:
            sd.check_input_settings(device=device, channels=1, samplerate=SR, dtype="float32")
        except Exception:
            # many cheap USB mics only do 44.1k/48k -> capture native and resample
            rate = int(sd.query_devices(device, "input")["default_samplerate"])
        self.rate = rate
        self.stream = sd.InputStream(device=device, channels=1, samplerate=rate, dtype="float32",
                                     blocksize=int(rate * chunk_sec), callback=self._cb)

    def _cb(self, indata, frames, t, status):
        self.q.put(indata[:, 0].copy())

    def start(self):
        self.stream.start()
        return self

    def read(self, timeout=1.0):
        x = self.q.get(timeout=timeout)
        return resample(x, self.rate, SR)

    def drain(self):
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break

    def record(self, seconds):
        self.drain()
        out, need = [], int(seconds * SR)
        while sum(len(c) for c in out) < need:
            out.append(self.read())
        return np.concatenate(out)[:need]

    def stop(self):
        self.stream.stop()
        self.stream.close()


def list_devices():
    print(sd.query_devices())
