#!/bin/bash
# Start the v2 voice client automatically at boot, as a *user* service.
#
#   bash ~/mes/Voice/v2/install_user_service.sh
#
# Why a user service: the Bluetooth speaker lives in your login's PipeWire session.
# A system service (install_service.sh) can't reach it, so it would play nothing.
# Settings (mic, speaker, TTS_TAIL...) come from voice_config.json next to this file.
#
#   journalctl --user-unit mes-voice -f        watch the log
#   systemctl --user restart mes-voice       after changing voice_config.json or git pull
#   systemctl --user stop mes-voice          before running client.py by hand (it holds the mic)
#   systemctl --user disable --now mes-voice turn auto-start off
set -e
V2="$(cd "$(dirname "$0")" && pwd)"
PY="$V2/../Voice/.venv/bin/python"
ME="$(id -un)"

[ -x "$PY" ] || { echo "No venv at $PY. Run Voice/Voice/setup.sh first."; exit 1; }
[ -f "$V2/voice_config.json" ] || echo "note: no voice_config.json, using the defaults in vconfig.py"

# the old system-level service would grab the mic first and can't play to Bluetooth
if [ -f /etc/systemd/system/mes-voice.service ]; then
  echo "Disabling the system-level mes-voice service..."
  sudo systemctl disable --now mes-voice || true
fi

mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/mes-voice.service <<EOF
[Unit]
Description=Voice MES voice client (v2)
After=pipewire.service wireplumber.service
Wants=pipewire.service wireplumber.service

[Service]
WorkingDirectory=$V2
# give the backend and the Bluetooth speaker a moment to come up
ExecStartPre=/bin/sleep 8
ExecStart=$PY client.py
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# start user services at boot, even before anyone logs in
sudo loginctl enable-linger "$ME"
systemctl --user daemon-reload
systemctl --user enable --now mes-voice
echo
echo "Voice now starts at boot. Watch it:  journalctl --user-unit mes-voice -f"
