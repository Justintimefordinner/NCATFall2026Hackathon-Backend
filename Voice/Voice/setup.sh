#!/usr/bin/env bash
# One-time setup for the Voice process on the Pi 5. Needs real internet
# (phone hotspot works; campus Wi-Fi login pages break apt).
set -e
cd "$(dirname "$0")"
sudo apt-get update
sudo apt-get install -y python3-venv python3-full python3-dev libportaudio2 portaudio19-dev alsa-utils curl bzip2
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
./download_models.sh
echo "Voice setup done. Next: python3 enroll.py --devices"
