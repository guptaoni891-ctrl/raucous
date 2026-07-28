from __future__ import annotations

import json
from pathlib import Path

import pytest

from raucous.config import AppConfig, ConfigError, load_config, write_default_config


def test_defaults_are_valid() -> None:
    config = AppConfig().validated()
    assert config.bar_count == 72
    assert config.spotify_client_id is None


def test_unknown_configuration_key_is_rejected() -> None:
    with pytest.raises(ConfigError, match="Unknown configuration"):
        AppConfig.from_mapping({"bar_counts": 64})


def test_invalid_frequency_range_is_rejected() -> None:
    with pytest.raises(ConfigError, match="frequency range"):
        AppConfig.from_mapping({"min_frequency": 500.0, "max_frequency": 100.0})


def test_environment_overrides_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"spotify_client_id": "file-id"}), encoding="utf-8")
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "environment-id")
    config = load_config(path)
    assert config.spotify_client_id == "environment-id"


def test_write_default_config(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "config.json"
    created = write_default_config(path)
    payload = json.loads(created.read_text(encoding="utf-8"))
    assert payload["window_size"] == 420
    assert "demo_mode" not in payload


def test_rejects_unknown_audio_backend() -> None:
    with pytest.raises(ConfigError, match="audio_backend"):
        AppConfig.from_mapping({"audio_backend": "alsa"})


def test_save_config_round_trip(tmp_path: Path) -> None:
    from raucous.config import save_config

    path = tmp_path / "saved" / "config.json"
    save_config(AppConfig(audio_backend="soundcard"), path)
    loaded = load_config(path)
    assert loaded.audio_backend == "soundcard"


def test_rejects_redirect_hostname_lookalike() -> None:
    with pytest.raises(ConfigError, match="127.0.0.1"):
        AppConfig.from_mapping(
            {"spotify_redirect_uri": "http://127.0.0.1.example.com/callback"}
        )


def test_accepts_custom_loopback_port() -> None:
    config = AppConfig.from_mapping(
        {"spotify_redirect_uri": "http://127.0.0.1:9999/callback"}
    )
    assert config.spotify_redirect_uri.endswith("9999/callback")
