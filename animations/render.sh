#!/usr/bin/env bash
# Render lesson animations inside the pinned Manim image (see Dockerfile).
#
#   animations/render.sh limit                      # every animated limit lesson
#   animations/render.sh limit factoring_0_0        # just one
#   animations/render.sh limit factoring_0_0 --draft  # fast low-res preview
#
# Writes web/public/animations/<topic>/<lesson>.{mp4,480.mp4,webp} and the cue
# timings in backend/engine/topics/<topic>/data/animations.json.
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -q -t bacii-manim:0.21.0 animations >/dev/null
exec docker run --rm \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  --security-opt label=disable \
  -v "$PWD:/repo" -w /repo \
  --entrypoint python bacii-manim:0.21.0 animations/render.py "$@"
