# Changelog

All notable changes to VinylPulse are documented here.

## [1.1.0] - 2026-07-28

### Added

- cross-platform native audio selection through SoundCard
- Windows WASAPI output-loopback support
- macOS CoreAudio/virtual-loopback device support
- first-launch Spotify Client ID setup with Demo Mode fallback
- separate Windows, Linux, Apple Silicon macOS and Intel macOS release builds
- PyInstaller specification and tagged GitHub Release workflow
- Windows, macOS and general Linux setup guides
- cross-platform CI smoke tests
- in-app audio backend and device settings for downloaded builds
- native Windows and macOS application icons
- release archive checksums and bundled license notices

### Changed

- Linux automatic audio fallback is now PipeWire → SoundCard → PortAudio
- repository metadata and README now advertise Windows, macOS and Linux
- audio device listing now shows native, PipeWire and PortAudio devices

## [1.0.0] - 2026-07-28

### Added

- Spotify PKCE authentication and playback polling
- current track and podcast episode artwork
- custom PyQt6 vinyl rendering and circular FFT visualizer
- native PipeWire-Pulse output-monitor capture on Arch Linux
- PortAudio fallback device discovery
- persisted window position and UI preferences
- native Qt Wayland startup with XWayland fallback
- demo mode, structured logs and validated configuration
- unit tests, packaging metadata and GitHub Actions CI
