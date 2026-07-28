# Windows setup

## Release download

1. Download `Raucous-Windows-x64.zip` from GitHub Releases.
2. Extract the entire archive.
3. Run `Raucous.exe` from the extracted folder.
4. Enter a Spotify Client ID or choose Demo Mode.

Do not move only the `.exe`; the adjacent bundled files are required.

## Audio capture

Raucous uses Windows WASAPI loopback through the native `SoundCard` backend.
This captures the audio playing through an output device without recording it to
disk.

Automatic mode prefers the active output. For source installations, inspect the
devices with:

```powershell
raucous --list-audio-devices
```

Then create the config and choose a device by name:

```powershell
raucous --create-config
raucous --print-config-path
```

```json
{
  "audio_backend": "soundcard",
  "audio_device": "Speakers",
  "allow_microphone_fallback": false
}
```

Try `Headphones`, `Speakers`, the device model name, or `Stereo Mix` depending on
what the device list reports.

## Source installation

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
raucous --demo
```

The included helper automates this:

```powershell
.\scripts\setup_windows.ps1
```

## Troubleshooting

### SmartScreen warning

Community releases are not code-signed yet. Open **More info** and verify that
you downloaded the archive from the project's official GitHub Release before
choosing **Run anyway**.

### Visualizer is flat

- Play audio before launching Raucous.
- Confirm Spotify is using the same output device Raucous selected.
- Run `raucous --list-audio-devices` from a source installation.
- Set `audio_device` to the active speaker name.
- Update the sound driver if no WASAPI loopback device is exposed.

### Widget works but Spotify does not

Confirm the Spotify app contains this redirect URI exactly:

```text
http://127.0.0.1:8888/callback
```

## Spotify account requirement

Spotify currently requires Premium for Web API Development Mode. Each user
should create their own Spotify app and Client ID; Demo Mode works without it.
