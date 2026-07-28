from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)

from vinylpulse.config import AppConfig
from vinylpulse.geometry import radial_bar_segment

DEFAULT_ACCENT = QColor(225, 232, 255)


def placeholder_record(size: int) -> QPixmap:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(20, 20, 24, 245))
    painter.drawEllipse(QRectF(2, 2, size - 4, size - 4))
    _draw_grooves(painter, size)
    painter.end()
    return QPixmap.fromImage(image)


def create_demo_artwork(size: int = 640) -> QPixmap:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(27, 31, 48))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QRadialGradient(QPointF(size * 0.35, size * 0.3), size * 0.85)
    gradient.setColorAt(0.0, QColor(126, 249, 255))
    gradient.setColorAt(0.42, QColor(99, 102, 241))
    gradient.setColorAt(1.0, QColor(19, 22, 38))
    painter.fillRect(image.rect(), QBrush(gradient))

    painter.setPen(QPen(QColor(255, 255, 255, 55), max(2, size // 100)))
    for offset in range(-size, size * 2, size // 8):
        painter.drawLine(offset, 0, offset + size, size)

    painter.setPen(QColor(255, 255, 255, 235))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(max(28, size // 14))
    painter.setFont(font)
    painter.drawText(
        image.rect().adjusted(size // 12, 0, -size // 12, -size // 8),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        "VINYLPULSE",
    )
    painter.end()
    return QPixmap.fromImage(image)


def make_record(artwork: QPixmap, size: int) -> QPixmap:
    """Build a vinyl record while preserving the full square album artwork."""

    result = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(13, 13, 16, 252))
    painter.drawEllipse(QRectF(2, 2, size - 4, size - 4))
    _draw_grooves(painter, size)

    cover_side = int(size * 0.46)
    scaled = artwork.scaled(
        cover_side,
        cover_side,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.fillRect(
        QRectF(
            (size - cover_side) / 2,
            (size - cover_side) / 2,
            cover_side,
            cover_side,
        ),
        QColor(8, 8, 10),
    )
    painter.drawPixmap(x, y, scaled)

    painter.setPen(QPen(QColor(255, 255, 255, 28), 1.0))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(4, 4, size - 8, size - 8))
    painter.end()
    return QPixmap.fromImage(result)


def _draw_grooves(painter: QPainter, size: int) -> None:
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    center = size / 2
    for ratio in (0.93, 0.86, 0.79, 0.72, 0.65, 0.58, 0.53):
        diameter = size * ratio
        alpha = 24 if int(ratio * 100) % 2 else 36
        painter.setPen(QPen(QColor(255, 255, 255, alpha), 1.0))
        painter.drawEllipse(
            QRectF(
                center - diameter / 2,
                center - diameter / 2,
                diameter,
                diameter,
            )
        )
    painter.restore()


def extract_accent(source: QPixmap) -> QColor:
    image = source.scaled(
        40,
        40,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    ).toImage()

    samples: list[tuple[int, int, int]] = []
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            color = image.pixelColor(x, y)
            _hue, saturation, value, _alpha = color.getHsv()
            if color.alpha() > 180 and saturation > 45 and value > 70:
                samples.append((color.red(), color.green(), color.blue()))

    if not samples:
        return QColor(DEFAULT_ACCENT)

    accent = QColor(
        sum(sample[0] for sample in samples) // len(samples),
        sum(sample[1] for sample in samples) // len(samples),
        sum(sample[2] for sample in samples) // len(samples),
    )
    if accent.lightness() < 125:
        accent = accent.lighter(155)
    return accent


def draw_ambient_glow(
    painter: QPainter,
    *,
    width: int,
    height: int,
    vinyl_size: int,
    accent: QColor,
    is_playing: bool,
) -> None:
    center = QPointF(width / 2, height / 2)
    radius = vinyl_size / 2 + 18
    gradient = QRadialGradient(center, radius)

    transparent = QColor(accent)
    transparent.setAlpha(0)
    soft = QColor(accent)
    soft.setAlpha(48 if is_playing else 20)
    edge = QColor(accent)
    edge.setAlpha(84 if is_playing else 30)

    gradient.setColorAt(0.70, transparent)
    gradient.setColorAt(0.87, soft)
    gradient.setColorAt(0.97, edge)
    gradient.setColorAt(1.0, transparent)

    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawEllipse(center, radius, radius)
    painter.restore()


def draw_visualizer(
    painter: QPainter,
    *,
    config: AppConfig,
    levels: object,
    accent: QColor,
    center_x: float,
    center_y: float,
) -> None:
    base_radius = config.vinyl_size / 2 + config.bar_gap
    painter.save()

    for index, raw_level in enumerate(levels):
        level = float(raw_level)
        bar_length = config.min_bar_length + level * config.max_bar_length
        start_xy, end_xy = radial_bar_segment(
            index=index,
            count=config.bar_count,
            center_x=center_x,
            center_y=center_y,
            base_radius=base_radius,
            bar_length=bar_length,
        )
        start = QPointF(*start_xy)
        end = QPointF(*end_xy)

        glow = QColor(accent)
        glow.setAlpha(int(18 + level * 76))
        glow_pen = QPen(glow, 8.0)
        glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(glow_pen)
        painter.drawLine(start, end)

        foreground = QColor(accent)
        foreground.setAlpha(int(110 + level * 145))
        pen = QPen(foreground, 2.1 + level * 1.9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(start, end)

    painter.restore()


def draw_record(
    painter: QPainter,
    *,
    record: QPixmap,
    angle: float,
    center_x: float,
    center_y: float,
) -> None:
    painter.save()
    painter.translate(center_x, center_y)
    painter.rotate(angle)
    painter.drawPixmap(-record.width() // 2, -record.height() // 2, record)
    painter.restore()


def demo_levels(bar_count: int, phase: float) -> list[float]:
    values: list[float] = []
    for index in range(bar_count):
        angle = 2.0 * math.pi * index / bar_count
        low = 0.5 + 0.5 * math.sin(angle * 2.0 + phase)
        mid = 0.5 + 0.5 * math.sin(angle * 5.0 - phase * 1.6)
        pulse = 0.5 + 0.5 * math.sin(phase * 2.4)
        values.append(min(1.0, 0.08 + 0.42 * low + 0.30 * mid * pulse))
    return values
