from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Sequence


def unique_sorted_ints(values: Iterable[int]) -> tuple[int, ...]:
    seen: set[int] = set()
    out: list[int] = []
    for raw in values:
        value = int(raw)
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    out.sort()
    return tuple(out)


def fixture_length_from_metadata(
    *,
    fixture_row: Mapping[str, Any],
    repo_root: Any,
    load_json_fn: Callable[..., Any],
) -> int:
    for key in ("length", "text_length", "plaintext_length"):
        value = fixture_row.get(key)
        if isinstance(value, int) and value > 0:
            return int(value)

    rel_path = fixture_row.get("path")
    if isinstance(rel_path, str) and rel_path.strip():
        fixture_path = (repo_root / rel_path).resolve()
        if fixture_path.exists():
            payload = load_json_fn(fixture_path)
            if isinstance(payload, Mapping):
                for key in ("length", "text_length", "plaintext_length"):
                    value = payload.get(key)
                    if isinstance(value, int) and value > 0:
                        return int(value)

    raise ValueError(
        f"fixture {fixture_row.get('text_fixture_id', '')!r} missing length metadata "
        "(expected length/text_length/plaintext_length or path payload with one of those fields)"
    )


def load_fixture_specs(
    *,
    campaign_config: Mapping[str, Any],
    repo_root: Any,
    fixture_ids: Sequence[str] | None,
    fixture_length_override: int | None,
    fixture_spec_cls: type,
    fixture_length_from_metadata_fn: Callable[..., int],
) -> list[Any]:
    rows = campaign_config.get("fixtures")
    if not isinstance(rows, list) or not rows:
        raise ValueError("campaign_config.fixtures must be a non-empty list")

    selected: set[str] | None = None
    if fixture_ids is not None:
        selected = {str(x) for x in fixture_ids}

    out: list[Any] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each fixtures row must be an object")
        fixture_id = str(row.get("text_fixture_id", "")).strip()
        if not fixture_id:
            raise ValueError("fixtures row missing text_fixture_id")
        if selected is not None and fixture_id not in selected:
            continue
        length = fixture_length_from_metadata_fn(fixture_row=row, repo_root=repo_root)
        if fixture_length_override is not None:
            override = int(fixture_length_override)
            if override <= 0:
                raise ValueError(
                    f"fixture_length_override must be > 0, got {fixture_length_override}"
                )
            length = int(override)
        src = row.get("path")
        source_path = (str(src).strip() if isinstance(src, str) and str(src).strip() else None)
        out.append(
            fixture_spec_cls(
                fixture_id=fixture_id,
                length=int(length),
                source_path=source_path,
            )
        )

    if not out:
        if selected is not None:
            raise ValueError(
                "fixture filter matched zero rows; " f"requested={sorted(selected)}"
            )
        raise ValueError("no fixtures resolved")
    return out


def resolve_period_columns(
    *,
    campaign_config: Mapping[str, Any],
    use_campaign_grid: bool,
    periods_override: Sequence[int] | None,
    columns_override_by_period: Mapping[int, Sequence[int]] | None,
    unique_sorted_ints_fn: Callable[[Iterable[int]], tuple[int, ...]],
) -> dict[int, tuple[int, ...]]:
    grid = campaign_config.get("grid", {})
    if not isinstance(grid, Mapping):
        grid = {}

    period_min = int(grid.get("period_min", 0) or 0)
    period_max = int(grid.get("period_max", 0) or 0)
    columns_min = int(grid.get("columns_min", 0) or 0)
    columns_max = int(grid.get("columns_max", 0) or 0)

    if periods_override is not None:
        # Preserve explicit caller ordering (for example p13-first campaigns).
        seen_periods: set[int] = set()
        ordered_periods: list[int] = []
        for raw in periods_override:
            period = int(raw)
            if period in seen_periods:
                continue
            seen_periods.add(period)
            ordered_periods.append(period)
        periods = tuple(ordered_periods)
    elif use_campaign_grid:
        if period_min <= 0 or period_max < period_min:
            raise ValueError("campaign grid period_min/period_max are invalid")
        periods = tuple(range(period_min, period_max + 1))
    else:
        raise ValueError(
            "no periods source configured (set PERIODS_OVERRIDE or USE_CAMPAIGN_GRID)"
        )

    if not periods:
        raise ValueError("resolved periods is empty")

    out: dict[int, tuple[int, ...]] = {}
    override = columns_override_by_period or {}
    for period in periods:
        per_cols_raw = override.get(int(period))
        if per_cols_raw is not None:
            cols = unique_sorted_ints_fn(int(x) for x in per_cols_raw)
        else:
            if not use_campaign_grid:
                raise ValueError(
                    f"columns not provided for period={int(period)} while USE_CAMPAIGN_GRID=False"
                )
            if columns_min <= 0 or columns_max < columns_min:
                raise ValueError("campaign grid columns_min/columns_max are invalid")
            cols = tuple(range(columns_min, columns_max + 1))
        if not cols:
            raise ValueError(f"resolved columns empty for period={int(period)}")
        out[int(period)] = cols
    return out
