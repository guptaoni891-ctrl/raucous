from __future__ import annotations

import math


def radial_bar_segment(
    *,
    index: int,
    count: int,
    center_x: float,
    center_y: float,
    base_radius: float,
    bar_length: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return the start and end coordinates for one circular spectrum bar."""

    if count <= 0:
        raise ValueError("count must be positive")
    if not 0 <= index < count:
        raise ValueError("index must be inside the bar range")

    angle = -math.pi / 2 + 2 * math.pi * index / count
    direction_x = math.cos(angle)
    direction_y = math.sin(angle)

    start = (
        center_x + direction_x * base_radius,
        center_y + direction_y * base_radius,
    )
    end = (
        center_x + direction_x * (base_radius + bar_length),
        center_y + direction_y * (base_radius + bar_length),
    )
    return start, end
