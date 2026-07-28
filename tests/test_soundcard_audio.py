from __future__ import annotations

import pytest

from raucous.soundcard_audio import (
    SoundCardDevice,
    SoundCardError,
    choose_soundcard_device,
    list_soundcard_devices,
)


def device(
    index: int,
    name: str,
    *,
    loopback: bool = False,
    default_output: bool = False,
    default_input: bool = False,
) -> SoundCardDevice:
    return SoundCardDevice(
        index=index,
        identifier=f"id-{index}",
        name=name,
        is_loopback=loopback,
        is_default_output=default_output,
        is_default_input=default_input,
        handle=object(),
    )


def test_prefers_default_output_loopback() -> None:
    selected = choose_soundcard_device(
        [
            device(0, "Microphone", default_input=True),
            device(1, "Speakers", loopback=True, default_output=True),
            device(2, "HDMI", loopback=True),
        ],
        None,
        allow_microphone_fallback=False,
        platform="win32",
    )
    assert selected.index == 1


def test_selects_virtual_macos_device_by_name() -> None:
    selected = choose_soundcard_device(
        [device(3, "BlackHole 2ch", loopback=True)],
        "blackhole",
        allow_microphone_fallback=False,
        platform="darwin",
    )
    assert selected.name == "BlackHole 2ch"


def test_macos_explains_missing_loopback() -> None:
    with pytest.raises(SoundCardError, match="BlackHole"):
        choose_soundcard_device(
            [device(0, "MacBook Microphone", default_input=True)],
            None,
            allow_microphone_fallback=False,
            platform="darwin",
        )


def test_microphone_fallback_requires_opt_in() -> None:
    microphone = device(0, "Built-in Microphone", default_input=True)
    selected = choose_soundcard_device(
        [microphone],
        None,
        allow_microphone_fallback=True,
        platform="darwin",
    )
    assert selected.index == 0


class FakeAudioObject:
    def __init__(self, identifier: str, name: str) -> None:
        self.id = identifier
        self.name = name


class FakeSoundCardModule:
    def __init__(self) -> None:
        self.microphone = FakeAudioObject("mic", "Built-in Microphone")
        self.speaker = FakeAudioObject("speaker", "Speakers")
        self.loopback = FakeAudioObject("speaker-loopback", "Speakers")

    def all_microphones(self, *, include_loopback: bool) -> list[FakeAudioObject]:
        return (
            [self.microphone, self.loopback]
            if include_loopback
            else [self.microphone]
        )

    def default_microphone(self) -> FakeAudioObject:
        return self.microphone

    def default_speaker(self) -> FakeAudioObject:
        return self.speaker


def test_discovers_extra_loopback_and_defaults() -> None:
    devices = list_soundcard_devices(FakeSoundCardModule())
    assert len(devices) == 2
    assert devices[0].is_default_input is True
    assert devices[1].is_loopback is True
    assert devices[1].is_default_output is True
