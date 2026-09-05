from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

from tools.robustness import cipher_solver_campaign_config as campaign

pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]
TUTORIAL_ROOT = ROOT / 'tutorials' / 'v1'
TUTORIALS = TUTORIAL_ROOT / 'examples'

def _load(filename: str, *, directory: Path = TUTORIALS):
    path = directory / filename
    spec = importlib.util.spec_from_file_location(f'test_{path.stem}', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def test_robust_autokey_recipe_matches_campaign() -> None:
    module = _load("autokey_robust.py")
    recipe = campaign.CAMPAIGN_RECIPES["autokey_beam"]
    budget = recipe.solver
    assert isinstance(budget, campaign.BeamPlan)
    assert module.BEAM_WIDTH == budget.width
    assert module.ROUNDS == budget.rounds
    assert module.RESTARTS == budget.restarts == 3
    assert module.SCORER_PARAMS == recipe.scoring


def test_robust_mono_recipe_and_selection_match_campaign() -> None:
    module = _load("mono_substitution_ga_robust.py")
    recipe = campaign.CAMPAIGN_RECIPES["mono_ga"]
    budget = recipe.solver
    assert isinstance(budget, campaign.GeneticPlan)
    assert module.SCORER_PARAMS == recipe.scoring
    assert len(module.ATTEMPT_SEEDS) == recipe.attempt_count == 3
    assert module.SEED_KEYS == budget.seed_keys
    assert module.SEED_SWAPS == budget.seed_swaps
    assert module.POP_SIZE == budget.population_size
    assert module.GENERATIONS == budget.generations
    assert module.ELITE_FRAC == budget.elite_fraction
    assert module.CX_FRAC == budget.crossover_fraction
    assert module.MUT_PROB == budget.mutation_probability
    assert module.TOURNAMENT_K == budget.tournament_size
    assert module.PLATEAU_ROUNDS == budget.plateau_generations
    assert module.MIN_MATCH_RATIO == recipe.acceptance.plaintext_match
    selection_source = inspect.getsource(module.select_attempt).lower()
    assert 'score' in selection_source and 'valid' in selection_source
    assert not {'plaintext', 'truth', 'match', 'classification', 'key'} & set(selection_source.replace('(', ' ').replace(')', ' ').split())
    module.enforce_acceptance(module.MIN_MATCH_RATIO)
    with pytest.raises(AssertionError, match='below acceptance threshold'):
        module.enforce_acceptance(module.MIN_MATCH_RATIO - 0.001)

def test_robust_interruptor_recipe_matches_campaign() -> None:
    module = _load("vigenere_interruptors_robust.py")
    recipe = campaign.CAMPAIGN_RECIPES["vigenere_interruptors_beam"]
    budget = recipe.solver
    assert isinstance(budget, campaign.BeamPlan)
    assert module.BEAM_WIDTH == budget.width
    assert module.RESTARTS == budget.restarts == 3
    assert module.SCORER_PARAMS == recipe.scoring
    assert module.INTERRUPTOR_COUNT == 2

def test_robust_tutorials_do_not_use_oracles_true_key_seeds_or_repo_outputs() -> None:
    for filename in ('autokey_robust.py', 'mono_substitution_ga_robust.py', 'vigenere_interruptors_robust.py'):
        source = (TUTORIALS / filename).read_text(encoding='utf-8').lower()
        assert 'oracle_stop_score(' not in source
        assert 'initial_keys=[true' not in source
        assert 'tools.robustness' not in source
        assert 'cipher_development' not in source
        assert 'output/' not in source and 'artifacts/' not in source
        assert 'api.display.print_result(' in source
        assert 'recovered plaintext:' in source

def test_alternative_labels_and_truth_use_are_honest() -> None:
    for filename in (
        "autokey.py",
        "mono_substitution_ga_ltr.py",
        "mono_substitution_ga_rtl.py",
    ):
        source = (TUTORIALS / filename).read_text(encoding="utf-8").lower()
        assert (
            "not the qualified robust recipe" in source
            or "not the robust recipe" in source
        )
    for filename in (
        "vigenere_interruptors_solve.py",
        "vigenere_interruptors_nontrivial.py",
    ):
        source = (TUTORIALS / filename).read_text(encoding="utf-8").lower()
        assert "api.solverspec.beam_search(" in source
        assert "single-start" in source
    for filename in (
        "scheduled_stream_lookup_p13_sequence.py",
        "scheduled_stream_lookup_p13_primes.py",
        "scheduled_stream_lookup_p13_p31_segmented.py",
    ):
        source = (TUTORIALS / filename).read_text(encoding="utf-8").lower()
        assert "oracle_stop_score(" not in source


def test_bounded_best_practice_cleanup_contracts() -> None:
    start = (TUTORIALS / "vigenere_known_key_and_general_map.py").read_text(encoding="utf-8")
    assert "build_cipher_config" not in start
    assert "build_scorer" not in start
    assert "known key supplied to wrapper interface demo" in start
    assert "api.encrypt(" in start
    rail = (TUTORIALS / "rail_fence.py").read_text(encoding="utf-8")
    assert "def encrypt_railfence" not in rail
    assert "api.encrypt(" in rail
    assert "oracle_stop_score(" not in rail
    sa = (TUTORIALS / "mono_substitution_sa_ltr.py").read_text(encoding="utf-8")
    assert "Retrying with stronger SA settings" not in sa
    assert sa.count("_solve_with_sa(solver_spec)") == 1


def test_robust_examples_are_bundled_but_not_in_the_release_group() -> None:
    runner = _load('run_tutorials.py', directory=TUTORIAL_ROOT)
    runner.RUN_SET = runner.TutorialRunSet.BUNDLED_EXAMPLES
    bundled = {path.name for path in runner._selected_tutorials()}
    robust = {
        'autokey_robust.py',
        'mono_substitution_ga_robust.py',
        'vigenere_interruptors_robust.py',
    }
    assert robust <= bundled
    assert not robust & set(runner.RELEASE_EXAMPLE_NAMES)
