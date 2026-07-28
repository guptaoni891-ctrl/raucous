from __future__ import annotations

from PyQt6.QtCore import QPoint, QSettings

from raucous.config import APP_AUTHOR, APP_NAME, AppConfig


class SettingsStore:
    """Small typed wrapper around platform-native QSettings."""

    def __init__(self) -> None:
        self._settings = QSettings(APP_AUTHOR, APP_NAME)

    def window_position(self) -> QPoint | None:
        value = self._settings.value("window/position")
        return value if isinstance(value, QPoint) else None

    def set_window_position(self, position: QPoint) -> None:
        self._settings.setValue("window/position", position)

    def always_on_top(self, default: bool) -> bool:
        return bool(self._settings.value("window/always_on_top", default, type=bool))

    def set_always_on_top(self, enabled: bool) -> None:
        self._settings.setValue("window/always_on_top", enabled)

    def visualizer_enabled(self, default: bool) -> bool:
        return bool(self._settings.value("visualizer/enabled", default, type=bool))

    def set_visualizer_enabled(self, enabled: bool) -> None:
        self._settings.setValue("visualizer/enabled", enabled)

    def apply_defaults(self, config: AppConfig) -> tuple[bool, bool]:
        return (
            self.always_on_top(config.always_on_top),
            self.visualizer_enabled(config.visualizer_enabled),
        )
