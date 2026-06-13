from __future__ import annotations

import pytest

from rune_decrypter_prime.data.liber_primus.lp_routes import (
    LPLineReadMode,
    LPLineRuneSelector,
    LPSpiralDirection,
    LPSpiralRoute,
    read_lines,
    spiral_read,
)


pytestmark = pytest.mark.tier_a


def test_read_lines_left_to_right() -> None:
    assert read_lines(["ABC", "DEF", "GHI"], mode=LPLineReadMode.LEFT_TO_RIGHT) == "ABCDEFGHI"


def test_read_lines_right_to_left() -> None:
    assert read_lines(["ABC", "DEF", "GHI"], mode=LPLineReadMode.RIGHT_TO_LEFT) == "CBAFEDIHG"


def test_read_lines_boustrophedon() -> None:
    assert read_lines(["ABC", "DEF", "GHI"], mode=LPLineReadMode.BOUSTROPHEDON) == "ABCFEDGHI"


def test_first_and_last_rune_per_line() -> None:
    assert read_lines(
        ["ABC", "DE", "F"],
        mode=LPLineReadMode.LEFT_TO_RIGHT,
        selector=LPLineRuneSelector.FIRST_ONLY,
    ) == "ADF"
    assert read_lines(
        ["ABC", "DE", "F"],
        mode=LPLineReadMode.LEFT_TO_RIGHT,
        selector=LPLineRuneSelector.LAST_ONLY,
    ) == "CEF"


def test_spiral_read_clockwise_on_square_grid() -> None:
    assert spiral_read(["ABC", "DEF", "GHI"]) == "ABCFIHGDE"


def test_spiral_read_counterclockwise_on_square_grid() -> None:
    route = LPSpiralRoute(direction=LPSpiralDirection.COUNTERCLOCKWISE)
    assert spiral_read(["ABC", "DEF", "GHI"], route=route) == "ADGHIFCBE"


def test_spiral_read_skips_empty_cells_on_ragged_grid() -> None:
    assert spiral_read(["ABCD", "EF", "G"]) == "ABCDGEF"
