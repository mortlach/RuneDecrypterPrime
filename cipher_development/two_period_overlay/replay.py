from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np

from cipher_development.shared.replay import CandidateReplayContext
from cipher_development.shared.replay_binding import load_bound_replay_source
from cipher_development.shared.replay_evidence import (
    ReplayEvaluation,
    ReplayMode,
    write_candidate_replay,
)
from cipher_development.shared.replay_execution import replay_candidate_batch
from cipher_development.shared.replay_provenance import (
    build_evaluator_provenance,
    validate_evaluator_provenance,
)
from cipher_development.two_period_overlay.config import (
    DECISION_SCORE,
    SCORING_CONTRACT,
    TARGET_BENCHMARK,
    benchmark_for,
)
from cipher_development.two_period_overlay.keyspace import expand

SOURCE_RUN_ID = ""
SOURCE_BINDING_RELPATH = Path("artifacts/archive_handoff_binding.json")
REPLAY_MODE = ReplayMode.VERIFY
DECISION_SCORE_NAME = DECISION_SCORE
REPEAT_COUNT = 2
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12


def _portable_json(value):
    if isinstance(value, Mapping):
        return {str(key): _portable_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable_json(item) for item in value]
    return value


def make_replay_context(
    search_case: Any,
    *,
    run_id: str,
    configuration_hash: str,
    evaluator_provenance: Mapping[str, Any],
) -> CandidateReplayContext:
    benchmark = getattr(search_case, "benchmark", TARGET_BENCHMARK)
    return CandidateReplayContext.create(
        campaign_id="two_period_overlay",
        run_id=run_id,
        configuration_hash=configuration_hash,
        evaluator_id="two_period_overlay_wli_v3",
        payload={
            "benchmark_id": benchmark.benchmark_id,
            "benchmark": benchmark.to_json_dict(),
            "ciphertext": np.asarray(search_case.ciphertext, dtype=np.uint8).tolist(),
            "wli": [list(pair) for pair in search_case.wli],
            "crib": np.asarray(search_case.crib, dtype=np.uint8).tolist(),
            "particular": np.asarray(search_case.particular, dtype=np.uint8).tolist(),
            "basis": np.asarray(search_case.basis, dtype=np.uint8).tolist(),
            "free_columns": list(search_case.free_columns),
            "decision_score": DECISION_SCORE,
            "scoring": _portable_json(SCORING_CONTRACT),
            "evaluator_provenance": _portable_json(evaluator_provenance),
        },
    )


def _context_benchmark(context: CandidateReplayContext):
    payload = context.payload
    benchmark_id = str(payload.get("benchmark_id"))
    if "benchmark" not in payload:
        # WP5 unit fixtures used the pre-ladder target identifier. This is a
        # replay-context compatibility boundary, not support for the discarded
        # exploratory result schema.
        if benchmark_id != "alice_308_p13_p17":
            raise ValueError("legacy replay context does not identify the P13/P17 target")
        if payload.get("gauge") != "B[0]=0":
            raise ValueError("legacy replay context does not establish B[0] = 0")
        if (int(payload.get("period_a", -1)), int(payload.get("period_b", -1))) != (
            TARGET_BENCHMARK.period_a,
            TARGET_BENCHMARK.period_b,
        ):
            raise ValueError("legacy replay periods do not match the P13/P17 target")
        return TARGET_BENCHMARK
    benchmark = benchmark_for(benchmark_id)
    if _portable_json(payload.get("benchmark")) != benchmark.to_json_dict():
        raise ValueError("replay benchmark contract does not match the registered ladder")
    return benchmark


def validate_candidate_payload(candidate, context: CandidateReplayContext) -> np.ndarray:
    payload = context.payload
    benchmark = _context_benchmark(context)
    particular = np.asarray(payload["particular"], dtype=np.uint8)
    basis = np.asarray(payload["basis"], dtype=np.uint8)
    variables = np.asarray(candidate.payload["variables"], dtype=np.uint8)
    stored_key = np.asarray(candidate.payload["expanded_key"], dtype=np.uint8)
    strict_ladder_context = "benchmark" in payload
    candidate_benchmark_id = candidate.payload.get("benchmark_id")
    if strict_ladder_context and candidate_benchmark_id != benchmark.benchmark_id:
        raise ValueError("candidate payload belongs to a different benchmark")
    if particular.shape != (benchmark.key_length,):
        raise ValueError("replay particular solution has the wrong length")
    expected_free_dimension = (
        benchmark.expected_free_dimension if strict_ladder_context else basis.shape[1]
    )
    if basis.shape != (benchmark.key_length, expected_free_dimension):
        raise ValueError("replay basis has the wrong shape")
    if variables.shape != (expected_free_dimension,):
        raise ValueError("stored affine variables have the wrong length")
    if stored_key.shape != (benchmark.key_length,):
        raise ValueError("stored expanded key has the wrong length")
    identity = _portable_json(candidate.identity)
    if identity != {"expanded_key": stored_key.astype(int).tolist()}:
        raise ValueError("candidate identity and payload expanded key disagree")
    rebuilt = expand(variables, particular, basis, benchmark)
    if not np.array_equal(rebuilt, stored_key):
        raise ValueError("candidate variables do not reproduce the stored expanded key")
    if int(stored_key[benchmark.gauge_key_index]) != benchmark.gauge_value:
        raise ValueError("candidate violates the B[0] = 0 gauge")
    return stored_key


def build_replay_evaluator(context: CandidateReplayContext):
    if context.campaign_id != "two_period_overlay":
        raise ValueError("replay context belongs to a different campaign")
    payload = context.payload
    benchmark = _context_benchmark(context)
    from rune_decrypter_prime.api import by_name, cipher_instance
    from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
    from rune_decrypter_prime.core.config import HardCribConfig, ScoringConfig
    from rune_decrypter_prime.core.engine.builders import build_scorer
    from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
    from rune_decrypter_prime.core.types import Device, Direction

    ciphertext = np.asarray(payload["ciphertext"], dtype=np.uint8)
    wli = tuple((int(a), int(b)) for a, b in payload["wli"])
    crib = np.asarray(payload["crib"], dtype=np.uint8)
    if len(ciphertext) != benchmark.text_length or len(wli) != benchmark.text_length:
        raise ValueError("replay ciphertext, WLI and benchmark lengths differ")
    if len(crib) != len(benchmark.crib_word):
        raise ValueError("replay crib length does not match the benchmark")
    scoring_contract = dict(payload["scoring"])
    spec, key_spec = by_name.cipher_with_key(
        "two_period_vigenere",
        period_a=benchmark.period_a,
        period_b=benchmark.period_b,
        schedule=benchmark.schedule,
        alphabet_size=benchmark.alphabet_size,
        default_key=True,
    )
    cipher = cipher_instance(spec)
    direction = Direction(str(scoring_contract["encoding_direction"]))
    cipher_cfg = build_cipher_config(
        cipher=spec,
        key=key_spec,
        ciphertext=ciphertext,
        wli=[list(pair) for pair in wli],
        device=Device.CPU,
        encoding_dir=direction,
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )
    hard_crib = HardCribConfig(
        enabled=bool(scoring_contract["hard_crib"]),
        fixed_chars={
            benchmark.crib_start + index: [int(value)]
            for index, value in enumerate(crib)
        },
    )
    scoring_values = dict(scoring_contract)
    scoring_values["encoding_dir"] = direction
    scoring_values["hard_crib"] = hard_crib
    scoring_values.pop("encoding_direction", None)
    scoring = ScoringConfig(**scoring_values)
    problem = DecryptionProblem(
        cipher=cipher,
        scorer=build_scorer(cipher_cfg, scoring),
        c_cfg=cipher_cfg,
        s_cfg=scoring,
        enable_telemetry=False,
    )

    def evaluator(candidate, replay_context):
        stored_key = validate_candidate_payload(candidate, replay_context)
        score = float(np.asarray(problem.evaluate_keys(stored_key[None, :]))[0])
        return ReplayEvaluation(
            scores={DECISION_SCORE: score},
            stable_metrics={
                "candidate_id": candidate.candidate_id,
                "benchmark_id": benchmark.benchmark_id,
                "payload_valid": True,
                "gauge_valid": True,
            },
        )

    return evaluator


def _resolve_source_run(repo_root: Path, run_id: str) -> Path:
    if not run_id or run_id in {".", ".."} or "/" in run_id or "\\" in run_id:
        raise ValueError("source run ID must be one directory name")
    campaign_root = (repo_root / "output/cipher_development/two_period_overlay").resolve()
    run_dir = (campaign_root / run_id).resolve()
    if campaign_root not in run_dir.parents:
        raise ValueError("source run ID escaped the campaign output root")
    return run_dir


def run_saved_replay(repo_root: Path) -> Path:
    if not SOURCE_RUN_ID:
        raise ValueError("configure SOURCE_RUN_ID before running replay")
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    source_run = _resolve_source_run(repo_root, SOURCE_RUN_ID)
    _, _, binding, context, batch = load_bound_replay_source(
        source_run,
        SOURCE_BINDING_RELPATH,
        expected_campaign_id="two_period_overlay",
        expected_run_id=SOURCE_RUN_ID,
    )
    actual_provenance = build_evaluator_provenance(
        repo_root=repo_root,
        evaluator_source=Path(__file__),
        scoring_contracts=(dict(context.payload["scoring"]),),
        require_assets=True,
    )
    validate_evaluator_provenance(
        context.payload["evaluator_provenance"], actual_provenance
    )
    evaluator = build_replay_evaluator(context)
    evidence = replay_candidate_batch(
        batch,
        context,
        binding,
        evaluator=evaluator,
        mode=REPLAY_MODE,
        decision_score=DECISION_SCORE_NAME,
        higher_is_better=True,
        evaluator_configuration={
            "campaign": "two_period_overlay",
            "binding_id": binding.binding_id,
            "context_id": context.context_id,
            "decision_score": DECISION_SCORE_NAME,
            "evaluator_provenance": actual_provenance,
        },
        repeat_count=REPEAT_COUNT,
        absolute_tolerance=ABSOLUTE_TOLERANCE,
        relative_tolerance=RELATIVE_TOLERANCE,
    )
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="candidate_replay_v1",
        benchmark_id=binding.benchmark_id,
        question="Can a bound candidate batch be rescored deterministically without discovery?",
        hypothesis="The bound candidate surface reproduces its scores and order.",
        alternative=(
            "The saved surface or evaluator provenance is insufficient to reproduce its "
            "recorded scores and order."
        ),
        decision_rule="Replay studies always refine; report reproducibility evidence only.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.NONE,
        mechanisms=(FailureMechanism.EVIDENCE_REPRODUCIBILITY,),
        lesson_ids=("CSL-001", "CSL-002", "CSL-004", "CSL-005", "CSL-007"),
    )
    with ExperimentRun(
        spec=spec,
        configuration={
            "source_run_id": SOURCE_RUN_ID,
            "source_binding_id": binding.binding_id,
            "source_batch_id": batch.batch_id,
            "source_context_id": context.context_id,
            "mode": str(REPLAY_MODE),
            "decision_score": DECISION_SCORE_NAME,
            "repeat_count": REPEAT_COUNT,
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE,
        },
        repo_root=repo_root,
    ) as run:
        assert run.run_dir is not None
        artifact = run.run_dir / "artifacts/candidate_replay.json"
        write_candidate_replay(artifact, evidence)
        return run.finish(
            decision=ExperimentDecision.REFINE,
            stop_reason="done",
            result_summary={
                "source_run_id": SOURCE_RUN_ID,
                "source_binding_id": binding.binding_id,
                "source_batch_id": batch.batch_id,
                "source_context_id": context.context_id,
                "replay_id": evidence.replay_id,
                "mode": evidence.mode.value,
                "candidate_count": len(evidence.candidate_ids),
                "decision_score": evidence.decision_score,
                "deterministic": evidence.deterministic,
                "stored_scores_verified": evidence.stored_scores_verified,
                "ranking": list(evidence.ranking),
                "artifact": "artifacts/candidate_replay.json",
            },
        )


def main() -> int:
    run_saved_replay(Path(__file__).resolve().parents[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
