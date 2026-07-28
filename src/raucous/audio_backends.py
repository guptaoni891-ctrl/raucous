from __future__ import annotations


def backend_order(platform: str, requested_backend: str) -> tuple[str, ...]:
    """Return the capture fallback order for the current operating system."""
    if requested_backend != "auto":
        return (requested_backend,)
    if platform.startswith("linux"):
        return ("pipewire", "soundcard", "portaudio")
    return ("soundcard", "portaudio")
