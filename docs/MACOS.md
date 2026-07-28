# macOS setup

## Choose the correct download

- Apple Silicon Macs: `VinylPulse-macOS-Apple-Silicon.zip`
- Intel Macs: `VinylPulse-macOS-Intel.zip`

Extract the archive and open `VinylPulse.app`.

## First launch and permissions

The first time VinylPulse opens an audio input, macOS can ask for microphone
permission. Allow it in:

**System Settings → Privacy & Security → Microphone**

The release bundle includes an `NSMicrophoneUsageDescription` explaining that
audio is processed locally for the visualizer and is not stored or uploaded.

## Desktop-output visualization

CoreAudio does not expose ordinary speaker output as a normal recording input for
this app. Install a virtual audio loopback device such as BlackHole, then route
the Mac's playback through it.

Official BlackHole project:

https://github.com/ExistentialAudio/BlackHole

After installation:

1. Open **Audio MIDI Setup**.
2. Create a Multi-Output Device containing your speakers/headphones and BlackHole.
3. Select that Multi-Output Device as macOS output.
4. From a source installation, run `vinylpulse --list-audio-devices`.
5. Set `audio_device` to `BlackHole`.

```json
{
  "audio_backend": "soundcard",
  "audio_device": "BlackHole",
  "allow_microphone_fallback": false
}
```

Without a loopback device, Spotify artwork and record rotation still work, but
the live spectrum remains unavailable.

## Source installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
vinylpulse --demo
```

Or:

```bash
./scripts/setup_macos.sh
```

## Gatekeeper warning

The community build is not notarized yet. Verify the archive came from the
project's official GitHub Release. You can then Control-click the app, select
**Open**, and confirm.

## Spotify account requirement

Spotify currently requires Premium for Web API Development Mode. Each user
should create their own Spotify app and Client ID; Demo Mode works without it.
