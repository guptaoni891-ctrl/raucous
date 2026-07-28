from __future__ import annotations

from vinylpulse.spotify_parser import parse_playback


def test_parses_track_payload() -> None:
    parsed = parse_playback(
        {
            "is_playing": True,
            "item": {
                "id": "track-1",
                "name": "Midnight Compile",
                "type": "track",
                "artists": [{"name": "Anubhav"}, {"name": "Python"}],
                "album": {"images": [{"url": "https://example.test/cover.jpg"}]},
                "external_urls": {"spotify": "https://open.spotify.com/track/1"},
            },
        }
    )
    assert parsed is not None
    assert parsed.artist == "Anubhav, Python"
    assert parsed.is_playing is True
    assert parsed.artwork_url.endswith("cover.jpg")


def test_parses_episode_payload() -> None:
    parsed = parse_playback(
        {
            "is_playing": False,
            "item": {
                "id": "episode-1",
                "name": "Building Desktop Apps",
                "type": "episode",
                "show": {"publisher": "VinylPulse Labs"},
                "images": [{"url": "https://example.test/episode.jpg"}],
                "external_urls": {},
            },
        }
    )
    assert parsed is not None
    assert parsed.item_type == "episode"
    assert parsed.artist == "VinylPulse Labs"
    assert parsed.spotify_url is None


def test_missing_artwork_is_rejected() -> None:
    assert (
        parse_playback(
            {
                "item": {
                    "id": "track-1",
                    "name": "No Artwork",
                    "type": "track",
                    "artists": [],
                    "album": {"images": []},
                }
            }
        )
        is None
    )
