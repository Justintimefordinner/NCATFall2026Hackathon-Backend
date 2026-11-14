#!/usr/bin/env bash
# Downloads all offline models into ./models  (~150 MB total).
# Run this while the Pi still has INTERNET (before you switch it to hotspot mode).
set -e
cd "$(dirname "$0")"
mkdir -p models && cd models
REL=https://github.com/k2-fsa/sherpa-onnx/releases/download

get() { [ -e "$2" ] && { echo "have $2"; return 0; }; echo "-> $2"; curl -fL --retry 3 -o "$2" "$1" || { rm -f "$2"; return 1; }; }

# 1) Voice activity detection
get $REL/asr-models/silero_vad.onnx silero_vad.onnx

# 2) Speech-to-text: Moonshine tiny English (int8) - fast on Pi 5
if [ ! -d sherpa-onnx-moonshine-tiny-en-int8 ]; then
  get $REL/asr-models/sherpa-onnx-moonshine-tiny-en-int8.tar.bz2 moon.tar.bz2
  tar xjf moon.tar.bz2 && rm moon.tar.bz2
fi

# 3) Speaker ID (voiceprints). Tries WeSpeaker ResNet34, falls back to NeMo TitaNet-small.
#    (note: "recongition" is the real, misspelled release tag name)
if ! ls speaker_*.onnx >/dev/null 2>&1; then
  get $REL/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx speaker_wespeaker_resnet34.onnx \
  || get $REL/speaker-recongition-models/nemo_en_titanet_small.onnx speaker_titanet_small.onnx
fi

# 4) Text-to-speech: Piper "amy" (clear, low CPU)
if [ ! -d vits-piper-en_US-amy-low ]; then
  get $REL/tts-models/vits-piper-en_US-amy-low.tar.bz2 piper.tar.bz2
  tar xjf piper.tar.bz2 && rm piper.tar.bz2
fi

echo; echo "Models ready:"; ls -1
