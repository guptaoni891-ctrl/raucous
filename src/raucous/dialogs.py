from __future__ import annotations

import sys
from collections.abc import Sequence

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from raucous.config import AppConfig


class AudioSettingsDialog(QDialog):
    """Small cross-platform audio configuration dialog."""

    def __init__(
        self,
        config: AppConfig,
        devices: Sequence[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Raucous audio settings")
        self.setModal(True)
        self.setMinimumWidth(470)

        explanation = QLabel(
            "Automatic mode chooses the best capture backend for this operating "
            "system. Leave the device blank to follow the active/default output."
        )
        explanation.setWordWrap(True)

        self._backend = QComboBox(self)
        backends = ["auto", "soundcard", "portaudio"]
        if sys.platform.startswith("linux"):
            backends.insert(1, "pipewire")
        if config.audio_backend not in backends:
            backends.append(config.audio_backend)
        self._backend.addItems(backends)
        self._backend.setCurrentText(config.audio_backend)

        self._device = QComboBox(self)
        self._device.setEditable(True)
        self._device.addItem("")
        self._device.addItems(list(dict.fromkeys(devices)))
        line_edit = self._device.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("Automatic (recommended)")
        if config.audio_device is not None:
            self._device.setCurrentText(str(config.audio_device))

        self._microphone_fallback = QCheckBox(
            "Use the default microphone when output loopback is unavailable",
            self,
        )
        self._microphone_fallback.setChecked(config.allow_microphone_fallback)

        form = QFormLayout()
        form.addRow("Backend", self._backend)
        form.addRow("Device name or index", self._device)
        form.addRow("", self._microphone_fallback)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(explanation)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def selected_values(self) -> tuple[str, int | str | None, bool]:
        raw_device = self._device.currentText().strip()
        device: int | str | None
        if not raw_device:
            device = None
        elif raw_device.isdigit():
            device = int(raw_device)
        else:
            device = raw_device
        return (
            self._backend.currentText(),
            device,
            self._microphone_fallback.isChecked(),
        )
