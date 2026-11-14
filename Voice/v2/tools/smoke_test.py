"""
Test plan step 1 - smoke test: Moonshine ALONE on the Pi (no filters).
Pass: it runs and returns in under about 500 ms.

  python tools/smoke_test.py                       # records 3 s from the mic
  python tools/smoke_test.py some.wav other.wav    # or uses WAV files
  python tools/smoke_test.py --testset             # every WAV in testset/

Stop the voice service first if you use the mic: sudo systemctl stop mes-voice
"""
import argparse
import os
import statistics
import sys
import time

from common import TESTSET, read_manifest, read_wav  # noqa: E402  (sets sys.path)
import engines as E
import vconfig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wavs", nargs="*")
    ap.add_argument("--testset", action="store_true")
    ap.add_argument("--device")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()
    cfg = vconfig.load(a.set)

    print(f"sherpa-onnx {E.sherpa_version()}")
    t = time.perf_counter()
    asr, name = E.load_asr(cfg)
    print(f"Loaded {name} in {time.perf_counter() - t:.1f}s")

    clips = []
    if a.testset:
        clips = [(r["expected"], read_wav(os.path.join(TESTSET, r["file"]))) for r in read_manifest()]
    for p in a.wavs:
        clips.append((os.path.basename(p), read_wav(p)))
    if not clips:
        from audio_io import Mic
        mic = Mic(a.device if a.device is not None else cfg.MIC_DEVICE)
        input(f"Mic: {mic.name}. Press Enter, then say 'step three done'... ")
        clips = [("mic", mic.record(a.seconds))]
        mic.close()

    warm = []
    for label, x in clips:
        times = []
        for _ in range(3):
            t = time.perf_counter()
            text = E.transcribe(asr, x)
            times.append((time.perf_counter() - t) * 1000)
        warm.append(statistics.median(times[1:]))
        print(f"  {label:<28} {len(x)/16000:4.1f}s audio  first {times[0]:5.0f} ms  warm {warm[-1]:5.0f} ms  \"{text}\"")

    med = statistics.median(warm)
    verdict = "PASS" if med < 500 else "FAIL (try fewer threads elsewhere, or check CPU load with top)"
    print(f"\nMedian warm time: {med:.0f} ms -> {verdict}")
    sys.exit(0 if med < 500 else 1)


if __name__ == "__main__":
    main()
