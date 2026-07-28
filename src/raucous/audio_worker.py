from __future__ import annotations

import logging
import queue
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import Any

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from raucous.audio_backends import backend_order
from raucous.audio_devices import (
    AudioDeviceError,
    choose_audio_device,
    list_input_devices,
    system_default_input_index,
)
from raucous.config import AppConfig
from raucous.pulse_audio import (
    PulseAudioError,
    build_parec_command,
    choose_pulse_source,
    default_sink_name,
    list_pulse_sources,
    pulse_tools_available,
)
from raucous.soundcard_audio import (
    SoundCardError,
    choose_soundcard_device,
    list_soundcard_devices,
)
from raucous.spectrum import calculate_spectrum

logger = logging.getLogger(__name__)


class AudioWorker(QThread):
    """Capture local audio and emit normalized FFT bars without blocking Qt."""

    levels_ready = pyqtSignal(object)
    status_changed = pyqtSignal(str)
    device_changed = pyqtSignal(str)

    def __init__(self, config: AppConfig, parent: Any = None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop_event = threading.Event()
        self._capture_process: subprocess.Popen[bytes] | None = None
        self._process_lock = threading.Lock()

    def stop(self) -> None:
        self._stop_event.set()
        self.requestInterruption()
        with self._process_lock:
            process = self._capture_process
        if process is not None and process.poll() is None:
            process.terminate()

    def _should_stop(self) -> bool:
        return self._stop_event.is_set() or self.isInterruptionRequested()

    def run(self) -> None:
        runners: dict[str, Callable[[], None]] = {
            "pipewire": self._run_pipewire_pulse,
            "soundcard": self._run_soundcard,
            "portaudio": self._run_portaudio,
        }
        errors: list[str] = []
        order = backend_order(sys.platform, self._config.audio_backend)

        for position, backend in enumerate(order):
            if self._should_stop():
                return
            if backend == "pipewire" and not sys.platform.startswith("linux"):
                errors.append("pipewire: available only on Linux")
                continue
            try:
                runners[backend]()
                return
            except (PulseAudioError, SoundCardError, AudioDeviceError) as exc:
                logger.warning("%s audio backend unavailable: %s", backend, exc)
                errors.append(f"{backend}: {exc}")
                if position < len(order) - 1:
                    self.status_changed.emit(
                        f"{backend.title()} audio unavailable; trying "
                        f"{order[position + 1].title()}."
                    )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected %s audio backend failure", backend)
                errors.append(f"{backend}: {exc}")

        summary = " | ".join(errors) if errors else "No compatible backend found"
        self.status_changed.emit(f"Audio visualizer unavailable: {summary}")

    def _emit_spectrum(
        self,
        samples: np.ndarray[Any, np.dtype[np.float32]],
        *,
        sample_rate: int | None = None,
    ) -> None:
        actual_rate = sample_rate or self._config.sample_rate
        levels = calculate_spectrum(
            samples,
            sample_rate=actual_rate,
            bar_count=self._config.bar_count,
            min_frequency=self._config.min_frequency,
            max_frequency=min(self._config.max_frequency, actual_rate / 2),
            sensitivity=self._config.sensitivity,
        )
        self.levels_ready.emit(levels)

    def _run_pipewire_pulse(self) -> None:
        if not pulse_tools_available():
            raise PulseAudioError(
                "pactl and parec are required (Arch package: libpulse)"
            )

        requested = (
            self._config.audio_device
            if isinstance(self._config.audio_device, str)
            else None
        )
        selected = choose_pulse_source(
            list_pulse_sources(),
            requested,
            default_sink=default_sink_name(),
        )
        channels = 2
        command = build_parec_command(
            selected.name,
            sample_rate=self._config.sample_rate,
            channels=channels,
        )

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except OSError as exc:
            raise PulseAudioError(f"Could not start parec: {exc}") from exc

        with self._process_lock:
            self._capture_process = process

        self.device_changed.emit(selected.name)
        self.status_changed.emit(f"Capturing Linux output: {selected.name}")
        bytes_per_chunk = self._config.block_size * channels * 4

        try:
            assert process.stdout is not None
            while not self._should_stop():
                raw = process.stdout.read(bytes_per_chunk)
                if not raw:
                    if process.poll() is not None:
                        break
                    continue
                samples = np.frombuffer(raw, dtype="<f4")
                complete_frames = samples.size // channels
                if complete_frames == 0:
                    continue
                samples = samples[: complete_frames * channels]
                mono = samples.reshape(-1, channels).mean(axis=1).astype(np.float32)
                self._emit_spectrum(mono)

            return_code = process.poll()
            if return_code not in (None, 0, -15) and not self._should_stop():
                stderr = b""
                if process.stderr is not None:
                    stderr = process.stderr.read()
                message = stderr.decode(errors="replace").strip()
                raise PulseAudioError(
                    f"parec exited with status {return_code}"
                    + (f": {message}" if message else "")
                )
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
            with self._process_lock:
                self._capture_process = None

    def _run_soundcard(self) -> None:
        selected = choose_soundcard_device(
            list_soundcard_devices(),
            self._config.audio_device,
            allow_microphone_fallback=self._config.allow_microphone_fallback,
            platform=sys.platform,
        )
        microphone = selected.handle
        if microphone is None:
            raise SoundCardError("Selected native audio device is unavailable")

        self.device_changed.emit(selected.name)
        kind = "output loopback" if selected.is_loopback else "input"
        self.status_changed.emit(f"Capturing native {kind}: {selected.name}")

        try:
            with microphone.recorder(
                samplerate=self._config.sample_rate,
                blocksize=max(self._config.block_size * 2, 4_096),
            ) as recorder:
                while not self._should_stop():
                    data = recorder.record(numframes=self._config.block_size)
                    samples = np.asarray(data, dtype=np.float32)
                    if samples.size == 0:
                        self._stop_event.wait(0.02)
                        continue
                    if samples.ndim == 2:
                        samples = samples.mean(axis=1)
                    elif samples.ndim != 1:
                        samples = samples.reshape(-1)
                    self._emit_spectrum(samples.astype(np.float32, copy=False))
        except Exception as exc:  # noqa: BLE001
            if self._should_stop():
                return
            raise SoundCardError(f"Native audio stream failed: {exc}") from exc

    def _run_portaudio(self) -> None:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise AudioDeviceError("The sounddevice package is not installed") from exc

        chunks: queue.Queue[np.ndarray[Any, np.dtype[np.float32]]] = queue.Queue(
            maxsize=2
        )
        try:
            selected = choose_audio_device(
                list_input_devices(),
                self._config.audio_device,
                default_input_index=system_default_input_index(),
                allow_microphone_fallback=self._config.allow_microphone_fallback,
            )
        except (OSError, RuntimeError) as exc:
            raise AudioDeviceError(str(exc)) from exc

        channels = max(1, min(2, selected.max_input_channels))
        sample_rate = self._config.sample_rate or selected.default_sample_rate
        self.device_changed.emit(selected.name)
        self.status_changed.emit(f"Capturing PortAudio input: {selected.name}")

        def callback(
            indata: np.ndarray[Any, np.dtype[np.float32]],
            frames: int,
            time_info: Any,
            status: Any,
        ) -> None:
            del frames, time_info
            if status:
                logger.debug("PortAudio callback status: %s", status)
            mono = np.asarray(indata, dtype=np.float32).mean(axis=1).copy()
            try:
                chunks.put_nowait(mono)
            except queue.Full:
                try:
                    chunks.get_nowait()
                except queue.Empty:
                    pass
                try:
                    chunks.put_nowait(mono)
                except queue.Full:
                    pass

        try:
            with sd.InputStream(
                device=selected.index,
                channels=channels,
                samplerate=sample_rate,
                blocksize=self._config.block_size,
                dtype="float32",
                latency="low",
                callback=callback,
            ):
                while not self._should_stop():
                    try:
                        samples = chunks.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    self._emit_spectrum(samples, sample_rate=sample_rate)
        except sd.PortAudioError as exc:
            raise AudioDeviceError(f"PortAudio stream failed: {exc}") from exc
