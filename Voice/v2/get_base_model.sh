#!/bin/bash
# Downloads Moonshine BASE (more accurate than tiny, slower) next to the other models.
# Risk plan: if tiny misses too many commands, try this, then:
#   python tools/score.py --set ASR_MODEL=base     (compare accuracy AND latency)
# Needs internet (campus Wi-Fi or a phone hotspot, not MESPanel).
set -e
cd "$(dirname "$0")/../Voice/models"
NAME=sherpa-onnx-moonshine-base-en-int8
if [ -d "$NAME" ]; then echo "already have $NAME"; exit 0; fi
curl -fL --retry 3 -o base.tar.bz2 \
  "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/$NAME.tar.bz2"
tar xjf base.tar.bz2 && rm base.tar.bz2
echo "Done: $(pwd)/$NAME"
