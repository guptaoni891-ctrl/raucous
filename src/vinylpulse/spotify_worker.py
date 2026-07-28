from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import requests
import spotipy
from platformdirs import user_cache_path
from PyQt6.QtCore import QThread, pyqtSignal
from spotipy.cache_handler import CacheFileHandler
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyPKCE

from vinylpulse import __version__
from vinylpulse.config import APP_AUTHOR, APP_NAME, AppConfig
from vinylpulse.models import TrackUpdate
from vinylpulse.spotify_parser import ParsedPlayback, parse_playback

logger = logging.getLogger(__name__)


class SpotifyWorker(QThread):
    """Poll Spotify metadata and download artwork outside the GUI thread."""

    track_changed = pyqtSignal(object)
    playback_changed = pyqtSignal(bool)
    status_changed = pyqtSignal(str)

    def __init__(self, config: AppConfig, parent: Any = None) -> None:
        super().__init__(parent)
        self._config = config
        self._stop_event = threading.Event()
        self._last_item_key: tuple[str, str] | None = None
        self._last_status: str | None = None

    def stop(self) -> None:
        self._stop_event.set()
        self.requestInterruption()

    def _emit_status_once(self, message: str) -> None:
        if message != self._last_status:
            self._last_status = message
            self.status_changed.emit(message)

    def _wait(self, seconds: float) -> bool:
        return self._stop_event.wait(seconds) or self.isInterruptionRequested()

    def _build_client(self) -> spotipy.Spotify:
        client_id = (self._config.spotify_client_id or "").strip()
        if not client_id:
            raise RuntimeError(
                "Missing SPOTIPY_CLIENT_ID. Copy .env.example to .env and add "
                "your Spotify application Client ID."
            )

        cache_dir = user_cache_path(APP_NAME, APP_AUTHOR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = Path(cache_dir) / "spotify-pkce-token.json"
        cache_handler = CacheFileHandler(cache_path=str(cache_path))
        auth_manager = SpotifyPKCE(
            client_id=client_id,
            redirect_uri=self._config.spotify_redirect_uri,
            scope="user-read-currently-playing",
            cache_handler=cache_handler,
            requests_timeout=self._config.request_timeout_seconds,
            open_browser=True,
        )
        return spotipy.Spotify(
            auth_manager=auth_manager,
            requests_timeout=self._config.request_timeout_seconds,
            retries=0,
        )

    def _fetch_artwork(
        self,
        session: requests.Session,
        playback: ParsedPlayback,
    ) -> bytes:
        response = session.get(
            playback.artwork_url,
            timeout=self._config.request_timeout_seconds,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if content_type and not content_type.startswith("image/"):
            raise RuntimeError(f"Artwork URL returned {content_type}")
        if len(response.content) > 8 * 1024 * 1024:
            raise RuntimeError("Artwork response exceeded 8 MB")
        return response.content

    @staticmethod
    def _retry_after(exc: SpotifyException) -> float | None:
        headers = getattr(exc, "headers", None)
        if not headers:
            return None
        raw = headers.get("Retry-After") or headers.get("retry-after")
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    def run(self) -> None:
        try:
            client = self._build_client()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Spotify setup failed")
            self._emit_status_once(f"Spotify setup failed: {exc}")
            return

        session = requests.Session()
        session.headers["User-Agent"] = f"VinylPulse/{__version__}"
        backoff = 2.0

        while not self._stop_event.is_set() and not self.isInterruptionRequested():
            try:
                payload = client.current_user_playing_track(
                    additional_types=("track", "episode")
                )
                playback = parse_playback(payload)

                if playback is None:
                    self.playback_changed.emit(False)
                    self._emit_status_once("Nothing is currently playing on Spotify.")
                else:
                    self.playback_changed.emit(playback.is_playing)
                    self._emit_status_once(
                        "Spotify playback detected."
                        if playback.is_playing
                        else "Spotify playback is paused."
                    )
                    item_key = (playback.item_id, playback.artwork_url)
                    if item_key != self._last_item_key:
                        artwork = self._fetch_artwork(session, playback)
                        self.track_changed.emit(
                            TrackUpdate(
                                item_id=playback.item_id,
                                title=playback.title,
                                artist=playback.artist,
                                artwork=artwork,
                                spotify_url=playback.spotify_url,
                                item_type=playback.item_type,
                            )
                        )
                        self._last_item_key = item_key

                backoff = 2.0
                if self._wait(self._config.spotify_poll_seconds):
                    break
            except SpotifyException as exc:
                logger.warning("Spotify API request failed: %s", exc, exc_info=True)
                retry_after = self._retry_after(exc)
                delay = min(max(retry_after or backoff, 2.0), 60.0)
                self._emit_status_once(
                    f"Spotify request failed; retrying in {delay:.0f}s."
                )
                backoff = min(backoff * 2.0, 60.0)
                if self._wait(delay):
                    break
            except requests.RequestException as exc:
                logger.warning("Artwork request failed: %s", exc, exc_info=True)
                self._emit_status_once(
                    f"Artwork download failed; retrying in {backoff:.0f}s."
                )
                if self._wait(backoff):
                    break
                backoff = min(backoff * 2.0, 60.0)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected Spotify worker failure")
                self._emit_status_once(
                    f"Unexpected Spotify error; retrying in {backoff:.0f}s: {exc}"
                )
                if self._wait(backoff):
                    break
                backoff = min(backoff * 2.0, 60.0)

        session.close()
