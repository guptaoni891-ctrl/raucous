#!/usr/bin/env bash
set -euo pipefail

if ! command -v pacman >/dev/null 2>&1; then
  echo "This installer is for Arch Linux and Arch-based distributions." >&2
  exit 1
fi

sudo pacman -S --needed \
  python \
  python-pip \
  portaudio \
  pipewire \
  pipewire-pulse \
  wireplumber \
  libpulse \
  qt6-wayland

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

cat <<'EOF'

VinylPulse is installed in .venv.

Run the reviewer demo:
  source .venv/bin/activate
  vinylpulse --demo

List PipeWire monitor sources:
  vinylpulse --list-audio-devices
EOF
