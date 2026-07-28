from __future__ import annotations

import pytest

from vinylpulse.audio_devices import AudioDevice, AudioDeviceError, choose_audio_device


def device(index: int, name: str, *, loopback: bool = False) -> AudioDevice:
    return AudioDevice(
        index=index,
        name=name,
        max_input_channels=2,
        default_sample_rate=48_000,
        is_loopback_candidate=loopback,
    )


def test_prefers_loopback_candidate() -> None:
    selected = choose_audio_device(
        [device(1, "Microphone"), device(4, "PipeWire Monitor", loopback=True)],
        None,
        default_input_index=1,
        allow_microphone_fallback=False,
    )
    assert selected.index == 4


def test_selects_by_name_substring() -> None:
    selected = choose_audio_device(
        [device(2, "Stereo Mix", loopback=True)],
        "stereo",
        default_input_index=None,
        allow_microphone_fallback=False,
    )
    assert selected.name == "Stereo Mix"


def test_microphone_fallback_requires_opt_in() -> None:
    devices = [device(1, "Microphone")]
    with pytest.raises(AudioDeviceError):
        choose_audio_device(
            devices,
            None,
            default_input_index=1,
            allow_microphone_fallback=False,
        )
    assert (
        choose_audio_device(
            devices,
            None,
            default_input_index=1,
            allow_microphone_fallback=True,
        ).index
        == 1
    )
