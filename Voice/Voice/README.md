# Voice/ — voice process for the Voice MES Assistant

Owner: Adan. This is a separate process from the Flask backend: it **never imports backend code** and **never decides what a command means**. That's `Backend/parser.py`.

```
USB mic ─► 120 Hz high-pass ─► Silero VAD ─► loudness gate ─► speaker ID ─► Moonshine STT
                                                                                │
                              POST /api/command {"text", "confidence", "source": "voice", ...}
                                                                                ▼
USB speaker ◄── Piper TTS ◄── {"type": "announce"} on ws://<PI>/ws/ui ◄── backend
```

## How it follows the team doc
| Doc rule | Where |
|---|---|
| Send the raw transcript to `/api/command` with `confidence` and `source: "voice"` | `VoiceClient.post` |
| Speak **only** `announce` messages from `/ws/ui`, not the POST response | `on_ws_message` → `tts_worker` |
| Stop sending while `listening` is false (Listen button) | `segments()` drops audio when `listening` is false |
| Mute STT while TTS is speaking (feedback loop) | mic ignored while speaking, plus an echo filter on the last announcement |

**Extra fields for Justin:** each POST also carries `speaker`, `role` (`operator`/`supervisor`) and `speaker_score`. The backend can ignore them, or use `role` later.

## Noise handling and two voices
- **Speaker ID:** only the 2 enrolled voices are transcribed. Other talkers on the floor never reach the backend.
- **High-pass filter:** removes motor hum. **VAD:** ignores bangs and clicks. **Adaptive loudness gate:** speech must be `--snr`× louder than the room.
- Moonshine doesn't give a confidence score, so `confidence` is `1.0` as the doc says. The speaker gate and noise gates do the filtering before anything is sent.

## Models (all offline, via sherpa-onnx)
Moonshine tiny (STT), Silero (VAD), WeSpeaker ResNet34 (speaker ID), Piper amy-low (TTS). `download_models.sh` fetches them into `models/`. They're ~150 MB and git-ignored, so don't commit them.

## Setup (Pi 5; needs real internet, e.g. a phone hotspot)
```bash
cd Voice
./setup.sh                                  # apt deps, .venv, pip, models
source .venv/bin/activate
python3 client.py --devices                 # find the mic / speaker numbers
python3 enroll.py --name adan  --role operator   --device 1
python3 enroll.py --name justin --role supervisor --device 1
python3 enroll.py --list                    # how different the 2 voices are
```
Voiceprints are saved in `voices/` (git-ignored, since they're people's biometrics).

## Run
```bash
python3 client.py --device 1 --out-device 2                   # backend on the same Pi
python3 client.py --pi 10.42.0.1:5000 --device 1 --out-device 2
```
**Testing without the real backend:**
```bash
pip install flask flask-sock
python3 tools/fake_backend.py            # terminal 1: prints transcripts, speaks "Heard: ..."
python3 client.py --device 1             # terminal 2
```

## Tuning
| Problem | Flag |
|---|---|
| Picks up background noise | `--vad 0.65 --snr 3.5`, or `--wake` ("bench, next page") |
| Misses commands | `--vad 0.45 --snr 1.8`, mic closer |
| Enrolled person shows "unknown voice" | `--spk-threshold 0.38`, re-enroll in the demo noise |
| Mixes up the 2 people | `--spk-threshold 0.55`, re-enroll with `--seconds 7` |
| Testing alone | `--open` |

## Files
`client.py` main process · `models.py` model loading and audio helpers · `mic.py` USB mic at 16 kHz · `enroll.py` voice enrollment and test · `tools/fake_backend.py` stand-in backend
