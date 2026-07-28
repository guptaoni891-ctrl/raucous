# Changelog

All notable changes to Raucous are documented here.

## [1.2.0] - 2026-07-28

### Changed

- rebranded the application, Python package, CLI command and release artifacts as Raucous
- updated desktop identifiers, application metadata, documentation and GitHub workflows
- renamed native Windows, macOS and Linux bundles to use the Raucous brand

### Added

- Spotify Authorization Code with PKCE authentication
- current track and podcast episode metadata polling
- asynchronous album-art retrieval with retry and rate-limit handling
- native PipeWire-Pulse output-monitor capture on Arch Linux
- Windows WASAPI and macOS CoreAudio-compatible capture support
- PortAudio fallback and real-time FFT visualizer
- automatic loopback/monitor source discovery
- native Qt Wayland startup with XWayland fallback
- dynamic album-derived visualizer colour
- draggable frameless PyQt6 widget
- persisted window position and menu preferences
- demo mode for reviewers
- validated JSON configuration and `.env` support
- rotating logs, unit tests, packaging and CI
