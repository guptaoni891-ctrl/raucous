from __future__ import annotations

import numpy as np
import pytest

from raucous.spectrum import calculate_spectrum, smooth_levels


def test_silence_returns_zero_levels() -> None:
    levels = calculate_spectrum(
        np.zeros(2048, dtype=np.float32),
        sample_rate=48_000,
        bar_count=64,
        min_frequency=45,
        max_frequency=16_000,
        sensitivity=1.0,
    )
    assert levels.shape == (64,)
    assert np.all(levels == 0)


def test_tone_produces_visible_peak() -> None:
    sample_rate = 48_000
    timeline = np.arange(4096, dtype=np.float32) / sample_rate
    samples = 0.8 * np.sin(2 * np.pi * 440.0 * timeline)
    levels = calculate_spectrum(
        samples,
        sample_rate=sample_rate,
        bar_count=72,
        min_frequency=45,
        max_frequency=16_000,
        sensitivity=1.35,
    )
    assert float(np.max(levels)) > 0.35
    assert int(np.argmax(levels)) > 0


def test_smoothing_uses_different_rise_and_fall_rates() -> None:
    current = np.array([0.2, 0.8], dtype=np.float32)
    target = np.array([1.0, 0.0], dtype=np.float32)
    result = smooth_levels(current, target, rise=0.5, fall=0.1)
    assert result == pytest.approx(np.array([0.6, 0.72], dtype=np.float32))


def test_smoothing_shape_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="same shape"):
        smooth_levels(np.zeros(2), np.zeros(3), rise=0.5, fall=0.1)
