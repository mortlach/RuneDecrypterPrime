from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from cipher_development.periodic_sub_trans_wli.config import (
    ALPHABET_SIZE,
    KAEDING_SOLVER_CONTRACT,
    MASTER_SEED,
    ORDER,
    RAW_SCORING_CONTRACT,
    WLI_SCORING_CONTRACT,
    BenchmarkSpec,
    RunBudget,
)

ScoreKeys = Callable[[Sequence[Sequence[int]] | np.ndarray], tuple[np.ndarray, np.ndarray]]
GenerateKeys = Callable[[int], list[list[int]]]
ValidateKey = Callable[[Sequence[int] | np.ndarray], np.ndarray]
ExploitKey = Callable[[Sequence[int] | np.ndarray, int, RunBudget], "SolverEvidence"]


@dataclass(frozen=True, slots=True)
class SolverEvidence:
    final_key: tuple[int, ...]
    reported_score: float
    evaluations: int
    elapsed_s: float
    stop_reason: str | None
    telemetry: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SearchCase:
    benchmark_id: str
    family: str
    period: int
    columns: int
    length: int
    order: str
    sample_start: int
    ciphertext: tuple[int, ...]
    wli: tuple[tuple[int, int], ...]
    validate_key: ValidateKey
    generate_seed_keys: GenerateKeys
    score_keys: ScoreKeys
    exploit_key: ExploitKey


@dataclass(frozen=True, slots=True)
class ReferenceCase:
    cipher: Any
    plaintext: np.ndarray
    ciphertext: np.ndarray
    wli: tuple[tuple[int, int], ...]
    true_key: np.ndarray


def _validated_wli_pairs(
    wli: Sequence[Sequence[int]],
) -> tuple[tuple[int, int], ...]:
    pairs = tuple((int(pair[0]), int(pair[1])) for pair in wli)
    if not pairs:
        raise ValueError("WLI must not be empty")
    index = 0
    while index < len(pairs):
        offset, word_length = pairs[index]
        if offset != 0 or word_length <= 0 or index + word_length > len(pairs):
            raise ValueError("WLI must contain complete contiguous words")
        expected = tuple((position, word_length) for position in range(word_length))
        if pairs[index : index + word_length] != expected:
            raise ValueError("WLI must contain complete contiguous words")
        index += word_length
    return pairs


def tile_text_and_wli(
    plaintext: Sequence[int],
    wli: Sequence[Sequence[int]],
    *,
    minimum_length: int,
) -> tuple[np.ndarray, tuple[tuple[int, int], ...]]:
    if isinstance(minimum_length, bool) or not isinstance(minimum_length, int):
        raise TypeError("minimum_length must be a positive integer")
    if minimum_length <= 0:
        raise ValueError("minimum_length must be a positive integer")
    plain = np.asarray(plaintext, dtype=np.uint8).reshape(-1)
    pairs = _validated_wli_pairs(wli)
    if plain.size == 0:
        raise ValueError("plaintext must not be empty")
    if plain.size != len(pairs):
        raise ValueError("plaintext and WLI lengths must match")
    repeats = max(1, math.ceil(minimum_length / int(plain.size)))
    return np.tile(plain, repeats), pairs * repeats


def resolve_whole_word_slice(
    wli: Sequence[Sequence[int]], *, length: int, offset_hint: int
) -> int:
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        raise ValueError("length must be a positive integer")
    if isinstance(offset_hint, bool) or not isinstance(offset_hint, int) or offset_hint < 0:
        raise ValueError("offset_hint must be a non-negative integer")
    pairs = _validated_wli_pairs(wli)
    if length > len(pairs):
        raise ValueError("requested slice is longer than the WLI")
    starts = [index for index, (offset, _word_len) in enumerate(pairs) if offset == 0]
    for start in starts:
        if start < offset_hint or start + length > len(pairs):
            continue
        end_offset, end_word_len = pairs[start + length - 1]
        if end_offset == end_word_len - 1:
            return start
    raise ValueError("no exact whole-word slice satisfies the requested length and offset")

def candidate_generation_seed(
    *, period: int, columns: int, length: int, sample_start: int
) -> int:
    for name, value in (
        ("period", period),
        ("columns", columns),
        ("length", length),
        ("sample_start", sample_start),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
    if period <= 0 or columns <= 0 or length <= 0 or sample_start < 0:
        raise ValueError("period, columns and length must be positive; sample_start non-negative")
    payload = f"{MASTER_SEED}:{period}:{columns}:{length}:{sample_start}".encode("ascii")
    return int.from_bytes(
        hashlib.blake2b(payload, digest_size=8, person=b"rdp-wp4-pool").digest(),
        "big",
    )


def _portable_telemetry(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, np.generic):
        return _portable_telemetry(value.item())
    if isinstance(value, float):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {
            str(key): cooked
            for key, item in value.items()
            if (cooked := _portable_telemetry(item)) is not None
        }
    if isinstance(value, (list, tuple)):
        return [
            cooked
            for item in value
            if (cooked := _portable_telemetry(item)) is not None
        ]
    return None


def deterministic_truth_key(spec: BenchmarkSpec) -> np.ndarray:
    rng = np.random.default_rng(spec.truth_key_seed)
    blocks = [rng.permutation(ALPHABET_SIZE).astype(np.int16) for _ in range(spec.period)]
    tail = rng.permutation(spec.columns).astype(np.int16)
    return np.concatenate([*blocks, tail]).astype(np.int16, copy=False)


def validate_structured_key(
    key: Sequence[int] | np.ndarray,
    *,
    period: int,
    columns: int,
    permutation_validator: Callable[[Sequence[int], int], Any] | None = None,
) -> np.ndarray:
    raw = np.asarray(key, dtype=object).reshape(-1)
    expected = int(period * ALPHABET_SIZE + columns)
    if raw.size != expected:
        raise ValueError(f"periodic-columnar key length must be {expected}, got {raw.size}")
    lower, upper = np.iinfo(np.int16).min, np.iinfo(np.int16).max
    cooked: list[int] = []
    for index, value in enumerate(raw.tolist()):
        if isinstance(value, (bool, np.bool_)):
            raise TypeError(f"key[{index}] must be an integer, not bool")
        if isinstance(value, (int, np.integer)):
            number = int(value)
        elif isinstance(value, (float, np.floating)):
            number_float = float(value)
            if not math.isfinite(number_float) or not number_float.is_integer():
                raise ValueError(f"key[{index}] must be a finite integer")
            number = int(number_float)
        else:
            raise TypeError(f"key[{index}] must be an integer")
        if number < lower or number > upper:
            raise ValueError(f"key[{index}] is outside the int16 range")
        cooked.append(number)
    values = np.asarray(cooked, dtype=np.int16)
    if permutation_validator is None:
        from rune_decrypter_prime.core.transpositions import assert_is_permutation

        permutation_validator = assert_is_permutation
    for phase in range(period):
        block = values[phase * ALPHABET_SIZE : (phase + 1) * ALPHABET_SIZE]
        permutation_validator(block.tolist(), ALPHABET_SIZE)
    permutation_validator(values[period * ALPHABET_SIZE :].tolist(), columns)
    return np.ascontiguousarray(values, dtype=np.int16)


def _scoring_values(contract: Mapping[str, Any]) -> dict[str, Any]:
    if bool(contract.get("hard_crib", False)):
        raise ValueError("WP4 does not permit a hard crib")
    char_weights = {int(k): float(v) for k, v in contract["char_weights"].items()}
    wli_weights = {int(k): float(v) for k, v in contract["wli_weights"].items()}
    values = {
        "model_root": contract["model_root"],
        "smoothing": str(contract["smoothing"]),
        "alpha": float(contract["alpha"]),
        "oov_policy": str(contract["oov_policy"]),
        "objective": str(contract["objective"]),
        "include_char": bool(contract["include_char"]),
        "use_word_breaks": bool(contract["use_word_breaks"]),
        "n_char": int(contract["n_char"]),
        "n_wli": int(contract["n_wli"]),
        "win": int(contract["win"]),
        "stride": int(contract["stride"]),
        "se_mode": str(contract["se_mode"]),
        "maximize": bool(contract["maximize"]),
        "char_weights": char_weights,
        "wli_weights": wli_weights,
        "avg_window_policy": str(contract["avg_window_policy"]),
        "impl": str(contract["impl"]),
        "compute_dtype": str(contract["compute_dtype"]),
        "acc_dtype": str(contract["acc_dtype"]),
        "dtype": str(contract["dtype"]),
        "ecdf_clamp_min": float(contract["ecdf_clamp_min"]),
        "ecdf_clamp_max": float(contract["ecdf_clamp_max"]),
        "diagnostics_enabled": bool(contract["diagnostics_enabled"]),
        "hard_crib": None,
        "hamming_enabled": bool(contract["hamming_enabled"]),
        "span_hamming_enabled": bool(contract["span_hamming_enabled"]),
        "word_ngram_judge_enabled": bool(contract["word_ngram_judge_enabled"]),
    }
    # These frozen development contracts predate A3 and record both an aggregate
    # pair and non-empty per-order maps. The maps were always the effective
    # runtime weights, so the adapter preserves that behaviour by omitting the
    # stale aggregate pair when materialising strict ScoringConfig kwargs.
    if not char_weights and not wli_weights:
        values["weights"] = tuple(float(v) for v in contract["weights"])
    return values


def scoring_kwargs(contract: Mapping[str, Any], direction_type: Any) -> dict[str, Any]:
    values = _scoring_values(contract)
    values["encoding_dir"] = direction_type(str(contract["encoding_direction"]))
    return values


def scorer_params_for_run(contract: Mapping[str, Any]) -> dict[str, Any]:
    values = _scoring_values(contract)
    values["encoding_dir"] = str(contract["encoding_direction"])
    return values


def solver_params_for_run(run_budget: RunBudget, solver_seed: int) -> dict[str, Any]:
    if run_budget.solver_restarts != 1:
        raise ValueError("WP4 requires one seeded solver restart per campaign replicate")
    return {
        "steps": run_budget.solver_steps,
        "restarts": run_budget.solver_restarts,
        "inner_batch": run_budget.solver_inner_batch,
        "seed": solver_seed,
        **KAEDING_SOLVER_CONTRACT,
    }


def _solution_telemetry(solution: Any) -> dict[str, Any]:
    meta = getattr(solution, "meta", None)
    telemetry = meta.get("telemetry") if isinstance(meta, Mapping) else None
    if not isinstance(telemetry, Mapping):
        extras = getattr(solution, "extras", None)
        telemetry = extras if isinstance(extras, Mapping) else {}
    cooked = _portable_telemetry(telemetry)
    return dict(cooked) if isinstance(cooked, Mapping) else {}


def _key_hash16(key: Sequence[int] | np.ndarray) -> str:
    values = np.asarray(key, dtype=np.int16).reshape(-1)
    return hashlib.sha1(values.tobytes()).hexdigest()[:16]


def build_rdp_case(spec: BenchmarkSpec, budget: RunBudget) -> tuple[SearchCase, ReferenceCase]:
    from rune_decrypter_prime.api import KeySpec, SolverSpec, by_name, cipher_instance, run
    from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
    from rune_decrypter_prime.core.config import ScoringConfig
    from rune_decrypter_prime.core.engine.builders import build_scorer
    from rune_decrypter_prime.core.types import Device, Direction
    from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1
    from rune_decrypter_prime.utils.seed_utils_periodic_columnar import (
        SeedPlan,
        generate_seed_keys_periodic_columnar,
    )

    benchmark_id = str(spec.benchmark_id)
    family = str(spec.family)
    period = int(spec.period)
    columns = int(spec.columns)
    length = int(spec.length)
    offset_hint = int(spec.text_offset_hint)

    source_plaintext, source_wli = tile_text_and_wli(
        plaintext1,
        word_breaks1,
        minimum_length=offset_hint + length + len(word_breaks1),
    )
    sample_start = resolve_whole_word_slice(
        source_wli, length=length, offset_hint=offset_hint
    )
    plaintext = np.asarray(
        source_plaintext[sample_start : sample_start + length], dtype=np.uint8
    )
    wli = source_wli[sample_start : sample_start + length]
    if len(plaintext) != length or len(wli) != length:
        raise RuntimeError("benchmark text and WLI lengths drifted")

    cipher_spec, key_spec = by_name.cipher_with_key(
        "periodic_columnar",
        period=period,
        columns=columns,
        order=ORDER,
        alphabet_size=ALPHABET_SIZE,
        default_key=True,
    )
    cipher = cipher_instance(cipher_spec)
    true_key = validate_structured_key(
        deterministic_truth_key(spec), period=period, columns=columns
    )
    ciphertext = np.asarray(
        cipher.encrypt_single(plaintext=plaintext, key=true_key), dtype=np.uint8
    )
    decoded = np.asarray(
        cipher.decrypt_single(ciphertext=ciphertext, key=true_key), dtype=np.uint8
    )
    if not np.array_equal(decoded, plaintext):
        raise RuntimeError("periodic-columnar known-key roundtrip failed")

    direction = Direction(str(WLI_SCORING_CONTRACT["encoding_direction"]))
    raw_cipher_cfg = build_cipher_config(
        cipher=cipher_spec,
        key=key_spec,
        ciphertext=ciphertext,
        wli=None,
        device=Device.CPU,
        encoding_dir=direction,
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )
    wli_lists = [list(pair) for pair in wli]
    wli_cipher_cfg = build_cipher_config(
        cipher=cipher_spec,
        key=key_spec,
        ciphertext=ciphertext,
        wli=wli_lists,
        device=Device.CPU,
        encoding_dir=direction,
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )
    raw_scoring = ScoringConfig(**scoring_kwargs(RAW_SCORING_CONTRACT, Direction))
    wli_scoring = ScoringConfig(**scoring_kwargs(WLI_SCORING_CONTRACT, Direction))
    raw_scorer = build_scorer(raw_cipher_cfg, raw_scoring)
    wli_scorer = build_scorer(wli_cipher_cfg, wli_scoring)

    candidate_seed = candidate_generation_seed(
        period=period,
        columns=columns,
        length=length,
        sample_start=sample_start,
    )
    seed_plan = budget.seed_plan

    def validate_key(key: Sequence[int] | np.ndarray) -> np.ndarray:
        return validate_structured_key(key, period=period, columns=columns)

    def generate_keys(count: int) -> list[list[int]]:
        return generate_seed_keys_periodic_columnar(
            ciphertext,
            period=period,
            columns=columns,
            order=ORDER,
            direction=direction,
            seed=candidate_seed,
            wli_data=None,
            scoring_cfg=raw_scoring,
            n_keys=count,
            plan=SeedPlan(
                n_block_seeds=seed_plan.n_block_seeds,
                n_tail_seeds=seed_plan.n_tail_seeds,
                n_starts=seed_plan.n_starts,
                refine_steps=seed_plan.refine_steps,
                tail_move_prob=seed_plan.tail_move_prob,
                temp_start=seed_plan.temp_start,
                temp_end=seed_plan.temp_end,
            ),
            refine=seed_plan.refine_steps > 0,
            rerank_cfg=None,
        )

    def score_keys(
        keys: Sequence[Sequence[int]] | np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        batch = np.asarray(keys, dtype=object)
        if batch.ndim == 1:
            rows = [batch]
        elif batch.ndim == 2:
            rows = [batch[index] for index in range(batch.shape[0])]
        else:
            raise ValueError("candidate key batch must be one- or two-dimensional")
        raw_scores: list[float] = []
        wli_scores: list[float] = []
        for row in rows:
            valid = validate_key(row)
            plain = cipher.decrypt_single(ciphertext=ciphertext, key=valid)
            raw_scores.append(float(raw_scorer.score(plain, None)))
            wli_scores.append(float(wli_scorer.score(plain, wli_lists)))
        return (
            np.asarray(raw_scores, dtype=np.float64),
            np.asarray(wli_scores, dtype=np.float64),
        )

    def exploit_key(
        initial_key: Sequence[int] | np.ndarray,
        solver_seed: int,
        run_budget: RunBudget,
    ) -> SolverEvidence:
        valid = validate_key(initial_key)
        solver_params = solver_params_for_run(run_budget, solver_seed)
        solution = run(
            text=ciphertext.tolist(),
            cipher=by_name.cipher(
                "periodic_columnar",
                period=period,
                columns=columns,
                order=ORDER,
                alphabet_size=ALPHABET_SIZE,
            ),
            key=KeySpec.periodic_columnar(
                period=period,
                columns=columns,
                alphabet_size=ALPHABET_SIZE,
            ),
            solver=SolverSpec.kaeding(**solver_params),
            scorer="rune",
            scorer_params=scorer_params_for_run(WLI_SCORING_CONTRACT),
            wli_data=wli_lists,
            force_no_wli=False,
            initial_keys=[valid.astype(int).tolist()],
            telemetry_on=True,
            encoding_dir=direction,
        )
        final_key = validate_key(solution.key)
        telemetry = _solution_telemetry(solution)
        kaeding = telemetry.get("kaeding")
        run_meta = telemetry.get("run")
        if not isinstance(kaeding, Mapping):
            raise RuntimeError("Kaeding telemetry is required for WP4 evidence")
        if str(kaeding.get("seed_selection_metric")) != "pct":
            raise RuntimeError("Kaeding did not select the supplied seed by WLI score")
        if int(kaeding.get("seed_restarts_used", 0)) != 1:
            raise RuntimeError("Kaeding did not use exactly one supplied seed restart")
        starts = kaeding.get("restart_start_hashes")
        if not isinstance(starts, list) or starts != [_key_hash16(valid)]:
            raise RuntimeError("Kaeding restart did not begin from the supplied candidate")
        if not isinstance(run_meta, Mapping):
            raise RuntimeError("Kaeding run telemetry is required for WP4 evidence")
        params = run_meta.get("params")
        if not isinstance(params, Mapping) or bool(params.get("use_raw_score", True)):
            raise RuntimeError("Kaeding exploitation was not configured for WLI decisions")
        return SolverEvidence(
            final_key=tuple(int(value) for value in final_key),
            reported_score=float(solution.score),
            evaluations=int(getattr(solution, "evals", 0) or 0),
            elapsed_s=float(getattr(solution, "wall_time_s", 0.0) or 0.0),
            stop_reason=(
                None if getattr(solution, "stop_reason", None) is None
                else str(solution.stop_reason)
            ),
            telemetry=telemetry,
        )

    return (
        SearchCase(
            benchmark_id=benchmark_id,
            family=family,
            period=period,
            columns=columns,
            length=length,
            order=ORDER,
            sample_start=sample_start,
            ciphertext=tuple(int(value) for value in ciphertext),
            wli=wli,
            validate_key=validate_key,
            generate_seed_keys=generate_keys,
            score_keys=score_keys,
            exploit_key=exploit_key,
        ),
        ReferenceCase(
            cipher=cipher,
            plaintext=plaintext,
            ciphertext=ciphertext,
            wli=wli,
            true_key=true_key,
        ),
    )


def reference_metrics(reference: ReferenceCase, key: Sequence[int] | np.ndarray) -> dict[str, Any]:
    candidate = np.asarray(key, dtype=np.int16).reshape(-1)
    decoded = np.asarray(
        reference.cipher.decrypt_single(ciphertext=reference.ciphertext, key=candidate),
        dtype=np.uint8,
    )
    word_starts = [
        (index, length)
        for index, (offset, length) in enumerate(reference.wli)
        if offset == 0
    ]
    return {
        "exact_plaintext": bool(np.array_equal(decoded, reference.plaintext)),
        "rune_matches": int(np.count_nonzero(decoded == reference.plaintext)),
        "complete_word_matches": int(sum(
            np.array_equal(
                decoded[index : index + length],
                reference.plaintext[index : index + length],
            )
            for index, length in word_starts
        )),
        "complete_words_total": len(word_starts),
        "canonical_key_equal": bool(np.array_equal(candidate, reference.true_key)),
    }
