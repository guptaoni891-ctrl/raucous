from __future__ import annotations

from raucous import app


def test_configures_wayland_for_hyprland(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    environment = {
        "XDG_SESSION_TYPE": "wayland",
        "XDG_CURRENT_DESKTOP": "Hyprland",
    }
    monkeypatch.setattr(app.sys, "platform", "linux")
    app._configure_qt_platform(environment)
    assert environment["QT_QPA_PLATFORM"] == "wayland;xcb"


def test_preserves_explicit_qt_backend(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    environment = {
        "XDG_SESSION_TYPE": "wayland",
        "QT_QPA_PLATFORM": "xcb",
    }
    monkeypatch.setattr(app.sys, "platform", "linux")
    app._configure_qt_platform(environment)
    assert environment["QT_QPA_PLATFORM"] == "xcb"


def test_smoke_test_flag_is_hidden_but_parsed() -> None:
    args = app.build_parser().parse_args(["--smoke-test"])
    assert args.smoke_test is True
    assert "--smoke-test" not in app.build_parser().format_help()
