# Arch Linux and Hyprland setup

Arch Linux, Hyprland and PipeWire are a first-class Linux target for VinylPulse.
The same repository also supports Windows and macOS. On Hyprland, the application
automatically requests Qt's native Wayland backend and keeps XWayland as a fallback.

## 1. Install system packages

```bash
sudo pacman -S --needed \
  python python-pip portaudio \
  pipewire pipewire-pulse wireplumber libpulse \
  qt6-wayland
```

Or run:

```bash
./scripts/setup_arch.sh
```

## 2. Verify the audio stack

```bash
systemctl --user status pipewire pipewire-pulse wireplumber
pactl info
pactl list short sources
```

The source ending in `.monitor` is the desktop-output source used by the live
visualizer. VinylPulse automatically prefers the monitor belonging to the
current default sink.

## 3. Install and test

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
vinylpulse --demo
```

The demo proves the Qt rendering and animation work without Spotify login or
audio capture.

## 4. Configure Spotify

```bash
cp .env.example .env
nano .env
```

Set:

```dotenv
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

Then run:

```bash
vinylpulse
```

## 5. Select a PipeWire monitor manually

```bash
vinylpulse --list-audio-devices
vinylpulse --create-config
vinylpulse --print-config-path
```

Set a unique substring or the complete monitor name:

```json
{
  "audio_backend": "pipewire",
  "audio_device": "alsa_output.pci-0000_01_00.1.hdmi-stereo.monitor"
}
```

Using `"audio_device": "monitor"` is enough when there is only one monitor
source.

## Hyprland notes

VinylPulse sets its Wayland desktop application ID to `vinylpulse`. The window
is frameless, transparent and draggable using Qt's compositor-controlled system
move operation.

If Hyprland tiles the widget on your configuration, first run:

```bash
hyprctl clients
```

Confirm the reported class is `vinylpulse`, then create a matching floating
window rule using the syntax supported by your installed Hyprland version.
Hyprland changes rule syntax occasionally, so the repository does not silently
edit your personal compositor configuration.

## Troubleshooting

### `Could not load the Qt platform plugin "wayland"`

```bash
sudo pacman -S --needed qt6-wayland
QT_QPA_PLATFORM=xcb vinylpulse --demo
```

The second command is a temporary XWayland fallback for diagnosis.

### No `.monitor` source appears

```bash
pactl get-default-sink
pactl list short sinks
pactl list short sources
```

Confirm `pipewire-pulse` and `wireplumber` are running. Logging out and back in
may be needed after replacing another PulseAudio provider.

### The visualizer selects the wrong output

Set `audio_backend` to `pipewire` and set `audio_device` to the full `.monitor`
source name in the generated config file.

### NVIDIA/Wayland rendering issue

Run the demo once with explicit backend selection:

```bash
QT_QPA_PLATFORM='wayland;xcb' vinylpulse --demo
```

Do not add global NVIDIA or Wayland environment overrides solely for this
project unless your wider Hyprland setup already requires them.

## Spotify account requirement

Spotify currently requires Premium for Web API Development Mode. Each user
should create their own Spotify app and Client ID; Demo Mode works without it.
