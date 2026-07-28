from __future__ import annotations

"""WP6 Pack 02A perturbation-shell and matched exact-d8 profile pilots.

The module deliberately keeps the two scientific questions separate:

* ``multiscale_perturbation_shells_v1`` is a truth-derived scorer diagnostic.
  Its candidates never enter a normal candidate archive or a later search.
* ``matched_d8_profile_pilot_v1`` is a normal search over the declared
  offset-206 exact-extra-crib d8 benchmark. All search-visible evidence is
  completed before terminal benchmark metrics are opened.

No scout/bridge/judge ladder is frozen here. Pack 02B is prepared only after
these two review packs have been assessed.
"""

import hashlib
import json
import math
import shutil
import sys
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateProvenance,
    CandidateRecord,
    archive_content_hash,
    candidate_id_for,
    write_candidate_archive,
)
from cipher_development.shared.replay import (
    CandidateReplayContext,
    select_candidate_batch,
    write_candidate_batch,
    write_replay_context,
)
from cipher_development.shared.replay_binding import (
    CandidateReplayBinding,
    write_replay_binding,
)
from cipher_development.shared.replay_evidence import ReplayMode, write_candidate_replay
from cipher_development.shared.replay_execution import replay_candidate_batch
from cipher_development.shared.replay_provenance import build_evaluator_provenance
from cipher_development.two_period_overlay.benchmark import build_rdp_case, reference_metrics
from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    EXACT_EXTRA_CRIB_BENCHMARKS,
    MASTER_SEED,
    TARGET_BENCHMARK,
)
from cipher_development.two_period_overlay.coordinate_supply import coordinate_supply_seed
from cipher_development.two_period_overlay.keyspace import coordinate_search, expand
from cipher_development.two_period_overlay.multiscale import (
    ABSOLUTE_TOLERANCE,
    RELATIVE_TOLERANCE,
    REPLAY_REPEAT_COUNT,
    _numeric_summary,
    aggregate_profile_diagnostic,
)
from cipher_development.two_period_overlay.target_ranking import (
    _pairwise_concordance,
    spearman_rank_correlation,
)
from cipher_development.two_period_overlay.replay import (
    build_replay_evaluator,
    make_replay_context,
)
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.scorer_profiles import (
    SCORER_PANEL,
    ScorerProfile,
    portable_contract,
)

SHELL_DISTANCES = (1, 2, 4, 6, 8, 12, 16)
SHELL_SAMPLES_PER_DISTANCE = 32
SHELL_TOP_K = (8, 16, 32)

PILOT_BENCHMARK = EXACT_EXTRA_CRIB_BENCHMARKS[0]
PILOT_RESTARTS = 8
PILOT_FIXED_CORE_SWEEPS = 2
PILOT_TARGET_SCORING_SECONDS = 120.0
PILOT_MAX_CALIBRATED_SWEEPS = 8
PILOT_SEED_BLOCK = 20
PILOT_ARCHIVE_CAPACITY = PILOT_RESTARTS
PILOT_PROFILE_WALLCLOCK_SAFETY_LIMIT = 900.0

STATIC_PANEL_EXPERIMENT_ID = "multiscale_static_panel_v1"


@dataclass(frozen=True, slots=True)
class ProfileArmOutcome:
    profile_id: str
    arm_id: str
    sweeps_requested: int
    archive: CandidateArchive
    restart_rows: tuple[Mapping[str, Any], ...]
    generated_candidates: int
    unique_candidates: int
    duplicate_candidates: int
    evaluations: int
    elapsed_s: float

    def search_summary(self) -> dict[str, Any]:
        scores = [
            float(row["final_score"])
            for row in self.restart_rows
        ]
        gains = [
            float(row["score_gain"])
            for row in self.restart_rows
        ]
        attempt_elapsed = [
            float(row["elapsed_s"])
            for row in self.restart_rows
        ]
        attempt_rates = [
            float(row["candidate_evaluations_per_s"])
            for row in self.restart_rows
        ]
        return {
            "profile_id": self.profile_id,
            "arm_id": self.arm_id,
            "sweeps_requested": self.sweeps_requested,
            "generated_candidates": self.generated_candidates,
            "unique_candidates": self.unique_candidates,
            "duplicate_candidates": self.duplicate_candidates,
            "duplicate_rate": self.duplicate_candidates / self.generated_candidates,
            "evaluations": self.evaluations,
            "elapsed_s": self.elapsed_s,
            "candidate_evaluations_per_s": self.evaluations / self.elapsed_s,
            "attempt_count": len(self.restart_rows),
            "attempt_elapsed_s_summary": _numeric_summary(attempt_elapsed),
            "attempt_candidate_evaluations_per_s_summary": _numeric_summary(attempt_rates),
            "score_summary": _numeric_summary(scores),
            "score_gain_summary": _numeric_summary(gains),
            "archive_hash": archive_content_hash(self.archive),
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _campaign_root(repo_root: Path) -> Path:
    return (repo_root.resolve() / "output/cipher_development/two_period_overlay").resolve()


def _source_run(repo_root: Path, run_id: str) -> Path:
    if not run_id or run_id in {".", ".."} or "/" in run_id or "\\" in run_id:
        raise ValueError("run ID must be one directory name")
    root = _campaign_root(repo_root)
    run = (root / run_id).resolve()
    if root not in run.parents:
        raise ValueError("run ID escaped the campaign output root")
    return run


def latest_completed_static_panel(repo_root: Path) -> str:
    root = _campaign_root(repo_root)
    candidates: list[str] = []
    if not root.is_dir():
        raise FileNotFoundError("the two-period campaign output directory does not exist")
    for run_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        manifest_path = run_dir / "artifacts/experiment_manifest.json"
        result_path = run_dir / "artifacts/experiment_result.json"
        summary_path = run_dir / "artifacts/static_panel_summary.json"
        if not manifest_path.is_file() or not result_path.is_file() or not summary_path.is_file():
            continue
        manifest = _read_json(manifest_path)
        result = _read_json(result_path)
        experiment = manifest.get("experiment")
        result_summary = result.get("result_summary")
        if not isinstance(experiment, Mapping) or not isinstance(result_summary, Mapping):
            continue
        if (
            experiment.get("experiment_id") == STATIC_PANEL_EXPERIMENT_ID
            and result.get("status") == "completed"
            and result.get("run_id") == run_dir.name
            and result_summary.get("static_panel_gate_passed") is True
        ):
            candidates.append(run_dir.name)
    if not candidates:
        raise FileNotFoundError("no completed multiscale_static_panel_v1 run was found")
    return max(candidates)


def _static_profile_rates(summary: Mapping[str, Any]) -> dict[str, float]:
    surfaces = summary.get("surfaces")
    if not isinstance(surfaces, Mapping) or not surfaces:
        raise ValueError("static panel summary has no surfaces")
    values: dict[str, list[float]] = {
        profile.profile_id: [] for profile in SCORER_PANEL
    }
    for surface in surfaces.values():
        if not isinstance(surface, Mapping):
            raise ValueError("static panel surface must be a mapping")
        profiles = surface.get("profiles")
        if not isinstance(profiles, Mapping):
            raise ValueError("static panel surface has no profiles")
        for profile in SCORER_PANEL:
            row = profiles.get(profile.profile_id)
            if not isinstance(row, Mapping):
                raise ValueError(f"static panel is missing profile {profile.profile_id}")
            rate = float(row["candidate_evaluations_per_s"])
            if not math.isfinite(rate) or rate <= 0.0:
                raise ValueError("static panel contains an invalid throughput")
            values[profile.profile_id].append(rate)
    return {
        profile_id: float(np.median(np.asarray(rates, dtype=np.float64)))
        for profile_id, rates in values.items()
    }


def calibrated_sweeps(
    evaluations_per_second: float,
    *,
    target_seconds: float = PILOT_TARGET_SCORING_SECONDS,
    restarts: int = PILOT_RESTARTS,
    dimension: int = PILOT_BENCHMARK.expected_free_dimension,
    alphabet_size: int = ALPHABET_SIZE,
    maximum: int = PILOT_MAX_CALIBRATED_SWEEPS,
) -> int:
    for name, value in (
        ("evaluations_per_second", evaluations_per_second),
        ("target_seconds", target_seconds),
    ):
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError(f"{name} must be a positive finite number")
    for name, value in (
        ("restarts", restarts),
        ("dimension", dimension),
        ("alphabet_size", alphabet_size),
        ("maximum", maximum),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    per_sweep = restarts * dimension * alphabet_size
    estimate = int(math.floor(float(evaluations_per_second) * float(target_seconds) / per_sweep))
    return max(1, min(maximum, estimate))


def _shell_indices(dimension: int, distance: int, sample_index: int) -> tuple[int, ...]:
    if not 1 <= distance <= dimension:
        raise ValueError("shell distance must be within the affine dimension")
    if sample_index < 0:
        raise ValueError("sample_index must be non-negative")
    # Repeating all dimension rotations exactly twice for 32 samples gives
    # every variable exactly 2*distance appearances in each shell.
    return tuple(sorted((sample_index + offset) % dimension for offset in range(distance)))


def _shell_deltas(distance: int, sample_index: int) -> tuple[int, ...]:
    if distance <= 0 or sample_index < 0:
        raise ValueError("distance must be positive and sample_index non-negative")
    # Cycle through every non-zero modulo-29 delta. Counts differ by at most
    # one within each shell.
    start = sample_index * distance
    return tuple(((start + offset) % (ALPHABET_SIZE - 1)) + 1 for offset in range(distance))


def build_perturbation_shells(
    true_variables: np.ndarray,
) -> tuple[np.ndarray, tuple[dict[str, Any], ...]]:
    base = np.asarray(true_variables, dtype=np.uint8)
    if base.ndim != 1 or len(base) != TARGET_BENCHMARK.expected_free_dimension:
        raise ValueError("true_variables must be the frozen d16 affine vector")
    rows: list[np.ndarray] = []
    metadata: list[dict[str, Any]] = []
    for distance in SHELL_DISTANCES:
        for sample_index in range(SHELL_SAMPLES_PER_DISTANCE):
            indices = _shell_indices(len(base), distance, sample_index)
            deltas = _shell_deltas(distance, sample_index)
            candidate = base.copy()
            for index, delta in zip(indices, deltas, strict=True):
                candidate[index] = (int(candidate[index]) + delta) % ALPHABET_SIZE
            sample_id = hashlib.blake2b(
                json.dumps(
                    {
                        "distance": distance,
                        "sample_index": sample_index,
                        "indices": indices,
                        "deltas": deltas,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8"),
                digest_size=12,
                person=b"rdp-shell-v1",
            ).hexdigest()
            rows.append(candidate)
            metadata.append({
                "sample_id": sample_id,
                "distance": distance,
                "sample_index": sample_index,
                "changed_variable_indices": list(indices),
                "modulo_29_deltas": list(deltas),
            })
    return np.asarray(rows, dtype=np.uint8), tuple(metadata)


def _shell_profile_summary(
    scores: Sequence[float],
    shell_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    score_values = np.asarray(scores, dtype=np.float64)
    if score_values.shape != (len(shell_rows),) or not np.all(np.isfinite(score_values)):
        raise ValueError("shell profile scores must align and be finite")
    distances = np.asarray([int(row["distance"]) for row in shell_rows], dtype=np.int64)
    rune_matches = np.asarray([int(row["rune_matches"]) for row in shell_rows], dtype=np.int64)
    word_matches = np.asarray(
        [int(row["complete_word_matches"]) for row in shell_rows], dtype=np.int64
    )
    affine_matches = np.asarray(
        [TARGET_BENCHMARK.expected_free_dimension - int(row["distance"]) for row in shell_rows],
        dtype=np.int64,
    )
    by_distance: dict[str, Any] = {}
    medians: list[float] = []
    for distance in SHELL_DISTANCES:
        mask = distances == distance
        values = score_values[mask]
        medians.append(float(np.median(values)))
        by_distance[str(distance)] = {
            "candidate_count": int(np.count_nonzero(mask)),
            "score_summary": _numeric_summary(values.tolist()),
            "rune_match_summary": _numeric_summary(rune_matches[mask].tolist()),
            "complete_word_match_summary": _numeric_summary(word_matches[mask].tolist()),
            "expanded_key_hamming_summary": _numeric_summary(
                [int(shell_rows[index]["expanded_key_hamming"]) for index in np.flatnonzero(mask)]
            ),
        }
    adjacent: dict[str, Any] = {}
    for near, far in zip(SHELL_DISTANCES, SHELL_DISTANCES[1:]):
        near_scores = score_values[distances == near]
        far_scores = score_values[distances == far]
        comparisons = np.greater_equal(far_scores[:, None], near_scores[None, :])
        adjacent[f"{near}_vs_{far}"] = {
            "farther_score_ge_nearer_fraction": float(np.mean(comparisons)),
            "pair_count": int(comparisons.size),
        }
    top_k: dict[str, Any] = {}
    order = np.argsort(-score_values, kind="stable")
    for k in SHELL_TOP_K:
        selected = order[:k]
        top_k[str(k)] = {
            "distance_summary": _numeric_summary(distances[selected].tolist()),
            "rune_match_summary": _numeric_summary(rune_matches[selected].tolist()),
            "complete_word_match_summary": _numeric_summary(word_matches[selected].tolist()),
        }
    return {
        "candidate_count": len(shell_rows),
        "score_vs_affine_variable_matches_spearman": spearman_rank_correlation(
            score_values.tolist(), affine_matches.tolist()
        ),
        "score_vs_rune_matches_spearman": spearman_rank_correlation(
            score_values.tolist(), rune_matches.tolist()
        ),
        "score_vs_complete_word_matches_spearman": spearman_rank_correlation(
            score_values.tolist(), word_matches.tolist()
        ),
        "score_vs_rune_pairwise": _pairwise_concordance(
            score_values.tolist(), rune_matches.tolist()
        ),
        "adjacent_shell_overlap": adjacent,
        "median_score_monotonic_steps_towards_truth": sum(
            medians[index] >= medians[index + 1]
            for index in range(len(medians) - 1)
        ),
        "median_score_monotonic_steps_total": len(medians) - 1,
        "by_distance": by_distance,
        "top_k": top_k,
    }


def run_multiscale_perturbation_shells(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    repo_root = repo_root.resolve()
    experiment_started_at_utc = _utc_now_iso()
    experiment_started = time.perf_counter()
    candidate_count = len(SHELL_DISTANCES) * SHELL_SAMPLES_PER_DISTANCE
    scoring_evaluations = candidate_count * len(SCORER_PANEL) * 2
    terminal_evaluations = candidate_count
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="multiscale_perturbation_shells_v1",
        benchmark_id=TARGET_BENCHMARK.benchmark_id,
        question="How smoothly do the predeclared scorer profiles order controlled d16 affine perturbations around the true key?",
        hypothesis="Low-to-medium order profiles provide stronger monotonic movement and adjacent-shell separation than J0/J1.",
        alternative="Shell ordering is weak, non-monotonic or no better than the recorded high-order baseline.",
        decision_rule="Diagnostics always refine. Freeze no ladder; report all shell metrics and preserve the candidates outside normal archives.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(FailureMechanism.RANKING, FailureMechanism.EVIDENCE_REPRODUCIBILITY),
        budget_evaluations=scoring_evaluations + terminal_evaluations,
        lesson_ids=("CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "shell_distances": list(SHELL_DISTANCES),
        "samples_per_distance": SHELL_SAMPLES_PER_DISTANCE,
        "profile_ids": [profile.profile_id for profile in SCORER_PANEL],
        "balancing": {
            "variable_schedule": "32 samples repeat all 16 cyclic rotations twice",
            "delta_schedule": "cycle through all non-zero modulo-29 deltas",
        },
        "normal_candidate_archive_written": False,
        "normal_search_seed_allowed": False,
        "scoring_evaluations": scoring_evaluations,
        "terminal_evaluations": terminal_evaluations,
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            provenance = build_evaluator_provenance(
                repo_root=repo_root,
                evaluator_source=Path(__file__).with_name("replay.py"),
                scoring_contracts=tuple(
                    profile.scoring_contract() for profile in SCORER_PANEL
                ),
                require_assets=True,
            )
            design_path = run_dir / "artifacts/perturbation_shell_design.json"
            _write_json(design_path, {
                "schema": "rdp.two_period_overlay.perturbation_shell_design.v1",
                **configuration,
                "diagnostic_candidate_values_persisted_here": False,
                "asset_provenance": provenance,
            })

            base_case, base_reference = build_rdp_case(
                TARGET_BENCHMARK,
                scoring_contract=SCORER_PANEL[0].scoring_contract(),
            )
            true_variables = np.asarray(
                [base_reference.true_key[index] for index in base_case.free_columns],
                dtype=np.uint8,
            )
            shell_vectors, shell_metadata = build_perturbation_shells(true_variables)
            profile_scores: dict[str, list[float]] = {}
            profile_performance: dict[str, Any] = {}
            all_deterministic = True
            scoring_phase_started = time.perf_counter()
            for profile in SCORER_PANEL:
                search_case, _reference = build_rdp_case(
                    TARGET_BENCHMARK,
                    scoring_contract=profile.scoring_contract(),
                )
                tracemalloc.start()
                started = time.perf_counter()
                first = np.asarray(search_case.evaluate_variables(shell_vectors), dtype=np.float64)
                second = np.asarray(search_case.evaluate_variables(shell_vectors), dtype=np.float64)
                elapsed = time.perf_counter() - started
                _current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                deterministic = bool(np.allclose(
                    first, second, atol=ABSOLUTE_TOLERANCE, rtol=RELATIVE_TOLERANCE
                ))
                all_deterministic = all_deterministic and deterministic
                profile_scores[profile.profile_id] = first.tolist()
                profile_performance[profile.profile_id] = {
                    "profile": profile.to_json_dict(),
                    "deterministic": deterministic,
                    "evaluations": 2 * candidate_count,
                    "elapsed_s": elapsed,
                    "candidate_evaluations_per_s": (2 * candidate_count) / elapsed,
                    "python_peak_allocated_bytes": peak,
                }
            scoring_phase_elapsed = time.perf_counter() - scoring_phase_started

            # Terminal diagnostic phase. These rows remain only under
            # experiment_result.reference_evaluation and never enter an archive.
            terminal_phase_started = time.perf_counter()
            shell_rows: list[dict[str, Any]] = []
            for variables, metadata in zip(shell_vectors, shell_metadata, strict=True):
                key = expand(
                    variables, base_case.particular, base_case.basis, TARGET_BENCHMARK
                )
                metrics = reference_metrics(
                    base_reference, variables, base_case.particular, base_case.basis
                )
                shell_rows.append({
                    **metadata,
                    "expanded_key_hamming": int(
                        np.count_nonzero(key != base_reference.true_key)
                    ),
                    "rune_matches": int(metrics["rune_matches"]),
                    "rune_mismatches": TARGET_BENCHMARK.text_length - int(metrics["rune_matches"]),
                    "complete_word_matches": int(metrics["complete_word_matches"]),
                    "complete_word_mismatches": (
                        int(metrics["complete_words_total"])
                        - int(metrics["complete_word_matches"])
                    ),
                })
            profile_diagnostics = {
                profile.profile_id: _shell_profile_summary(
                    profile_scores[profile.profile_id], shell_rows
                )
                for profile in SCORER_PANEL
            }
            terminal_phase_elapsed = time.perf_counter() - terminal_phase_started
            experiment_elapsed = time.perf_counter() - experiment_started
            timing = {
                "schema": "rdp.two_period_overlay.execution_timing.v1",
                "experiment_id": "multiscale_perturbation_shells_v1",
                "scope": "Scientific work through terminal diagnostics; review-pack creation is measured by the Pack 02A collector.",
                "started_at_utc": experiment_started_at_utc,
                "finished_at_utc": _utc_now_iso(),
                "elapsed_s": experiment_elapsed,
                "phases": {
                    "profile_scoring_elapsed_s": scoring_phase_elapsed,
                    "terminal_diagnostics_elapsed_s": terminal_phase_elapsed,
                },
                "candidate_count": candidate_count,
                "scoring_evaluations": scoring_evaluations,
                "terminal_evaluations": terminal_evaluations,
                "profiles": profile_performance,
            }
            _write_json(run_dir / "artifacts/execution_timing.json", timing)
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done" if all_deterministic else "non_deterministic",
                result_summary={
                    "candidate_count": candidate_count,
                    "profile_count": len(SCORER_PANEL),
                    "profile_ids": [profile.profile_id for profile in SCORER_PANEL],
                    "all_deterministic": all_deterministic,
                    "normal_candidate_archive_written": False,
                    "normal_search_seed_allowed": False,
                    "artifact": "artifacts/perturbation_shell_design.json",
                    "profile_performance": profile_performance,
                    "timing": timing,
                },
                reference_evaluation={
                    "diagnostic_only": True,
                    "candidate_specific_shell_diagnostics": shell_rows,
                    "profile_shell_diagnostics": profile_diagnostics,
                },
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


def _pilot_starts() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for restart_index in range(PILOT_RESTARTS):
        seed = coordinate_supply_seed(
            PILOT_BENCHMARK.benchmark_id, PILOT_SEED_BLOCK, restart_index
        )
        rng = np.random.default_rng(seed)
        variables = rng.integers(
            0,
            PILOT_BENCHMARK.alphabet_size,
            size=PILOT_BENCHMARK.expected_free_dimension,
            dtype=np.uint8,
        )
        rows.append({
            "restart_index": restart_index,
            "seed": seed,
            "variables": variables.astype(int).tolist(),
        })
    return tuple(rows)


def _archive_policy(profile: ScorerProfile) -> ArchivePolicy:
    return ArchivePolicy(
        capacity=PILOT_ARCHIVE_CAPACITY,
        decision_score=profile.score_name,
        higher_is_better=True,
        family_limit=None,
    )


def _pilot_record(
    variables: np.ndarray,
    score: float,
    search_case: Any,
    profile: ScorerProfile,
    *,
    arm_id: str,
    restart_index: int,
    evaluation_index: int,
    details: Mapping[str, Any],
) -> CandidateRecord:
    expanded = expand(
        np.asarray(variables, dtype=np.uint8),
        search_case.particular,
        search_case.basis,
        PILOT_BENCHMARK,
    )
    identity = {"expanded_key": expanded.astype(int).tolist()}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={
            "variables": np.asarray(variables, dtype=np.uint8).astype(int).tolist(),
            "expanded_key": expanded.astype(int).tolist(),
            "benchmark_id": PILOT_BENCHMARK.benchmark_id,
        },
        scores={profile.score_name: float(score)},
        provenance=CandidateProvenance(
            source="matched_d8_profile_pilot",
            operation="coordinate_descent",
            evaluation_index=evaluation_index,
            details={
                "profile_id": profile.profile_id,
                "arm_id": arm_id,
                "restart_index": restart_index,
                **dict(details),
            },
        ),
    )


def run_profile_arm(
    search_case: Any,
    profile: ScorerProfile,
    starts: Sequence[Mapping[str, Any]],
    *,
    arm_id: str,
    sweeps: int,
) -> ProfileArmOutcome:
    if sweeps <= 0:
        raise ValueError("sweeps must be positive")
    archive = CandidateArchive(_archive_policy(profile))
    restart_rows: list[dict[str, Any]] = []
    generated_ids: set[str] = set()
    evaluations = 0
    started = time.monotonic()
    timing_started = time.perf_counter()
    deadline = started + PILOT_PROFILE_WALLCLOCK_SAFETY_LIMIT
    for row in starts:
        attempt_started = time.perf_counter()
        restart_index = int(row["restart_index"])
        seed = int(row["seed"])
        starting = np.asarray(row["variables"], dtype=np.uint8)
        start_score = float(search_case.evaluate_variables(starting)[0])
        rng = np.random.default_rng(seed)
        regenerated = rng.integers(
            0,
            PILOT_BENCHMARK.alphabet_size,
            size=PILOT_BENCHMARK.expected_free_dimension,
            dtype=np.uint8,
        )
        if not np.array_equal(regenerated, starting):
            raise RuntimeError("pilot start regeneration is inconsistent")
        ending, final_score, used = coordinate_search(
            search_case.evaluate_variables,
            rng,
            starting,
            sweeps,
            deadline=deadline,
        )
        # ``coordinate_search`` accounts for its own initial score. The
        # separately measured start score is an evidence call.
        attempt_evaluations = 1 + used
        evaluations += attempt_evaluations
        attempt_elapsed = time.perf_counter() - attempt_started
        attempt_rate = attempt_evaluations / attempt_elapsed
        record = _pilot_record(
            ending,
            final_score,
            search_case,
            profile,
            arm_id=arm_id,
            restart_index=restart_index,
            evaluation_index=evaluations,
            details={
                "seed": seed,
                "starting_variables": starting.astype(int).tolist(),
                "ending_variables": ending.astype(int).tolist(),
                "start_score": start_score,
                "final_score": float(final_score),
                "score_gain": float(final_score - start_score),
                "sweeps_requested": sweeps,
                "evaluations_used": attempt_evaluations,
                "elapsed_s": attempt_elapsed,
                "candidate_evaluations_per_s": attempt_rate,
            },
        )
        generated_ids.add(record.candidate_id)
        offer = archive.offer(record)
        restart_rows.append({
            "restart_index": restart_index,
            "seed": seed,
            "starting_variables": starting.astype(int).tolist(),
            "ending_variables": ending.astype(int).tolist(),
            "start_score": start_score,
            "final_score": float(final_score),
            "score_gain": float(final_score - start_score),
            "sweeps_requested": sweeps,
            "evaluations_used": attempt_evaluations,
            "elapsed_s": attempt_elapsed,
            "candidate_evaluations_per_s": attempt_rate,
            "candidate_id": record.candidate_id,
            "archive_offer_action": offer.action.value,
            "archive_retained": offer.retained,
        })
    elapsed = time.perf_counter() - timing_started
    return ProfileArmOutcome(
        profile_id=profile.profile_id,
        arm_id=arm_id,
        sweeps_requested=sweeps,
        archive=archive,
        restart_rows=tuple(restart_rows),
        generated_candidates=len(restart_rows),
        unique_candidates=len(generated_ids),
        duplicate_candidates=len(restart_rows) - len(generated_ids),
        evaluations=evaluations,
        elapsed_s=elapsed,
    )


def _pairwise_hamming_summary(vectors: Sequence[Sequence[int]]) -> dict[str, float]:
    rows = [np.asarray(row, dtype=np.uint8) for row in vectors]
    values: list[int] = []
    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            values.append(int(np.count_nonzero(rows[left] != rows[right])))
    if not values:
        return {
            "minimum": 0.0,
            "q25": 0.0,
            "median": 0.0,
            "q75": 0.0,
            "maximum": 0.0,
            "mean": 0.0,
        }
    return _numeric_summary(values)


def _arm_terminal_summary(
    outcome: ProfileArmOutcome,
    profile: ScorerProfile,
    search_case: Any,
    reference: Any,
) -> dict[str, Any]:
    records = outcome.archive.records
    candidate_ids = [record.candidate_id for record in records]
    scores = [float(record.scores[profile.score_name]) for record in records]
    terminal_rows: list[dict[str, Any]] = []
    true_variables = np.asarray(
        [reference.true_key[index] for index in search_case.free_columns],
        dtype=np.uint8,
    )
    for record in records:
        variables = np.asarray(record.payload["variables"], dtype=np.uint8)
        row = reference_metrics(
            reference, variables, search_case.particular, search_case.basis
        )
        row["affine_variable_matches"] = int(np.count_nonzero(variables == true_variables))
        terminal_rows.append(row)

    restart_terminal: list[dict[str, Any]] = []
    for row in outcome.restart_rows:
        start = np.asarray(row["starting_variables"], dtype=np.uint8)
        final = np.asarray(row["ending_variables"], dtype=np.uint8)
        start_metrics = reference_metrics(
            reference, start, search_case.particular, search_case.basis
        )
        final_metrics = reference_metrics(
            reference, final, search_case.particular, search_case.basis
        )
        restart_terminal.append({
            "rune_improvement": int(final_metrics["rune_matches"]) - int(start_metrics["rune_matches"]),
            "complete_word_improvement": (
                int(final_metrics["complete_word_matches"])
                - int(start_metrics["complete_word_matches"])
            ),
            "affine_variable_improvement": (
                int(np.count_nonzero(final == true_variables))
                - int(np.count_nonzero(start == true_variables))
            ),
        })
    return {
        "archive_profile_diagnostic": aggregate_profile_diagnostic(
            candidate_ids, scores, terminal_rows
        ),
        "matched_start_to_final": {
            "restart_count": len(restart_terminal),
            "rune_improvement_summary": _numeric_summary(
                [row["rune_improvement"] for row in restart_terminal]
            ),
            "rune_improved_count": sum(row["rune_improvement"] > 0 for row in restart_terminal),
            "complete_word_improvement_summary": _numeric_summary(
                [row["complete_word_improvement"] for row in restart_terminal]
            ),
            "complete_word_improved_count": sum(
                row["complete_word_improvement"] > 0 for row in restart_terminal
            ),
            "affine_variable_improvement_summary": _numeric_summary(
                [row["affine_variable_improvement"] for row in restart_terminal]
            ),
            "affine_variable_improved_count": sum(
                row["affine_variable_improvement"] > 0 for row in restart_terminal
            ),
        },
    }


def _write_arm_and_replay(
    run_dir: Path,
    run: Any,
    profile: ScorerProfile,
    search_case: Any,
    outcome: ProfileArmOutcome,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path("artifacts/matched_d8_pilot") / profile.profile_id / outcome.arm_id
    archive_rel = root / "candidate_archive.json"
    restarts_rel = root / "restart_evidence.json"
    batch_rel = root / "all_candidates_batch.json"
    context_rel = root / "replay_context.json"
    binding_rel = root / "replay_binding.json"
    replay_rel = root / "replay_evidence.json"

    write_candidate_archive(run_dir / archive_rel, outcome.archive)
    _write_json(run_dir / restarts_rel, {
        "schema": "rdp.two_period_overlay.matched_d8_restart_evidence.v1",
        "profile_id": profile.profile_id,
        "arm_id": outcome.arm_id,
        "rows": list(outcome.restart_rows),
    })
    batch = select_candidate_batch(
        outcome.archive,
        purpose="replay",
        selection_label=f"{profile.profile_id}__{outcome.arm_id}__all",
        candidate_ids=tuple(record.candidate_id for record in outcome.archive.records),
    )
    write_candidate_batch(run_dir / batch_rel, batch)
    context: CandidateReplayContext = make_replay_context(
        search_case,
        run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        evaluator_provenance=provenance,
        scoring_contract=profile.scoring_contract(),
        decision_score=profile.score_name,
        evaluator_id=f"two_period_overlay_{profile.profile_id}_d8_pilot_v1",
    )
    write_replay_context(run_dir / context_rel, context)
    binding = CandidateReplayBinding.create(
        campaign_id="two_period_overlay",
        source_run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        benchmark_id=PILOT_BENCHMARK.benchmark_id,
        context=context,
        batch=batch,
        context_artifact=context_rel.as_posix(),
        batch_artifact=batch_rel.as_posix(),
    )
    write_replay_binding(run_dir / binding_rel, binding)
    replay = replay_candidate_batch(
        batch,
        context,
        binding,
        evaluator=build_replay_evaluator(context),
        mode=ReplayMode.VERIFY,
        decision_score=profile.score_name,
        higher_is_better=True,
        evaluator_configuration={
            "experiment": "matched_d8_profile_pilot_v1",
            "profile": profile.to_json_dict(),
            "arm_id": outcome.arm_id,
            "evaluator_provenance": dict(provenance),
        },
        repeat_count=REPLAY_REPEAT_COUNT,
        absolute_tolerance=ABSOLUTE_TOLERANCE,
        relative_tolerance=RELATIVE_TOLERANCE,
    )
    write_candidate_replay(run_dir / replay_rel, replay)
    return {
        **outcome.search_summary(),
        "replay_deterministic": replay.deterministic,
        "replay_stored_scores_verified": replay.stored_scores_verified,
        "affine_pairwise_hamming": _pairwise_hamming_summary(
            [record.payload["variables"] for record in outcome.archive.records]
        ),
        "expanded_key_pairwise_hamming": _pairwise_hamming_summary(
            [record.payload["expanded_key"] for record in outcome.archive.records]
        ),
        "artifacts": {
            "archive": archive_rel.as_posix(),
            "restart_evidence": restarts_rel.as_posix(),
            "batch": batch_rel.as_posix(),
            "context": context_rel.as_posix(),
            "binding": binding_rel.as_posix(),
            "replay": replay_rel.as_posix(),
        },
    }


def run_matched_d8_profile_pilot(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    repo_root = repo_root.resolve()
    experiment_started_at_utc = _utc_now_iso()
    experiment_started = time.perf_counter()
    static_run_id = latest_completed_static_panel(repo_root)
    static_run = _source_run(repo_root, static_run_id)
    static_summary_path = static_run / "artifacts/static_panel_summary.json"
    static_summary = _read_json(static_summary_path)
    profile_rates = _static_profile_rates(static_summary)
    calibrated = {
        profile.profile_id: calibrated_sweeps(profile_rates[profile.profile_id])
        for profile in SCORER_PANEL
    }
    # Upper bound assumes every requested sweep completes.
    fixed_eval_upper = len(SCORER_PANEL) * PILOT_RESTARTS * (
        2 + PILOT_FIXED_CORE_SWEEPS
        * PILOT_BENCHMARK.expected_free_dimension
        * PILOT_BENCHMARK.alphabet_size
    )
    calibrated_eval_upper = sum(
        PILOT_RESTARTS * (
            2 + calibrated[profile.profile_id]
            * PILOT_BENCHMARK.expected_free_dimension
            * PILOT_BENCHMARK.alphabet_size
        )
        for profile in SCORER_PANEL
    )
    replay_eval_upper = (
        len(SCORER_PANEL)
        * 2
        * PILOT_ARCHIVE_CAPACITY
        * REPLAY_REPEAT_COUNT
    )
    terminal_eval_upper = (
        len(SCORER_PANEL)
        * 2
        * (PILOT_ARCHIVE_CAPACITY + 2 * PILOT_RESTARTS)
    )
    evaluation_budget_upper = (
        fixed_eval_upper
        + calibrated_eval_upper
        + replay_eval_upper
        + terminal_eval_upper
    )
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="matched_d8_profile_pilot_v1",
        benchmark_id=PILOT_BENCHMARK.benchmark_id,
        question="Which scorer profiles generate useful candidates on the exact-extra-crib P13/P17 d8 surface under matched starts and cost-aware budgets?",
        hypothesis="S2 or S3 improves search movement and terminal enrichment over J0/J1 while B1 or F1 remains useful for later-stage judgement.",
        alternative="The static ranking lift does not translate into dynamic search, or any apparent lift disappears under matched starts and cost-aware budgets.",
        decision_rule="Pilots always refine. Freeze no ladder here; require deterministic replay and report fixed-evaluation and static-throughput-calibrated arms separately.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.RANKING,
            FailureMechanism.EVIDENCE_REPRODUCIBILITY,
        ),
        budget_evaluations=evaluation_budget_upper,
        lesson_ids=("CSL-004", "CSL-005", "CSL-007"),
    )
    budget_resolution = {
        "affected_item": "WP6 C.9 matched wall-clock budgets",
        "reason": (
            "Deadline-driven stopping would make candidate counts and final states depend on "
            "machine timing. Pack 02A therefore preserves a fixed common core and derives "
            "deterministic profile-specific sweep caps from the accepted Pack 01 static "
            "throughput evidence."
        ),
        "replacement_action": (
            "Run one identical-start, identical-sweep fixed core for landscape comparison, "
            "plus a separately reported static-throughput-calibrated equal-time arm. "
            "Record actual elapsed time and do not freeze the ladder if the calibration is poor."
        ),
        "target_scoring_seconds": PILOT_TARGET_SCORING_SECONDS,
        "static_source_run_id": static_run_id,
        "static_summary_sha256": hashlib.sha256(
            static_summary_path.read_bytes()
        ).hexdigest(),
        "profile_median_candidate_evaluations_per_s": profile_rates,
        "calibrated_sweeps": calibrated,
    }
    configuration = {
        "benchmark": PILOT_BENCHMARK.to_json_dict(),
        "profile_ids": [profile.profile_id for profile in SCORER_PANEL],
        "restarts": PILOT_RESTARTS,
        "seed_block": PILOT_SEED_BLOCK,
        "fixed_core_sweeps": PILOT_FIXED_CORE_SWEEPS,
        "budget_resolution": budget_resolution,
        "archive_capacity": PILOT_ARCHIVE_CAPACITY,
        "terminal_metrics_opened_only_after_all_search_visible_work": True,
        "ladder_frozen": False,
        "evaluation_budget_upper_bound": evaluation_budget_upper,
        "evaluation_budget_breakdown": {
            "fixed_search": fixed_eval_upper,
            "calibrated_search": calibrated_eval_upper,
            "replay": replay_eval_upper,
            "terminal": terminal_eval_upper,
        },
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            provenance = build_evaluator_provenance(
                repo_root=repo_root,
                evaluator_source=Path(__file__).with_name("replay.py"),
                scoring_contracts=tuple(
                    profile.scoring_contract() for profile in SCORER_PANEL
                ),
                require_assets=True,
            )
            starts = _pilot_starts()
            _write_json(run_dir / "artifacts/matched_d8_pilot/starts.json", {
                "schema": "rdp.two_period_overlay.matched_d8_starts.v1",
                "benchmark_id": PILOT_BENCHMARK.benchmark_id,
                "seed_block": PILOT_SEED_BLOCK,
                "rows": list(starts),
            })
            shutil.copyfile(
                static_summary_path,
                run_dir / "artifacts/matched_d8_pilot/source_static_panel_summary.json",
            )
            search_visible: dict[str, Any] = {}
            outcomes: dict[tuple[str, str], tuple[ProfileArmOutcome, Any, Any]] = {}
            all_replays_deterministic = True

            # Search-visible phase: every profile and both arms finish before
            # any terminal benchmark metric is computed.
            search_phase_started = time.perf_counter()
            for profile in SCORER_PANEL:
                search_case, reference = build_rdp_case(
                    PILOT_BENCHMARK,
                    scoring_contract=profile.scoring_contract(),
                )
                fixed = run_profile_arm(
                    search_case,
                    profile,
                    starts,
                    arm_id="fixed_core",
                    sweeps=PILOT_FIXED_CORE_SWEEPS,
                )
                calibrated_arm = run_profile_arm(
                    search_case,
                    profile,
                    starts,
                    arm_id="calibrated_time",
                    sweeps=calibrated[profile.profile_id],
                )
                profile_rows: dict[str, Any] = {}
                for outcome in (fixed, calibrated_arm):
                    arm_summary = _write_arm_and_replay(
                        run_dir, run, profile, search_case, outcome, provenance
                    )
                    all_replays_deterministic = (
                        all_replays_deterministic
                        and arm_summary["replay_deterministic"]
                        and arm_summary["replay_stored_scores_verified"]
                    )
                    profile_rows[outcome.arm_id] = arm_summary
                    outcomes[(profile.profile_id, outcome.arm_id)] = (
                        outcome,
                        search_case,
                        reference,
                    )
                search_visible[profile.profile_id] = {
                    "profile": profile.to_json_dict(),
                    "arms": profile_rows,
                }
            search_phase_elapsed = time.perf_counter() - search_phase_started

            summary_path = run_dir / "artifacts/matched_d8_pilot_summary.json"
            _write_json(summary_path, {
                "schema": "rdp.two_period_overlay.matched_d8_profile_pilot.v1",
                "benchmark": PILOT_BENCHMARK.to_json_dict(),
                "source_static_panel_run_id": static_run_id,
                "budget_resolution": budget_resolution,
                "starts_artifact": "artifacts/matched_d8_pilot/starts.json",
                "profiles": search_visible,
                "all_replays_deterministic": all_replays_deterministic,
                "terminal_metrics_included": False,
                "ladder_frozen": False,
            })

            # Terminal phase: search-visible artifacts and all candidate pools
            # are now complete and immutable.
            terminal_phase_started = time.perf_counter()
            terminal: dict[str, Any] = {}
            for profile in SCORER_PANEL:
                terminal[profile.profile_id] = {
                    arm_id: _arm_terminal_summary(
                        outcomes[(profile.profile_id, arm_id)][0],
                        profile,
                        outcomes[(profile.profile_id, arm_id)][1],
                        outcomes[(profile.profile_id, arm_id)][2],
                    )
                    for arm_id in ("fixed_core", "calibrated_time")
                }
            terminal_phase_elapsed = time.perf_counter() - terminal_phase_started
            experiment_elapsed = time.perf_counter() - experiment_started
            attempt_rows = [
                {
                    "profile_id": profile_id,
                    "arm_id": arm_id,
                    "restart_index": int(row["restart_index"]),
                    "seed": int(row["seed"]),
                    "sweeps_requested": int(row["sweeps_requested"]),
                    "evaluations": int(row["evaluations_used"]),
                    "elapsed_s": float(row["elapsed_s"]),
                    "candidate_evaluations_per_s": float(row["candidate_evaluations_per_s"]),
                    "candidate_id": str(row["candidate_id"]),
                }
                for (profile_id, arm_id), (outcome, _case, _reference) in outcomes.items()
                for row in outcome.restart_rows
            ]
            attempt_rows.sort(
                key=lambda row: (
                    str(row["profile_id"]),
                    str(row["arm_id"]),
                    int(row["restart_index"]),
                )
            )
            attempt_timing_path = run_dir / "artifacts/matched_d8_pilot/attempt_timing.json"
            _write_json(attempt_timing_path, {
                "schema": "rdp.two_period_overlay.matched_d8_attempt_timing.v1",
                "timing_scope": "Each deterministic restart attempt includes its start-score evidence call and coordinate-search work.",
                "attempt_count": len(attempt_rows),
                "rows": attempt_rows,
            })
            timing = {
                "schema": "rdp.two_period_overlay.execution_timing.v1",
                "experiment_id": "matched_d8_profile_pilot_v1",
                "scope": "Scientific work through terminal diagnostics; review-pack creation is measured by the Pack 02A collector.",
                "started_at_utc": experiment_started_at_utc,
                "finished_at_utc": _utc_now_iso(),
                "elapsed_s": experiment_elapsed,
                "phases": {
                    "search_and_replay_elapsed_s": search_phase_elapsed,
                    "terminal_diagnostics_elapsed_s": terminal_phase_elapsed,
                },
                "attempt_count": len(attempt_rows),
                "attempt_elapsed_s_summary": _numeric_summary(
                    [float(row["elapsed_s"]) for row in attempt_rows]
                ),
                "profiles": {
                    profile_id: {
                        arm_id: search_visible[profile_id]["arms"][arm_id]
                        for arm_id in ("fixed_core", "calibrated_time")
                    }
                    for profile_id in sorted(search_visible)
                },
                "attempt_timing_artifact": "artifacts/matched_d8_pilot/attempt_timing.json",
            }
            _write_json(run_dir / "artifacts/execution_timing.json", timing)
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done" if all_replays_deterministic else "replay_failure",
                result_summary={
                    "benchmark_id": PILOT_BENCHMARK.benchmark_id,
                    "profile_count": len(SCORER_PANEL),
                    "profile_ids": [profile.profile_id for profile in SCORER_PANEL],
                    "restarts": PILOT_RESTARTS,
                    "fixed_core_sweeps": PILOT_FIXED_CORE_SWEEPS,
                    "calibrated_sweeps": calibrated,
                    "all_replays_deterministic": all_replays_deterministic,
                    "ladder_frozen": False,
                    "artifact": "artifacts/matched_d8_pilot_summary.json",
                    "profiles": search_visible,
                    "timing": timing,
                },
                reference_evaluation={
                    "aggregate_dynamic_profile_diagnostics": terminal,
                    "candidate_specific_truth_emitted": False,
                },
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


__all__ = [
    "PILOT_BENCHMARK",
    "PILOT_FIXED_CORE_SWEEPS",
    "PILOT_RESTARTS",
    "PILOT_TARGET_SCORING_SECONDS",
    "SHELL_DISTANCES",
    "SHELL_SAMPLES_PER_DISTANCE",
    "_shell_deltas",
    "_shell_indices",
    "build_perturbation_shells",
    "calibrated_sweeps",
    "latest_completed_static_panel",
    "run_matched_d8_profile_pilot",
    "run_multiscale_perturbation_shells",
    "run_profile_arm",
]
