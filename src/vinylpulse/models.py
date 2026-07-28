from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackUpdate:
    """Artwork and metadata delivered from the Spotify worker."""

    item_id: str
    title: str
    artist: str
    artwork: bytes
    spotify_url: str | None
    item_type: str
