from __future__ import annotations

from raucous.audio_backends import backend_order


def test_linux_auto_prefers_pipewire() -> None:
    assert backend_order("linux", "auto") == (
        "pipewire",
        "soundcard",
        "portaudio",
    )


def test_windows_auto_prefers_native_soundcard() -> None:
    assert backend_order("win32", "auto") == ("soundcard", "portaudio")


def test_macos_auto_prefers_native_soundcard() -> None:
    assert backend_order("darwin", "auto") == ("soundcard", "portaudio")


def test_explicit_backend_has_no_fallback() -> None:
    assert backend_order("linux", "portaudio") == ("portaudio",)
