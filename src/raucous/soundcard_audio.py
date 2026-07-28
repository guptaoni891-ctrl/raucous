from __future__ import annotations

import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

LOOPBACK_HINTS = (
    "loopback",
    "monitor",
    "stereo mix",
    "what u hear",
    "wave out mix",
    "blackhole",
    "soundflower",
    "vb-audio",
    "cable output",
    "loopback audio",
)


class SoundCardError(RuntimeError):
    """Raised when native cross-platform audio capture cannot start."""


@dataclass(slots=True)
class SoundCardDevice:
    index: int
    identifier: str
    name: str
    is_loopback: bool
    is_default_output: bool
    is_default_input: bool
    handle: Any = field(repr=False, compare=False, default=None)


def _normalized(value: object) -> str:
    return " ".join(str(value).casefold().split())


def _device_identifier(device: object) -> str:
    for attribute in ("id", "_id"):
        value = getattr(device, attribute, None)
        if value is not None:
            return str(value)
    return str(getattr(device, "name", repr(device)))


def _same_device(left: object | None, right: object) -> bool:
    if left is None:
        return False
    return _device_identifier(left) == _device_identifier(right)


def _name_matches_output(microphone_name: str, speaker_name: str) -> bool:
    microphone = _normalized(microphone_name)
    speaker = _normalized(speaker_name)
    return bool(microphone and speaker) and (
        microphone == speaker or microphone in speaker or speaker in microphone
    )


def list_soundcard_devices(
    soundcard_module: Any | None = None,
) -> list[SoundCardDevice]:
    """Return inputs and output-loopback devices from SoundCard's native backend."""
    if soundcard_module is None:
        try:
            import soundcard as soundcard_module
        except ImportError as exc:
            raise SoundCardError("The SoundCard package is not installed") from exc

    try:
        microphones = list(soundcard_module.all_microphones(include_loopback=True))
        physical_inputs = list(soundcard_module.all_microphones(include_loopback=False))
    except Exception as exc:
        raise SoundCardError(
            f"Could not enumerate native audio devices: {exc}"
        ) from exc

    try:
        default_input = soundcard_module.default_microphone()
    except Exception:  # noqa: BLE001
        default_input = None
    try:
        default_output = soundcard_module.default_speaker()
    except Exception:  # noqa: BLE001
        default_output = None

    physical_ids = {_device_identifier(device) for device in physical_inputs}
    default_output_name = str(getattr(default_output, "name", ""))

    devices: list[SoundCardDevice] = []
    for index, microphone in enumerate(microphones):
        identifier = _device_identifier(microphone)
        name = str(getattr(microphone, "name", identifier))
        lowered = _normalized(name)
        is_loopback = identifier not in physical_ids or any(
            hint in lowered for hint in LOOPBACK_HINTS
        )
        is_default_output = is_loopback and _name_matches_output(
            name,
            default_output_name,
        )
        devices.append(
            SoundCardDevice(
                index=index,
                identifier=identifier,
                name=name,
                is_loopback=is_loopback,
                is_default_output=is_default_output,
                is_default_input=_same_device(default_input, microphone),
                handle=microphone,
            )
        )
    return devices


def choose_soundcard_device(
    devices: Iterable[SoundCardDevice],
    requested: int | str | None,
    *,
    allow_microphone_fallback: bool,
    platform: str | None = None,
) -> SoundCardDevice:
    candidates = list(devices)
    if not candidates:
        raise SoundCardError("No native audio capture devices were found")

    if isinstance(requested, int):
        for device in candidates:
            if device.index == requested:
                return device
        raise SoundCardError(f"Native audio device index {requested} was not found")

    if isinstance(requested, str) and requested.strip():
        query = requested.strip().casefold()
        if query.isdigit():
            return choose_soundcard_device(
                candidates,
                int(query),
                allow_microphone_fallback=allow_microphone_fallback,
                platform=platform,
            )
        matches = [
            device
            for device in candidates
            if query in device.name.casefold() or query in device.identifier.casefold()
        ]
        if matches:
            return sorted(
                matches,
                key=lambda device: (
                    not device.is_default_output,
                    not device.is_loopback,
                    device.index,
                ),
            )[0]
        raise SoundCardError(f"No native audio device contains {requested!r}")

    default_loopbacks = [device for device in candidates if device.is_default_output]
    if default_loopbacks:
        return sorted(default_loopbacks, key=lambda device: device.index)[0]

    loopbacks = [device for device in candidates if device.is_loopback]
    if loopbacks:
        return sorted(loopbacks, key=lambda device: device.index)[0]

    if allow_microphone_fallback:
        default_inputs = [device for device in candidates if device.is_default_input]
        if default_inputs:
            return sorted(default_inputs, key=lambda device: device.index)[0]
        return sorted(candidates, key=lambda device: device.index)[0]

    current_platform = platform or sys.platform
    if current_platform == "darwin":
        raise SoundCardError(
            "No macOS loopback device was found. Install a virtual audio device "
            "such as BlackHole, then select it with --list-audio-devices/config."
        )
    if current_platform.startswith("win"):
        raise SoundCardError(
            "No Windows WASAPI loopback device was found. Select the active "
            "speaker by name or enable Stereo Mix if your driver provides it."
        )
    raise SoundCardError(
        "No output monitor/loopback device was found. Run "
        "'raucous --list-audio-devices' and select one in the config."
    )
