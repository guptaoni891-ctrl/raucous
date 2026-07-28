from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass


class PulseAudioError(RuntimeError):
    """Raised when PipeWire-Pulse source discovery or selection fails."""


@dataclass(frozen=True, slots=True)
class PulseSource:
    index: int
    name: str
    is_monitor: bool


def parse_short_sources(output: str) -> list[PulseSource]:
    """Parse ``pactl list short sources`` output without depending on locale."""
    sources: list[PulseSource] = []
    for line in output.splitlines():
        columns = line.split("\t")
        if len(columns) < 2:
            columns = line.split(maxsplit=2)
        if len(columns) < 2:
            continue
        try:
            index = int(columns[0])
        except ValueError:
            continue
        name = columns[1].strip()
        if not name:
            continue
        sources.append(
            PulseSource(
                index=index,
                name=name,
                is_monitor=name.casefold().endswith(".monitor")
                or ".monitor." in name.casefold(),
            )
        )
    return sources


def pulse_tools_available() -> bool:
    return shutil.which("pactl") is not None and shutil.which("parec") is not None


def _run_text(command: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=4,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PulseAudioError(f"Could not run {' '.join(command)}: {exc}") from exc
    return completed.stdout.strip()


def list_pulse_sources() -> list[PulseSource]:
    if not pulse_tools_available():
        raise PulseAudioError("pactl/parec are not installed")
    return parse_short_sources(_run_text(("pactl", "list", "short", "sources")))


def default_sink_name() -> str | None:
    if shutil.which("pactl") is None:
        return None
    try:
        value = _run_text(("pactl", "get-default-sink"))
    except PulseAudioError:
        return None
    return value or None


def choose_pulse_source(
    sources: Iterable[PulseSource],
    requested: str | None,
    *,
    default_sink: str | None,
) -> PulseSource:
    candidates = list(sources)
    if not candidates:
        raise PulseAudioError("PipeWire-Pulse reported no capture sources")

    if requested and requested.strip():
        query = requested.strip().casefold()
        matches = [source for source in candidates if query in source.name.casefold()]
        if matches:
            return sorted(
                matches,
                key=lambda item: (not item.is_monitor, item.index),
            )[0]
        raise PulseAudioError(f"No PipeWire-Pulse source contains {requested!r}")

    if default_sink:
        expected_monitor = f"{default_sink}.monitor"
        for source in candidates:
            if source.name == expected_monitor:
                return source

    monitors = [source for source in candidates if source.is_monitor]
    if monitors:
        return sorted(monitors, key=lambda item: item.index)[0]

    raise PulseAudioError(
        "No output monitor source was detected. Run 'pactl list short sources' "
        "and set audio_device to a source containing '.monitor'."
    )


def build_parec_command(
    source_name: str,
    *,
    sample_rate: int,
    channels: int,
) -> list[str]:
    return [
        "parec",
        f"--device={source_name}",
        "--raw",
        "--format=float32le",
        f"--rate={sample_rate}",
        f"--channels={channels}",
        "--latency-msec=50",
        "--client-name=Raucous",
        "--stream-name=Raucous visualizer",
    ]
