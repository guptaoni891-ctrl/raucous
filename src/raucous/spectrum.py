from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float32]


def calculate_spectrum(
    samples: NDArray[np.floating],
    *,
    sample_rate: int,
    bar_count: int,
    min_frequency: float,
    max_frequency: float,
    sensitivity: float,
) -> FloatArray:
    """Convert mono PCM samples into normalized logarithmic FFT bands."""

    values = np.asarray(samples, dtype=np.float32).reshape(-1)
    if values.size < 8 or not np.any(values):
        return np.zeros(bar_count, dtype=np.float32)
    if bar_count <= 0:
        raise ValueError("bar_count must be positive")
    if not 0 < min_frequency < max_frequency <= sample_rate / 2:
        raise ValueError("frequency bounds are invalid")

    centered = values - float(np.mean(values))
    windowed = centered * np.hanning(values.size).astype(np.float32)
    magnitudes = np.abs(np.fft.rfft(windowed)) / max(values.size, 1)
    frequencies = np.fft.rfftfreq(values.size, d=1.0 / sample_rate)
    edges = np.geomspace(min_frequency, max_frequency, bar_count + 1)

    levels = np.zeros(bar_count, dtype=np.float32)
    for index in range(bar_count):
        mask = (frequencies >= edges[index]) & (frequencies < edges[index + 1])
        if np.any(mask):
            levels[index] = float(np.sqrt(np.mean(np.square(magnitudes[mask]))))

    # Convert the expected float PCM range into a stable 0..1 display range.
    decibels = 20.0 * np.log10(levels + 1e-7)
    normalized = (decibels + 72.0) / 72.0
    normalized *= sensitivity
    return np.clip(normalized, 0.0, 1.0).astype(np.float32)


def smooth_levels(
    current: NDArray[np.floating],
    target: NDArray[np.floating],
    *,
    rise: float,
    fall: float,
) -> FloatArray:
    """Apply asymmetric interpolation so peaks rise quickly and decay smoothly."""

    current_values = np.asarray(current, dtype=np.float32)
    target_values = np.asarray(target, dtype=np.float32)
    if current_values.shape != target_values.shape:
        raise ValueError("current and target levels must have the same shape")
    if not 0.0 <= rise <= 1.0 or not 0.0 <= fall <= 1.0:
        raise ValueError("smoothing coefficients must be between 0 and 1")

    coefficients = np.where(target_values > current_values, rise, fall).astype(
        np.float32
    )
    return (
        current_values + coefficients * (target_values - current_values)
    ).astype(np.float32)
