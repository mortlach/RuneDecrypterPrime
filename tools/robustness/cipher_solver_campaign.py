"""Deterministic known-answer cipher/solver robustness campaign."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / 'src'
TOOL_ROOT = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, SRC_ROOT, TOOL_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
from rdp import api
from tutorials.v1.data.two_period_cribs_demo import encrypt_interruptor_fixture
from tools.robustness.fixtures.cipher_books.book_corpus import load_book, select_passage
from rdp.io.rng import RNGController
from rdp.scoring.language_model import _fastlm
from rdp.scoring.language_model.paths import default_lm_root, expand_pattern, load_index
from rdp.data.runeglish import Runeglish
from rdp.solvers.seed_generation import make_seeds_from_freq
from solving.solve_output import match_ratio
import cipher_solver_campaign_config as config
ALPHABET = 29
CAMPAIGN_SEED = config.CAMPAIGN_SEED
OUTPUT_ROOT = config.OUTPUT_ROOT

@dataclass(slots=True)
class CampaignCase:
    family: str
    direction: api.TextDirection
    ciphertext: list[int]
    reference: list[int]
    wli: list[list[int]]
    cipher: Any
    key: Any
    solver: Any
    scoring: api.ScoringConfig
    cipher_parameters: dict[str, Any]
    solver_parameters: dict[str, Any]
    source: dict[str, Any]
    key_length: int
    expected_key: list[int] | None = None
    expected_interruptors: list[int] | None = None
    initial_keys: Any = None
    interruptors: Any = None

@dataclass(frozen=True, slots=True)
class FamilyDefinition:
    name: str
    group: str
    builder: Callable[[int, int], CampaignCase]
    key_equivalence: Callable[[CampaignCase, list[int]], bool] | None = None
RESULT_FIELDS = ('campaign_seed', 'trial_seed', 'trial_index', 'trial_id', 'family', 'recipe_id', 'recipe_fingerprint', 'configuration_fingerprint', 'scorer_profile', 'selection_policy', 'truth_used_for_selection', 'campaign_group', 'direction', 'plaintext_source', 'book', 'start_word', 'word_count', 'plaintext_length', 'cipher_parameters', 'solver_parameters', 'attempt_count', 'attempt_seeds', 'attempts', 'selected_attempt', 'selection_reason', 'requested_seed', 'effective_seed', 'match_ratio', 'exact_recovery', 'expected_key', 'recovered_key', 'key_equivalent', 'expected_interruptors', 'recovered_interruptors', 'interruptor_match', 'run_status', 'stop_reason', 'best_score', 'evaluations', 'tokens', 'runtime_seconds', 'classification', 'notes')
_SELECTION_POLICIES = {'highest_valid_solver_score'}
_RECIPE_ID_PATTERN = re.compile('^[a-z0-9][a-z0-9_]*_v[1-9][0-9]*$')
_RUNTIME_SOURCE_PATHS = ('src', 'tools/robustness', 'tutorials/v1', 'asset_profiles_v1.json', 'assets_manifest_ci_light_v1.json', 'assets_manifest_v1.json')

def _validated_weights(value: Any, label: str) -> dict[int, float]:
    if not isinstance(value, Mapping):
        raise ValueError(f'{label} must be a mapping')
    weights: dict[int, float] = {}
    for raw_order, raw_weight in value.items():
        if isinstance(raw_order, bool) or not isinstance(raw_order, int):
            raise ValueError(f'{label} orders must be integers')
        order = int(raw_order)
        if order not in {1, 2, 3, 4}:
            raise ValueError(f'{label} orders must be in 1..4')
        if isinstance(raw_weight, bool) or not isinstance(raw_weight, (int, float)):
            raise ValueError(f'{label} weights must be numeric')
        weight = float(raw_weight)
        if not math.isfinite(weight) or weight < 0.0:
            raise ValueError(f'{label} weights must be finite and non-negative')
        if weight > 0.0:
            weights[order] = weight
    return weights

def validate_campaign_recipes(registered_families: Sequence[str] | None=None) -> None:
    family_names = set(config.FAMILY_GROUPS)
    recipe_names = set(config.CAMPAIGN_RECIPES)
    if family_names != recipe_names:
        raise ValueError('campaign family/recipe registry mismatch')
    if registered_families is not None and family_names != set(registered_families):
        raise ValueError('campaign builder registry does not match configured families')
    recipe_ids = [recipe.recipe_id for recipe in config.CAMPAIGN_RECIPES.values()]
    if len(recipe_ids) != len(set(recipe_ids)):
        raise ValueError('campaign recipe_id values must be unique')
    for family, recipe in config.CAMPAIGN_RECIPES.items():
        if recipe.attempt_count < 1:
            raise ValueError(f'{family}: attempt_count must be positive')
        if recipe.selection not in _SELECTION_POLICIES:
            raise ValueError(f'{family}: unsupported selection policy')

def case_seed_namespace(family: str) -> str:
    return str(config.CASE_SEED_NAMESPACES.get(family, family))

def trial_seed(family: str, trial_index: int) -> int:
    rng = RNGController(CAMPAIGN_SEED).scope('cipher_solver_campaign')
    namespace = case_seed_namespace(family)
    return int(rng.child(f'{namespace}.{trial_index}').integers(1, 2 ** 31 - 1))

def attempt_seed(family: str, trial_index: int, attempt_index: int) -> int:
    seed = trial_seed(family, trial_index)
    if int(attempt_index) == 0:
        return seed
    rng = RNGController(seed).scope('solver_attempts')
    return int(rng.child(str(attempt_index)).integers(1, 2 ** 31 - 1))

def trial_direction(trial_index: int) -> api.TextDirection:
    return config.DIRECTIONS[int(trial_index) % len(config.DIRECTIONS)]

def _book_passage(seed: int, direction: api.TextDirection):
    rng = RNGController(seed).child('book')
    book = config.BOOKS[int(rng.integers(0, len(config.BOOKS)))]
    passage = select_passage(load_book(book, direction), seed=seed, target_runes=config.TARGET_RUNES, tolerance_runes=config.RUNE_TOLERANCE)
    source = {'plaintext_source': f'packaged_book:{book}', 'book': book, 'start_word': passage.start_word, 'word_count': passage.word_count}
    return (passage.plaintext, passage.wli.tolist(), source)

def resolved_recipe(family: str) -> config.CampaignRecipe:
    try:
        return config.CAMPAIGN_RECIPES[family]
    except KeyError as exc:
        raise ValueError(f'unknown campaign family: {family!r}') from exc

def recipe_fingerprint(family: str) -> str:
    return _canonical_hash(config.recipe_to_dict(resolved_recipe(family)))

def resolved_campaign_configuration(family: str, mode: str) -> dict[str, Any]:
    return {'campaign_seed': CAMPAIGN_SEED, 'mode': mode, 'family': family, 'campaign_group': FAMILIES[family].group, 'recipe': config.recipe_to_dict(resolved_recipe(family)), 'recipe_fingerprint': recipe_fingerprint(family), 'books': list(config.BOOKS), 'directions': [item.value for item in config.DIRECTIONS], 'target_runes': config.TARGET_RUNES, 'rune_tolerance': config.RUNE_TOLERANCE, 'cipher_range': config.CIPHER_RANGES.get(family)}

def configuration_fingerprint(family: str, mode: str) -> str:
    return _canonical_hash(resolved_campaign_configuration(family, mode))

def _scorer(family: str, direction: api.TextDirection) -> api.ScoringConfig:
    del direction
    return resolved_recipe(family).scoring

def _range_value(rng: RNGController, limits: tuple[int, int]) -> int:
    low, high = (int(value) for value in limits)
    return int(rng.integers(low, high + 1))

def _multiply(value: int, key_value: int) -> int:
    return int(value) * int(key_value) % ALPHABET

def _exact_key_equivalence(case: CampaignCase, recovered: list[int]) -> bool:
    return case.expected_key is not None and recovered == case.expected_key

def _repeating_key_equivalence(case: CampaignCase, recovered: list[int]) -> bool:
    expected = list(case.expected_key or [])
    if not expected or len(recovered) != len(expected):
        return False
    if case.direction is api.TextDirection.LEFT_TO_RIGHT:
        return recovered == expected
    core_length = len(case.reference) - len(case.expected_interruptors or ())
    shift = core_length % len(expected)
    transformed = list(reversed(expected))
    if shift:
        transformed = transformed[-shift:] + transformed[:-shift]
    return recovered == transformed

def campaign_trial_count(mode: str | None=None) -> int:
    selected = config.CAMPAIGN_MODE if mode is None else str(mode)
    try:
        count = int(config.TRIALS_PER_MODE[selected])
    except KeyError as exc:
        raise ValueError(f'unknown campaign mode: {selected!r}') from exc
    if count < 1:
        raise ValueError(f'campaign mode {selected!r} requires at least one trial')
    return count

def qualification_exit_code(records: Sequence[Mapping[str, Any]], mode: str | None=None) -> int:
    selected = config.CAMPAIGN_MODE if mode is None else str(mode)
    if selected not in config.BLOCKING_REVIEW_GROUPS:
        raise ValueError(f'unknown campaign mode: {selected!r}')
    if any((record.get('classification') == 'FAIL' for record in records)):
        return 1
    blocking_groups = set(config.BLOCKING_REVIEW_GROUPS[selected])
    return int(any((record.get('classification') == 'REVIEW' and record.get('campaign_group') in blocking_groups for record in records)))

def _ordinary_inputs(family: str, trial_index: int, attempt_index: int):
    seed = trial_seed(family, trial_index)
    solver_seed = attempt_seed(family, trial_index, attempt_index)
    direction = trial_direction(trial_index)
    plaintext, wli, source = _book_passage(seed, direction)
    rng = RNGController(seed).scope(case_seed_namespace(family))
    limits = config.CIPHER_RANGES[family]
    plan = resolved_recipe(family).solver
    if plan is None:
        raise ValueError(f'{family}: ordinary family has no solver plan')
    solver_spec = plan.build(solver_seed)
    return (seed, direction, plaintext, wli, source, rng, limits, solver_spec)

def _case(*, family: str, direction: api.TextDirection, plaintext: np.ndarray, wli: list[list[int]], source: dict[str, Any], ciphertext: Sequence[int], cipher: api.CipherSpec, key: api.KeySpec, solver: api.SolverSpec, cipher_parameters: dict[str, Any], key_length: int, expected_key: Sequence[int] | None=None, expected_interruptors: Sequence[int] | None=None, initial_keys: Any=None, interruptors: api.InterruptorConfig | None=None, scoring: api.ScoringConfig | None=None) -> CampaignCase:
    typed_initial_keys = None if initial_keys is None else tuple(tuple(int(value) for value in item) for item in initial_keys)
    return CampaignCase(family=family, direction=direction, ciphertext=[int(value) for value in ciphertext], reference=[int(value) for value in plaintext], wli=wli, cipher=cipher, key=key, solver=solver, scoring=resolved_recipe(family).scoring if scoring is None else scoring, cipher_parameters=cipher_parameters, solver_parameters=solver.to_dict(), source=source, key_length=key_length, expected_key=None if expected_key is None else [int(value) for value in expected_key], expected_interruptors=None if expected_interruptors is None else sorted((int(value) for value in expected_interruptors)), initial_keys=typed_initial_keys, interruptors=interruptors)

def _build_vigenere(trial_index: int, attempt_index: int) -> CampaignCase:
    family = 'vigenere_beam'
    _, direction, pt, wli, source, rng, limits, solver_spec = _ordinary_inputs(family, trial_index, attempt_index)
    length = _range_value(rng.child('shape'), limits['key_length'])
    truth = rng.child('key').integers(0, ALPHABET, size=length).tolist()
    cipher = api.CipherSpec.vigenere(alphabet_size=29)
    key = api.KeySpec.repeating(length=length)
    ct = api.encrypt(tuple(int(value) for value in pt), cipher=cipher, key=tuple(int(value) for value in truth))
    return _case(family=family, direction=direction, plaintext=pt, wli=wli, source=source, ciphertext=ct, cipher=cipher, key=key, solver=solver_spec, cipher_parameters={'key_length': length, 'key': truth}, key_length=length, expected_key=truth)

def _build_railfence(trial_index: int, attempt_index: int) -> CampaignCase:
    family = 'railfence_beam'
    _, direction, pt, wli, source, rng, limits, solver_spec = _ordinary_inputs(family, trial_index, attempt_index)
    low, high = limits['rails']
    rails = _range_value(rng.child('key'), (low, high))
    truth = [rails]
    cipher = api.CipherSpec.rail_fence(minimum_rails=low, maximum_rails=high, alphabet_size=29)
    key = api.KeySpec.scalar(minimum=low, maximum=high)
    ct = api.encrypt(tuple(int(value) for value in pt), cipher=cipher, key=(rails,))
    return _case(family=family, direction=direction, plaintext=pt, wli=wli, source=source, ciphertext=ct, cipher=cipher, key=key, solver=solver_spec, cipher_parameters={'rails': rails, 'min_rails': low, 'max_rails': high, 'key': truth}, key_length=1, expected_key=truth)

def _build_autokey(trial_index: int, attempt_index: int) -> CampaignCase:
    family = 'autokey_beam'
    _, direction, pt, wli, source, rng, limits, solver_spec = _ordinary_inputs(family, trial_index, attempt_index)
    length = _range_value(rng.child('shape'), limits['seed_length'])
    truth = rng.child('key').integers(0, ALPHABET, size=length).tolist()
    cipher = api.CipherSpec.autokey(alphabet_size=ALPHABET)
    key = api.KeySpec.repeating(length=length)
    ct = api.encrypt(tuple(int(value) for value in pt), cipher=cipher, key=tuple(int(value) for value in truth))
    return _case(family=family, direction=direction, plaintext=pt, wli=wli, source=source, ciphertext=ct, cipher=cipher, key=key, solver=solver_spec, cipher_parameters={'seed_length': length, 'key': truth}, key_length=length, expected_key=truth)

def _build_columnar(trial_index: int, attempt_index: int) -> CampaignCase:
    family = 'columnar_hybrid'
    _, direction, pt, wli, source, rng, limits, solver_spec = _ordinary_inputs(family, trial_index, attempt_index)
    columns = _range_value(rng.child('shape'), limits['columns'])
    truth = rng.child('key').permutation(columns).tolist()
    cipher = api.CipherSpec.columnar(columns=columns, alphabet_size=29)
    key = api.KeySpec.permutation(length=columns)
    ct = api.encrypt(tuple(int(value) for value in pt), cipher=cipher, key=tuple(int(value) for value in truth))
    return _case(family=family, direction=direction, plaintext=pt, wli=wli, source=source, ciphertext=ct, cipher=cipher, key=key, solver=solver_spec, cipher_parameters={'columns': columns, 'key': truth}, key_length=columns, expected_key=truth)

def _build_mono(trial_index: int, attempt_index: int) -> CampaignCase:
    family = 'mono_ga'
    _, direction, pt, wli, source, rng, _, solver_spec = _ordinary_inputs(family, trial_index, attempt_index)
    truth = rng.child('key').permutation(ALPHABET).astype(np.uint8)
    cipher = api.CipherSpec.substitution(alphabet_size=29)
    key = api.KeySpec.permutation(length=ALPHABET)
    ct = api.encrypt(tuple(int(value) for value in pt), cipher=cipher, key=tuple(int(value) for value in truth))
    seed_count = config.CAMPAIGN_RECIPES[family].solver.seed_keys
    seed_swaps = config.CAMPAIGN_RECIPES[family].solver.seed_swaps
    solver_seed = solver_spec.seed or 0
    initial_keys = make_seeds_from_freq(
        Runeglish.to_rune(list(ct), wli).replace(" ", ""),
        n_keys=seed_count,
        swaps_per_key=seed_swaps,
        seed=solver_seed,
        direction=direction,
    )
    return _case(
        family=family,
        direction=direction,
        plaintext=pt,
        wli=wli,
        source=source,
        ciphertext=ct,
        cipher=cipher,
        key=key,
        solver=solver_spec,
        cipher_parameters={"alphabet_size": ALPHABET, "key": truth.tolist()},
        key_length=ALPHABET,
        expected_key=truth,
        initial_keys=initial_keys,
    )


def _build_vigenere_interruptors(trial_index: int, attempt_index: int) -> CampaignCase:
    family = 'vigenere_interruptors_beam'
    _, direction, pt, wli, source, rng, limits, solver_spec = _ordinary_inputs(family, trial_index, attempt_index)
    length = _range_value(rng.child('shape'), limits['key_length'])
    truth = rng.child('key').integers(0, ALPHABET, size=length).tolist()
    pool_size = _range_value(rng.child('pool_size'), limits['pool_size'])
    count = _range_value(rng.child('count'), limits['interruptor_count'])
    pool = sorted(rng.child('pool').choice(len(pt), size=pool_size, replace=False).tolist())
    chosen = sorted(rng.child('chosen').choice(pool, size=count, replace=False).tolist())
    cipher = api.CipherSpec.vigenere(alphabet_size=29)
    key = api.KeySpec.repeating(length=length)
    ct = encrypt_interruptor_fixture(pt, cipher=cipher, key=tuple((int(_concrete_key_value) for _concrete_key_value in truth)), interruptor_positions=chosen)
    interruptors = api.InterruptorConfig.search(pool, minimum_count=count, maximum_count=count, strategy=api.advanced.InterruptorSearchStrategy.AUTO, maximum_combinations=5000)
    return _case(family=family, direction=direction, plaintext=pt, wli=wli, source=source, ciphertext=ct, cipher=cipher, key=key, solver=solver_spec, cipher_parameters={'key_length': length, 'key': truth, 'interruptor_pool': pool, 'interruptors': chosen}, key_length=length, expected_key=truth, expected_interruptors=chosen, interruptors=interruptors)

def _build_generic_map(trial_index: int, attempt_index: int) -> CampaignCase:
    family = 'generic_map_multiply_beam'
    _, direction, pt, wli, source, rng, limits, solver_spec = _ordinary_inputs(family, trial_index, attempt_index)
    length = _range_value(rng.child('shape'), limits['key_length'])
    truth = rng.child('key').integers(1, ALPHABET, size=length).tolist()
    cipher = api.experimental.define_cipher_map(_multiply, alphabet_size=ALPHABET)
    key = api.KeySpec.repeating(length=length)
    stream = np.resize(np.asarray(truth, dtype=np.uint8), len(pt))
    ct = (pt.astype(np.int16) * stream.astype(np.int16) % ALPHABET).astype(np.uint8)
    return _case(family=family, direction=direction, plaintext=pt, wli=wli, source=source, ciphertext=ct, cipher=cipher, key=key, solver=solver_spec, cipher_parameters={'key_length': length, 'key': truth}, key_length=length, expected_key=truth)

def _build_scheduled_stream(trial_index: int, attempt_index: int) -> CampaignCase:
    family = 'scheduled_stream_beam'
    _, direction, pt, wli, source, rng, limits, solver_spec = _ordinary_inputs(family, trial_index, attempt_index)
    period = _range_value(rng.child('shape'), limits['period'])
    truth = rng.child('key').integers(0, ALPHABET, size=period).tolist()
    cipher, default_key = (api.CipherSpec.vigenere(alphabet_size=ALPHABET), api.KeySpec.repeating(length=period))
    key = default_key or api.KeySpec.repeating(length=period)
    ct = api.encrypt(tuple(int(value) for value in pt), cipher=cipher, key=tuple(int(value) for value in truth))
    return _case(family=family, direction=direction, plaintext=pt, wli=wli, source=source, ciphertext=ct, cipher=cipher, key=key, solver=solver_spec, cipher_parameters={'period': period, 'key': truth}, key_length=period, expected_key=truth)

def _build_two_period(trial_index: int, attempt_index: int) -> CampaignCase:
    family = 'two_period_cribs'
    solver_seed = attempt_seed(family, trial_index, attempt_index)
    tutorial_root = REPO_ROOT / 'tutorials' / 'v1'
    if str(tutorial_root) not in sys.path:
        sys.path.insert(0, str(tutorial_root))
    from tutorials.v1.data.two_period_cribs_demo import build_demo_fixture
    from tutorials.v1.Tutorial_TwoPeriodCribs import FIXED_CRIBS, PERIOD_A, PERIOD_B, STARTS
    cipher, key = (api.CipherSpec.two_period_vigenere(first_period=PERIOD_A, second_period=PERIOD_B, alphabet_size=ALPHABET), api.KeySpec.repeating(length=PERIOD_A + PERIOD_B))
    fixture = build_demo_fixture(cipher)
    solver = api.SolverSpec.two_period_cribs(fixed_cribs=FIXED_CRIBS, starts=STARTS, seed=solver_seed)
    return CampaignCase(family=family, direction=api.TextDirection.LEFT_TO_RIGHT, ciphertext=list(fixture.ciphertext), reference=list(fixture.reference_plaintext), wli=[list(row) for row in fixture.wli], cipher=cipher, key=key, solver=solver, scoring=api.ScoringConfig(), cipher_parameters={'period_a': PERIOD_A, 'period_b': PERIOD_B, 'key': list(fixture.reference_key)}, solver_parameters=solver.to_dict(), source={'plaintext_source': 'two_period_cribs_demo', 'book': None, 'start_word': None, 'word_count': None}, key_length=PERIOD_A + PERIOD_B, expected_key=list(fixture.reference_key))
FAMILIES = {definition.name: definition for definition in (FamilyDefinition('vigenere_beam', config.FAMILY_GROUPS['vigenere_beam'], _build_vigenere, _repeating_key_equivalence), FamilyDefinition('railfence_beam', config.FAMILY_GROUPS['railfence_beam'], _build_railfence), FamilyDefinition('autokey_beam', config.FAMILY_GROUPS['autokey_beam'], _build_autokey, _exact_key_equivalence), FamilyDefinition('columnar_hybrid', config.FAMILY_GROUPS['columnar_hybrid'], _build_columnar, _exact_key_equivalence), FamilyDefinition('mono_ga', config.FAMILY_GROUPS['mono_ga'], _build_mono), FamilyDefinition('vigenere_interruptors_beam', config.FAMILY_GROUPS['vigenere_interruptors_beam'], _build_vigenere_interruptors, _repeating_key_equivalence), FamilyDefinition('generic_map_multiply_beam', config.FAMILY_GROUPS['generic_map_multiply_beam'], _build_generic_map, _exact_key_equivalence), FamilyDefinition('scheduled_stream_beam', config.FAMILY_GROUPS['scheduled_stream_beam'], _build_scheduled_stream, _exact_key_equivalence), FamilyDefinition('two_period_cribs', config.FAMILY_GROUPS['two_period_cribs'], _build_two_period))}
ORDINARY_FAMILIES = tuple((name for name, definition in FAMILIES.items() if definition.group != 'SPECIALIST'))
SPECIALIST_FAMILIES = tuple((name for name, definition in FAMILIES.items() if definition.group == 'SPECIALIST'))
validate_campaign_recipes(tuple(FAMILIES))

def build_case(family: str, trial_index: int, attempt_index: int=0) -> CampaignCase:
    try:
        definition = FAMILIES[family]
    except KeyError as exc:
        raise KeyError(f'unknown campaign family: {family}') from exc
    return definition.builder(int(trial_index), int(attempt_index))

def execute_case(case: CampaignCase) -> api.RunResult:
    return api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=case.ciphertext, word_lengths=case.wli), cipher=case.cipher, key_space=case.key, solver=case.solver, scoring=case.scoring, initial_keys=case.initial_keys, text_direction=case.direction, telemetry_enabled=True, interruptors=case.interruptors))

def _plain_value(value: Any) -> Any:
    return getattr(value, 'value', value)

def _run_status(report: Any) -> str | None:
    value = report.details.get('run_status') if report is not None else None
    if isinstance(value, Mapping):
        status = value.get('execution_status')
        return None if status is None else str(_plain_value(status))
    return None

def _int_list(value: Any) -> list[int]:
    if value is None:
        return []
    if hasattr(value, 'tolist'):
        value = value.tolist()
    return [int(item) for item in list(value)]

def classify_result(*, valid: bool, truth_accepted: bool) -> str:
    if not valid:
        return 'FAIL'
    return 'PASS' if truth_accepted else 'REVIEW'

def assess_result(case: CampaignCase, result: api.RunResult) -> dict[str, Any]:
    report = result.solver_report
    plaintext = _int_list(result.plaintext)
    ratio = match_ratio(plaintext, case.reference)
    score = result.score
    recovered_values = _int_list(result.key)
    recovered_key = recovered_values[:case.key_length]
    recovered_interruptors = sorted(recovered_values[case.key_length:])
    assessor = FAMILIES[case.family].key_equivalence
    key_equivalent = None if assessor is None else bool(assessor(case, recovered_key))
    interruptor_match = None if case.expected_interruptors is None else recovered_interruptors == case.expected_interruptors
    rule = resolved_recipe(case.family).acceptance
    truth_accepted = ratio >= rule.plaintext_match
    if rule.require_interruptor_match:
        truth_accepted = truth_accepted and interruptor_match is True
    valid = score is not None and math.isfinite(float(score)) and (len(plaintext) == len(case.reference)) and (result.status.execution_status is api.advanced.ExecutionStatus.COMPLETED)
    return {'valid': valid, 'truth_accepted': truth_accepted, 'classification': classify_result(valid=valid, truth_accepted=truth_accepted), 'match_ratio': ratio, 'exact_recovery': ratio == 1.0, 'expected_key': case.expected_key, 'recovered_key': recovered_key, 'key_equivalent': key_equivalent, 'expected_interruptors': case.expected_interruptors, 'recovered_interruptors': recovered_interruptors, 'interruptor_match': interruptor_match, 'run_status': result.status.execution_status.value, 'stop_reason': result.status.stop_reason.value, 'best_score': report.best_score, 'evaluations': report.evaluations, 'tokens': report.tokens_processed, 'requested_seed': report.requested_seed, 'effective_seed': report.effective_seed}

def _attempt_record(case: CampaignCase, attempt_index: int, seed: int, result: Any, elapsed: float) -> dict[str, Any]:
    assessment = assess_result(case, result)
    return {'attempt_index': attempt_index, 'attempt_seed': seed, 'runtime_seconds': elapsed, **assessment, 'notes': '' if assessment['classification'] == 'PASS' else 'truth_not_accepted'}

def _attempt_failure(attempt_index: int, seed: int, exc: BaseException, elapsed: float) -> dict[str, Any]:
    return {'attempt_index': attempt_index, 'attempt_seed': seed, 'runtime_seconds': elapsed, 'valid': False, 'truth_accepted': False, 'classification': 'FAIL', 'match_ratio': None, 'exact_recovery': None, 'expected_key': None, 'recovered_key': None, 'key_equivalent': None, 'expected_interruptors': None, 'recovered_interruptors': None, 'interruptor_match': None, 'run_status': None, 'stop_reason': None, 'best_score': None, 'evaluations': None, 'tokens': None, 'requested_seed': seed, 'effective_seed': None, 'notes': f'{type(exc).__name__}: {exc}'}

def _selection_key(attempt: dict[str, Any]) -> tuple[int, float, int]:
    valid = int(bool(attempt['valid']))
    score = -math.inf if attempt['best_score'] is None else float(attempt['best_score'])
    return (valid, score, -int(attempt['attempt_index']))

def run_trial(family: str, trial_index: int, mode: str | None=None) -> dict[str, Any]:
    seed = trial_seed(family, trial_index)
    group = FAMILIES[family].group
    recipe = resolved_recipe(family)
    selected_mode = config.CAMPAIGN_MODE if mode is None else str(mode)
    count = int(recipe.attempt_count)
    if count < 1:
        raise ValueError(f'{family}: attempts per trial must be >= 1')
    print(f'[campaign] START family={family} group={group} trial={trial_index + 1} seed={seed} attempts={count}', flush=True)
    attempts: list[dict[str, Any]] = []
    cases: dict[int, CampaignCase] = {}
    for index in range(count):
        solver_seed = attempt_seed(family, trial_index, index)
        started = time.perf_counter()
        try:
            case = build_case(family, trial_index, index)
            cases[index] = case
            result = execute_case(case)
            attempt = _attempt_record(case, index, solver_seed, result, time.perf_counter() - started)
        except Exception as exc:
            attempt = _attempt_failure(index, solver_seed, exc, time.perf_counter() - started)
        attempts.append(attempt)
        print(f"[campaign] ATTEMPT family={family} index={index} class={attempt['classification']} match={attempt['match_ratio']} runtime={attempt['runtime_seconds']:.3f}s", flush=True)
    selected = max(attempts, key=_selection_key)
    selected_index = int(selected['attempt_index'])
    selected_case = cases.get(selected_index)
    record = {field: None for field in RESULT_FIELDS}
    record.update(campaign_seed=CAMPAIGN_SEED, trial_seed=seed, trial_index=trial_index, trial_id=f'{family}.{trial_index}', family=family, recipe_id=recipe.recipe_id, recipe_fingerprint=recipe_fingerprint(family), configuration_fingerprint=configuration_fingerprint(family, selected_mode), scorer_profile=config.scoring_to_dict(recipe.scoring), selection_policy=recipe.selection, truth_used_for_selection=False, campaign_group=group, attempt_count=count, attempt_seeds=[int(item['attempt_seed']) for item in attempts], attempts=attempts, selected_attempt=selected_index, selection_reason='highest valid solver score; earliest attempt breaks ties', requested_seed=selected['requested_seed'], effective_seed=selected['effective_seed'], match_ratio=selected['match_ratio'], exact_recovery=selected['exact_recovery'], expected_key=selected['expected_key'], recovered_key=selected['recovered_key'], key_equivalent=selected['key_equivalent'], expected_interruptors=selected['expected_interruptors'], recovered_interruptors=selected['recovered_interruptors'], interruptor_match=selected['interruptor_match'], run_status=selected['run_status'], stop_reason=selected['stop_reason'], best_score=selected['best_score'], evaluations=selected['evaluations'], tokens=selected['tokens'], runtime_seconds=sum((float(item['runtime_seconds']) for item in attempts)), classification=selected['classification'], notes=selected['notes'])
    if selected_case is not None:
        record.update(direction=selected_case.direction.value, **selected_case.source, plaintext_length=len(selected_case.reference), cipher_parameters=selected_case.cipher_parameters, solver_parameters=selected_case.solver_parameters)
    print(f"[campaign] END family={family} class={record['classification']} match={record['match_ratio']} runtime={record['runtime_seconds']:.3f}s stop={record['stop_reason']}", flush=True)
    return record

def failure_record(family: str, trial_index: int, seed: int, exc: BaseException, elapsed: float, mode: str | None=None) -> dict[str, Any]:
    recipe = resolved_recipe(family)
    selected_mode = config.CAMPAIGN_MODE if mode is None else str(mode)
    record = {field: None for field in RESULT_FIELDS}
    record.update(campaign_seed=CAMPAIGN_SEED, trial_seed=seed, trial_index=trial_index, trial_id=f'{family}.{trial_index}', family=family, recipe_id=recipe.recipe_id, recipe_fingerprint=recipe_fingerprint(family), configuration_fingerprint=configuration_fingerprint(family, selected_mode), scorer_profile=config.scoring_to_dict(recipe.scoring), selection_policy=recipe.selection, truth_used_for_selection=False, campaign_group=config.FAMILY_GROUPS.get(family), runtime_seconds=elapsed, classification='FAIL', notes=f'{type(exc).__name__}: {exc}')
    return record

def write_records(records: Sequence[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + '\n')

def append_record(record: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + '\n')
        handle.flush()
        os.fsync(handle.fileno())

def campaign_plan(mode: str, family: str) -> list[tuple[str, int]]:
    if family not in FAMILIES:
        raise ValueError(f'unknown campaign family: {family!r}')
    count = 1 if FAMILIES[family].group == 'SPECIALIST' else campaign_trial_count(mode)
    return [(family, trial_index) for trial_index in range(count)]

def campaign_artifact_paths(output: Path) -> tuple[Path, Path]:
    return (output.with_suffix('.log'), output.with_suffix('.provenance.json'))

def qualification_output_path(mode: str, family: str) -> Path:
    recipe_id = str(resolved_recipe(family).recipe_id)
    revision = _git_value('rev-parse', 'HEAD').lower()
    if not re.fullmatch(r'[0-9a-f]{40,64}', revision):
        raise ValueError(f'invalid Git revision for qualification output: {revision!r}')
    filename = f'{mode}_{recipe_id}_seed{CAMPAIGN_SEED}_git{revision}.jsonl'
    return (OUTPUT_ROOT / 'qualifications' / filename).resolve()

def _git_value(*args: str) -> str:
    return subprocess.check_output(['git', '-C', str(REPO_ROOT), *args], text=True, encoding='utf-8').strip()

def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def runtime_provenance() -> dict[str, Any]:
    fastlm_path = Path(_fastlm.__file__).resolve()
    identity = {'python_implementation': platform.python_implementation(), 'python_version': platform.python_version(), 'platform': platform.platform(), 'numpy_version': np.__version__, 'zstandard_version': importlib.metadata.version('zstandard'), 'fastlm_filename': fastlm_path.name, 'fastlm_sha256': _sha256_file(fastlm_path)}
    return {**identity, 'runtime_fingerprint': _canonical_hash(identity)}

def source_state() -> dict[str, Any]:
    """Identify every repository source byte that can affect the campaign."""
    tracked_status = _git_value('status', '--short', '--untracked-files=no', '--', *_RUNTIME_SOURCE_PATHS)
    tracked_diff = subprocess.check_output(['git', '-C', str(REPO_ROOT), 'diff', '--binary', 'HEAD', '--', *_RUNTIME_SOURCE_PATHS])
    untracked_text = _git_value('ls-files', '--others', '--exclude-standard', '--', *_RUNTIME_SOURCE_PATHS)
    untracked_files = sorted((line for line in untracked_text.splitlines() if line))
    digest = hashlib.sha256()
    digest.update(tracked_diff)
    for relative in untracked_files:
        path = (REPO_ROOT / relative).resolve()
        if not path.is_file() or not path.is_relative_to(REPO_ROOT):
            raise ValueError(f'invalid untracked runtime source path: {relative!r}')
        digest.update(relative.encode('utf-8'))
        digest.update(b'\x00')
        digest.update(path.read_bytes())
        digest.update(b'\x00')
    dirty = bool(tracked_status or untracked_files)
    return {'source_dirty': dirty, 'tracked_dirty': bool(tracked_status), 'untracked_runtime_files': untracked_files, 'source_diff_sha256': digest.hexdigest() if dirty else None}

def required_lm_lanes(family: str) -> dict[str, tuple[int, ...]]:
    if family == 'two_period_cribs':
        return {'char': (1, 2, 3, 4), 'wli': (1, 2, 3, 4)}
    scoring = resolved_recipe(family).scoring
    char = tuple(sorted((int(order) for order, weight in (scoring.character_order_weights or {}).items() if float(weight) > 0.0))) if scoring.character_lane_enabled else ()
    wli = tuple(sorted((int(order) for order, weight in (scoring.word_length_order_weights or {}).items() if float(weight) > 0.0))) if scoring.word_length_lane_enabled else ()
    return {'char': char, 'wli': wli}

def _asset_profile_for_lanes(lanes: Mapping[str, Sequence[int]]) -> dict[str, Any]:
    profile_manifest = REPO_ROOT / 'asset_profiles_v1.json'
    raw = json.loads(profile_manifest.read_text(encoding='utf-8'))
    required_orders = {int(order) for orders in lanes.values() for order in orders}
    candidates: list[tuple[int, str, Mapping[str, Any]]] = []
    for name, profile in raw['profiles'].items():
        available = {int(order) for order in profile['language_model_orders']}
        if required_orders.issubset(available):
            candidates.append((len(available), str(name), profile))
    if not candidates:
        raise ValueError(f'no asset profile covers LM orders {sorted(required_orders)}')
    _size, name, profile = min(candidates, key=lambda item: (item[0], item[1]))
    verification_manifest = REPO_ROOT / str(profile['verification_manifest'])
    return {'asset_profile': name, 'asset_profile_manifest_sha256': _sha256_file(profile_manifest), 'asset_verification_manifest': verification_manifest.name, 'asset_verification_manifest_sha256': _sha256_file(verification_manifest), 'verification_manifest_path': verification_manifest}

def language_model_asset_provenance(family: str) -> dict[str, Any]:
    """Resolve, verify and fingerprint the exact LM files used by a family."""
    lanes = required_lm_lanes(family)
    profile = _asset_profile_for_lanes(lanes)
    verification = json.loads(profile['verification_manifest_path'].read_text(encoding='utf-8'))
    manifest_entries = {str(entry['final_relpath']): entry for section in ('required_assets', 'installed_assets') for entry in verification.get(section, ()) if isinstance(entry, Mapping) and 'final_relpath' in entry}
    root = default_lm_root().resolve()
    index = load_index(root)
    required_paths = {root / 'index.json'}
    se_mode = str(config.scoring_to_dict(resolved_recipe(family).scoring).get('se_mode', 'nose'))
    direction_tokens = {
        api.TextDirection.LEFT_TO_RIGHT: 'ltr',
        api.TextDirection.RIGHT_TO_LEFT: 'rtl',
    }
    for direction in config.DIRECTIONS:
        mode = direction_tokens[direction]
        for model, orders in lanes.items():
            for order in orders:
                model_config = index.models[model]
                required_paths.add(expand_pattern(root, model_config['joint_pattern'], mode=mode, pos=se_mode, n=int(order)))
                required_paths.add(expand_pattern(root, model_config['ecdf_pattern'], mode=mode, pos=se_mode, n=int(order), stat='logp', win=10))
    asset_root = (REPO_ROOT / 'assets').resolve()
    assets: list[dict[str, Any]] = []
    for path in sorted(required_paths, key=lambda item: item.as_posix()):
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f'required campaign LM asset is missing: {path.name}')
        if not resolved.is_relative_to(asset_root):
            raise ValueError('campaign LM assets must resolve under the repository asset root')
        logical_path = resolved.relative_to(asset_root).as_posix()
        actual_sha256 = _sha256_file(resolved)
        actual_size = resolved.stat().st_size
        expected = manifest_entries.get(logical_path)
        if expected is None:
            raise ValueError(f'campaign LM asset is absent from verification manifest: {logical_path}')
        if str(expected.get('sha256')) != actual_sha256:
            raise ValueError(f'campaign LM asset SHA-256 mismatch: {logical_path}')
        if int(expected.get('size_bytes', -1)) != actual_size:
            raise ValueError(f'campaign LM asset size mismatch: {logical_path}')
        assets.append({'logical_path': logical_path, 'sha256': actual_sha256, 'size_bytes': actual_size})
    public_profile = {key: value for key, value in profile.items() if key != 'verification_manifest_path'}
    return {**public_profile, 'language_model_lanes': {model: list(orders) for model, orders in lanes.items()}, 'language_model_assets': assets, 'language_model_assets_sha256': _canonical_hash(assets)}

def build_provenance(*, mode: str, family: str, output: Path, plan: Sequence[tuple[str, int]], command: Sequence[str]) -> dict[str, Any]:
    validate_campaign_recipes(tuple(FAMILIES))
    recipe = resolved_recipe(family)
    fingerprint = recipe_fingerprint(family)
    source = source_state()
    if mode == 'full' and source['source_dirty']:
        raise RuntimeError('full qualification requires a clean runtime source tree')
    asset_provenance = language_model_asset_provenance(family)
    runtime = runtime_provenance()
    configuration = resolved_campaign_configuration(family, mode)
    configuration.update(trial_count=len(plan), trial_ids=[f'{name}.{index}' for name, index in plan], attempts_per_trial=recipe.attempt_count)
    return {'schema_version': 2, 'recipe_id': recipe.recipe_id, 'recipe_fingerprint': fingerprint, 'configuration_fingerprint': configuration_fingerprint(family, mode), 'created_utc': datetime.now(timezone.utc).isoformat(), 'git_commit': _git_value('rev-parse', 'HEAD'), 'git_branch': _git_value('branch', '--show-current'), 'git_dirty': source['source_dirty'], **source, **runtime, 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'config_sha256': hashlib.sha256((TOOL_ROOT / 'cipher_solver_campaign_config.py').read_bytes()).hexdigest(), 'campaign_configuration': configuration, 'campaign_configuration_sha256': _canonical_hash(configuration), **asset_provenance, 'output': str(output.resolve()), 'command_argv': list(command)}

def load_completed_records(path: Path, *, repair_trailing_partial: bool=False) -> list[dict[str, Any]]:
    lines = path.read_bytes().splitlines(keepends=True)
    records: list[dict[str, Any]] = []
    valid_bytes = 0
    for index, raw_line in enumerate(lines):
        try:
            record = json.loads(raw_line.decode('utf-8'))
            if not isinstance(record, dict) or set(record) != set(RESULT_FIELDS):
                raise ValueError('record does not match campaign result schema')
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            if repair_trailing_partial and index == len(lines) - 1:
                with path.open('r+b') as handle:
                    handle.truncate(valid_bytes)
                break
            raise ValueError(f'invalid JSONL record at line {index + 1}') from None
        records.append(record)
        valid_bytes += len(raw_line)
    trial_ids = [str(record['trial_id']) for record in records]
    if len(trial_ids) != len(set(trial_ids)):
        raise ValueError('duplicate completed trial IDs in JSONL evidence')
    return records

def initialise_run(*, output: Path, provenance: Mapping[str, Any], resume: bool) -> tuple[list[dict[str, Any]], Path]:
    log_path, provenance_path = campaign_artifact_paths(output)
    if resume:
        if not output.is_file() or not provenance_path.is_file():
            raise FileNotFoundError('resume requires existing JSONL and provenance files')
        recorded = json.loads(provenance_path.read_text(encoding='utf-8'))
        for field in ('git_commit', 'source_diff_sha256', 'runner_sha256', 'config_sha256', 'recipe_id', 'recipe_fingerprint', 'configuration_fingerprint', 'campaign_configuration_sha256', 'asset_profile', 'asset_profile_manifest_sha256', 'asset_verification_manifest_sha256', 'language_model_assets_sha256', 'runtime_fingerprint', 'output'):
            if recorded.get(field) != provenance.get(field):
                raise ValueError(f'resume provenance mismatch: {field}')
        return (load_completed_records(output, repair_trailing_partial=True), log_path)
    existing = [path for path in (output, log_path, provenance_path) if path.exists()]
    if existing:
        raise FileExistsError('fresh run refuses to overwrite existing artifacts: ' + ', '.join((str(path) for path in existing)))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.open('x', encoding='utf-8').close()
    provenance_path.write_text(json.dumps(dict(provenance), indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return ([], log_path)

class _Tee:

    def __init__(self, console: Any, log: Any) -> None:
        self.console = console
        self.log = log

    def write(self, value: str) -> int:
        self.console.write(value)
        self.log.write(value)
        return len(value)

    def flush(self) -> None:
        self.console.flush()
        self.log.flush()

def summarise_records(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {name: sum((record['classification'] == name for record in records)) for name in ('PASS', 'REVIEW', 'FAIL')}
    return {'records': len(records), 'classifications': counts}

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=tuple(config.TRIALS_PER_MODE), required=True)
    parser.add_argument('--family', choices=tuple(FAMILIES), required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--resume', action='store_true')
    action.add_argument('--dry-run', action='store_true')
    action.add_argument('--summarize', action='store_true')
    return parser

def _scorer_summary(recipe: config.CampaignRecipe) -> str:
    scorer = recipe.scoring
    parts = [*(f'char{order}={float(weight):.2f}' for order, weight in sorted((scorer.character_order_weights or {}).items())), *(f'WLI{order}={float(weight):.2f}' for order, weight in sorted((scorer.word_length_order_weights or {}).items()))]
    return ', '.join(parts) if parts else 'none'

def print_resolved_plan(mode: str, family: str, plan: Sequence[tuple[str, int]]) -> None:
    recipe = resolved_recipe(family)
    attempts = int(recipe.attempt_count)
    print(f'family: {family}')
    print(f'recipe: {recipe.recipe_id}')
    print(f'trials: {len(plan)}')
    print(f'attempts per trial: {attempts}')
    print(f'total solver attempts: {len(plan) * attempts}')
    print(f'scorer: {_scorer_summary(recipe)}')
    print(f"selection: {str(recipe.selection).replace('_', ' ')}")
    print("truth used for selection: no")
    print(f"recipe fingerprint: {recipe_fingerprint(family)}")
    print(f"configuration fingerprint: {configuration_fingerprint(family, mode)}")
    print(
        "resolved recipe: " + json.dumps(config.recipe_to_dict(recipe), sort_keys=True)
    )


def main(argv: Sequence[str] | None=None) -> int:
    args = _parser().parse_args(argv)
    try:
        output = qualification_output_path(args.mode, args.family)
        plan = campaign_plan(args.mode, args.family)
        if args.dry_run:
            validate_campaign_recipes(tuple(FAMILIES))
            print_resolved_plan(args.mode, args.family, plan)
            source = source_state()
            assets = language_model_asset_provenance(args.family)
            runtime = runtime_provenance()
            print(f"source tree clean: {('no' if source['source_dirty'] else 'yes')}")
            if args.mode == 'full' and source['source_dirty']:
                print('full execution preflight: BLOCKED until runtime source is clean')
            else:
                print('full execution preflight: ready')
            print(f"asset profile: {assets['asset_profile']}")
            print(f"language-model asset fingerprint: {assets['language_model_assets_sha256']}")
            print(f"runtime fingerprint: {runtime['runtime_fingerprint']}")
            print(f'[campaign] RESULTS {output}')
            print(f'[campaign] LOG {campaign_artifact_paths(output)[0]}')
            return 0
        if args.summarize:
            records = load_completed_records(output)
            print(json.dumps(summarise_records(records), indent=2, sort_keys=True))
            return qualification_exit_code(records, args.mode)
        command = [sys.executable, str(Path(__file__).resolve()), *(argv or sys.argv[1:])]
        provenance = build_provenance(mode=args.mode, family=args.family, output=output, plan=plan, command=command)
        records, log_path = initialise_run(output=output, provenance=provenance, resume=args.resume)
        planned_ids = {f'{family}.{index}' for family, index in plan}
        completed_ids = {str(record['trial_id']) for record in records}
        unexpected = completed_ids - planned_ids
        if unexpected:
            raise ValueError(f'resume evidence contains unplanned trial IDs: {sorted(unexpected)}')
        expected_fingerprint = recipe_fingerprint(args.family)
        wrong_recipe = {str(record.get('recipe_fingerprint')) for record in records if record.get('recipe_fingerprint') != expected_fingerprint}
        if wrong_recipe:
            raise ValueError(f'resume evidence contains a different recipe fingerprint: {sorted(wrong_recipe)}')
        expected_configuration = configuration_fingerprint(args.family, args.mode)
        wrong_configuration = {str(record.get('configuration_fingerprint')) for record in records if record.get('configuration_fingerprint') != expected_configuration}
        if wrong_configuration:
            raise ValueError(f'resume evidence contains a different configuration fingerprint: {sorted(wrong_configuration)}')
        log_mode = 'a' if args.resume else 'x'
        with log_path.open(log_mode, encoding='utf-8', newline='\n') as log_handle:
            with contextlib.redirect_stdout(_Tee(sys.stdout, log_handle)):
                with contextlib.redirect_stderr(_Tee(sys.stderr, log_handle)):
                    print_resolved_plan(args.mode, args.family, plan)
                    print(f'[campaign] RUN mode={args.mode} family={args.family} planned={len(plan)} completed={len(records)} output={output}', flush=True)
                    for ordinal, (family, trial_index) in enumerate(plan, start=1):
                        trial_id = f'{family}.{trial_index}'
                        if trial_id in completed_ids:
                            continue
                        print(f'[campaign] PROGRESS {ordinal}/{len(plan)} trial_id={trial_id}', flush=True)
                        record = run_trial(family, trial_index, mode=args.mode)
                        append_record(record, output)
                        records.append(record)
                        completed_ids.add(trial_id)
                    summary = summarise_records(records)
                    print(f'[campaign] RESULTS {output}', flush=True)
                    print(f'[campaign] SUMMARY {json.dumps(summary, sort_keys=True)}', flush=True)
        return qualification_exit_code(records, args.mode)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f'[campaign] ERROR {exc}', file=sys.stderr)
        return 2
if __name__ == '__main__':
    raise SystemExit(main())
