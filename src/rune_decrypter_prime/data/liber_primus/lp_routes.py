from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class LPLineReadMode(str, Enum):
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    BOUSTROPHEDON = "boustrophedon"


class LPLineRuneSelector(str, Enum):
    ALL = "all"
    FIRST_ONLY = "first_only"
    LAST_ONLY = "last_only"


class LPSpiralDirection(str, Enum):
    CLOCKWISE = "clockwise"
    COUNTERCLOCKWISE = "counterclockwise"


class LPSpiralStartCorner(str, Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM_LEFT = "bottom_left"


@dataclass(frozen=True)
class LPSpiralRoute:
    direction: LPSpiralDirection = LPSpiralDirection.CLOCKWISE
    start_corner: LPSpiralStartCorner = LPSpiralStartCorner.TOP_LEFT
    skip_empty: bool = True


def read_lines(
    lines: Sequence[str],
    *,
    mode: LPLineReadMode,
    selector: LPLineRuneSelector = LPLineRuneSelector.ALL,
) -> str:
    pieces: list[str] = []
    for line_index, line in enumerate(lines):
        selected = _select_line(line, selector)
        if mode is LPLineReadMode.LEFT_TO_RIGHT:
            pieces.append(selected)
        elif mode is LPLineReadMode.RIGHT_TO_LEFT:
            pieces.append(selected[::-1])
        elif mode is LPLineReadMode.BOUSTROPHEDON:
            pieces.append(selected if line_index % 2 == 0 else selected[::-1])
        else:
            raise TypeError(f"Unsupported line read mode: {mode}")
    return "".join(pieces)


def make_ragged_grid(lines: Sequence[str]) -> list[list[str | None]]:
    width = max((len(line) for line in lines), default=0)
    grid: list[list[str | None]] = []
    for line in lines:
        row = [ch for ch in line]
        row.extend([None] * (width - len(row)))
        grid.append(row)
    return grid


def spiral_read(lines: Sequence[str], *, route: LPSpiralRoute | None = None) -> str:
    route = route or LPSpiralRoute()
    grid = make_ragged_grid(lines)
    if not grid:
        return ""

    rotated = _rotate_grid_to_top_left(grid, route.start_corner)
    collected = _spiral_collect(rotated, direction=route.direction, skip_empty=route.skip_empty)
    return "".join(collected)


def _select_line(line: str, selector: LPLineRuneSelector) -> str:
    if selector is LPLineRuneSelector.ALL:
        return line
    if selector is LPLineRuneSelector.FIRST_ONLY:
        return line[:1]
    if selector is LPLineRuneSelector.LAST_ONLY:
        return line[-1:] if line else ""
    raise TypeError(f"Unsupported line selector: {selector}")


def _rotate_grid_to_top_left(
    grid: list[list[str | None]],
    start_corner: LPSpiralStartCorner,
) -> list[list[str | None]]:
    if start_corner is LPSpiralStartCorner.TOP_LEFT:
        return [row[:] for row in grid]
    if start_corner is LPSpiralStartCorner.TOP_RIGHT:
        return [list(reversed(row)) for row in grid]
    if start_corner is LPSpiralStartCorner.BOTTOM_RIGHT:
        return [list(reversed(row)) for row in reversed(grid)]
    if start_corner is LPSpiralStartCorner.BOTTOM_LEFT:
        return [row[:] for row in reversed(grid)]
    raise TypeError(f"Unsupported start corner: {start_corner}")


def _spiral_collect(
    grid: list[list[str | None]],
    *,
    direction: LPSpiralDirection,
    skip_empty: bool,
) -> list[str]:
    top = 0
    bottom = len(grid) - 1
    left = 0
    right = len(grid[0]) - 1 if grid and grid[0] else -1
    out: list[str] = []

    def maybe_add(value: str | None) -> None:
        if value is None and skip_empty:
            return
        if value is None:
            out.append("")
            return
        out.append(value)

    while top <= bottom and left <= right:
        if direction is LPSpiralDirection.CLOCKWISE:
            for col in range(left, right + 1):
                maybe_add(grid[top][col])
            top += 1

            for row in range(top, bottom + 1):
                maybe_add(grid[row][right])
            right -= 1

            if top <= bottom:
                for col in range(right, left - 1, -1):
                    maybe_add(grid[bottom][col])
                bottom -= 1

            if left <= right:
                for row in range(bottom, top - 1, -1):
                    maybe_add(grid[row][left])
                left += 1
        elif direction is LPSpiralDirection.COUNTERCLOCKWISE:
            for row in range(top, bottom + 1):
                maybe_add(grid[row][left])
            left += 1

            for col in range(left, right + 1):
                maybe_add(grid[bottom][col])
            bottom -= 1

            if left <= right:
                for row in range(bottom, top - 1, -1):
                    maybe_add(grid[row][right])
                right -= 1

            if top <= bottom:
                for col in range(right, left - 1, -1):
                    maybe_add(grid[top][col])
                top += 1
        else:
            raise TypeError(f"Unsupported spiral direction: {direction}")
    return out


__all__ = [
    "LPLineReadMode",
    "LPLineRuneSelector",
    "LPSpiralDirection",
    "LPSpiralStartCorner",
    "LPSpiralRoute",
    "read_lines",
    "make_ragged_grid",
    "spiral_read",
]
