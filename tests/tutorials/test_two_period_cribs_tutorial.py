from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from rdp import api
from rune_decrypter_prime.api.two_period_cribs import normalize_two_period_cribs_request
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.solvers.two_period_cribs import build_branches


pytestmark = pytest.mark.tier_a


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "tutorials" / "v1"
FAST = TUTORIALS / "Tutorial_TwoPeriodCribs.py"
SEARCH = TUTORIALS / "Tutorial_TwoPeriodCribs_P13P31_Search.py"
HELPER = TUTORIALS / "data" / "two_period_cribs_demo.py"


def _load(path: Path, name: str):
    sys.path.insert(0, str(TUTORIALS))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(TUTORIALS))


def test_tutorial_sources_use_only_the_simple_public_route() -> None:
    required = (
        "from rdp import api",
        "api.by_name.cipher_with_key(",
        '"two_period_vigenere"',
        "default_key=True",
        "api.SolverSpec.two_period_cribs(",
        "api.run(",
    )
    forbidden = (
        "KeySpec.repeat",
        "cipher_development",
        "scorer_params=",
        "initial_keys=",
        "test_key=",
        "interruptors=",
        "interruptors_exact=",
        "interruptors_pool=",
    )
    for path in (FAST, SEARCH):
        text = path.read_text(encoding="utf-8")
        assert all(fragment in text for fragment in required)
        assert not any(fragment in text for fragment in forbidden)


def test_tutorials_are_uniquely_active_and_honestly_manifested() -> None:
    manifest = json.loads(
        (TUTORIALS / "tutorial_manifest_v1.json").read_text(encoding="utf-8")
    )
    entries = manifest["tutorials"]
    for filename in (FAST.name, SEARCH.name):
        matches = [entry for entry in entries if entry["path"] == filename]
        assert len(matches) == 1
        entry = matches[0]
        assert entry["current_status"] == "active"
        assert entry["acceptance_kind"] == "exact"
        assert entry["min_match_ratio"] == 1.0
        assert entry["uses_oracle_stop_score"] is False
        assert entry["supplies_true_key_to_solver"] is False
        assert entry["required_asset_profile"] == "full_v1"


@pytest.mark.full_assets
def test_fast_walkthrough_returns_exact_plaintext_and_key(capsys) -> None:
    module = _load(FAST, "rdp_tutorial_two_period_fast_test")
    result = module.run_tutorial()
    output = capsys.readouterr().out
    assert "match_ratio : 1.000000" in output
    assert result.solver_report.details["two_period_solve"]["derived_dimension"] == 0
    portable = result.solver_report.to_json_dict()["details"]["two_period_solve"]
    encoded = json.dumps(portable, sort_keys=True)
    assert "truth" not in encoded.lower()
    assert "reference" not in encoded.lower()


def test_search_fixture_contains_the_required_d14_branch() -> None:
    helper = _load(HELPER, "rdp_tutorial_two_period_fixture_test")
    search = _load(SEARCH, "rdp_tutorial_two_period_search_structure_test")
    cipher, _key = api.by_name.cipher_with_key(
        "two_period_vigenere", period_a=13, period_b=31, default_key=True
    )
    fixture = helper.build_demo_fixture(cipher)
    request = normalize_two_period_cribs_request(
        api.SolverSpec.two_period_cribs(
            fixed_cribs=search.FIXED_CRIBS,
            candidate_words=search.WORDS_TO_TRY,
            starts=search.STARTS,
            seed=search.SEED,
        )
    )
    branches, rejected = build_branches(
        np.asarray(fixture.ciphertext, dtype=np.uint8),
        fixture.wli,
        request,
        period_a=13,
        period_b=31,
        modulus=29,
        direction=Direction.LTR,
    )
    summary = {(branch.candidate_crib.word, branch.candidate_crib.start): branch.constraint_space.dimension for branch in branches}
    assert summary[("dormouse", 81)] == 22
    assert summary[("dormouse", 206)] == 14
    assert rejected == ()
