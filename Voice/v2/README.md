# Voice v2 — voice process for the Voice MES Assistant

Rebuilt from the team doc's **Voice pipeline**, **Integrating voice with the backend**,
**Supervisor voice confirmation**, **Moonshine risk plan** and **Test plan** sections.
It reuses the models and Python environment from `Voice/Voice/` (Adan's v1), so nothing new to download.

```
USB mic ─► 120 Hz high-pass ─► Silero VAD ─► loudness gate ─► [speaker score ‖ Moonshine STT] ─► POST /api/command
USB speaker ◄── Voice/Voice/tts.py ◄── {"type":"announce", "priority"} on ws /ws/ui
```

**Speech output is shared with v1:** `client.py` uses `Voice/Voice/tts.py` (Piper with an espeak-ng
fallback, a WAV cache with pre-rendered phrases, a priority queue where quality alerts chime and interrupt,
and an "MES activated" greeting). Settings: `TTS_VOICE`, `TTS_SPEED`, `TTS_TAIL`, `TTS_LEAD_IN`,
`TTS_PLAYER`, `TTS_PRERENDER`, `GREETING` in `vconfig.py`. `engines.TTS` is no longer used by the client.

## What changed from v1, and why

| v1 | v2 | Doc section |
|---|---|---|
| Only enrolled voices were transcribed; everyone else was dropped | **Anyone** can give tech commands. Speaker ID only produces `speaker_score` vs the enrolled **supervisor**; the backend decides | Supervisor voice confirmation: "Tech commands work for anyone, so a judge can still try the system" |
| Enrolled 2 people, one short sample each | Enrolls **only the supervisor**, 4+ samples, speech-only (VAD-trimmed), with a consistency check and a live `--test` to pick the threshold | "Enroll one teammate as the supervisor: several samples, in the demo room" |
| Speaker ID ran before STT (added latency) | Runs **in parallel** with Moonshine | Latency target under 1 s |
| Settings spread across flags and code | **One config file** (`vconfig.py`, optional `voice_config.json`), every stage has an on/off switch | Risk plan: "keep them in one config file", "every stage has an on/off switch" |
| Dropped segments were mostly silent | **Every segment and gate decision logged** with its level, plus a JSON log in `logs/` | Risk plan: "Silent drops" |
| No latency measurement | Prints **end of speech → spoken reply** for every command | Risk plan: "Latency stacks up past about 1 s" |
| TTS failed on sherpa-onnx 2.x and on speakers that reject 16 kHz | Pins sherpa-onnx `<2`, checks Piper at startup, **falls back to espeak-ng**, resamples to the speaker's rate | TTS engine still open |
| Picked the default device even if it had no mic | **Auto-picks a real mic** (prefers USB), clear error if the mic is busy, reopens the mic if USB drops | Dress rehearsal |
| No test tooling | `smoke_test.py`, `record_testset.py`, `score.py` (with stage-by-stage `--ablate`) | Test plan steps 1–5 |

What stays the same: raw transcript, `confidence: 1.0` (Moonshine has no score), speak **only** from the
`/ws/ui` announce messages, skip VAD and STT entirely while listening is off, mute the mic while the bench talks.

## Run it (on the Pi)

Voice and the backend share the mic, so stop the service before running by hand:

```bash
sudo systemctl stop mes-voice
cd ~/mes/Voice/v2
PY=../Voice/.venv/bin/python
$PY client.py --devices                 # find the mic name
$PY client.py --device fifine           # run, watch the log
```

Make it the boot/service version:

```bash
MIC=fifine bash ~/mes/Voice/v2/install_service.sh
journalctl -u mes-voice -f
```

A typical log line:

```
06:31:02 #4 [1.1s lvl 0.0412 = 6.3x room] spk=0.31 stt=262ms  "step three done"
           -> 200 ok: Step three signed off
06:31:02   BENCH: Step three signed off
           latency: end of speech -> spoken reply 742 ms
06:31:09 #5 [0.6s lvl 0.0061 = 1.1x room] DROPPED: too quiet vs room (needs 2.5x)
```

## Supervisor enrollment

```bash
$PY enroll.py --name justin             # 4 samples, read the prompts, in the demo room, station mic
$PY enroll.py --test                    # supervisor AND others talk; watch the scores
sudo systemctl restart mes-voice
```

Pick the backend's threshold between the supervisor's **lowest** score and everyone else's **highest**.
The doc says to set it strict. The threshold lives in the **backend** (`Backend/config.py`), not here.

**Backend side (Justin):** a voice command with no `role` and `speaker_score >= MES_SUPERVISOR_VOICE`
(default 0.65) is treated as the supervisor. Tune that threshold to the room-adjusted scores from `enroll.py --test`.
The challenge flow ("supervisor confirm" → random phrase → repeat it within 15 s,
words match and `speaker_score >= threshold`) has to exist in `Backend/state.py` for voice confirmation to work.
Voice already sends `speaker_score` on every command. With no supervisor enrolled it sends `0.0`,
so supervisor voice actions fail safely and the PIN still works.

## Test plan

| Step | Command |
|---|---|
| 1. Smoke test (Moonshine alone, < 500 ms) | `$PY tools/smoke_test.py` |
| 2. Record the test set (each voice, clean + noise) | `$PY tools/record_testset.py --speaker adan --condition clean` then `--condition noise` with factory noise playing |
| 3. Score accuracy and latency (95 % in noise, < 1 s) | `$PY tools/score.py` |
| 4. Add stages one at a time | `$PY tools/score.py --ablate` |
| 5. 4-hour checkpoint: try Moonshine base | `bash get_base_model.sh` then `$PY tools/score.py --set ASR_MODEL=base` |
| 6. Dress rehearsal | full stack running, real mic and speaker, watch the latency lines |

`score.py` uses the **backend's own parser** (`Backend/parser.py`), so "correct" means the backend would
run the right command. "Parser gap" means the parser doesn't know the intended phrase: add it to `PHRASES` / `NUMBER_WORDS`.

Re-run `score.py` after **every** threshold change (risk plan).

## Tuning (all in `vconfig.py`, or `voice_config.json`, or `--set`)

| Problem | Try |
|---|---|
| Picks up background noise / other talkers | `GATE_SNR=3.5`, `VAD_THRESHOLD=0.6` |
| Misses commands, log shows `DROPPED: too quiet` | `GATE_SNR=1.8`, or `USE_GATE=false`, mic closer to the work area |
| Cuts you off mid-command ("step... three") | `VAD_END_SILENCE=0.5` |
| Feels slow | `VAD_END_SILENCE=0.3`, shorter backend confirmations |
| Phantom commands right after the bench talks | `TTS_TAIL=0.7` |
| A stage misbehaves during the demo | `--set USE_<STAGE>=false` |
| Voice dead during the demo | supervisor screen's `/api/command` debug box |

Example `voice_config.json` (tuned in the room, shared via git):

```json
{"GATE_SNR": 3.0, "VAD_END_SILENCE": 0.4, "MIC_DEVICE": "fifine"}
```

## Not done here

- **Moonshine "Tiny/Small Streaming"**: sherpa-onnx ships Moonshine tiny and base (non-streaming).
  Tiny measured ~270 ms on this Pi, under the 500 ms smoke-test target. Base is the accuracy step-up.
- **Vosk fallback**: not included. If Moonshine fails the 4-hour checkpoint, that's the next step.
- **"Heard" indicator on the tech screen**: needs a backend endpoint; the log shows every detection meanwhile.
