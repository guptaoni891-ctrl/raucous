from __future__ import annotations

import math

import pytest

from vinylpulse.geometry import radial_bar_segment


def test_first_bar_points_up() -> None:
    start, end = radial_bar_segment(
        index=0,
        count=4,
        center_x=100.0,
        center_y=100.0,
        base_radius=20.0,
        bar_length=10.0,
    )
    assert start == pytest.approx((100.0, 80.0))
    assert end == pytest.approx((100.0, 70.0))


def test_quarter_turn_points_right() -> None:
    start, _end = radial_bar_segment(
        index=1,
        count=4,
        center_x=0.0,
        center_y=0.0,
        base_radius=2.0,
        bar_length=1.0,
    )
    assert math.isclose(start[0], 2.0, abs_tol=1e-9)
    assert math.isclose(start[1], 0.0, abs_tol=1e-9)


def test_invalid_index_is_rejected() -> None:
    with pytest.raises(ValueError):
        radial_bar_segment(
            index=4,
            count=4,
            center_x=0,
            center_y=0,
            base_radius=1,
            bar_length=1,
        )
