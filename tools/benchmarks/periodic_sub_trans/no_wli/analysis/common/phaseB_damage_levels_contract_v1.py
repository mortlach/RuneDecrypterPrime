from __future__ import annotations

DAMAGE_LEVELS = (0.10, 0.20, 0.30, 0.40, 0.50)
DAMAGE_TOLERANCE = 0.01
ORDINARY_NULL_MODELS = ("uniform_random", "global_frequency_random", "within_chunk_shuffle")
HARD_LOCAL_ORDER_CONTROLS = ("block_shuffle_10", "block_shuffle_25", "block_shuffle_50")
DAMAGE_MODELS = (
    "independent_substitution",
    "frequency_matched_global",
    "frequency_matched_book",
    "word_local_substitution",
    "burst_substitution",
    "lane_period_substitution",
)


def damage_level_text(level: float) -> str:
    value = float(level)
    if value not in DAMAGE_LEVELS:
        raise ValueError(f"unsupported damage level {level!r}; expected one of {DAMAGE_LEVELS!r}")
    return f"{value:.2f}"


def null_class(model_name: str) -> str:
    if model_name in ORDINARY_NULL_MODELS:
        return "ordinary_null"
    if model_name in HARD_LOCAL_ORDER_CONTROLS:
        return "hard_local_order_control"
    if model_name in {"", "none"}:
        return "not_null"
    raise ValueError(f"unknown null/control model {model_name!r}")


def validate_actual_damage(requested: float, actual: float, *, tolerance: float = DAMAGE_TOLERANCE) -> None:
    if abs(float(requested) - float(actual)) > float(tolerance):
        raise AssertionError(f"damage miss too large: requested={requested:.6f} actual={actual:.6f}")


def changed_fraction_bin(value: float, *, step: float = 0.10) -> str:
    value = max(0.0, min(1.0, float(value)))
    lo = int(value / step) * step
    hi = min(1.0, lo + step)
    return f"{lo:.2f}-{hi:.2f}"
