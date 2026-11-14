#!/bin/bash
# Run on the Pi after copying the v2 folder from the USB stick into ~/mes/Voice/
#     bash ~/mes/Voice/v2/pi_setup.sh
# Needs internet (campus Wi-Fi) the first time, to install sherpa-onnx 1.x.
V2="$(cd "$(dirname "$0")" && pwd)"
MODELS="$V2/../Voice/models"

echo "== 1. Supervisor voice files"
ok=1
for f in supervisor.npy supervisor_samples.npy supervisor.json room_samples.npy; do
  if [ -f "$V2/voices/$f" ]; then echo "  ok  $f"; else echo "  !!  missing voices/$f"; ok=0; fi
done
[ "$ok" = 1 ] || echo "  Copy the voices folder from the stick into $V2/ and run this again."

echo "== 2. Speaker model (must be the same one the PC used)"
mkdir -p "$MODELS"
if [ -f "$V2/speaker_wespeaker_resnet34.onnx" ]; then
  mv -f "$V2/speaker_wespeaker_resnet34.onnx" "$MODELS/"
  echo "  installed speaker_wespeaker_resnet34.onnx from the stick"
fi
for f in "$MODELS"/speaker_*.onnx; do
  [ -e "$f" ] || continue
  if [ "$(basename "$f")" != "speaker_wespeaker_resnet34.onnx" ]; then
    mv "$f" "$f.unused"
    echo "  set aside $(basename "$f") (a different model wouldn't match the PC voiceprint)"
  fi
done
if [ -f "$MODELS/speaker_wespeaker_resnet34.onnx" ]; then
  echo "  ok  speaker_wespeaker_resnet34.onnx ($(stat -c %s "$MODELS/speaker_wespeaker_resnet34.onnx") bytes, expect 26530550)"
else
  echo "  !!  speaker_wespeaker_resnet34.onnx not found - copy it from the stick"
fi

echo "== 3. Voice service -> v2"
MIC="${MIC:-fifine}" bash "$V2/install_service.sh"

echo "== 4. Startup log (waiting 15 s)"
sleep 15
journalctl -u mes-voice -n 25 --no-pager
echo
echo "Look for: supervisor 'justin' enrolled ... and room-adjusted scores (6 room samples)"
