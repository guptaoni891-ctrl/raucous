from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ParsedPlayback:
    item_id: str
    title: str
    artist: str
    artwork_url: str
    spotify_url: str | None
    item_type: str
    is_playing: bool


def _first_image_url(images: object) -> str | None:
    if not isinstance(images, Sequence) or isinstance(images, (str, bytes)):
        return None
    for image in images:
        if isinstance(image, Mapping):
            url = image.get("url")
            if isinstance(url, str) and url:
                return url
    return None


def parse_playback(payload: Mapping[str, Any] | None) -> ParsedPlayback | None:
    """Defensively parse Spotify's currently-playing response."""

    if not payload:
        return None
    item = payload.get("item")
    if not isinstance(item, Mapping):
        return None

    item_id = item.get("id")
    title = item.get("name")
    item_type = item.get("type", "track")
    if not isinstance(item_id, str) or not item_id:
        return None
    if not isinstance(title, str) or not title:
        return None
    if not isinstance(item_type, str):
        item_type = "track"

    artist = "Unknown artist"
    artwork_url: str | None = None

    if item_type == "episode":
        show = item.get("show")
        if isinstance(show, Mapping):
            publisher = show.get("publisher") or show.get("name")
            if isinstance(publisher, str) and publisher:
                artist = publisher
        artwork_url = _first_image_url(item.get("images"))
    else:
        artists = item.get("artists")
        if isinstance(artists, Sequence) and not isinstance(artists, (str, bytes)):
            names = [
                artist_value.get("name")
                for artist_value in artists
                if isinstance(artist_value, Mapping)
                and isinstance(artist_value.get("name"), str)
            ]
            clean_names = [name for name in names if name]
            if clean_names:
                artist = ", ".join(clean_names)

        album = item.get("album")
        if isinstance(album, Mapping):
            artwork_url = _first_image_url(album.get("images"))

    if not artwork_url:
        return None

    spotify_url: str | None = None
    external_urls = item.get("external_urls")
    if isinstance(external_urls, Mapping):
        candidate = external_urls.get("spotify")
        if isinstance(candidate, str) and candidate:
            spotify_url = candidate

    return ParsedPlayback(
        item_id=item_id,
        title=title,
        artist=artist,
        artwork_url=artwork_url,
        spotify_url=spotify_url,
        item_type=item_type,
        is_playing=bool(payload.get("is_playing", False)),
    )
