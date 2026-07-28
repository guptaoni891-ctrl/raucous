#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This setup helper is for Linux." >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'

cat <<'EOF'

Raucous's Python environment is installed.
Ensure your distribution also provides PulseAudio/PipeWire client libraries,
PortAudio, and Qt Wayland support where applicable.

Activate: source .venv/bin/activate
Demo:    raucous --demo
Devices: raucous --list-audio-devices
EOF
