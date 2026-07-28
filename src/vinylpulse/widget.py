from __future__ import annotations

import logging
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QByteArray, QPoint, QTimer, QUrl, Qt, pyqtSlot
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QContextMenuEvent,
    QDesktopServices,
    QKeyEvent,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPixmap,
)
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QMessageBox, QWidget

from vinylpulse.audio_devices import list_input_devices
from vinylpulse.audio_worker import AudioWorker
from vinylpulse.config import (
    AppConfig,
    ConfigError,
    default_config_path,
    save_config,
)
from vinylpulse.dialogs import AudioSettingsDialog
from vinylpulse.models import TrackUpdate
from vinylpulse.pulse_audio import list_pulse_sources, pulse_tools_available
from vinylpulse.renderer import (
    DEFAULT_ACCENT,
    create_demo_artwork,
    demo_levels,
    draw_ambient_glow,
    draw_record,
    draw_visualizer,
    extract_accent,
    make_record,
    placeholder_record,
)
from vinylpulse.settings import SettingsStore
from vinylpulse.spectrum import smooth_levels
from vinylpulse.soundcard_audio import list_soundcard_devices
from vinylpulse.spotify_worker import SpotifyWorker

logger = logging.getLogger(__name__)


class VinylWidget(QWidget):
    """Transparent draggable widget coordinating workers and custom rendering."""

    def __init__(
        self,
        config: AppConfig,
        *,
        config_path: Path | None = None,
    ) -> None:
        super().__init__()
        self._config = config
        self._config_path = config_path or default_config_path()
        self._settings = SettingsStore()
        self._always_on_top, self._visualizer_enabled = self._settings.apply_defaults(
            config
        )

        self._apply_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(config.window_size, config.window_size)
        self.setWindowTitle("VinylPulse")

        self._record = placeholder_record(config.vinyl_size)
        self._accent = QColor(DEFAULT_ACCENT)
        self._angle = 0.0
        self._is_playing = False
        self._target_levels = np.zeros(config.bar_count, dtype=np.float32)
        self._display_levels = np.zeros(config.bar_count, dtype=np.float32)
        self._spotify_url: str | None = None
        self._track_label = "VinylPulse"
        self._status_message = "Starting VinylPulse…"
        self._audio_device_name: str | None = None

        self._drag_offset: QPoint | None = None
        self._system_move_active = False
        self._closing = False
        self._shutdown_started_at = 0.0

        saved_position = self._settings.window_position()
        if saved_position is not None:
            self.move(saved_position)

        self._animation_timer = QTimer(self)
        self._animation_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._animation_timer.setInterval(config.animation_interval_ms)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.start()

        self._shutdown_timer = QTimer(self)
        self._shutdown_timer.setInterval(80)
        self._shutdown_timer.timeout.connect(self._poll_shutdown)

        self._spotify_worker: SpotifyWorker | None = None
        self._audio_worker: AudioWorker | None = None
        self._demo_phase = 0.0

        if config.demo_mode:
            self._start_demo_mode()
        else:
            self._start_workers()

    def _apply_window_flags(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _start_workers(self) -> None:
        self._spotify_worker = SpotifyWorker(self._config, self)
        self._spotify_worker.track_changed.connect(self._set_track)
        self._spotify_worker.playback_changed.connect(self._set_playback_state)
        self._spotify_worker.status_changed.connect(self._set_status)
        self._spotify_worker.start()

        self._audio_worker = AudioWorker(self._config, self)
        self._audio_worker.levels_ready.connect(self._set_audio_levels)
        self._audio_worker.status_changed.connect(self._set_status)
        self._audio_worker.device_changed.connect(self._set_audio_device)
        self._audio_worker.start()

    def _start_demo_mode(self) -> None:
        artwork = create_demo_artwork()
        self._record = make_record(artwork, self._config.vinyl_size)
        self._accent = extract_accent(artwork)
        self._track_label = "Midnight Compile — VinylPulse Demo"
        self._status_message = "Demo mode"
        self._is_playing = True
        self.setToolTip(self._tooltip_text())

    def _tooltip_text(self) -> str:
        lines = [self._track_label, self._status_message]
        if self._audio_device_name:
            lines.append(f"Audio: {self._audio_device_name}")
        return "\n".join(line for line in lines if line)

    @pyqtSlot(object)
    def _set_track(self, update: TrackUpdate) -> None:
        source = QPixmap()
        if not source.loadFromData(QByteArray(update.artwork)):
            self._set_status("Qt could not decode the album artwork.")
            return

        self._record = make_record(source, self._config.vinyl_size)
        self._accent = extract_accent(source)
        self._spotify_url = update.spotify_url
        self._track_label = f"{update.title} — {update.artist}"
        self.setToolTip(self._tooltip_text())
        self.update()

    @pyqtSlot(bool)
    def _set_playback_state(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        if not is_playing:
            self._target_levels.fill(0.0)

    @pyqtSlot(object)
    def _set_audio_levels(self, levels: object) -> None:
        values = np.asarray(levels, dtype=np.float32)
        if values.shape != self._target_levels.shape:
            logger.debug(
                "Ignoring audio level shape %s; expected %s",
                values.shape,
                self._target_levels.shape,
            )
            return
        if self._is_playing:
            self._target_levels = np.clip(values, 0.0, 1.0)

    @pyqtSlot(str)
    def _set_audio_device(self, name: str) -> None:
        self._audio_device_name = name
        self.setToolTip(self._tooltip_text())

    @pyqtSlot(str)
    def _set_status(self, message: str) -> None:
        self._status_message = message
        self.setToolTip(self._tooltip_text())
        logger.info(message)

    @pyqtSlot()
    def _animate(self) -> None:
        seconds = self._animation_timer.interval() / 1000.0
        if self._is_playing:
            self._angle = (
                self._angle
                + self._config.rotation_speed_degrees_per_second * seconds
            ) % 360.0

        if self._config.demo_mode:
            self._demo_phase += seconds * 3.0
            self._target_levels = np.asarray(
                demo_levels(self._config.bar_count, self._demo_phase),
                dtype=np.float32,
            )

        self._display_levels = smooth_levels(
            self._display_levels,
            self._target_levels,
            rise=self._config.rise_smoothing,
            fall=self._config.fall_smoothing,
        )

        if not self._is_playing:
            self._target_levels *= self._config.idle_decay
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        draw_ambient_glow(
            painter,
            width=self.width(),
            height=self.height(),
            vinyl_size=self._config.vinyl_size,
            accent=self._accent,
            is_playing=self._is_playing,
        )
        if self._visualizer_enabled:
            draw_visualizer(
                painter,
                config=self._config,
                levels=self._display_levels,
                accent=self._accent,
                center_x=self.width() / 2,
                center_y=self.height() / 2,
            )
        draw_record(
            painter,
            record=self._record,
            angle=self._angle,
            center_x=self.width() / 2,
            center_y=self.height() / 2,
        )
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.windowHandle()
            if window is not None and window.startSystemMove():
                self._system_move_active = True
                self._drag_offset = None
            else:
                self._system_move_active = False
                self._drag_offset = (
                    event.globalPosition().toPoint()
                    - self.frameGeometry().topLeft()
                )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            not self._system_move_active
            and self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self._system_move_active = False
            self._settings.set_window_position(self.pos())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)

        open_action = QAction("Open in Spotify", self)
        open_action.setEnabled(bool(self._spotify_url))
        open_action.triggered.connect(self._open_in_spotify)
        menu.addAction(open_action)

        menu.addSeparator()

        visualizer_action = QAction("Visualizer", self)
        visualizer_action.setCheckable(True)
        visualizer_action.setChecked(self._visualizer_enabled)
        visualizer_action.triggered.connect(self._toggle_visualizer)
        menu.addAction(visualizer_action)

        top_action = QAction("Always on top", self)
        top_action.setCheckable(True)
        top_action.setChecked(self._always_on_top)
        top_action.triggered.connect(self._toggle_always_on_top)
        menu.addAction(top_action)

        menu.addSeparator()

        audio_action = QAction("Audio settings…", self)
        audio_action.triggered.connect(self._show_audio_settings)
        menu.addAction(audio_action)

        config_action = QAction("Open configuration folder", self)
        config_action.triggered.connect(self._open_config_folder)
        menu.addAction(config_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    @pyqtSlot()
    def _open_in_spotify(self) -> None:
        if self._spotify_url:
            QDesktopServices.openUrl(QUrl(self._spotify_url))

    @pyqtSlot(bool)
    def _toggle_visualizer(self, enabled: bool) -> None:
        self._visualizer_enabled = enabled
        self._settings.set_visualizer_enabled(enabled)
        self.update()

    @pyqtSlot(bool)
    def _toggle_always_on_top(self, enabled: bool) -> None:
        self._always_on_top = enabled
        self._settings.set_always_on_top(enabled)
        self._apply_window_flags()
        self.show()

    def _detected_audio_devices(self) -> list[str]:
        names: list[str] = []
        try:
            names.extend(device.name for device in list_soundcard_devices())
        except Exception as exc:  # noqa: BLE001
            logger.debug("Native audio discovery failed: %s", exc)

        if pulse_tools_available():
            try:
                names.extend(source.name for source in list_pulse_sources())
            except Exception as exc:  # noqa: BLE001
                logger.debug("PipeWire-Pulse discovery failed: %s", exc)

        try:
            names.extend(device.name for device in list_input_devices())
        except Exception as exc:  # noqa: BLE001
            logger.debug("PortAudio discovery failed: %s", exc)

        return sorted(set(names), key=str.casefold)

    @pyqtSlot()
    def _show_audio_settings(self) -> None:
        dialog = AudioSettingsDialog(
            self._config,
            self._detected_audio_devices(),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        backend, device, microphone_fallback = dialog.selected_values()
        try:
            updated = replace(
                self._config,
                audio_backend=backend,
                audio_device=device,
                allow_microphone_fallback=microphone_fallback,
            ).validated()
            save_config(updated, self._config_path)
        except ConfigError as exc:
            QMessageBox.warning(
                self,
                "Could not save audio settings",
                str(exc),
            )
            return

        self._config = updated
        QMessageBox.information(
            self,
            "Audio settings saved",
            "Restart VinylPulse to apply the new audio capture settings.",
        )

    @pyqtSlot()
    def _open_config_folder(self) -> None:
        folder = self._config_path.parent
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Could not open configuration folder",
                str(exc),
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._closing:
            self._closing = True
            self._shutdown_started_at = time.monotonic()
            self._animation_timer.stop()
            self._settings.set_window_position(self.pos())
            for worker in (self._audio_worker, self._spotify_worker):
                if worker is not None:
                    worker.stop()
            self._shutdown_timer.start()
            event.ignore()
            return

        if self._workers_stopped():
            self._shutdown_timer.stop()
            event.accept()
            return

        event.ignore()

    def _workers_stopped(self) -> bool:
        return all(
            worker is None or not worker.isRunning()
            for worker in (self._audio_worker, self._spotify_worker)
        )

    @pyqtSlot()
    def _poll_shutdown(self) -> None:
        if self._workers_stopped():
            self._shutdown_timer.stop()
            self.close()
            return

        if time.monotonic() - self._shutdown_started_at > 15.0:
            logger.error("Worker shutdown timed out; forcing application exit")
            self._shutdown_timer.stop()
            QApplication.exit(1)
