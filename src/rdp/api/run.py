"""Canonical V1 solve operation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import overload

import numpy as np

from rdp.api.pipeline import execute_run
from rdp.api.run_artifact_manifest import write_run_artifacts_manifest
from rdp.api.run_result import RunResult
from rdp.api.run_spec import ProblemInput, RunSpec
from rdp.api.run_spec_routing import materialize_runspec_problem_input
from rdp.api.solver_report import (
    ConfigurationResolution,
    OracleReport,
    ReproducibilityMetadata,
    RunConfigurationReport,
    SolverReport,
)
from rdp.api.solver_report_export import write_solver_report_json
from rdp.api.specs import CipherSpec, KeySpec, SolverSpec
from rdp.api.stop_reason_contract import (
    ExecutionStatus,
    execution_status_for_category,
    run_status_from_solution,
    stop_category_for_reason,
)
from rune_decrypter_prime.core.component_contracts import ScorerCapabilityReport
from rune_decrypter_prime.core.config import SolverConfig
from rune_decrypter_prime.core.config.interruptor import InterruptorConfig
from rune_decrypter_prime.core.config.logging_config import LoggingConfig
from rune_decrypter_prime.core.config.logging_config import get_run_dir, init_logging
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.types import (
    ComputeDevice,
    Device,
    IndexPermutation,
    InitialKeys,
    ProgressCallback,
    SolverKind,
    TextDirection,
    WordLengthPolicy,
    Direction,
)
from rune_decrypter_prime.scoring.scorer_report import ScorerReport


_UNSET = object()


@overload
def run(
    run_spec: RunSpec,
    /,
    *,
    progress_callback: ProgressCallback | None = None,
    progress_interval: int | None = None,
) -> RunResult: ...


@overload
def run(
    *,
    problem_input: ProblemInput,
    cipher: CipherSpec,
    key_space: KeySpec,
    solver: SolverSpec,
    scoring: ScoringConfig | None = None,
    initial_keys: InitialKeys | None = None,
    logging: LoggingConfig | None = None,
    word_length_policy: WordLengthPolicy = WordLengthPolicy.INFER,
    text_direction: TextDirection = TextDirection.RIGHT_TO_LEFT,
    compute_device: ComputeDevice = ComputeDevice.CPU,
    telemetry_enabled: bool = True,
    text_permutation: IndexPermutation | None = None,
    interruptors: InterruptorConfig | None = None,
    progress_callback: ProgressCallback | None = None,
    progress_interval: int | None = None,
) -> RunResult: ...


def run(
    run_spec: RunSpec | object = _UNSET,
    /,
    *,
    problem_input: ProblemInput | object = _UNSET,
    cipher: CipherSpec | object = _UNSET,
    key_space: KeySpec | object = _UNSET,
    solver: SolverSpec | object = _UNSET,
    scoring: ScoringConfig | None = None,
    initial_keys: InitialKeys | None = None,
    logging: LoggingConfig | None = None,
    word_length_policy: WordLengthPolicy = WordLengthPolicy.INFER,
    text_direction: TextDirection = TextDirection.RIGHT_TO_LEFT,
    compute_device: ComputeDevice = ComputeDevice.CPU,
    telemetry_enabled: bool = True,
    text_permutation: IndexPermutation | None = None,
    interruptors: InterruptorConfig | None = None,
    progress_callback: ProgressCallback | None = None,
    progress_interval: int | None = None,
) -> RunResult:
    """Run one solve through the single typed execution route."""
    component_values = (problem_input, cipher, key_space, solver)
    if run_spec is not _UNSET:
        if not isinstance(run_spec, RunSpec):
            raise TypeError("run_spec must be RunSpec")
        if any(value is not _UNSET for value in component_values):
            raise TypeError("run_spec cannot be combined with component arguments")
        if any(
            value is not None
            for value in (scoring, initial_keys, logging, text_permutation, interruptors)
        ) or (
            word_length_policy is not WordLengthPolicy.INFER
            or text_direction is not TextDirection.RIGHT_TO_LEFT
            or compute_device is not ComputeDevice.CPU
            or telemetry_enabled is not True
        ):
            raise TypeError("run_spec cannot be combined with durable component options")
        request = run_spec
    else:
        missing = [
            name
            for name, value in (
                ("problem_input", problem_input),
                ("cipher", cipher),
                ("key_space", key_space),
                ("solver", solver),
            )
            if value is _UNSET
        ]
        if missing:
            raise TypeError(f"missing required keyword-only arguments: {', '.join(missing)}")
        request = RunSpec(
            problem_input=problem_input,  # type: ignore[arg-type]
            cipher=cipher,  # type: ignore[arg-type]
            key_space=key_space,  # type: ignore[arg-type]
            solver=solver,  # type: ignore[arg-type]
            scoring=ScoringConfig() if scoring is None else scoring,
            initial_keys=initial_keys,
            logging=logging,
            word_length_policy=word_length_policy,
            text_direction=text_direction,
            compute_device=compute_device,
            telemetry_enabled=telemetry_enabled,
            text_permutation=text_permutation,
            interruptors=interruptors,
        )

    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable or None")
    if progress_interval is not None:
        if isinstance(progress_interval, bool) or not isinstance(progress_interval, int):
            raise TypeError("progress_interval must be an integer or None")
        if progress_interval < 1:
            raise ValueError("progress_interval must be >= 1")
    return _execute(request, progress_callback=progress_callback, progress_interval=progress_interval)


def _execute(
    request: RunSpec,
    *,
    progress_callback: ProgressCallback | None,
    progress_interval: int | None,
) -> RunResult:
    materialized = materialize_runspec_problem_input(request)
    device = Device.CPU if request.compute_device is ComputeDevice.CPU else Device.CUDA
    direction = Direction.LTR if request.text_direction is TextDirection.LEFT_TO_RIGHT else Direction.RTL
    effective_seed = 0 if request.solver.seed is None else request.solver.seed
    logging_runtime: dict[str, object] = {}
    if progress_callback is not None:
        logging_runtime["progress_callback"] = progress_callback
    if progress_interval is not None:
        logging_runtime["log_interval"] = progress_interval

    if request.solver.kind is SolverKind.TWO_PERIOD_CRIBS:
        if request.logging is not None:
            init_logging(request.logging)
        from rdp.api.two_period_cribs import normalize_two_period_cribs_request
        from rune_decrypter_prime.solvers.two_period_cribs import run_two_period_stages

        special_request = normalize_two_period_cribs_request(request.solver)
        solution = run_two_period_stages(
            ciphertext=materialized.ciphertext,
            wli=materialized.wli,
            cipher=request.cipher,
            key=request.key_space,
            request=special_request,
            device=device,
            direction=direction,
            telemetry_on=request.telemetry_enabled,
            interruptors=request.interruptors,
            interruptors_exact=None,
            interruptors_pool=None,
            interruptors_max=None,
        )
    else:
        solver_config = _runtime_solver_config(request.solver, effective_seed=effective_seed)
        solution = execute_run(
            ciphertext=materialized.ciphertext,
            wli=materialized.wli,
            cipher=request.cipher,
            key=request.key_space,
            solver=solver_config,
            scoring=request.scoring,
            scorer_name="rune",
            logging_config=request.logging,
            logging_runtime=logging_runtime,
            initialize_logging=request.logging is not None,
            telemetry_on=request.telemetry_enabled,
            device=device,
            encoding_dir=direction,
            initial_keys=request.initial_keys,
            initial_text_permutation_indices=request.text_permutation,
            interruptors=request.interruptors,
            interruptors_exact=None,
            interruptors_pool=None,
            interruptors_max=None,
        )
    result = _result_from_solution(request, solution, effective_seed=effective_seed)
    _write_requested_artifacts(request, result)
    return result


def _runtime_solver_config(solver: SolverSpec, *, effective_seed: int) -> SolverConfig:
    runtime_name = {
        SolverKind.BEAM_SEARCH: "beam",
        SolverKind.GENETIC_ALGORITHM: "ga",
        SolverKind.SIMULATED_ANNEALING: "sa",
        SolverKind.HYBRID: "hybrid",
        SolverKind.KAEDING: "kaeding",
    }[solver.kind]
    runtime_params = _runtime_solver_parameters(solver)
    return SolverConfig(name=runtime_name, params=runtime_params, seed=effective_seed)


def _runtime_solver_parameters(solver: SolverSpec) -> dict[str, object]:
    """Translate one canonical SolverSpec into the existing engine contract.

    This is the sole public-to-runtime solver boundary.  Each public field has
    one explicit runtime owner, and exact key checks prevent future constructor
    additions from being silently dropped.
    """
    params = dict(solver.parameters)

    if solver.kind is SolverKind.BEAM_SEARCH:
        _require_exact_solver_fields(
            solver.kind,
            params,
            {
                "width",
                "rounds",
                "restarts",
                "expansion",
                "maximum_children_per_parent",
                "sample_per_parent",
                "top_parents_fraction",
                "plateau_rounds",
                "plateau_minimum_delta",
                "target_score",
            },
        )
        return _without_none({
            "beam_width": params["width"],
            "rounds": params["rounds"],
            "restarts": params["restarts"],
            "expand_mode": params["expansion"],
            "expand.max_children_per_parent": params["maximum_children_per_parent"],
            "sample_per_parent": params["sample_per_parent"],
            "top_parents_factor": params["top_parents_fraction"],
            "plateau_rounds": params["plateau_rounds"],
            "plateau_min_delta": params["plateau_minimum_delta"],
            "stop_score": params["target_score"],
        })

    if solver.kind is SolverKind.GENETIC_ALGORITHM:
        _require_exact_solver_fields(
            solver.kind,
            params,
            {
                "population_size",
                "generations",
                "elite_fraction",
                "mutation_probability",
                "crossover_fraction",
                "tournament_size",
                "plateau_generations",
                "plateau_minimum_delta",
                "target_score",
            },
        )
        return _without_none({
            "pop_size": params["population_size"],
            "generations": params["generations"],
            "elite_frac": params["elite_fraction"],
            "mut_prob": params["mutation_probability"],
            "cx_frac": params["crossover_fraction"],
            "tournament_k": params["tournament_size"],
            "plateau_rounds": params["plateau_generations"],
            "plateau_min_delta": params["plateau_minimum_delta"],
            "stop_score": params["target_score"],
        })

    if solver.kind is SolverKind.SIMULATED_ANNEALING:
        _require_exact_solver_fields(
            solver.kind,
            params,
            {
                "iterations",
                "initial_temperature",
                "minimum_temperature",
                "cooling_rate",
                "automatic_cooling",
                "reseed_interval",
                "local_improvement_on_accept",
                "rescue_drop_absolute",
                "rescue_drop_ratio",
                "plateau_iterations",
                "plateau_minimum_delta",
                "target_score",
            },
        )
        return _without_none({
            "iters": params["iterations"],
            "T0": params["initial_temperature"],
            "Tmin": params["minimum_temperature"],
            "cool": params["cooling_rate"],
            "auto_cooling": params["automatic_cooling"],
            "sa_reseed_interval": params["reseed_interval"],
            "local_improve_on_accept": params["local_improvement_on_accept"],
            "sa_rescue_drop_abs": params["rescue_drop_absolute"],
            "sa_rescue_drop_ratio": params["rescue_drop_ratio"],
            "plateau_rounds": params["plateau_iterations"],
            "plateau_min_delta": params["plateau_minimum_delta"],
            "stop_score": params["target_score"],
        })

    if solver.kind is SolverKind.HYBRID:
        _require_exact_solver_fields(
            solver.kind,
            params,
            {
                "genetic_algorithm",
                "simulated_annealing",
                "use_beam_search",
                "beam_width",
                "beam_rounds",
                "beam_expansion",
                "sample_per_parent",
                "top_parents_fraction",
                "plateau_rounds",
                "plateau_minimum_delta",
                "target_score",
            },
        )
        genetic_algorithm = _solver_spec_from_mapping(
            params["genetic_algorithm"], "genetic_algorithm"
        )
        simulated_annealing = _solver_spec_from_mapping(
            params["simulated_annealing"], "simulated_annealing"
        )
        if genetic_algorithm.kind is not SolverKind.GENETIC_ALGORITHM:
            raise TypeError("hybrid genetic_algorithm must contain a genetic-algorithm SolverSpec")
        if simulated_annealing.kind is not SolverKind.SIMULATED_ANNEALING:
            raise TypeError("hybrid simulated_annealing must contain a simulated-annealing SolverSpec")
        ga_params = _runtime_solver_parameters(genetic_algorithm)
        sa_params = _runtime_solver_parameters(simulated_annealing)
        if genetic_algorithm.seed is not None:
            ga_params["seed"] = genetic_algorithm.seed
        if simulated_annealing.seed is not None:
            sa_params["seed"] = simulated_annealing.seed
        return _without_none({
            "ga": ga_params,
            "sa": sa_params,
            "use_beam": params["use_beam_search"],
            "beam_width": params["beam_width"],
            "rounds": params["beam_rounds"],
            "beam.expand_mode": params["beam_expansion"],
            "beam.sample_per_parent": params["sample_per_parent"],
            "beam.top_parents_factor": params["top_parents_fraction"],
            "plateau_rounds": params["plateau_rounds"],
            "plateau_min_delta": params["plateau_minimum_delta"],
            "stop_score": params["target_score"],
        })

    if solver.kind is SolverKind.KAEDING:
        _require_exact_solver_fields(
            solver.kind,
            params,
            {
                "steps",
                "restarts",
                "inner_batch_size",
                "block_schedule",
                "column_batch_size",
                "column_interval",
                "slip_blocks",
                "slip_interval",
                "slip_policy",
                "slip_swaps",
                "stall_rounds",
                "stall_slip_limit",
                "stop_after_stall_slip_limit",
                "plateau_rounds",
                "plateau_minimum_delta",
                "target_score",
            },
        )
        slip_policy = {
            "fixed_interval": "fixed",
            "on_stall": "stall",
        }.get(str(params["slip_policy"]))
        if slip_policy is None:
            raise ValueError(f"unsupported Kaeding slip policy: {params['slip_policy']!r}")
        return _without_none({
            "steps": params["steps"],
            "restarts": params["restarts"],
            "inner_batch": params["inner_batch_size"],
            "block_schedule": params["block_schedule"],
            "col_batch": params["column_batch_size"],
            "col_every": params["column_interval"],
            "slip_blocks": params["slip_blocks"],
            "slip_every": params["slip_interval"],
            "slip_policy": slip_policy,
            "slip_swaps": params["slip_swaps"],
            "stall_rounds": params["stall_rounds"],
            "stall_slip_limit": params["stall_slip_limit"],
            "stall_stop_on_limit": params["stop_after_stall_slip_limit"],
            "plateau_rounds": params["plateau_rounds"],
            "plateau_min_delta": params["plateau_minimum_delta"],
            "stop_score": params["target_score"],
        })

    raise ValueError(f"solver kind {solver.kind.value!r} does not use the generic engine route")


def _without_none(values: Mapping[str, object]) -> dict[str, object]:
    return {name: value for name, value in values.items() if value is not None}


def _require_exact_solver_fields(
    kind: SolverKind,
    params: Mapping[str, object],
    expected: set[str],
) -> None:
    actual = set(params)
    if actual == expected:
        return
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    raise RuntimeError(
        f"incomplete {kind.value} runtime translation: "
        f"missing public fields={missing}, unexpected public fields={unexpected}"
    )


def _solver_spec_from_mapping(value: object, field_name: str) -> SolverSpec:
    if not isinstance(value, Mapping):
        raise TypeError(f"hybrid {field_name} must be a serialized SolverSpec mapping")
    payload = dict(value)
    kind = payload.get("kind")
    parameters = payload.get("parameters")
    if not isinstance(kind, str) or not isinstance(parameters, Mapping):
        raise TypeError(f"hybrid {field_name} must contain kind and parameters fields")
    parsed_parameters = dict(parameters)
    seed = payload.get("seed")
    if seed is not None:
        parsed_parameters["seed"] = seed
    return SolverSpec.from_name(kind, parameters=parsed_parameters)


def _write_requested_artifacts(request: RunSpec, result: RunResult) -> None:
    logging = request.logging
    if logging is None:
        return
    run_dir = get_run_dir()
    if logging.write_solver_report:
        write_solver_report_json(result.solver_report, run_dir=run_dir)
    if logging.write_display_summary:
        from rdp.api.display import build_summary, write_summary_json

        summary = build_summary(
            result,
            spec=request,
            scorer_report=result.scorer_report,
        )
        write_summary_json(summary, run_dir / "artifacts" / "rdp_display_summary.json")
    if logging.write_artifact_manifest:
        write_run_artifacts_manifest(
            run_dir=run_dir,
            include_solver_report=logging.write_solver_report,
        )


def _solution_key(solution: object) -> tuple[int, ...] | None:
    value = getattr(solution, "key", None)
    if value is None:
        return None
    array = np.asarray(value).reshape(-1)
    return tuple(int(item) for item in array.tolist())


def _solution_plaintext(solution: object) -> tuple[int, ...] | None:
    value = getattr(solution, "plaintext_idx", None)
    if value is None or (hasattr(value, "__len__") and len(value) == 0):
        value = getattr(solution, "plaintext", None)
    if value is None:
        return None
    array = np.asarray(value).reshape(-1)
    return tuple(int(item) for item in array.tolist())


def _solution_telemetry(solution: object) -> Mapping[str, object]:
    meta = getattr(solution, "meta", None)
    if not isinstance(meta, Mapping):
        return {}
    telemetry = meta.get("telemetry")
    return telemetry if isinstance(telemetry, Mapping) else {}


def _scorer_report_details_from_solution(solution: object) -> Mapping[str, object]:
    """Retain the runtime scorer-capability evidence in its canonical report owner."""
    meta = getattr(solution, "meta", None)
    if not isinstance(meta, Mapping):
        return {}
    scorer_lanes = meta.get("scorer_lanes")
    if not isinstance(scorer_lanes, Mapping):
        return {}
    return {"scorer_lanes": dict(scorer_lanes)}


def _solver_report_details_from_solution(
    solution: object, *, status: object
) -> Mapping[str, object]:
    meta = getattr(solution, "meta", None)
    details: dict[str, object] = {
        "run_status": status.to_json_dict(),
    }
    if not isinstance(meta, Mapping):
        return details
    for name, value in meta.items():
        if name not in {"telemetry", "scorer_lanes"}:
            details[str(name)] = value
    two_period = meta.get("two_period_solve")
    if isinstance(two_period, Mapping) and "execution_route" in two_period:
        details["execution_route"] = two_period["execution_route"]
    return details


def _result_from_solution(
    request: RunSpec, solution: object, *, effective_seed: int
) -> RunResult:
    runtime_reason = getattr(solution, "stop_reason", None)
    category = stop_category_for_reason(runtime_reason)
    execution_status = execution_status_for_category(category)
    if runtime_reason is None:
        execution_status = ExecutionStatus.COMPLETED
    status = run_status_from_solution(solution, execution_status=execution_status)
    key = _solution_key(solution)
    plaintext = _solution_plaintext(solution)
    score_value = getattr(solution, "score", None)
    score = None if score_value is None else float(score_value)

    solver_resolution = ConfigurationResolution(
        requested=request.solver.to_dict(),
        effective=request.solver.to_dict(),
    )
    scoring_resolution = ConfigurationResolution(
        requested=request.scoring.to_dict(),
        effective=request.scoring.to_dict(),
    )
    cipher_resolution = ConfigurationResolution(
        requested={
            "cipher": request.cipher.to_dict(),
            "key_space": request.key_space.to_dict(),
        },
        effective={
            "cipher": request.cipher.to_dict(),
            "key_space": request.key_space.to_dict(),
        },
    )
    configuration = RunConfigurationReport(
        solver=solver_resolution,
        scoring=scoring_resolution,
        cipher=cipher_resolution,
    )
    solver_report = SolverReport(
        solver=request.solver.kind,
        parameters=solver_resolution,
        requested_seed=request.solver.seed,
        effective_seed=effective_seed,
        status=status,
        best_key=key,
        best_score=score,
        evaluations=int(getattr(solution, "evals", 0) or 0),
        steps=int(getattr(solution, "step", 0) or 0),
        tokens_processed=int(getattr(solution, "tokens_processed", 0) or 0),
        wall_time_seconds=float(getattr(solution, "wall_time_s", 0.0) or 0.0),
        decrypt_time_seconds=float(getattr(solution, "decrypt_time_s", 0.0) or 0.0),
        score_time_seconds=float(getattr(solution, "score_time_s", 0.0) or 0.0),
        details=_solver_report_details_from_solution(solution, status=status),
    )
    scorer_report = ScorerReport(
        objective=request.scoring.objective,
        score=score,
        raw_score=score,
        telemetry=_solution_telemetry(solution),
        time_seconds=float(getattr(solution, "score_time_s", 0.0) or 0.0),
        capabilities=ScorerCapabilityReport(lanes=()),
        details=_scorer_report_details_from_solution(solution),
    )
    reproducibility = ReproducibilityMetadata(
        backend=request.scoring.backend,
        compute_device=request.compute_device,
        compute_dtype=request.scoring.compute_dtype,
        accumulator_dtype=request.scoring.accumulator_dtype,
        requested_seed=request.solver.seed,
        effective_seed=effective_seed,
        stochastic=True,
        solver_config=request.solver.to_dict(),
        scoring_config=request.scoring.to_dict(),
        objective=request.scoring.objective.to_dict(),
        cipher={"cipher": request.cipher.to_dict(), "key_space": request.key_space.to_dict()},
        dictionary_policy=request.scoring.hamming_dictionary_policy.value,
        stop_category=status.stop_category,
        stop_reason=status.stop_reason,
    )
    plaintext_text = getattr(solution, "plaintext_str", None)
    if plaintext_text is not None:
        plaintext_text = str(plaintext_text)
    return RunResult(
        plaintext=plaintext,
        plaintext_text=plaintext_text,
        key=key,
        score=score,
        status=status,
        solver_report=solver_report,
        scorer_report=scorer_report,
        configuration=configuration,
        reproducibility=reproducibility,
        oracle=OracleReport(),
        telemetry=_solution_telemetry(solution),
        artifacts=(),
    )


__all__ = ["run"]
