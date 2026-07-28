from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from rune_decrypter_prime.core.types import Device, Direction
from rune_decrypter_prime.core.types import SolverName
from rune_decrypter_prime.api.pipeline import execute_run
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.api.logging_utils import _route_logging_input
from rune_decrypter_prime.api.run_spec import RunSpec
from rune_decrypter_prime.api.run_result import RunResult
from rune_decrypter_prime.api.run_spec_routing import (
    materialize_runspec_problem_input,
    reject_runspec_mixed_inputs,
    route_runspec_logging,
)
from rune_decrypter_prime.api.solver_report import build_solver_report
from rune_decrypter_prime.api.stop_reason_contract import stop_reason_details_from_solution
from rune_decrypter_prime.api.normalize import (
    normalize_ciphertext,
    to_indices,
    _assert_core_ready,
    normalize_device,
    normalize_optimizer_spec,
    normalize_encoding_dir,
    normalize_scorer_params,
    normalize_text_permutation,
)
from rune_decrypter_prime.api._resolve import resolve_scorer_aliases
from rune_decrypter_prime.core.config import ScoringConfig, SolverConfig, InterruptorConfig, LoggingConfig
from rune_decrypter_prime.core.config import logging_config as logging_state
from rune_decrypter_prime.api.solver_report_export import write_solver_report_json
from rune_decrypter_prime.api.run_artifact_manifest import (
    write_run_artifacts_manifest as write_run_artifacts_manifest_file,
)
from rune_decrypter_prime.api.two_period_cribs import (
    is_two_period_cribs_solver,
    normalize_two_period_cribs_request,
)


_UNSET = object()


class RunAPI:
    """
    High-level entrypoint for the decrypter.  This class owns the full solve
    pipeline: it normalises user inputs, constructs the cipher and solver
    configuration, seeds the main RNG, and delegates to the execution
    pipeline.  This replaces the legacy ``run.solve`` function; callers
    should prefer :meth:`RunAPI.run` for clarity.
    """

    @classmethod
    def run(
        cls,
        text: Union[str, np.ndarray, List[int], Tuple[np.ndarray, Sequence[Sequence[int]]], object] = _UNSET,
        *,
        spec: RunSpec | object = _UNSET,
        cipher: CipherSpec | object = _UNSET,
        key: Union[KeySpec, Tuple[KeySpec, KeySpec], object] = _UNSET,
        solver: SolverSpec | object = _UNSET,
        device: Optional[Union[str, Device]] | object = _UNSET,
        scorer: str | object = _UNSET,
        scorer_params: Optional[Dict[str, Any]] | object = _UNSET,
        logging: Optional[Union[Dict[str, Any], LoggingConfig]] | object = _UNSET,
        wli_data: Optional[Sequence[Sequence[int]]] | object = _UNSET,
        force_no_wli: Optional[bool] | object = _UNSET,
        initial_keys: Optional[List[List[int]]] | object = _UNSET,
        telemetry_on: bool | object = _UNSET,
        encoding_dir: Optional[Union[str, Direction]] | object = _UNSET,
        initial_text_permutation_indices: Optional[Sequence[int]] | object = _UNSET,
        interruptors: Optional[InterruptorConfig | Dict[str, Any]] | object = _UNSET,
        interruptors_exact: Optional[Sequence[int]] | object = _UNSET,
        interruptors_pool: Optional[Sequence[int]] | object = _UNSET,
        interruptors_max: Optional[int] | object = _UNSET,
        return_solver_report: bool = False,
    ):
        """
        Run a single decrypt attempt over the given ciphertext.

        This method accepts the plaintext/ciphertext in ``text``, along with a
        chosen cipher specification (``cipher``), key plan (``key``), and
        optimiser specification (``solver``).  Additional optional parameters
        configure the device, scoring implementation, logging, word-level
        segmentation (WLI), a pre-seeded key pool, the telemetry flag, the
        text-encoding direction, and an optional input text permutation.

        The method normalises all inputs (e.g. strings to enums, casing),
        applies WLI inference if not provided, resolves scorer aliases and
        parameters, and builds a solver configuration object.  It then
        delegates to :func:`~rune_decrypter_prime.api.pipeline.execute_run`,
        which performs the actual decryption and returns a structured
        solution.
        """
        if type(return_solver_report) is not bool:
            raise TypeError("return_solver_report must be a bool")

        if spec is not _UNSET:
            if not isinstance(spec, RunSpec):
                raise TypeError("spec must be a RunSpec")
            reject_runspec_mixed_inputs(
                {
                    "text": text,
                    "cipher": cipher,
                    "key": key,
                    "solver": solver,
                    "device": device,
                    "scorer": scorer,
                    "scorer_params": scorer_params,
                    "wli_data": wli_data,
                    "force_no_wli": force_no_wli,
                    "initial_keys": initial_keys,
                    "telemetry_on": telemetry_on,
                    "encoding_dir": encoding_dir,
                    "initial_text_permutation_indices": initial_text_permutation_indices,
                    "interruptors": interruptors,
                    "interruptors_exact": interruptors_exact,
                    "interruptors_pool": interruptors_pool,
                    "interruptors_max": interruptors_max,
                },
                unset=_UNSET,
            )
            materialized = materialize_runspec_problem_input(spec)
            if is_two_period_cribs_solver(spec.solver):
                from rune_decrypter_prime.api.run_spec import RawTextInput
                if isinstance(spec.problem_input, RawTextInput):
                    _validate_rune_only_text(spec.problem_input.text)
            logging_route = route_runspec_logging(
                spec,
                None if logging is _UNSET else logging,
            )
            return _run_normalized(
                ciphertext=materialized.ciphertext,
                wli=materialized.wli,
                cipher=spec.cipher,
                key=spec.key,
                solver=spec.solver,
                device=spec.device,
                scorer=spec.scorer,
                scorer_params=dict(spec.scorer_params),
                logging_config=logging_route.config,
                logging_runtime=logging_route.runtime_controls,
                initialize_logging=logging_route.initialize_output,
                telemetry_on=spec.telemetry_on,
                encoding_dir=spec.encoding_dir,
                initial_keys=None,
                initial_text_permutation_indices=None,
                interruptors=None,
                interruptors_exact=None,
                interruptors_pool=None,
                interruptors_max=None,
                return_solver_report=return_solver_report,
            )

        if text is _UNSET:
            raise TypeError("RunAPI.run() missing required argument: 'text'")
        if cipher is _UNSET:
            raise TypeError("RunAPI.run() missing required keyword-only argument: 'cipher'")
        if key is _UNSET:
            raise TypeError("RunAPI.run() missing required keyword-only argument: 'key'")
        if solver is _UNSET:
            raise TypeError("RunAPI.run() missing required keyword-only argument: 'solver'")
        if is_two_period_cribs_solver(solver) and isinstance(text, str):
            _validate_rune_only_text(text)

        device = Device.CPU if device is _UNSET else device
        scorer = "rune" if scorer is _UNSET else scorer
        scorer_params = None if scorer_params is _UNSET else scorer_params
        logging = None if logging is _UNSET else logging
        wli_data = None if wli_data is _UNSET else wli_data
        force_no_wli = None if force_no_wli is _UNSET else force_no_wli
        initial_keys = None if initial_keys is _UNSET else initial_keys
        telemetry_on = True if telemetry_on is _UNSET else telemetry_on
        encoding_dir = Direction.RTL if encoding_dir is _UNSET else encoding_dir
        initial_text_permutation_indices = (
            None if initial_text_permutation_indices is _UNSET else initial_text_permutation_indices
        )
        interruptors = None if interruptors is _UNSET else interruptors
        interruptors_exact = None if interruptors_exact is _UNSET else interruptors_exact
        interruptors_pool = None if interruptors_pool is _UNSET else interruptors_pool
        interruptors_max = None if interruptors_max is _UNSET else interruptors_max

        # Normalise device and encoding direction
        device = normalize_device(device)
        encoding_dir = normalize_encoding_dir(encoding_dir)

        # Normalise ciphertext and optional WLI data
        if force_no_wli:
            ct = to_indices(text)
            wli = None
        else:
            ct, wli = normalize_ciphertext(text, wli_data)
        _assert_core_ready(ct, wli)
        if initial_text_permutation_indices is not None:
            initial_text_permutation_indices = normalize_text_permutation(
                initial_text_permutation_indices,
                int(ct.size),
            )

        logging_route = _route_logging_input(logging)

        return _run_normalized(
            ciphertext=ct,
            wli=wli,
            cipher=cipher,
            key=key,
            solver=solver,
            scorer=scorer,
            scorer_params=scorer_params,
            logging_config=logging_route.config,
            logging_runtime=logging_route.runtime_controls,
            initialize_logging=logging_route.initialize_output,
            telemetry_on=telemetry_on,
            device=device,
            encoding_dir=encoding_dir,
            initial_keys=initial_keys,
            initial_text_permutation_indices=initial_text_permutation_indices,
            interruptors=interruptors,
            interruptors_exact=interruptors_exact,
            interruptors_pool=interruptors_pool,
            interruptors_max=interruptors_max,
            return_solver_report=return_solver_report,
        )

    # Backwards compatibility: ``solve`` maps to ``run`` for existing code
    solve = run


def _run_normalized(
    *,
    ciphertext: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    cipher: CipherSpec,
    key: Union[KeySpec, Tuple[KeySpec, KeySpec]],
    solver: SolverSpec,
    device: Device,
    scorer: str,
    scorer_params: Dict[str, Any],
    logging_config: Optional[LoggingConfig],
    logging_runtime: Dict[str, Any],
    initialize_logging: bool,
    telemetry_on: bool,
    encoding_dir: Direction,
    initial_keys: Optional[List[List[int]]],
    initial_text_permutation_indices: Optional[Sequence[int]],
    interruptors: Optional[InterruptorConfig | Dict[str, Any]],
    interruptors_exact: Optional[Sequence[int]],
    interruptors_pool: Optional[Sequence[int]],
    interruptors_max: Optional[int],
    return_solver_report: bool,
):
    if is_two_period_cribs_solver(solver):
        request = normalize_two_period_cribs_request(solver)
        _validate_two_period_run_options(
            wli=wli,
            cipher=cipher,
            key=key,
            device=device,
            scorer=scorer,
            scorer_params=scorer_params,
            initial_keys=initial_keys,
            initial_text_permutation_indices=initial_text_permutation_indices,
            interruptors=interruptors,
            interruptors_exact=interruptors_exact,
            interruptors_pool=interruptors_pool,
            interruptors_max=interruptors_max,
        )
        if initialize_logging and logging_config is not None:
            from rune_decrypter_prime.core.config.logging_config import init_logging
            init_logging(logging_config)
        from rune_decrypter_prime.solvers.two_period_cribs import run_two_period_stages
        solution = run_two_period_stages(
            ciphertext=ciphertext,
            wli=wli,
            cipher=cipher,
            key=key,
            request=request,
            device=device,
            direction=encoding_dir,
            telemetry_on=telemetry_on,
        )
        opt_name = "two_period_cribs"
        opt = request.normalized_params()
        special_route = True
    else:
        special_route = False
        scorer_params = normalize_scorer_params(resolve_scorer_aliases(scorer_params or {}))
        scoring_cfg = ScoringConfig(**scorer_params)
        scoring_cfg.encoding_dir = encoding_dir

        opt = normalize_optimizer_spec({"name": solver.name, **solver.params})
        opt_name = opt.pop("name")
        solver_cfg = SolverConfig(name=opt_name, params=opt, seed=solver.seed)

        solution = execute_run(
            ciphertext=ciphertext,
            wli=wli,
            cipher=cipher,
            key=key,
            solver=solver_cfg,
            scoring=scoring_cfg,
            scorer_name=scorer,
            logging_config=logging_config,
            logging_runtime=logging_runtime,
            initialize_logging=initialize_logging,
            telemetry_on=telemetry_on,
            device=device,
            encoding_dir=encoding_dir,
            initial_keys=initial_keys,
            initial_text_permutation_indices=initial_text_permutation_indices,
            interruptors=interruptors,
            interruptors_exact=interruptors_exact,
            interruptors_pool=interruptors_pool,
            interruptors_max=interruptors_max,
        )
    write_solver_report = (
        logging_config is not None
        and bool(getattr(logging_config, "write_solver_report", False))
    )
    write_run_artifacts_manifest_requested = (
        logging_config is not None
        and bool(getattr(logging_config, "write_run_artifacts_manifest", False))
    )
    if not return_solver_report and not write_solver_report and not write_run_artifacts_manifest_requested:
        return solution

    known_key_fastpath = isinstance(key, KeySpec) and key.plan in ("otp", "const")
    report = None
    if return_solver_report or write_solver_report:
        if special_route:
            report_solver_name = "two_period_cribs"
            effective_seed = request.effective_seed
            normalized_params = opt
            details = {"execution_route": "two_period_cribs"}
        elif known_key_fastpath:
            report_solver_name = "beam"
            effective_seed = None
            normalized_params = {"beam_width": 1}
            details = {"execution_route": "known_key_fastpath"}
        else:
            report_solver_name = _solver_name_to_report_string(opt_name)
            effective_seed = solver.seed if solver.seed is not None else 0
            normalized_params = opt
            details = {}
        details.update(_solver_report_details_from_solution(solution))

        report = build_solver_report(
            solver_name=report_solver_name,
            requested_seed=solver.seed,
            effective_seed=effective_seed,
            normalized_params=normalized_params,
            stop_reason=getattr(solution, "stop_reason", None),
            best_score=getattr(solution, "score", None),
            best_key=getattr(solution, "key", None),
            step=getattr(solution, "step", None),
            evals=getattr(solution, "evals", None),
            tokens_processed=getattr(solution, "tokens_processed", None),
            wall_time_s=getattr(solution, "wall_time_s", None),
            decrypt_time_s=getattr(solution, "decrypt_time_s", None),
            score_time_s=getattr(solution, "score_time_s", None),
            details=details,
        )
    if write_solver_report:
        if not initialize_logging:
            raise RuntimeError("write_solver_report requires initialized logging")
        assert report is not None
        write_solver_report_json(report, run_dir=logging_state.get_run_dir())
    if write_run_artifacts_manifest_requested:
        if not initialize_logging:
            raise RuntimeError("write_run_artifacts_manifest requires initialized logging")
        write_run_artifacts_manifest_file(
            run_dir=logging_state.get_run_dir(),
            include_solver_report=write_solver_report,
        )
    if not return_solver_report:
        return solution
    assert report is not None
    return RunResult(solution=solution, solver_report=report)


def _solver_report_details_from_solution(solution) -> dict[str, Any]:
    details = stop_reason_details_from_solution(solution)
    meta = getattr(solution, "meta", None)
    if not isinstance(meta, dict):
        return details
    scorer_lanes = meta.get("scorer_lanes")
    if scorer_lanes is not None:
        details["scorer_lanes"] = scorer_lanes
    two_period_solve = meta.get("two_period_solve")
    if two_period_solve is not None:
        details["two_period_solve"] = two_period_solve
    return details


def _validate_rune_only_text(text: str) -> None:
    from rune_decrypter_prime.utils.runeglish import Runeglish

    unsupported = sorted({char for char in text if not char.isspace() and char not in Runeglish.rune2pos})
    if unsupported:
        raise ValueError("two_period_cribs requires rune ciphertext; Latin or mixed input is unsupported")


def _validate_two_period_run_options(
    *,
    wli,
    cipher,
    key,
    device,
    scorer,
    scorer_params,
    initial_keys,
    initial_text_permutation_indices,
    interruptors,
    interruptors_exact,
    interruptors_pool,
    interruptors_max,
) -> None:
    if wli is None:
        raise ValueError("two_period_cribs requires WLI data")
    if device is not Device.CPU:
        raise ValueError("two_period_cribs currently supports CPU only")
    if str(scorer).strip().lower() != "rune":
        raise ValueError("two_period_cribs supports only the rune scorer")
    if scorer_params:
        raise ValueError("two_period_cribs does not accept scorer_params")
    if initial_keys is not None:
        raise ValueError("two_period_cribs does not accept initial_keys")
    if initial_text_permutation_indices is not None:
        raise ValueError("two_period_cribs does not accept text permutation")
    if any(
        value is not None
        for value in (interruptors, interruptors_exact, interruptors_pool, interruptors_max)
    ):
        raise ValueError(
            "two_period_cribs interruptor compatibility is not yet proven; "
            "exact and pool interruptor options are unsupported"
        )
    if not isinstance(cipher, CipherSpec) or not isinstance(key, KeySpec):
        raise TypeError("two_period_cribs requires canonical CipherSpec and KeySpec values")


def _solver_name_to_report_string(value) -> str:
    if isinstance(value, SolverName):
        return value.value
    return str(value)


def run(*args, **kwargs):
    """
    Convenience wrapper around :meth:`RunAPI.run`.  Accepts the same
    parameters as :meth:`RunAPI.run` and returns its result.  This free
    function is provided for ease of use so that callers can write
    ``from rune_decrypter_prime.api.run import run`` and call ``run(...)``
    directly.
    """
    return RunAPI.run(*args, **kwargs)

# Backwards compatibility alias: map legacy ``solve`` to the new ``run``
solve = run
