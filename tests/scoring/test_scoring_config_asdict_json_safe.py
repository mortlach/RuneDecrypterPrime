from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import pytest

from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.types import Direction, ObjectiveFamily, ObjectiveSpec, Stat


pytestmark = pytest.mark.tier_a


def _assert_jsonish(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int, float)):
        return
    if isinstance(value, Enum):
        raise AssertionError(f"enum leaked into asdict payload: {value!r}")
    if isinstance(value, Path):
        raise AssertionError(f"path leaked into asdict payload: {value!r}")
    if isinstance(value, dict):
        for k, v in value.items():
            assert isinstance(k, str)
            _assert_jsonish(v)
        return
    if isinstance(value, list):
        for item in value:
            _assert_jsonish(item)
        return
    raise AssertionError(f"non-jsonish value leaked: {type(value)!r}")


def test_scoring_config_asdict_emits_json_primitives() -> None:
    cfg = ScoringConfig(
        model_root=Path("assets/lm"),
        encoding_dir=Direction.LTR,
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        hamming_wordlist_dir=Path("assets/hamming"),
        span_hamming_wordlist_dir=Path("assets/span"),
        span_hamming_assets_dir=Path("assets/span_cal"),
    )

    payload = cfg.asdict()

    assert Path(payload["model_root"]).as_posix() == "assets/lm"
    assert payload["encoding_dir"] == "ltr"
    assert payload["objective"] == {"family": "pct", "stat": "logp", "win": 10}
    assert Path(payload["hamming_wordlist_dir"]).as_posix() == "assets/hamming"
    assert Path(payload["span_hamming_wordlist_dir"]).as_posix() == "assets/span"
    assert Path(payload["span_hamming_assets_dir"]).as_posix() == "assets/span_cal"
    _assert_jsonish(payload)
