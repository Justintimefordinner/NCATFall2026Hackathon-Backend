#!/usr/bin/env bash
# One-time setup for the Voice process on the Pi 5. Needs real internet
# (phone hotspot works; campus Wi-Fi login pages break apt).
set -e
cd "$(dirname "$0")"
sudo apt-get update
sudo apt-get install -y python3-venv python3-full python3-dev libportaudio2 portaudio19-dev alsa-utils espeak-ng curl bzip2
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
./download_models.sh
# Loud floor: max out the speaker volume (best effort; the USB card may name its control differently)
for c in Master PCM Speaker Headphone; do amixer -q sset "$c" 100% unmute 2>/dev/null || true; done
python3 tts.py --prerender || true          # fill tts_cache/ now so the first boot is instant
echo "Voice setup done. Next: python3 enroll.py --devices"
