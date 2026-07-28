from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from raucous import __version__
from raucous.audio_devices import list_input_devices
from raucous.config import (
    APP_AUTHOR,
    APP_NAME,
    AppConfig,
    ConfigError,
    default_config_path,
    load_config,
    save_config,
    write_default_config,
)
from raucous.logging_config import configure_logging
from raucous.pulse_audio import (
    PulseAudioError,
    list_pulse_sources,
    pulse_tools_available,
)
from raucous.soundcard_audio import SoundCardError, list_soundcard_devices

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="raucous",
        description="Spotify now-playing vinyl widget and circular audio visualizer.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, help="Path to a JSON config file")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run without Spotify or audio capture",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logs")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--list-audio-devices",
        action="store_true",
        help="Print available audio inputs and output-loopback devices and exit",
    )
    parser.add_argument(
        "--print-config-path",
        action="store_true",
        help="Print the default configuration path and exit",
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Write a default configuration file and exit",
    )
    return parser


def _print_audio_devices() -> int:
    found_any = False

    try:
        native_devices = list_soundcard_devices()
    except SoundCardError as exc:
        print(f"Could not query native audio devices: {exc}", file=sys.stderr)
    else:
        if native_devices:
            found_any = True
            print(
                "NATIVE AUDIO DEVICES "
                "(Windows WASAPI / macOS CoreAudio / Linux Pulse)"
            )
            print(f"{'INDEX':>5}  {'TYPE':>10}  {'DEFAULT':>9}  NAME")
            for device in native_devices:
                kind = "loopback" if device.is_loopback else "input"
                default = "output" if device.is_default_output else (
                    "input" if device.is_default_input else ""
                )
                print(
                    f"{device.index:>5}  {kind:>10}  {default:>9}  {device.name}"
                )
            print()

    if sys.platform.startswith("linux") and pulse_tools_available():
        try:
            sources = list_pulse_sources()
        except PulseAudioError as exc:
            print(f"Could not query PipeWire-Pulse sources: {exc}", file=sys.stderr)
        else:
            if sources:
                found_any = True
                print("LINUX PIPEWIRE-PULSE SOURCES")
                print(f"{'INDEX':>5}  {'TYPE':>8}  NAME")
                for source in sources:
                    kind = "monitor" if source.is_monitor else "input"
                    print(f"{source.index:>5}  {kind:>8}  {source.name}")
                print()

    try:
        devices = list_input_devices()
    except Exception as exc:  # noqa: BLE001
        print(f"Could not query PortAudio devices: {exc}", file=sys.stderr)
        devices = []

    if devices:
        found_any = True
        print("PORTAUDIO INPUTS (fallback)")
        print(f"{'INDEX':>5}  {'CHANNELS':>8}  {'RATE':>8}  NAME")
        for device in devices:
            marker = " [loopback candidate]" if device.is_loopback_candidate else ""
            print(
                f"{device.index:>5}  {device.max_input_channels:>8}  "
                f"{device.default_sample_rate:>8}  {device.name}{marker}"
            )

    if not found_any:
        print("No audio capture devices found.")
    return 0


def _configure_qt_platform(environment: dict[str, str] | None = None) -> None:
    env = os.environ if environment is None else environment
    if not sys.platform.startswith("linux"):
        return
    if env.get("QT_QPA_PLATFORM"):
        return
    session = env.get("XDG_SESSION_TYPE", "").casefold()
    desktop = env.get("XDG_CURRENT_DESKTOP", "").casefold()
    if session == "wayland" or "hyprland" in desktop:
        env["QT_QPA_PLATFORM"] = "wayland;xcb"


def _install_exception_hook(message_box: object) -> None:
    def handle_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        traceback: object,
    ) -> None:
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, traceback),
        )
        critical = getattr(message_box, "critical")
        critical(
            None,
            "Raucous error",
            "Raucous encountered an unexpected error. Check the log file for "
            "details.",
        )

    sys.excepthook = handle_exception


def _first_run_setup(
    config: AppConfig,
    config_path: Path | None,
    *,
    message_box: Any,
    input_dialog: Any,
) -> AppConfig | None:
    """Collect a public Spotify Client ID or offer demo mode on first launch."""
    if config.demo_mode or (config.spotify_client_id or "").strip():
        return config

    dialog = message_box()
    dialog.setWindowTitle("Set up Raucous")
    dialog.setIcon(message_box.Icon.Information)
    dialog.setText("Raucous needs a Spotify application Client ID.")
    dialog.setInformativeText(
        "Create an app in the Spotify Developer Dashboard, add "
        "http://127.0.0.1:8888/callback as its redirect URI, then enter the "
        "public Client ID. Spotify currently requires Premium for Web API "
        "development access. You can also launch Demo Mode without Spotify."
    )
    enter_button = dialog.addButton(
        "Enter Client ID",
        message_box.ButtonRole.AcceptRole,
    )
    demo_button = dialog.addButton("Demo Mode", message_box.ButtonRole.ActionRole)
    quit_button = dialog.addButton("Quit", message_box.ButtonRole.RejectRole)
    dialog.exec()
    clicked = dialog.clickedButton()

    if clicked is demo_button:
        return replace(config, demo_mode=True)
    if clicked is quit_button or clicked is None:
        return None
    if clicked is not enter_button:
        return None

    while True:
        client_id, accepted = input_dialog.getText(
            None,
            "Spotify Client ID",
            "Paste your Spotify application Client ID:",
        )
        if not accepted:
            return None
        client_id = client_id.strip()
        if client_id:
            configured = replace(config, spotify_client_id=client_id).validated()
            try:
                save_config(configured, config_path)
            except ConfigError as exc:
                message_box.warning(
                    None,
                    "Could not save configuration",
                    f"Raucous will continue for this session only.\n\n{exc}",
                )
            return configured
        message_box.warning(
            None,
            "Client ID required",
            "Enter a non-empty Spotify Client ID, choose Demo Mode, or quit.",
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.print_config_path:
        print(default_config_path())
        return 0

    if args.create_config:
        try:
            created = write_default_config(args.config)
        except ConfigError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(f"Created {created}")
        return 0

    if args.list_audio_devices:
        return _print_audio_devices()

    try:
        config = load_config(args.config).with_runtime_flags(
            demo_mode=args.demo or args.smoke_test,
            debug=args.debug,
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    log_path = configure_logging(debug=config.debug)
    logger.info("Starting Raucous %s", __version__)
    logger.info("Log file: %s", log_path)

    _configure_qt_platform()

    try:
        from PyQt6.QtCore import QCoreApplication, QTimer, Qt
        from PyQt6.QtGui import QGuiApplication, QIcon
        from PyQt6.QtWidgets import QApplication, QInputDialog, QMessageBox
    except ImportError:
        logger.error("PyQt6 is not installed")
        print(
            "PyQt6 is not installed. Run 'python -m pip install -e .' first.",
            file=sys.stderr,
        )
        return 1

    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setOrganizationName(APP_AUTHOR)
    QGuiApplication.setDesktopFileName("raucous")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(list(argv) if argv is not None else sys.argv)
    icon_path = Path(__file__).resolve().parent / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setQuitOnLastWindowClosed(True)
    _install_exception_hook(QMessageBox)

    config = _first_run_setup(
        config,
        args.config,
        message_box=QMessageBox,
        input_dialog=QInputDialog,
    )
    if config is None:
        return 0

    from raucous.widget import VinylWidget

    widget = VinylWidget(config, config_path=args.config)
    widget.show()
    if args.smoke_test:
        QTimer.singleShot(750, widget.close)
    return app.exec()
