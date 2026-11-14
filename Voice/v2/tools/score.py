"""
Test plan steps 3 and 4 - scoring script.

Plays every recorded clip through the SAME pipeline the live client uses
(high-pass -> VAD -> gate -> Moonshine, plus speaker score), then through the
backend's own parser, and checks the command matches what was supposed to be said.
Targets from the doc: 95 % of commands correct in noise, under 1 s end to end.

  python tools/score.py                          # current vconfig settings
  python tools/score.py --ablate                 # step 4: add stages one at a time
  python tools/score.py --set VAD_THRESHOLD=0.6  # try a change, compare
  python tools/score.py --condition noise --show-all

"Correct" = the backend parser turns what Moonshine heard into the same command
(intent + step number) as the phrase the speaker was reading. If the parser
can't be imported, it falls back to comparing words (marked in the output).
A "parser gap" means the parser doesn't understand the INTENDED phrase either:
add it to PHRASES / NUMBER_WORDS in Backend/parser.py.
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys
import time
from difflib import SequenceMatcher

from common import TESTSET, V2, read_manifest, read_wav  # noqa: E402
import engines as E
import vconfig
from pipeline import Pipeline, segments_from_clip

ABLATION = [
    ("Moonshine alone", dict(USE_HIGHPASS=False, USE_VAD=False, USE_GATE=False, USE_SPEAKER_ID=False)),
    ("+ high-pass", dict(USE_HIGHPASS=True, USE_VAD=False, USE_GATE=False, USE_SPEAKER_ID=False)),
    ("+ VAD", dict(USE_HIGHPASS=True, USE_VAD=True, USE_GATE=False, USE_SPEAKER_ID=False)),
    ("+ loudness gate", dict(USE_HIGHPASS=True, USE_VAD=True, USE_GATE=True, USE_SPEAKER_ID=False)),
    ("+ speaker score", dict(USE_HIGHPASS=True, USE_VAD=True, USE_GATE=True, USE_SPEAKER_ID=True)),
]


# ---------------- matching ----------------
class Matcher:
    def __init__(self, backend_dir):
        self.parse = None
        self.unknown = None
        try:
            sys.path.insert(0, backend_dir)
            import parser as P  # Backend/parser.py
            self.parse = P.parse
            self.unknown = self.key("xyzzy plugh frobnicate")
            print(f"Using the backend parser: {os.path.join(backend_dir, 'parser.py')}")
        except Exception as e:
            print(f"!! Backend parser not usable ({e}). Falling back to word matching.")

    def key(self, text):
        cmd = self.parse(text, 1.0, "voice")
        intent = None
        for attr in ("intent", "kind", "name", "type", "action"):
            if hasattr(cmd, attr):
                intent = getattr(cmd, attr)
                break
        if intent is None and isinstance(cmd, (tuple, list)) and cmd:
            intent = cmd[0]
        args = getattr(cmd, "args", None) or {}
        return f"{intent} {json.dumps(args, sort_keys=True, default=str)}"

    @staticmethod
    def norm(s):
        return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()

    def judge(self, expected, heard):
        """(correct, note)."""
        if not heard:
            return False, ""
        if self.parse:
            want = self.key(expected)
            if want == self.unknown:
                return False, "parser gap"
            return self.key(heard) == want, ""
        ok = SequenceMatcher(None, self.norm(expected), self.norm(heard)).ratio() >= 0.85
        return ok, "word match"


# ---------------- one run ----------------
def run(cfg, rows, matcher, label=""):
    asr, asr_name = E.load_asr(cfg)
    vad, window = E.load_vad(cfg) if cfg.USE_VAD else (None, 512)
    speaker = sup = center = None
    if cfg.USE_SPEAKER_ID:
        sup, _ = E.load_supervisor(cfg)
        speaker = E.load_speaker(cfg) if sup is not None else None
        if sup is not None and cfg.USE_ROOM_ADJUST:
            center, _ = E.load_room(cfg)
    pipe = Pipeline(cfg, asr, speaker, sup, center)

    results = []
    for i, row in enumerate(rows, 1):
        x = read_wav(os.path.join(TESTSET, row["file"]))
        t0 = time.perf_counter()
        segs, floor = segments_from_clip(cfg, x, vad, window)
        heard, reasons, proc_ms = [], [], 0
        for seg in segs:
            r = pipe.process(seg, floor)
            proc_ms += r.timings.get("after_stt_ms", 0)
            if r.passed:
                heard.append(r.text)
            elif r.reason:
                reasons.append(r.reason)
        text = " ".join(heard).strip()
        ok, note = matcher.judge(row["expected"], text)
        if not text:
            note = "; ".join(reasons) or "VAD found no speech"
        latency = proc_ms + (cfg.VAD_END_SILENCE * 1000 if cfg.USE_VAD else 0)
        results.append(dict(row, heard=text, correct=ok, note=note, latency_ms=int(latency),
                            wall_ms=int((time.perf_counter() - t0) * 1000)))
        print(f"\r  {label} {i}/{len(rows)}", end="", flush=True)
    print("\r" + " " * 60 + "\r", end="")
    return results, asr_name


def pct(rs):
    return 100.0 * sum(r["correct"] for r in rs) / len(rs) if rs else 0.0


def p95(v):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))] if v else 0


def report(results, asr_name, cfg, show_all=False):
    lat = [r["latency_ms"] for r in results if r["heard"]]
    print(f"\nModel {asr_name} | stages: {vconfig.stages(cfg)}")
    print(f"Overall: {pct(results):.1f}% correct ({sum(r['correct'] for r in results)}/{len(results)})")
    for key in ("condition", "speaker"):
        groups = sorted({r[key] for r in results})
        line = "  ".join(f"{g}: {pct([r for r in results if r[key] == g]):.1f}%" for g in groups)
        print(f"  by {key:<9} {line}")
    if lat:
        print(f"Latency end of speech -> transcript ready: mean {statistics.mean(lat):.0f} ms, p95 {p95(lat)} ms"
              " (live client also measures the spoken reply)")
    noise = [r for r in results if r["condition"].lower().startswith("noise")]
    target_rows = noise or results
    acc_ok = pct(target_rows) >= 95
    lat_ok = (p95(lat) if lat else 0) < 1000
    print(f"Targets: {'PASS' if acc_ok else 'FAIL'} 95% in {'noise' if noise else 'all clips (no noise set yet)'}"
          f", {'PASS' if lat_ok else 'FAIL'} under 1 s")

    bad = [r for r in results if not r["correct"]]
    gaps = sorted({r["expected"] for r in bad if r["note"] == "parser gap"})
    if gaps:
        print(f"\nParser gaps (parser doesn't know the intended phrase - add to Backend/parser.py): {', '.join(gaps)}")
    shown = results if show_all else bad
    if shown:
        print(f"\n{'expected':<26} {'heard':<34} {'cond':<6} {'who':<8} note")
        for r in shown:
            mark = "" if r["correct"] else "x "
            print(f"{mark}{r['expected']:<26} {r['heard'][:34]:<34} {r['condition'][:6]:<6} {r['speaker'][:8]:<8} {r['note']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ablate", action="store_true", help="run each stage combination (test plan step 4)")
    ap.add_argument("--condition", help="only this condition (clean / noise)")
    ap.add_argument("--speaker", help="only this speaker")
    ap.add_argument("--backend", default=os.path.join(V2, "..", "..", "Backend"))
    ap.add_argument("--show-all", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()

    rows = list({r["file"]: r for r in read_manifest()}.values())  # re-recorded clips: last one wins
    rows = [r for r in rows if os.path.exists(os.path.join(TESTSET, r["file"]))]
    if a.condition:
        rows = [r for r in rows if r["condition"] == a.condition]
    if a.speaker:
        rows = [r for r in rows if r["speaker"] == a.speaker]
    if not rows:
        sys.exit("No test clips. Record some: python tools/record_testset.py --speaker <name> --condition clean")
    print(f"{len(rows)} clips")
    matcher = Matcher(os.path.abspath(a.backend))

    if a.ablate:
        table = []
        for name, over in ABLATION:
            sets = list(a.set) + [f"{k}={v}" for k, v in over.items()]
            cfg = vconfig.load(sets)
            res, _ = run(cfg, rows, matcher, name)
            noise = [r for r in res if r["condition"].lower().startswith("noise")]
            lat = [r["latency_ms"] for r in res if r["heard"]]
            table.append((name, pct(res), pct(noise) if noise else None, p95(lat)))
        print(f"\n{'stages':<18} {'all':>7} {'noise':>7} {'p95 ms':>8}")
        prev = None
        for name, acc, nacc, l95 in table:
            n = f"{nacc:6.1f}%" if nacc is not None else "    -  "
            verdict = ""
            if prev is not None:
                verdict = "  keep" if acc >= prev - 0.5 else "  <- made it worse, consider turning off"
            print(f"{name:<18} {acc:6.1f}% {n} {l95:8d}{verdict}")
            prev = acc
        print("\nDoc rule: keep a stage only if accuracy holds or improves.")
        return

    cfg = vconfig.load(a.set)
    results, asr_name = run(cfg, rows, matcher)
    report(results, asr_name, cfg, a.show_all)
    out = os.path.join(V2, "logs", time.strftime("score-%Y%m%d-%H%M%S.csv"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
