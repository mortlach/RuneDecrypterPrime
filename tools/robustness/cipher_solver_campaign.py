from __future__ import annotations

"""Deterministic known-answer cipher/solver robustness campaign."""

import json
import math
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
TOOL_ROOT = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, SRC_ROOT, TOOL_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from rune_decrypter_prime import api
from rune_decrypter_prime.data.cipher_tests.book_corpus import load_book, select_passage
from rune_decrypter_prime.io.rng import RNGController
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.utils.solve_output import match_ratio

import cipher_solver_campaign_config as config


ALPHABET = 29
CAMPAIGN_SEED = config.CAMPAIGN_SEED
OUTPUT_ROOT = config.OUTPUT_ROOT
OUTPUT_PATH = config.OUTPUT_PATH


@dataclass(slots=True)
class CampaignCase:
    family: str
    direction: api.Direction
    ciphertext: list[int]
    reference: list[int]
    wli: list[list[int]]
    cipher: Any
    key: Any
    solver: Any
    scorer: dict[str, Any]
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


RESULT_FIELDS = (
    "campaign_seed", "trial_seed", "trial_index", "trial_id", "family",
    "campaign_group", "direction", "plaintext_source", "book", "start_word",
    "word_count", "plaintext_length", "cipher_parameters", "solver_parameters",
    "attempt_count", "attempt_seeds", "attempts", "selected_attempt",
    "selection_reason", "requested_seed", "effective_seed", "match_ratio",
    "exact_recovery", "expected_key", "recovered_key", "key_equivalent",
    "expected_interruptors", "recovered_interruptors", "interruptor_match",
    "run_status", "stop_reason", "best_score", "evaluations", "tokens",
    "runtime_seconds", "classification", "notes",
)


def case_seed_namespace(family: str) -> str:
    return str(config.CASE_SEED_NAMESPACES.get(family, family))


def trial_seed(family: str, trial_index: int) -> int:
    rng = RNGController(CAMPAIGN_SEED).scope("cipher_solver_campaign")
    namespace = case_seed_namespace(family)
    return int(rng.child(f"{namespace}.{trial_index}").integers(1, 2**31 - 1))


def attempt_seed(family: str, trial_index: int, attempt_index: int) -> int:
    seed = trial_seed(family, trial_index)
    if int(attempt_index) == 0:
        return seed
    rng = RNGController(seed).scope("solver_attempts")
    return int(rng.child(str(attempt_index)).integers(1, 2**31 - 1))


def trial_direction(trial_index: int) -> api.Direction:
    return api.Direction(config.DIRECTIONS[int(trial_index) % len(config.DIRECTIONS)])


def _book_passage(seed: int, direction: api.Direction):
    rng = RNGController(seed).child("book")
    book = config.BOOKS[int(rng.integers(0, len(config.BOOKS)))]
    passage = select_passage(
        load_book(book, direction),
        seed=seed,
        target_runes=config.TARGET_RUNES,
        tolerance_runes=config.RUNE_TOLERANCE,
    )
    source = {
        "plaintext_source": f"packaged_book:{book}",
        "book": book,
        "start_word": passage.start_word,
        "word_count": passage.word_count,
    }
    return passage.plaintext, passage.wli.tolist(), source


def _scorer(direction: api.Direction) -> dict[str, Any]:
    return {**config.SCORER, "encoding_dir": direction}


def _range_value(rng: RNGController, limits: tuple[int, int]) -> int:
    low, high = (int(value) for value in limits)
    return int(rng.integers(low, high + 1))


def _multiply(value: int, key_value: int) -> int:
    return (int(value) * int(key_value)) % ALPHABET


def _exact_key_equivalence(case: CampaignCase, recovered: list[int]) -> bool:
    return case.expected_key is not None and recovered == case.expected_key


def _repeating_key_equivalence(case: CampaignCase, recovered: list[int]) -> bool:
    expected = list(case.expected_key or [])
    if not expected or len(recovered) != len(expected):
        return False
    if case.direction is api.Direction.LTR:
        return recovered == expected
    core_length = len(case.reference) - len(case.expected_interruptors or ())
    shift = core_length % len(expected)
    transformed = list(reversed(expected))
    if shift:
        transformed = transformed[-shift:] + transformed[:-shift]
    return recovered == transformed


def campaign_trial_count(mode: str | None = None) -> int:
    selected = config.CAMPAIGN_MODE if mode is None else str(mode)
    try:
        count = int(config.TRIALS_PER_MODE[selected])
    except KeyError as exc:
        raise ValueError(f"unknown campaign mode: {selected!r}") from exc
    if count < 1:
        raise ValueError(f"campaign mode {selected!r} requires at least one trial")
    return count


def qualification_exit_code(
    records: Sequence[Mapping[str, Any]], mode: str | None = None
) -> int:
    selected = config.CAMPAIGN_MODE if mode is None else str(mode)
    if selected not in config.BLOCKING_REVIEW_GROUPS:
        raise ValueError(f"unknown campaign mode: {selected!r}")
    if any(record.get("classification") == "FAIL" for record in records):
        return 1
    blocking_groups = set(config.BLOCKING_REVIEW_GROUPS[selected])
    return int(
        any(
            record.get("classification") == "REVIEW"
            and record.get("campaign_group") in blocking_groups
            for record in records
        )
    )


def _ordinary_inputs(family: str, trial_index: int, attempt_index: int):
    seed = trial_seed(family, trial_index)
    solver_seed = attempt_seed(family, trial_index, attempt_index)
    direction = trial_direction(trial_index)
    plaintext, wli, source = _book_passage(seed, direction)
    rng = RNGController(seed).scope(case_seed_namespace(family))
    limits = config.CIPHER_RANGES[family]
    budget = dict(config.SOLVER_BUDGETS[family])
    budget["seed"] = solver_seed
    return seed, direction, plaintext, wli, source, rng, limits, budget


def _case(
    *, family: str, direction: api.Direction, plaintext: np.ndarray,
    wli: list[list[int]], source: dict[str, Any], ciphertext: Sequence[int],
    cipher: Any, key: Any, solver: Any, cipher_parameters: dict[str, Any],
    key_length: int, expected_key: Sequence[int] | None = None,
    expected_interruptors: Sequence[int] | None = None,
    initial_keys: Any = None, interruptors: Any = None,
    scorer: Mapping[str, Any] | None = None,
) -> CampaignCase:
    return CampaignCase(
        family=family,
        direction=direction,
        ciphertext=[int(value) for value in ciphertext],
        reference=[int(value) for value in plaintext],
        wli=wli,
        cipher=cipher,
        key=key,
        solver=solver,
        scorer=(
            _scorer(direction)
            if scorer is None
            else {**dict(scorer), "encoding_dir": direction}
        ),
        cipher_parameters=cipher_parameters,
        solver_parameters=dict(solver.params),
        source=source,
        key_length=key_length,
        expected_key=None if expected_key is None else [int(v) for v in expected_key],
        expected_interruptors=(
            None if expected_interruptors is None
            else sorted(int(v) for v in expected_interruptors)
        ),
        initial_keys=initial_keys,
        interruptors=interruptors,
    )


def _build_vigenere(trial_index: int, attempt_index: int) -> CampaignCase:
    family = "vigenere_beam"
    _, direction, pt, wli, source, rng, limits, budget = _ordinary_inputs(
        family, trial_index, attempt_index
    )
    length = _range_value(rng.child("shape"), limits["key_length"])
    truth = rng.child("key").integers(0, ALPHABET, size=length).tolist()
    cipher = api.by_name.cipher("vigenere", key_len=length)
    key = api.KeySpec.repeat(len=length)
    obj = api.cipher_instance(
        "vigenere", key_length=length, text_transposition=direction.value
    )
    ct = obj.encrypt_single(plaintext=pt, key=np.asarray(truth, dtype=np.uint8))
    return _case(
        family=family, direction=direction, plaintext=pt, wli=wli, source=source,
        ciphertext=ct, cipher=cipher, key=key, solver=api.SolverSpec.beam(**budget),
        cipher_parameters={"key_length": length, "key": truth}, key_length=length,
        expected_key=truth,
    )


def _build_railfence(trial_index: int, attempt_index: int) -> CampaignCase:
    family = "railfence_beam"
    _, direction, pt, wli, source, rng, limits, budget = _ordinary_inputs(
        family, trial_index, attempt_index
    )
    low, high = limits["rails"]
    rails = _range_value(rng.child("key"), (low, high))
    truth = [rails - low]
    cipher = api.by_name.cipher("railfence", min_rails=low, max_rails=high)
    key = api.KeySpec.scalar(max_val=high - low + 1)
    # CipherSpec stores wrapper parameters in ``extra`` while the concrete
    # RailFenceCipher reads direct attributes.  Pass the declared range
    # explicitly so generation and solving use the same key space.
    obj = api.cipher_instance("railfence", min_rails=low, max_rails=high)
    ct = obj.encrypt(
        plaintext=pt, key=np.asarray(truth, dtype=np.uint8)
    )
    return _case(
        family=family, direction=direction, plaintext=pt, wli=wli, source=source,
        ciphertext=ct, cipher=cipher, key=key, solver=api.SolverSpec.beam(**budget),
        cipher_parameters={"rails": rails, "min_rails": low, "max_rails": high,
                           "key": truth},
        key_length=1, expected_key=truth,
    )


def _build_autokey(trial_index: int, attempt_index: int) -> CampaignCase:
    family = "autokey_beam"
    _, direction, pt, wli, source, rng, limits, budget = _ordinary_inputs(
        family, trial_index, attempt_index
    )
    length = _range_value(rng.child("shape"), limits["seed_length"])
    truth = rng.child("key").integers(0, ALPHABET, size=length).tolist()
    cipher = api.by_name.cipher("autokey", seed_len=length, alphabet_size=ALPHABET)
    key = api.KeySpec.repeat(len=length)
    obj = api.cipher_instance("autokey", seed_length=length, alphabet_size=ALPHABET)
    ct = obj.encrypt_single(plaintext=pt, key=np.asarray(truth, dtype=np.uint8))
    return _case(
        family=family, direction=direction, plaintext=pt, wli=wli, source=source,
        ciphertext=ct, cipher=cipher, key=key, solver=api.SolverSpec.beam(**budget),
        cipher_parameters={"seed_length": length, "key": truth}, key_length=length,
        expected_key=truth, scorer=config.AUTOKEY_SCORER,
    )


def _build_columnar(trial_index: int, attempt_index: int) -> CampaignCase:
    family = "columnar_hybrid"
    _, direction, pt, wli, source, rng, limits, budget = _ordinary_inputs(
        family, trial_index, attempt_index
    )
    columns = _range_value(rng.child("shape"), limits["columns"])
    truth = rng.child("key").permutation(columns).tolist()
    cipher = api.by_name.cipher("columnar", key_length=columns)
    key = api.KeySpec.permutation(len=columns)
    ct = api.cipher_instance(cipher).encrypt_single(
        plaintext=pt, key=np.asarray(truth, dtype=np.uint8)
    )
    return _case(
        family=family, direction=direction, plaintext=pt, wli=wli, source=source,
        ciphertext=ct, cipher=cipher, key=key, solver=api.SolverSpec.hybrid(**budget),
        cipher_parameters={"columns": columns, "key": truth}, key_length=columns,
        expected_key=truth,
    )


def _build_mono(trial_index: int, attempt_index: int) -> CampaignCase:
    family = "mono_ga"
    _, direction, pt, wli, source, rng, _, budget = _ordinary_inputs(
        family, trial_index, attempt_index
    )
    truth = rng.child("key").permutation(ALPHABET).astype(np.uint8)
    cipher = api.by_name.cipher("mono")
    key = api.KeySpec.permutation(len=ALPHABET)
    ct = api.cipher_instance(cipher).encrypt(plaintext=pt, key=truth)
    seed_count = int(budget.pop("seed_keys"))
    seed_swaps = int(budget.pop("seed_swaps"))
    solver_seed = int(budget["seed"])
    initial_keys = make_seeds_from_freq(
        Runeglish.to_rune(ct.tolist(), wli).replace(" ", ""),
        n_keys=seed_count,
        swaps_per_key=seed_swaps,
        seed=solver_seed,
        direction=direction.value,
    )
    return _case(
        family=family, direction=direction, plaintext=pt, wli=wli, source=source,
        ciphertext=ct, cipher=cipher, key=key, solver=api.SolverSpec.ga(**budget),
        cipher_parameters={"alphabet_size": ALPHABET, "key": truth.tolist()},
        key_length=ALPHABET, expected_key=truth, initial_keys=initial_keys,
    )


def _build_vigenere_interruptors(
    trial_index: int, attempt_index: int
) -> CampaignCase:
    family = "vigenere_interruptors_beam"
    _, direction, pt, wli, source, rng, limits, budget = _ordinary_inputs(
        family, trial_index, attempt_index
    )
    length = _range_value(rng.child("shape"), limits["key_length"])
    truth = rng.child("key").integers(0, ALPHABET, size=length).tolist()
    pool_size = _range_value(rng.child("pool_size"), limits["pool_size"])
    count = _range_value(rng.child("count"), limits["interruptor_count"])
    pool = sorted(rng.child("pool").choice(len(pt), size=pool_size, replace=False).tolist())
    chosen = sorted(rng.child("chosen").choice(pool, size=count, replace=False).tolist())
    cipher = api.by_name.cipher("vigenere", key_len=length)
    key = api.KeySpec.repeat(len=length)
    obj = api.cipher_instance(
        "vigenere", key_length=length, text_transposition=direction.value
    )
    ct = obj.encrypt_single(
        plaintext=pt, key=np.asarray(truth, dtype=np.uint8), interrupt_idx=chosen
    )
    interruptors = api.InterruptorConfig(
        mode="pool", pool=pool, min_count=count, max_count=count
    )
    return _case(
        family=family, direction=direction, plaintext=pt, wli=wli, source=source,
        ciphertext=ct, cipher=cipher, key=key, solver=api.SolverSpec.beam(**budget),
        cipher_parameters={"key_length": length, "key": truth,
                           "interruptor_pool": pool, "interruptors": chosen},
        key_length=length, expected_key=truth, expected_interruptors=chosen,
        interruptors=interruptors,
    )


def _build_generic_map(trial_index: int, attempt_index: int) -> CampaignCase:
    family = "generic_map_multiply_beam"
    _, direction, pt, wli, source, rng, limits, budget = _ordinary_inputs(
        family, trial_index, attempt_index
    )
    length = _range_value(rng.child("shape"), limits["key_length"])
    truth = rng.child("key").integers(1, ALPHABET, size=length).tolist()
    cipher = api.define_map(function=_multiply, N=ALPHABET)
    key = api.KeySpec.repeat(len=length)
    stream = np.resize(np.asarray(truth, dtype=np.uint8), len(pt))
    ct = (pt.astype(np.int16) * stream.astype(np.int16) % ALPHABET).astype(np.uint8)
    return _case(
        family=family, direction=direction, plaintext=pt, wli=wli, source=source,
        ciphertext=ct, cipher=cipher, key=key, solver=api.SolverSpec.beam(**budget),
        cipher_parameters={"key_length": length, "key": truth}, key_length=length,
        expected_key=truth,
    )


def _build_scheduled_stream(trial_index: int, attempt_index: int) -> CampaignCase:
    family = "scheduled_stream_beam"
    _, direction, pt, wli, source, rng, limits, budget = _ordinary_inputs(
        family, trial_index, attempt_index
    )
    period = _range_value(rng.child("shape"), limits["period"])
    truth = rng.child("key").integers(0, ALPHABET, size=period).tolist()
    cipher, default_key = api.by_name.cipher_with_key(
        "scheduled_stream_lookup",
        streams=[{"name": "A", "kind": "periodic", "period": period}],
        schedule="overlay", operation="add", alphabet_size=ALPHABET,
        default_key=True,
    )
    key = default_key or api.KeySpec.repeat(len=period)
    ct = api.cipher_instance(cipher).encrypt_single(
        plaintext=pt, key=np.asarray(truth, dtype=np.uint8)
    )
    return _case(
        family=family, direction=direction, plaintext=pt, wli=wli, source=source,
        ciphertext=ct, cipher=cipher, key=key, solver=api.SolverSpec.beam(**budget),
        cipher_parameters={"period": period, "key": truth}, key_length=period,
        expected_key=truth,
    )


def _build_two_period(trial_index: int, attempt_index: int) -> CampaignCase:
    family = "two_period_cribs"
    solver_seed = attempt_seed(family, trial_index, attempt_index)
    tutorial_root = REPO_ROOT / "tutorials" / "v1"
    if str(tutorial_root) not in sys.path:
        sys.path.insert(0, str(tutorial_root))
    from tutorials.v1.data.two_period_cribs_demo import build_demo_fixture
    from tutorials.v1.Tutorial_TwoPeriodCribs import FIXED_CRIBS, PERIOD_A, PERIOD_B, STARTS

    cipher, key = api.by_name.cipher_with_key(
        "two_period_vigenere", period_a=PERIOD_A, period_b=PERIOD_B,
        alphabet_size=ALPHABET, default_key=True,
    )
    fixture = build_demo_fixture(cipher)
    solver = api.SolverSpec.two_period_cribs(
        fixed_cribs=FIXED_CRIBS, starts=STARTS, seed=solver_seed
    )
    return CampaignCase(
        family=family, direction=api.Direction.LTR,
        ciphertext=list(fixture.ciphertext), reference=list(fixture.reference_plaintext),
        wli=[list(row) for row in fixture.wli], cipher=cipher, key=key, solver=solver,
        scorer={}, cipher_parameters={"period_a": PERIOD_A, "period_b": PERIOD_B,
                                      "key": list(fixture.reference_key)},
        solver_parameters=dict(solver.params),
        source={"plaintext_source": "two_period_cribs_demo", "book": None,
                "start_word": None, "word_count": None},
        key_length=PERIOD_A + PERIOD_B, expected_key=list(fixture.reference_key),
    )


FAMILIES = {
    definition.name: definition
    for definition in (
        FamilyDefinition(
            "vigenere_beam", config.FAMILY_GROUPS["vigenere_beam"],
            _build_vigenere, _repeating_key_equivalence,
        ),
        FamilyDefinition("railfence_beam", config.FAMILY_GROUPS["railfence_beam"], _build_railfence),
        FamilyDefinition(
            "autokey_beam", config.FAMILY_GROUPS["autokey_beam"],
            _build_autokey, _exact_key_equivalence,
        ),
        FamilyDefinition(
            "columnar_hybrid", config.FAMILY_GROUPS["columnar_hybrid"],
            _build_columnar, _exact_key_equivalence,
        ),
        FamilyDefinition("mono_ga", config.FAMILY_GROUPS["mono_ga"], _build_mono),
        FamilyDefinition(
            "vigenere_interruptors_beam",
            config.FAMILY_GROUPS["vigenere_interruptors_beam"],
            _build_vigenere_interruptors, _repeating_key_equivalence,
        ),
        FamilyDefinition(
            "generic_map_multiply_beam",
            config.FAMILY_GROUPS["generic_map_multiply_beam"],
            _build_generic_map, _exact_key_equivalence,
        ),
        FamilyDefinition(
            "scheduled_stream_beam",
            config.FAMILY_GROUPS["scheduled_stream_beam"],
            _build_scheduled_stream, _exact_key_equivalence,
        ),
        FamilyDefinition("two_period_cribs", config.FAMILY_GROUPS["two_period_cribs"], _build_two_period),
    )
}
ORDINARY_FAMILIES = tuple(
    name for name, definition in FAMILIES.items() if definition.group != "SPECIALIST"
)
SPECIALIST_FAMILIES = tuple(
    name for name, definition in FAMILIES.items() if definition.group == "SPECIALIST"
)


def build_case(family: str, trial_index: int, attempt_index: int = 0) -> CampaignCase:
    try:
        definition = FAMILIES[family]
    except KeyError as exc:
        raise KeyError(f"unknown campaign family: {family}") from exc
    return definition.builder(int(trial_index), int(attempt_index))


def execute_case(case: CampaignCase):
    kwargs: dict[str, Any] = {
        "text": (
            (case.ciphertext, case.wli)
            if FAMILIES[case.family].group == "SPECIALIST"
            else case.ciphertext
        ),
        "cipher": case.cipher,
        "key": case.key,
        "solver": case.solver,
        "encoding_dir": case.direction,
        "telemetry_on": True,
        "return_solver_report": True,
    }
    if FAMILIES[case.family].group != "SPECIALIST":
        kwargs.update(
            device="cpu", scorer="rune", scorer_params=case.scorer,
            wli_data=case.wli, force_no_wli=False, initial_keys=case.initial_keys,
            interruptors=case.interruptors,
        )
    return api.run(**kwargs)


def _plain_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _run_status(report: Any) -> str | None:
    value = report.details.get("run_status") if report is not None else None
    if isinstance(value, Mapping):
        status = value.get("execution_status")
        return None if status is None else str(_plain_value(status))
    return None


def _int_list(value: Any) -> list[int]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [int(item) for item in list(value)]


def classify_result(*, valid: bool, truth_accepted: bool) -> str:
    if not valid:
        return "FAIL"
    return "PASS" if truth_accepted else "REVIEW"


def assess_result(case: CampaignCase, result: Any) -> dict[str, Any]:
    report = getattr(result, "solver_report", None)
    solution = getattr(result, "solution", result)
    plaintext = _int_list(getattr(solution, "plaintext_idx", []))
    ratio = match_ratio(plaintext, case.reference)
    score = getattr(solution, "score", None)
    recovered_values = _int_list(getattr(solution, "key", []))
    recovered_key = recovered_values[:case.key_length]
    recovered_interruptors = sorted(recovered_values[case.key_length:])
    key_assessor = FAMILIES[case.family].key_equivalence
    key_equivalent = (
        None if key_assessor is None else bool(key_assessor(case, recovered_key))
    )
    interruptor_match = (
        None if case.expected_interruptors is None
        else recovered_interruptors == case.expected_interruptors
    )
    rule = config.ACCEPTANCE_RULES[case.family]
    truth_accepted = ratio >= float(rule["plaintext_match"])
    if rule.get("require_interruptor_match"):
        truth_accepted = truth_accepted and interruptor_match is True
    run_status = _run_status(report)
    valid = (
        report is not None
        and score is not None
        and math.isfinite(float(score))
        and len(plaintext) == len(case.reference)
        and bool(getattr(report, "stop_reason", None))
        and run_status == "completed"
    )
    return {
        "valid": valid,
        "truth_accepted": truth_accepted,
        "classification": classify_result(valid=valid, truth_accepted=truth_accepted),
        "match_ratio": ratio,
        "exact_recovery": ratio == 1.0,
        "expected_key": case.expected_key,
        "recovered_key": recovered_key,
        "key_equivalent": key_equivalent,
        "expected_interruptors": case.expected_interruptors,
        "recovered_interruptors": recovered_interruptors,
        "interruptor_match": interruptor_match,
        "run_status": run_status,
        "stop_reason": _plain_value(getattr(report, "stop_reason", None)),
        "best_score": getattr(report, "best_score", score),
        "evaluations": getattr(report, "evals", None),
        "tokens": getattr(report, "tokens_processed", None),
        "requested_seed": getattr(report, "requested_seed", None),
        "effective_seed": getattr(report, "effective_seed", None),
    }


def _attempt_record(
    case: CampaignCase, attempt_index: int, seed: int, result: Any, elapsed: float
) -> dict[str, Any]:
    assessment = assess_result(case, result)
    return {
        "attempt_index": attempt_index,
        "attempt_seed": seed,
        "runtime_seconds": elapsed,
        **assessment,
        "notes": "" if assessment["classification"] == "PASS" else "truth_not_accepted",
    }


def _attempt_failure(
    attempt_index: int, seed: int, exc: BaseException, elapsed: float
) -> dict[str, Any]:
    return {
        "attempt_index": attempt_index, "attempt_seed": seed,
        "runtime_seconds": elapsed, "valid": False, "truth_accepted": False,
        "classification": "FAIL", "match_ratio": None, "exact_recovery": None,
        "expected_key": None, "recovered_key": None, "key_equivalent": None,
        "expected_interruptors": None, "recovered_interruptors": None,
        "interruptor_match": None, "run_status": None, "stop_reason": None,
        "best_score": None, "evaluations": None, "tokens": None,
        "requested_seed": seed, "effective_seed": None,
        "notes": f"{type(exc).__name__}: {exc}",
    }


def _selection_key(attempt: dict[str, Any]) -> tuple[int, float, float]:
    rank = {"FAIL": 0, "REVIEW": 1, "PASS": 2}[attempt["classification"]]
    ratio = -1.0 if attempt["match_ratio"] is None else float(attempt["match_ratio"])
    score = -math.inf if attempt["best_score"] is None else float(attempt["best_score"])
    return rank, ratio, score


def run_trial(family: str, trial_index: int) -> dict[str, Any]:
    seed = trial_seed(family, trial_index)
    group = FAMILIES[family].group
    count = int(config.ATTEMPTS_PER_TRIAL[family])
    if count < 1:
        raise ValueError(f"{family}: attempts per trial must be >= 1")
    print(
        f"[campaign] START family={family} group={group} "
        f"trial={trial_index + 1} seed={seed} attempts={count}", flush=True,
    )
    attempts: list[dict[str, Any]] = []
    cases: dict[int, CampaignCase] = {}
    for index in range(count):
        solver_seed = attempt_seed(family, trial_index, index)
        started = time.perf_counter()
        try:
            case = build_case(family, trial_index, index)
            cases[index] = case
            result = execute_case(case)
            attempt = _attempt_record(
                case, index, solver_seed, result, time.perf_counter() - started
            )
        except Exception as exc:
            attempt = _attempt_failure(
                index, solver_seed, exc, time.perf_counter() - started
            )
        attempts.append(attempt)
        print(
            f"[campaign] ATTEMPT family={family} index={index} "
            f"class={attempt['classification']} match={attempt['match_ratio']} "
            f"runtime={attempt['runtime_seconds']:.3f}s", flush=True,
        )

    selected = max(attempts, key=_selection_key)
    selected_index = int(selected["attempt_index"])
    selected_case = cases.get(selected_index)
    record = {field: None for field in RESULT_FIELDS}
    record.update(
        campaign_seed=CAMPAIGN_SEED,
        trial_seed=seed,
        trial_index=trial_index,
        trial_id=f"{family}.{trial_index}",
        family=family,
        campaign_group=group,
        attempt_count=count,
        attempt_seeds=[int(item["attempt_seed"]) for item in attempts],
        attempts=attempts,
        selected_attempt=selected_index,
        selection_reason="best classification, then plaintext match, then score",
        requested_seed=selected["requested_seed"],
        effective_seed=selected["effective_seed"],
        match_ratio=selected["match_ratio"],
        exact_recovery=selected["exact_recovery"],
        expected_key=selected["expected_key"],
        recovered_key=selected["recovered_key"],
        key_equivalent=selected["key_equivalent"],
        expected_interruptors=selected["expected_interruptors"],
        recovered_interruptors=selected["recovered_interruptors"],
        interruptor_match=selected["interruptor_match"],
        run_status=selected["run_status"],
        stop_reason=selected["stop_reason"],
        best_score=selected["best_score"],
        evaluations=selected["evaluations"],
        tokens=selected["tokens"],
        runtime_seconds=sum(float(item["runtime_seconds"]) for item in attempts),
        classification=selected["classification"],
        notes=selected["notes"],
    )
    if selected_case is not None:
        record.update(
            direction=selected_case.direction.value,
            **selected_case.source,
            plaintext_length=len(selected_case.reference),
            cipher_parameters=selected_case.cipher_parameters,
            solver_parameters=selected_case.solver_parameters,
        )
    print(
        f"[campaign] END family={family} class={record['classification']} "
        f"match={record['match_ratio']} runtime={record['runtime_seconds']:.3f}s "
        f"stop={record['stop_reason']}", flush=True,
    )
    return record


def failure_record(
    family: str, trial_index: int, seed: int, exc: BaseException, elapsed: float
) -> dict[str, Any]:
    record = {field: None for field in RESULT_FIELDS}
    record.update(
        campaign_seed=CAMPAIGN_SEED, trial_seed=seed, trial_index=trial_index,
        trial_id=f"{family}.{trial_index}", family=family,
        campaign_group=config.FAMILY_GROUPS.get(family), runtime_seconds=elapsed,
        classification="FAIL", notes=f"{type(exc).__name__}: {exc}",
    )
    return record


def write_records(records: Sequence[dict[str, Any]], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def append_record(record: dict[str, Any], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def main() -> int:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("", encoding="utf-8")
    records: list[dict[str, Any]] = []
    trial_count = campaign_trial_count()
    for family in ORDINARY_FAMILIES:
        for trial_index in range(trial_count):
            record = run_trial(family, trial_index)
            records.append(record)
            append_record(record)
    for family in SPECIALIST_FAMILIES:
        record = run_trial(family, 0)
        records.append(record)
        append_record(record)
    counts = {
        name: sum(record["classification"] == name for record in records)
        for name in ("PASS", "REVIEW", "FAIL")
    }
    print(f"[campaign] RESULTS {OUTPUT_PATH}", flush=True)
    print(f"[campaign] SUMMARY records={len(records)} {counts}", flush=True)
    return qualification_exit_code(records)


if __name__ == "__main__":
    raise SystemExit(main())
