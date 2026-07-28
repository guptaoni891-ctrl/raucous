#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This setup helper is for macOS." >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'

cat <<'EOF'

Raucous is installed.
Activate: source .venv/bin/activate
Demo:    raucous --demo
Devices: raucous --list-audio-devices

For desktop-output visualization, install and route audio through a virtual
loopback device such as BlackHole, then select it in Raucous's config.
EOF
