from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tutorials.v1 import Tutorial_PeriodicColumnar_Simple_P7_ColThenSub as tutorial
from tutorials.v1.data.periodic_columnar_p7_warm_start import (
    QUALIFICATION_CANDIDATE_ID,
    QUALIFICATION_RECIPE_ID,
    QUALIFIED_INITIAL_KEY,
)


pytestmark = pytest.mark.tier_a


def test_qualified_tutorial_builds_one_public_non_oracle_run() -> None:
    request, expected_plaintext = tutorial.build_run_spec()
    solver = request.solver.to_dict()
    parameters = solver["parameters"]

    assert QUALIFICATION_RECIPE_ID == "periodic_columnar_decomposed_v2"
    assert len(QUALIFIED_INITIAL_KEY) == 210
    assert QUALIFIED_INITIAL_KEY[-7:] == (3, 5, 6, 4, 2, 1, 0)
    payload = ",".join(str(value) for value in QUALIFIED_INITIAL_KEY).encode("ascii")
    assert (
        hashlib.blake2b(
            payload,
            digest_size=20,
            person=b"rdp-pc-qual-v1",
        ).hexdigest()
        == QUALIFICATION_CANDIDATE_ID
    )
    assert request.initial_keys == (QUALIFIED_INITIAL_KEY,)
    assert len(expected_plaintext) == tutorial.PLAINTEXT_LENGTH
    assert tuple(request.problem_input.indices) != expected_plaintext
    assert parameters["steps"] == 12_000
    assert parameters["restarts"] == 1
    assert solver["seed"] == 12_446
    assert parameters["target_score"] is None
    assert dict(request.scoring.character_order_weights) == {3: 0.5, 4: 0.5}
    assert request.scoring.word_length_lane_enabled is False


def test_qualified_tutorial_exposes_no_development_or_oracle_api() -> None:
    source = Path(tutorial.__file__).read_text(encoding="utf-8")

    assert "from rdp import api" in source
    for forbidden in (
        "cipher_development",
        "materialize_cipher_config",
        "build_scorer",
        "DecryptionProblem",
        "generate_seed_keys_periodic_columnar",
        "oracle_stop_score",
        "target_score=stop",
    ):
        assert forbidden not in source
