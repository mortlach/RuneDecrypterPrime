from __future__ import annotations
import importlib.util
import inspect
import json
import sys
from pathlib import Path
import pytest
from tools.robustness import cipher_solver_campaign_config as campaign
pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / 'tutorials' / 'v1'

def _load(filename: str):
    path = TUTORIALS / filename
    spec = importlib.util.spec_from_file_location(f'test_{path.stem}', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def test_robust_autokey_recipe_matches_campaign() -> None:
    module = _load("Tutorial_Autokey_Robust.py")
    recipe = campaign.CAMPAIGN_RECIPES["autokey_beam"]
    budget = recipe.solver
    assert isinstance(budget, campaign.BeamPlan)
    assert module.BEAM_WIDTH == budget.width
    assert module.ROUNDS == budget.rounds
    assert module.RESTARTS == budget.restarts == 3
    assert module.SCORER_PARAMS == recipe.scoring


def test_robust_mono_recipe_and_selection_match_campaign() -> None:
    module = _load("Tutorial_MonoSubstitution_GA_Robust.py")
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
    module = _load("Tutorial_Vigenere_Interruptors_Robust.py")
    recipe = campaign.CAMPAIGN_RECIPES["vigenere_interruptors_beam"]
    budget = recipe.solver
    assert isinstance(budget, campaign.BeamPlan)
    assert module.BEAM_WIDTH == budget.width
    assert module.RESTARTS == budget.restarts == 3
    assert module.SCORER_PARAMS == recipe.scoring
    assert module.INTERRUPTOR_COUNT == 2

def test_robust_tutorials_do_not_use_oracles_true_key_seeds_or_repo_outputs() -> None:
    for filename in ('Tutorial_Autokey_Robust.py', 'Tutorial_MonoSubstitution_GA_Robust.py', 'Tutorial_Vigenere_Interruptors_Robust.py'):
        source = (TUTORIALS / filename).read_text(encoding='utf-8').lower()
        assert 'oracle_stop_score(' not in source
        assert 'initial_keys=[true' not in source
        assert 'tools.robustness' not in source
        assert 'cipher_development' not in source
        assert 'output/' not in source and 'artifacts/' not in source
        assert 'api.display.print_result(' in source
        assert 'recovered plaintext:' in source

def test_alternative_labels_and_manifest_are_honest() -> None:
    manifest = json.loads(
        (TUTORIALS / "tutorial_manifest_v1.json").read_text(encoding="utf-8")
    )
    entries = {entry["path"]: entry for entry in manifest["tutorials"]}
    assert "Tutorial_PeriodicColumnar.py" not in entries
    for filename in (
        "Tutorial_Autokey.py",
        "Tutorial_MonoSubstitution_GA_LTR.py",
        "Tutorial_MonoSubstitution_GA_RTL.py",
    ):
        source = (TUTORIALS / filename).read_text(encoding="utf-8").lower()
        assert (
            "not the qualified robust recipe" in source
            or "not the robust recipe" in source
        )
    for filename in (
        "Tutorial_Vigenere_Interruptors_Solve.py",
        "Tutorial_Vigenere_Interruptors_NonTrivial.py",
    ):
        source = (TUTORIALS / filename).read_text(encoding="utf-8").lower()
        assert "api.solverspec.beam_search(" in source
        assert "single-start" in source
    for filename in (
        "Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py",
        "Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py",
        "Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py",
    ):
        assert entries[filename]["uses_oracle_stop_score"] is False


def test_bounded_best_practice_cleanup_contracts() -> None:
    start = (TUTORIALS / "Tutorial_Start_Here.py").read_text(encoding="utf-8")
    assert "build_cipher_config" not in start
    assert "build_scorer" not in start
    assert "known key supplied to wrapper interface demo" in start
    assert "api.encrypt(" in start
    rail = (TUTORIALS / "Tutorial_Railfence.py").read_text(encoding="utf-8")
    assert "def encrypt_railfence" not in rail
    assert "api.encrypt(" in rail
    assert "oracle_stop_score(" not in rail
    sa = (TUTORIALS / "Tutorial_MonoSubstitution_SA_LTR.py").read_text(encoding="utf-8")
    assert "Retrying with stronger SA settings" not in sa
    assert sa.count("_solve_with_sa(solver_spec)") == 1


def test_robust_tutorials_are_manual_extended_not_ordinary_ci_light() -> None:
    runner = _load('run_tutorials.py')
    entries = {entry.path: entry for entry in runner.TUTORIALS}
    for filename in ('Tutorial_Autokey_Robust.py', 'Tutorial_MonoSubstitution_GA_Robust.py', 'Tutorial_Vigenere_Interruptors_Robust.py'):
        assert tuple((item.value for item in entries[filename].run_sets)) == ('extended',)
