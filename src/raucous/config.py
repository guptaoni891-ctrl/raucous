from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from platformdirs import user_config_path

APP_NAME = "Raucous"
APP_AUTHOR = "Anubhav Gupta"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"


class ConfigError(ValueError):
    """Raised when configuration cannot be parsed or validated."""


@dataclass(frozen=True, slots=True)
class AppConfig:
    window_size: int = 420
    vinyl_size: int = 270
    bar_count: int = 72
    bar_gap: int = 10
    min_bar_length: int = 6
    max_bar_length: int = 45
    rotation_speed_degrees_per_second: float = 24.0
    animation_interval_ms: int = 16
    spotify_poll_seconds: float = 4.0
    request_timeout_seconds: float = 8.0
    always_on_top: bool = True
    visualizer_enabled: bool = True
    audio_backend: str = "auto"
    audio_device: int | str | None = None
    allow_microphone_fallback: bool = False
    sample_rate: int = 48_000
    block_size: int = 2_048
    sensitivity: float = 1.35
    min_frequency: float = 45.0
    max_frequency: float = 16_000.0
    rise_smoothing: float = 0.42
    fall_smoothing: float = 0.12
    idle_decay: float = 0.88
    spotify_client_id: str | None = None
    spotify_redirect_uri: str = DEFAULT_REDIRECT_URI
    demo_mode: bool = False
    debug: bool = False

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> AppConfig:
        known = {field.name for field in fields(cls)}
        unknown = sorted(set(values) - known)
        if unknown:
            names = ", ".join(unknown)
            raise ConfigError(f"Unknown configuration option(s): {names}")

        try:
            config = cls(**dict(values))
        except TypeError as exc:
            raise ConfigError(f"Invalid configuration: {exc}") from exc

        return config.validated()

    def validated(self) -> AppConfig:
        if not 280 <= self.window_size <= 1_200:
            raise ConfigError("window_size must be between 280 and 1200")
        if not 120 <= self.vinyl_size < self.window_size:
            raise ConfigError("vinyl_size must be at least 120 and below window_size")
        if not 24 <= self.bar_count <= 192:
            raise ConfigError("bar_count must be between 24 and 192")
        if self.bar_gap < 0:
            raise ConfigError("bar_gap cannot be negative")
        if self.min_bar_length < 0 or self.max_bar_length <= 0:
            raise ConfigError("bar lengths must be positive")
        if self.animation_interval_ms < 8:
            raise ConfigError("animation_interval_ms must be at least 8")
        if self.spotify_poll_seconds < 2.0:
            raise ConfigError("spotify_poll_seconds must be at least 2 seconds")
        if not 1.0 <= self.request_timeout_seconds <= 30.0:
            raise ConfigError("request_timeout_seconds must be between 1 and 30")
        if self.audio_backend not in {"auto", "pipewire", "soundcard", "portaudio"}:
            raise ConfigError(
                "audio_backend must be auto, pipewire, soundcard or portaudio"
            )
        if not 8_000 <= self.sample_rate <= 192_000:
            raise ConfigError("sample_rate must be between 8000 and 192000")
        if self.block_size < 256:
            raise ConfigError("block_size must be at least 256")
        if self.sensitivity <= 0:
            raise ConfigError("sensitivity must be positive")
        if not 1.0 <= self.min_frequency < self.max_frequency:
            raise ConfigError("frequency range is invalid")
        if self.max_frequency > self.sample_rate / 2:
            raise ConfigError("max_frequency cannot exceed the Nyquist frequency")
        for name in ("rise_smoothing", "fall_smoothing", "idle_decay"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ConfigError(f"{name} must be between 0 and 1")
        redirect = urlparse(self.spotify_redirect_uri)
        if redirect.scheme != "http" or redirect.hostname != "127.0.0.1":
            raise ConfigError(
                "spotify_redirect_uri must use the 127.0.0.1 loopback address"
            )
        try:
            redirect_port = redirect.port
        except ValueError as exc:
            raise ConfigError("spotify_redirect_uri contains an invalid port") from exc
        if redirect_port is not None and not 1 <= redirect_port <= 65_535:
            raise ConfigError("spotify_redirect_uri contains an invalid port")
        return self

    def with_runtime_flags(self, *, demo_mode: bool, debug: bool) -> AppConfig:
        return replace(self, demo_mode=demo_mode, debug=debug)

    def public_mapping(self) -> dict[str, Any]:
        values = asdict(self)
        values.pop("demo_mode")
        values.pop("debug")
        return values


def default_config_path() -> Path:
    return user_config_path(APP_NAME, APP_AUTHOR) / "config.json"


def load_config(path: Path | None = None) -> AppConfig:
    load_dotenv()
    selected_path = path or default_config_path()
    values: dict[str, Any] = {}

    if selected_path.exists():
        try:
            loaded = json.loads(selected_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"Invalid JSON in {selected_path} at line {exc.lineno}, "
                f"column {exc.colno}: {exc.msg}"
            ) from exc
        except OSError as exc:
            raise ConfigError(f"Could not read {selected_path}: {exc}") from exc

        if not isinstance(loaded, dict):
            raise ConfigError("The configuration root must be a JSON object")
        values.update(loaded)

    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")
    if client_id:
        values["spotify_client_id"] = client_id.strip()
    if redirect_uri:
        values["spotify_redirect_uri"] = redirect_uri.strip()

    return AppConfig.from_mapping(values)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    """Persist public configuration values to the selected user config file."""
    selected_path = path or default_config_path()
    try:
        selected_path.parent.mkdir(parents=True, exist_ok=True)
        selected_path.write_text(
            json.dumps(config.public_mapping(), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise ConfigError(f"Could not write {selected_path}: {exc}") from exc
    return selected_path


def write_default_config(path: Path | None = None, *, overwrite: bool = False) -> Path:
    selected_path = path or default_config_path()
    if selected_path.exists() and not overwrite:
        raise ConfigError(f"Configuration already exists: {selected_path}")

    template = AppConfig().public_mapping()
    try:
        selected_path.parent.mkdir(parents=True, exist_ok=True)
        selected_path.write_text(
            json.dumps(template, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise ConfigError(f"Could not write {selected_path}: {exc}") from exc
    return selected_path
