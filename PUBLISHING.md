# Publishing Raucous to GitHub

## 1. Validate locally on Arch/Hyprland

```bash
./scripts/setup_arch.sh
source .venv/bin/activate
make check
raucous --demo
raucous --list-audio-devices
```

Also launch Spotify, play a track and confirm the PipeWire `.monitor` source is
selected.

## 2. Push the repository

```bash
git init
git add .
git commit -m "feat: release cross-platform Raucous 1.1"
git branch -M main
git remote add origin https://github.com/guptaoni891-ctrl/raucous.git
git push -u origin main
```

## 3. Confirm CI

The `CI` workflow runs tests on Windows, macOS and Linux. Do not create the first
release until every job is green.

## 4. Improve the GitHub page

Repository description:

> Cross-platform PyQt6 Spotify vinyl widget with secure PKCE login and a live native-audio FFT visualizer.

Suggested topics:

```text
python pyqt6 spotify windows macos linux wayland pipewire wasapi coreaudio audio-visualizer fft desktop-widget
```

Replace the static preview with:

- one clean screenshot
- one short GIF showing album-art changes and the live spectrum
- a compatibility table listing the operating systems actually tested

## 5. Create a release

Commit and push everything, then tag the release:

```bash
git tag -a v1.2.0 -m "Raucous 1.2.0"
git push origin v1.2.0
```

The `Build release downloads` workflow creates and uploads:

- `Raucous-Windows-x64.zip`
- `Raucous-Linux-x64.tar.gz`
- `Raucous-macOS-Apple-Silicon.zip`
- `Raucous-macOS-Intel.zip`
- `SHA256SUMS.txt`

The workflow creates the GitHub Release automatically when the tag is pushed.
If the release already exists, it replaces the generated archives.

## 6. Test the downloads

Download each artifact from GitHub rather than testing only the local build.
At minimum, ask one Windows user and one macOS user to verify:

- first-launch setup
- Spotify browser authorization
- album-art updates
- dragging and right-click controls
- audio device detection
- clean shutdown

Do not claim a platform is personally verified until someone has run that exact
release artifact on the platform.

Never commit `.env`, generated config files, OAuth caches, logs, virtual
environments or recordings.
