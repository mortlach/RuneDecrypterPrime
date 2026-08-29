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
    params = dict(solver.parameters)
    runtime_name = {
        SolverKind.BEAM_SEARCH: "beam",
        SolverKind.GENETIC_ALGORITHM: "ga",
        SolverKind.SIMULATED_ANNEALING: "sa",
        SolverKind.HYBRID: "hybrid",
        SolverKind.KAEDING: "kaeding",
        SolverKind.TWO_PERIOD_CRIBS: "two_period_cribs",
    }[solver.kind]
    field_names = {
        SolverKind.BEAM_SEARCH: {"width": "beam_width"},
        SolverKind.GENETIC_ALGORITHM: {"population_size": "pop_size"},
        SolverKind.SIMULATED_ANNEALING: {"iterations": "sa_iters"},
        SolverKind.KAEDING: {"inner_batch_size": "inner_batch"},
    }.get(solver.kind, {})
    runtime_params = {field_names.get(name, name): value for name, value in params.items()}
    return SolverConfig(name=runtime_name, params=runtime_params, seed=effective_seed)


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


def _result_from_solution(request: RunSpec, solution: object, *, effective_seed: int) -> RunResult:
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
    )
    scorer_report = ScorerReport(
        objective=request.scoring.objective,
        score=score,
        raw_score=score,
        telemetry=_solution_telemetry(solution),
        time_seconds=float(getattr(solution, "score_time_s", 0.0) or 0.0),
        capabilities=ScorerCapabilityReport(lanes=()),
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
