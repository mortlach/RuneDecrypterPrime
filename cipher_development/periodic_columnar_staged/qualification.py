from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from rdp import api

from cipher_development.shared.experiment import (
    ExperimentDecision,
    ExperimentRun,
    ExperimentSpec,
    FailureMechanism,
    TruthPolicy,
    WliMode,
)
from rdp.core.config.cipher import materialize_cipher_config
from rdp.core.engine.builders import build_cipher, build_scorer
from rdp.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
from rdp.data.runeglish import Runeglish
from rdp.solvers.seed_generation import make_periodic_seed_pool

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_ID = "periodic_columnar_decomposed_v2"
ALPHABET_SIZE = 29
BENCHMARK_KEY_SEED = 54_321


@dataclass(frozen=True, slots=True)
class QualificationConfig:
    mode: str
    period: int
    columns: int
    plaintext_length: int
    head_seed: int
    head_pool_size: int
    head_block_seeds: int
    head_swaps_per_block: int
    retained_heads: int
    fast_shortlist_per_scorer: int
    complete_keys_per_head: int
    solver_seed: int
    solver_steps: int
    solver_restarts: int
    solver_inner_batch_size: int
    solver_column_batch_size: int
    solver_stall_rounds: int
    maximum_seconds: float


SMOKE = QualificationConfig(
    mode="smoke",
    period=1,
    columns=2,
    plaintext_length=400,
    head_seed=12_348,
    head_pool_size=16,
    head_block_seeds=8,
    head_swaps_per_block=2,
    retained_heads=2,
    fast_shortlist_per_scorer=2,
    complete_keys_per_head=2,
    solver_seed=12_446,
    solver_steps=100,
    solver_restarts=1,
    solver_inner_batch_size=64,
    solver_column_batch_size=64,
    solver_stall_rounds=80,
    maximum_seconds=5 * 60,
)

QUALIFICATION = QualificationConfig(
    mode="qualification",
    period=7,
    columns=7,
    plaintext_length=2_489,
    head_seed=12_348,
    head_pool_size=384,
    head_block_seeds=24,
    head_swaps_per_block=2,
    retained_heads=1,
    fast_shortlist_per_scorer=192,
    complete_keys_per_head=1,
    solver_seed=12_446,
    solver_steps=12_000,
    solver_restarts=1,
    solver_inner_batch_size=192,
    solver_column_batch_size=384,
    solver_stall_rounds=220,
    maximum_seconds=60 * 60,
)


class QualificationTimeLimit(RuntimeError):
    pass


class QualificationClock:
    def __init__(self, maximum_seconds: float) -> None:
        self.started = time.perf_counter()
        self.deadline = self.started + float(maximum_seconds)

    @property
    def elapsed(self) -> float:
        return max(0.0, time.perf_counter() - self.started)

    @property
    def remaining(self) -> float:
        return max(0.0, self.deadline - time.perf_counter())

    def require_time(self) -> None:
        if self.remaining <= 0.0:
            raise QualificationTimeLimit("qualification time limit reached")


class QualificationProgress:
    def __init__(
        self,
        *,
        clock: QualificationClock,
        progress_path: Path,
    ) -> None:
        self.clock = clock
        self.progress_path = progress_path
        self.latest_key: tuple[int, ...] | None = None
        self.latest_score: float | None = None

    def __call__(
        self,
        payload: dict[str, Any],
        key: Sequence[int] | None = None,
    ) -> None:
        if key is not None:
            self.latest_key = tuple(int(value) for value in key)
        if payload.get("best_score") is not None:
            self.latest_score = float(payload["best_score"])
        progress = {
            "schema": "rdp.periodic_columnar_qualification_progress.v1",
            "stage": "integrated_refinement",
            "percent": max(0, min(100, int(payload.get("pct", 0) or 0))),
            "step": int(payload.get("step", 0) or 0),
            "evaluations": int(payload.get("evals", 0) or 0),
            "best_score": self.latest_score,
            "elapsed_seconds": self.clock.elapsed,
            "remaining_seconds": self.clock.remaining,
        }
        _write_json(self.progress_path, progress)
        best = "n/a" if self.latest_score is None else f"{self.latest_score:.6f}"
        print(
            "[integrated_refinement] "
            f"step={progress['step']} evals={progress['evaluations']} best={best} "
            f"elapsed={_duration(self.clock.elapsed)} "
            f"remaining={_duration(self.clock.remaining)}",
            flush=True,
        )
        self.clock.require_time()


def config_for_mode(mode: str) -> QualificationConfig:
    if mode == "smoke":
        return SMOKE
    if mode in {"development", "qualification"}:
        return QUALIFICATION
    raise ValueError("mode must be 'smoke', 'development', or 'qualification'")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def _duration(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3_600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _key_id(key: Sequence[int]) -> str:
    payload = ",".join(str(int(value)) for value in key).encode("ascii")
    return hashlib.blake2b(
        payload,
        digest_size=20,
        person=b"rdp-pc-qual-v1",
    ).hexdigest()


def _unique_keys(keys: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    result: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    for key in keys:
        normalized = tuple(int(value) for value in key)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


def _complete_word_prefix(
    plaintext: Sequence[int],
    word_lengths: Sequence[Sequence[int]],
    *,
    limit: int,
) -> tuple[list[int], list[Sequence[int]]]:
    end = min(int(limit), len(plaintext), len(word_lengths))
    while end > 0:
        position, word_length = (int(value) for value in word_lengths[end - 1])
        if position == word_length - 1:
            break
        end -= 1
    if end <= 0:
        raise ValueError("plaintext limit does not contain one complete word")
    return list(plaintext[:end]), list(word_lengths[:end])


def _match(left: Sequence[int] | None, right: Sequence[int]) -> float:
    if left is None:
        return 0.0
    left_array = np.asarray(left, dtype=np.int64).reshape(-1)
    right_array = np.asarray(right, dtype=np.int64).reshape(-1)
    if left_array.size != right_array.size or left_array.size == 0:
        return 0.0
    return float(np.mean(left_array == right_array))


def _head_scoring() -> api.ScoringConfig:
    return api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=False,
        character_order_weights={1: 0.75, 2: 0.25},
        word_length_order_weights={},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )


def _fast_scoring(*, alternate: bool) -> api.ScoringConfig:
    return api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=False,
        character_order_weights={3: 0.2, 4: 0.8}
        if alternate
        else {3: 0.5, 4: 0.5},
        word_length_order_weights={},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )


def _ranking_scoring() -> api.ScoringConfig:
    return api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={3: 0.2, 4: 0.8},
        word_length_order_weights={2: 0.3, 4: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )


def _final_scoring(cfg: QualificationConfig) -> api.ScoringConfig:
    if cfg.mode == "smoke":
        return _ranking_scoring()
    return _fast_scoring(alternate=False)


def _final_solver(cfg: QualificationConfig) -> api.SolverSpec:
    return api.SolverSpec.kaeding(
        steps=cfg.solver_steps,
        restarts=cfg.solver_restarts,
        inner_batch_size=cfg.solver_inner_batch_size,
        column_interval=1,
        column_batch_size=cfg.solver_column_batch_size,
        block_schedule=api.advanced.KaedingBlockSchedule.ROUND_ROBIN,
        target_score=None,
        seed=cfg.solver_seed,
        slip_policy=api.advanced.KaedingSlipPolicy.ON_STALL,
        slip_interval=60,
        slip_blocks=1,
        stall_rounds=cfg.solver_stall_rounds,
        stall_slip_limit=3,
        slip_swaps=50,
        stop_after_stall_slip_limit=False,
    )


def _problem(
    *,
    cipher: api.CipherSpec,
    key_space: api.KeySpec,
    ciphertext: Sequence[int],
    word_lengths: Sequence[Sequence[int]] | None,
    scoring: api.ScoringConfig,
) -> DecryptionProblem:
    materialized = materialize_cipher_config(
        cipher=cipher,
        key_space=key_space,
        ciphertext=tuple(int(value) for value in ciphertext),
        word_lengths=word_lengths,
        compute_device=api.ComputeDevice.CPU,
        text_direction=api.TextDirection.RIGHT_TO_LEFT,
    )
    return DecryptionProblem(
        cipher=build_cipher(materialized),
        scorer=build_scorer(materialized, scoring),
        c_cfg=materialized,
        s_cfg=scoring,
    )


def _score_keys(
    problem: DecryptionProblem,
    keys: Sequence[Sequence[int]] | np.ndarray,
    *,
    clock: QualificationClock,
    chunk_size: int = 128,
) -> tuple[np.ndarray, int]:
    array = np.asarray(keys, dtype=np.int16)
    if array.ndim != 2:
        raise ValueError("keys must be a two-dimensional array")
    output: list[np.ndarray] = []
    evaluated = 0
    for start in range(0, int(array.shape[0]), int(chunk_size)):
        clock.require_time()
        batch = array[start : start + chunk_size]
        output.append(
            np.asarray(problem.evaluate_keys(batch), dtype=np.float64).reshape(-1)
        )
        evaluated += int(batch.shape[0])
    scores = np.concatenate(output) if output else np.empty(0, dtype=np.float64)
    return scores, evaluated


def _top_indices(scores: np.ndarray, limit: int) -> tuple[int, ...]:
    if scores.ndim != 1:
        raise ValueError("scores must be one-dimensional")
    count = min(max(0, int(limit)), int(scores.size))
    return tuple(int(index) for index in np.argsort(-scores, kind="stable")[:count])


def _tail_permutations(columns: int) -> np.ndarray:
    if columns < 1:
        raise ValueError("columns must be positive")
    return np.asarray(list(itertools.permutations(range(columns))), dtype=np.int16)


def _deduplicate_per_head_candidates(
    ranked_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Preserve each head's ranked selections; remove only identical keys."""
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in ranked_rows:
        candidate_id = str(row["candidate_id"])
        if candidate_id not in seen:
            seen.add(candidate_id)
            selected.append(row)
    return selected


def _search_candidates(
    *,
    cfg: QualificationConfig,
    ciphertext: Sequence[int],
    word_lengths: Sequence[Sequence[int]],
    cipher_spec: api.CipherSpec,
    key_space: api.KeySpec,
    clock: QualificationClock,
    artifact_root: Path,
) -> tuple[tuple[tuple[int, ...], ...], dict[str, Any]]:
    head_cipher = api.CipherSpec.periodic_substitution(
        period=cfg.period,
        alphabet_size=ALPHABET_SIZE,
    )
    head_key_space = api.KeySpec.periodic_substitution(
        period=cfg.period,
        alphabet_size=ALPHABET_SIZE,
    )
    head_pool = _unique_keys(
        make_periodic_seed_pool(
            ciphertext,
            period=cfg.period,
            direction=api.TextDirection.RIGHT_TO_LEFT,
            seed=cfg.head_seed,
            n_block_seeds=cfg.head_block_seeds,
            total_seeds=cfg.head_pool_size,
            swaps_per_block=cfg.head_swaps_per_block,
            alphabet_size=ALPHABET_SIZE,
        )
    )
    head_problem = _problem(
        cipher=head_cipher,
        key_space=head_key_space,
        ciphertext=ciphertext,
        word_lengths=None,
        scoring=_head_scoring(),
    )
    head_scores, direct_evaluations = _score_keys(
        head_problem,
        head_pool,
        clock=clock,
    )
    retained_head_indices = _top_indices(head_scores, cfg.retained_heads)
    retained_heads = tuple(head_pool[index] for index in retained_head_indices)
    head_rows = [
        {
            "candidate_id": _key_id(head_pool[index]),
            "decision_score": float(head_scores[index]),
            "key": list(head_pool[index]),
        }
        for index in retained_head_indices
    ]
    evidence: dict[str, Any] = {
        "schema": "rdp.periodic_columnar_candidate_search.v1",
        "recipe_id": RECIPE_ID,
        "head_pool_count": len(head_pool),
        "retained_heads": head_rows,
        "tail_permutation_count_per_head": 0,
        "completed_head_count": 0,
        "direct_candidate_evaluations": direct_evaluations,
        "ranked_complete_candidates": [],
        "selected_complete_candidates": [],
    }
    _write_json(artifact_root / "candidate_search.json", evidence)

    tails = _tail_permutations(cfg.columns)
    evidence["tail_permutation_count_per_head"] = int(tails.shape[0])
    fast_problems = (
        _problem(
            cipher=cipher_spec,
            key_space=key_space,
            ciphertext=ciphertext,
            word_lengths=word_lengths,
            scoring=_fast_scoring(alternate=False),
        ),
        _problem(
            cipher=cipher_spec,
            key_space=key_space,
            ciphertext=ciphertext,
            word_lengths=word_lengths,
            scoring=_fast_scoring(alternate=True),
        ),
    )
    ranking_problem = _problem(
        cipher=cipher_spec,
        key_space=key_space,
        ciphertext=ciphertext,
        word_lengths=word_lengths,
        scoring=_ranking_scoring(),
    )
    ranked_rows: list[dict[str, Any]] = []
    for head_number, head in enumerate(retained_heads, start=1):
        clock.require_time()
        head_array = np.asarray(head, dtype=np.int16).reshape(1, -1)
        complete_keys = np.concatenate(
            [np.repeat(head_array, int(tails.shape[0]), axis=0), tails],
            axis=1,
        )
        shortlist: set[int] = set()
        for problem in fast_problems:
            scores, evaluated = _score_keys(problem, complete_keys, clock=clock)
            direct_evaluations += evaluated
            shortlist.update(_top_indices(scores, cfg.fast_shortlist_per_scorer))
        shortlist_indices = tuple(sorted(shortlist))
        shortlist_keys = complete_keys[np.asarray(shortlist_indices, dtype=np.int64)]
        ranking_scores, evaluated = _score_keys(
            ranking_problem,
            shortlist_keys,
            clock=clock,
        )
        direct_evaluations += evaluated
        for local_index in _top_indices(ranking_scores, cfg.complete_keys_per_head):
            global_index = shortlist_indices[local_index]
            key = tuple(int(value) for value in complete_keys[global_index])
            ranked_rows.append(
                {
                    "candidate_id": _key_id(key),
                    "head_candidate_id": _key_id(head),
                    "decision_score": float(ranking_scores[local_index]),
                    "key": list(key),
                    "tail": [int(value) for value in tails[global_index]],
                }
            )
        evidence["completed_head_count"] = head_number
        evidence["direct_candidate_evaluations"] = direct_evaluations
        evidence["ranked_complete_candidates"] = ranked_rows
        _write_json(artifact_root / "candidate_search.json", evidence)
        print(
            f"candidate head {head_number}/{len(retained_heads)} complete: "
            f"tails={len(tails)} elapsed={_duration(clock.elapsed)}",
            flush=True,
        )

    selected_rows = _deduplicate_per_head_candidates(ranked_rows)
    selected_keys = tuple(
        tuple(int(value) for value in row["key"]) for row in selected_rows
    )
    evidence["direct_candidate_evaluations"] = direct_evaluations
    evidence["ranked_complete_candidates"] = ranked_rows
    evidence["selected_complete_candidates"] = selected_rows
    _write_json(artifact_root / "candidate_search.json", evidence)
    return selected_keys, evidence


def _solver_evidence(result: api.RunResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    report = result.solver_report
    status = result.status
    return {
        "score": result.score,
        "key": None if result.key is None else list(result.key),
        "status": {
            "execution_status": status.execution_status.value,
            "stop_category": status.stop_category.value,
            "stop_reason": status.stop_reason.value,
            "runtime_reason": status.runtime_reason,
        },
        "evaluations": report.evaluations,
        "steps": report.steps,
        "wall_time_seconds": report.wall_time_seconds,
        "effective_seed": report.effective_seed,
    }


def _configuration(cfg: QualificationConfig) -> dict[str, Any]:
    return {
        "recipe_id": RECIPE_ID,
        "mode": cfg.mode,
        "fixture_id": f"long_plaintext_rtl_keyseed{BENCHMARK_KEY_SEED}",
        "asset_profile": "full_v1",
        "period": cfg.period,
        "columns": cfg.columns,
        "alphabet_size": ALPHABET_SIZE,
        "order": "columnar_then_substitution",
        "plaintext_length": cfg.plaintext_length,
        "head_seed": cfg.head_seed,
        "head_pool_size": cfg.head_pool_size,
        "head_block_seeds": cfg.head_block_seeds,
        "head_swaps_per_block": cfg.head_swaps_per_block,
        "retained_heads": cfg.retained_heads,
        "tail_permutations_per_head": math.factorial(cfg.columns),
        "fast_shortlist_per_scorer": cfg.fast_shortlist_per_scorer,
        "complete_keys_per_head": cfg.complete_keys_per_head,
        "solver_seed": cfg.solver_seed,
        "solver_steps": cfg.solver_steps,
        "solver_restarts": cfg.solver_restarts,
        "solver_inner_batch_size": cfg.solver_inner_batch_size,
        "solver_column_batch_size": cfg.solver_column_batch_size,
        "solver_stall_rounds": cfg.solver_stall_rounds,
        "maximum_seconds": cfg.maximum_seconds,
        "scoring_sequence": [
            "char12_head",
            "char34_tail_shortlist",
            "char34_wli24_tail_rank",
            "char34_integrated_refinement",
        ],
    }


def run_qualification(*, mode: str, seed: int = 12_345, output_root: Path) -> Path:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    cfg = replace(
        config_for_mode(mode),
        head_seed=seed + 3,
        solver_seed=seed + 101,
    )
    spec = ExperimentSpec(
        campaign_id="periodic_columnar_staged",
        experiment_id=f"{cfg.mode}_seed{cfg.solver_seed}",
        benchmark_id=f"p{cfg.period}_c{cfg.columns}_rtl",
        question="Can decomposed head discovery, exhaustive column ranking and one integrated refinement recover the periodic-columnar benchmark exactly?",
        hypothesis="Low-order heads and WLI-assisted exhaustive tail ranking supply a basin that one character-scored Kaeding refinement can solve exactly.",
        alternative="The fixed candidate reduction does not supply or exploit an exact-solve basin within its bounded work.",
        decision_rule="Promote only when the fixed workflow completes and terminal evaluation reports exact plaintext recovery.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.RANKING,
            FailureMechanism.HANDOFF,
            FailureMechanism.EXPLOITATION,
            FailureMechanism.BUDGET,
            FailureMechanism.ACCEPTANCE,
        ),
        budget_seconds=cfg.maximum_seconds,
        lesson_ids=("CSL-001", "CSL-002", "CSL-003"),
    )
    clock = QualificationClock(cfg.maximum_seconds)
    with ExperimentRun(
        spec=spec,
        configuration=_configuration(cfg),
        repo_root=REPO_ROOT,
        output_root=output_root,
    ) as run:
        assert run.run_dir is not None
        artifact_root = run.run_dir / "artifacts/qualification"
        plaintext, word_lengths, _ = Runeglish.encode_english_to_runes(
            long_plaintext_string,
            direction=api.TextDirection.RIGHT_TO_LEFT,
        )
        plaintext, word_lengths = _complete_word_prefix(
            plaintext,
            word_lengths,
            limit=cfg.plaintext_length,
        )
        rng = np.random.default_rng(BENCHMARK_KEY_SEED)
        benchmark_key = tuple(
            int(value)
            for value in np.concatenate(
                [
                    *(
                        rng.permutation(ALPHABET_SIZE)
                        for _ in range(cfg.period)
                    ),
                    rng.permutation(cfg.columns),
                ]
            )
        )
        cipher_spec = api.CipherSpec.periodic_columnar(
            period=cfg.period,
            columns=cfg.columns,
            order=api.advanced.PeriodicColumnarOrder.COLUMNAR_THEN_SUBSTITUTION,
            alphabet_size=ALPHABET_SIZE,
        )
        key_space = api.KeySpec.periodic_columnar(
            period=cfg.period,
            columns=cfg.columns,
            alphabet_size=ALPHABET_SIZE,
        )
        ciphertext = api.encrypt(
            tuple(plaintext),
            cipher=cipher_spec,
            key=benchmark_key,
        )
        print("RDP periodic-columnar decomposed qualification", flush=True)
        print(
            f"profile: P{cfg.period}/C{cfg.columns} {cfg.mode}; "
            f"maximum={_duration(cfg.maximum_seconds)}",
            flush=True,
        )
        print(
            f"candidate reduction: {cfg.head_pool_size} heads -> "
            f"{cfg.retained_heads} x {len(_tail_permutations(cfg.columns))} tails -> "
            f"{cfg.retained_heads * cfg.complete_keys_per_head} complete keys",
            flush=True,
        )
        print(f"run artifacts: {run.run_dir}", flush=True)

        selected_keys, search_evidence = _search_candidates(
            cfg=cfg,
            ciphertext=ciphertext,
            word_lengths=word_lengths,
            cipher_spec=cipher_spec,
            key_space=key_space,
            clock=clock,
            artifact_root=artifact_root,
        )
        if not selected_keys:
            raise RuntimeError("candidate reduction produced no complete keys")
        print(
            f"integrated refinement: warm_keys={len(selected_keys)} "
            f"steps={cfg.solver_steps} restarts={cfg.solver_restarts}",
            flush=True,
        )
        callback = QualificationProgress(
            clock=clock,
            progress_path=artifact_root / "live_progress.json",
        )
        result: api.RunResult | None = None
        timed_out = False
        try:
            result = api.run(
                api.RunSpec(
                    problem_input=api.RuneIndexInput(
                        indices=ciphertext,
                        word_lengths=word_lengths,
                    ),
                    cipher=cipher_spec,
                    key_space=key_space,
                    solver=_final_solver(cfg),
                    scoring=_final_scoring(cfg),
                    initial_keys=selected_keys,
                    telemetry_enabled=True,
                    text_direction=api.TextDirection.RIGHT_TO_LEFT,
                    compute_device=api.ComputeDevice.CPU,
                ),
                progress_callback=callback,
                progress_interval=10,
            )
        except QualificationTimeLimit:
            timed_out = True

        recovered = None if result is None else result.plaintext
        match_ratio = _match(recovered, plaintext)
        exact_plaintext = bool(
            result is not None
            and recovered is not None
            and tuple(recovered) == tuple(plaintext)
        )
        exact_key = bool(result is not None and result.key == benchmark_key)
        contract_smoke_passed = bool(
            cfg.mode == "smoke" and result is not None and not timed_out
        )
        accepted = exact_plaintext if cfg.mode == "qualification" else contract_smoke_passed
        terminal = {
            "schema": "rdp.periodic_columnar_terminal_evaluation.v1",
            "completed_solver_result": result is not None,
            "time_limit_reached": timed_out,
            "plaintext_match_ratio": match_ratio,
            "exact_plaintext_recovery": exact_plaintext,
            "exact_key_recovery": exact_key,
            "selected_candidate_count": len(selected_keys),
            "solver": _solver_evidence(result),
        }
        _write_json(artifact_root / "terminal_evaluation.json", terminal)
        direct_evaluations = int(search_evidence["direct_candidate_evaluations"])
        solver_evaluations = (
            0 if result is None else result.solver_report.evaluations
        )
        print(
            f"{cfg.mode}: {'PASS' if accepted else 'REFINE'} "
            f"match_ratio={match_ratio:.6f} elapsed={_duration(clock.elapsed)}",
            flush=True,
        )
        telemetry = {
            "eval_keys": solver_evaluations,
            "candidates_evaluated": direct_evaluations,
            "tokens_processed": 0
            if result is None
            else result.solver_report.tokens_processed,
            "decrypt_time_s": 0.0
            if result is None
            else result.solver_report.decrypt_time_seconds,
            "score_time_s": 0.0
            if result is None
            else result.solver_report.score_time_seconds,
        }
        return run.finish(
            decision=ExperimentDecision.PROMOTE
            if exact_plaintext
            else ExperimentDecision.CLOSE
            if contract_smoke_passed
            else ExperimentDecision.REFINE,
            stop_reason="oracle_exact_plaintext_match"
            if exact_plaintext
            else "max_time_reached"
            if timed_out
            else "configured_work_limit_reached",
            result_summary={
                "recipe_id": RECIPE_ID,
                "head_pool_count": cfg.head_pool_size,
                "retained_head_count": cfg.retained_heads,
                "tail_permutation_count_per_head": len(
                    _tail_permutations(cfg.columns)
                ),
                "selected_complete_key_count": len(selected_keys),
                "candidate_search_relpath": "artifacts/qualification/candidate_search.json",
                "terminal_evaluation_relpath": "artifacts/qualification/terminal_evaluation.json",
            },
            telemetry=telemetry,
            reference_evaluation={
                "exact_plaintext_recovery": exact_plaintext,
                "plaintext_match_ratio": match_ratio,
                "exact_key_recovery": exact_key,
            },
        )


__all__ = [
    "QUALIFICATION",
    "RECIPE_ID",
    "SMOKE",
    "QualificationClock",
    "QualificationConfig",
    "QualificationProgress",
    "QualificationTimeLimit",
    "config_for_mode",
    "run_qualification",
]
