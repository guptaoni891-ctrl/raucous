from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

LOOPBACK_HINTS = (
    "monitor",
    "loopback",
    "stereo mix",
    "what u hear",
    "wave out mix",
    "blackhole",
    "soundflower",
)


class AudioDeviceError(RuntimeError):
    """Raised when no suitable audio capture device can be selected."""


@dataclass(frozen=True, slots=True)
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    default_sample_rate: int
    is_loopback_candidate: bool


def _as_device(index: int, raw: Mapping[str, Any]) -> AudioDevice:
    name = str(raw.get("name", f"Device {index}"))
    channels = int(raw.get("max_input_channels", 0))
    rate = int(float(raw.get("default_samplerate", 48_000)))
    lowered = name.casefold()
    return AudioDevice(
        index=index,
        name=name,
        max_input_channels=channels,
        default_sample_rate=rate,
        is_loopback_candidate=any(hint in lowered for hint in LOOPBACK_HINTS),
    )


def list_input_devices() -> list[AudioDevice]:
    import sounddevice as sd

    raw_devices = sd.query_devices()
    return [
        _as_device(index, raw)
        for index, raw in enumerate(raw_devices)
        if int(raw.get("max_input_channels", 0)) > 0
    ]


def choose_audio_device(
    devices: Iterable[AudioDevice],
    requested: int | str | None,
    *,
    default_input_index: int | None,
    allow_microphone_fallback: bool,
) -> AudioDevice:
    candidates = list(devices)
    if not candidates:
        raise AudioDeviceError("No audio input devices were found")

    if isinstance(requested, int):
        for device in candidates:
            if device.index == requested:
                return device
        raise AudioDeviceError(f"Audio device index {requested} was not found")

    if isinstance(requested, str) and requested.strip():
        query = requested.strip().casefold()
        if query.isdigit():
            return choose_audio_device(
                candidates,
                int(query),
                default_input_index=default_input_index,
                allow_microphone_fallback=allow_microphone_fallback,
            )
        matches = [device for device in candidates if query in device.name.casefold()]
        if matches:
            return sorted(
                matches,
                key=lambda device: (not device.is_loopback_candidate, device.index),
            )[0]
        raise AudioDeviceError(f"No audio input device name contains {requested!r}")

    loopback = [device for device in candidates if device.is_loopback_candidate]
    if loopback:
        return sorted(loopback, key=lambda device: device.index)[0]

    if allow_microphone_fallback and default_input_index is not None:
        for device in candidates:
            if device.index == default_input_index:
                return device

    raise AudioDeviceError(
        "No monitor/loopback input was detected. Run "
        "'raucous --list-audio-devices' and set audio_device in config.json."
    )


def system_default_input_index() -> int | None:
    import sounddevice as sd

    value = sd.default.device
    if isinstance(value, (tuple, list)) and value:
        index = value[0]
        return int(index) if index is not None and int(index) >= 0 else None
    return None
