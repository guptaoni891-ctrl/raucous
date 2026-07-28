# Linux setup

Raucous supports X11 and Wayland desktops. On Wayland it requests the native
Qt Wayland backend and keeps XWayland as a fallback.

## Audio backend order

Automatic mode tries:

1. PipeWire-Pulse output monitor through `pactl` and `parec`
2. PulseAudio/PipeWire through the cross-platform `SoundCard` backend
3. PortAudio input through `sounddevice`

## Distribution dependencies

Package names differ by distribution. Install:

- Python 3.11 or newer for source installs
- Qt 6 Wayland support when using Wayland
- PulseAudio-compatible client libraries/tools
- PortAudio for the final fallback
- PipeWire and a session manager on PipeWire desktops

### Arch Linux

```bash
sudo pacman -S --needed \
  python python-pip portaudio \
  pipewire pipewire-pulse wireplumber libpulse \
  qt6-wayland
```

### Ubuntu/Debian

```bash
sudo apt install python3 python3-venv libpulse0 pulseaudio-utils \
  libportaudio2 libegl1 libgl1
```

## Source installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
raucous --demo
```

## Inspect the output monitor

```bash
pactl get-default-sink
pactl list short sources
raucous --list-audio-devices
```

A desktop-output monitor normally ends in `.monitor`.

```json
{
  "audio_backend": "pipewire",
  "audio_device": "monitor",
  "allow_microphone_fallback": false
}
```

See [ARCH_HYPRLAND.md](ARCH_HYPRLAND.md) for Hyprland-specific details.

## Spotify account requirement

Spotify currently requires Premium for Web API Development Mode. Each user
should create their own Spotify app and Client ID; Demo Mode works without it.
