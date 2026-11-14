#!/bin/bash
# Points the mes-voice service at this v2 client (uses the existing Voice/Voice/.venv).
#   bash ~/mes/Voice/v2/install_service.sh
#   MIC=fifine SPK=fifine bash ~/mes/Voice/v2/install_service.sh
# To go back to the old client:  bash ~/mes/pi/install-boot.sh
set -e
V2="$(cd "$(dirname "$0")" && pwd)"
PY="$V2/../Voice/.venv/bin/python"
PIP="$V2/../Voice/.venv/bin/pip"
ME="$(id -un)"
MIC="${MIC:-}"
SPK="${SPK:-}"

[ -x "$PY" ] || { echo "No venv at $PY. Run Voice/Voice/setup.sh first."; exit 1; }

VER=$("$PY" -c "import sherpa_onnx; print(sherpa_onnx.__version__)" 2>/dev/null || echo none)
echo "sherpa-onnx: $VER"
if [[ "$VER" == 2.* ]]; then
  echo "Installing sherpa-onnx 1.x (2.x breaks Piper TTS). Needs internet..."
  "$PIP" install -q "sherpa-onnx>=1.10.30,<2" || echo "!! pin failed (no internet?). TTS will fall back to espeak-ng if installed."
fi

ARGS=""
[ -n "$MIC" ] && ARGS="$ARGS --device \"$MIC\""
[ -n "$SPK" ] && ARGS="$ARGS --out-device \"$SPK\""

sudo tee /etc/systemd/system/mes-voice.service >/dev/null <<EOF
[Unit]
Description=Voice MES voice client (v2)
After=mes.service sound.target
Wants=mes.service

[Service]
User=$ME
SupplementaryGroups=audio
WorkingDirectory=$V2
ExecStartPre=/bin/sleep 5
ExecStart=$PY client.py$ARGS
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl restart mes-voice
echo "mes-voice now runs v2. Watch it: journalctl -u mes-voice -f"
