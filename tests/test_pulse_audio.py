from __future__ import annotations

import pytest

from raucous.pulse_audio import (
    PulseAudioError,
    PulseSource,
    build_parec_command,
    choose_pulse_source,
    parse_short_sources,
)


def source(index: int, name: str) -> PulseSource:
    return PulseSource(
        index=index,
        name=name,
        is_monitor=name.endswith(".monitor"),
    )


def test_parses_pactl_short_sources() -> None:
    parsed = parse_short_sources(
        "51\talsa_output.pci.hdmi-stereo.monitor\tPipeWire\ts32le 2ch 48000Hz\tSUSPENDED\n"
        "52\talsa_input.pci.analog-stereo\tPipeWire\ts32le 2ch 48000Hz\tRUNNING\n"
    )
    assert [item.index for item in parsed] == [51, 52]
    assert parsed[0].is_monitor is True
    assert parsed[1].is_monitor is False


def test_prefers_default_sink_monitor() -> None:
    selected = choose_pulse_source(
        [
            source(2, "alsa_output.usb.monitor"),
            source(7, "alsa_output.pci.hdmi.monitor"),
        ],
        None,
        default_sink="alsa_output.pci.hdmi",
    )
    assert selected.index == 7


def test_selects_requested_source_substring() -> None:
    selected = choose_pulse_source(
        [source(3, "alsa_output.pci.analog-stereo.monitor")],
        "analog-stereo",
        default_sink=None,
    )
    assert selected.index == 3


def test_rejects_missing_monitor() -> None:
    with pytest.raises(PulseAudioError):
        choose_pulse_source(
            [source(1, "alsa_input.pci.analog-stereo")],
            None,
            default_sink=None,
        )


def test_builds_float32_parec_command() -> None:
    command = build_parec_command(
        "alsa_output.pci.monitor",
        sample_rate=48_000,
        channels=2,
    )
    assert command[0] == "parec"
    assert "--device=alsa_output.pci.monitor" in command
    assert "--format=float32le" in command
    assert "--rate=48000" in command
