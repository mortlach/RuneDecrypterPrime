from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


RUN_LABEL = "scorer_component_inventory_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_component_inventory_v1"
)
GITHUB_PARENT_REL = ".."

REQUIRED_FIELDS = (
    "component_id",
    "component_name",
    "source_project",
    "source_path",
    "component_type",
    "input_type",
    "output_type",
    "needs_plaintext",
    "needs_runes",
    "needs_spaces",
    "needs_word_boundaries",
    "uses_truth_or_oracle",
    "runtime_safe",
    "inner_loop_safe",
    "reranker_safe",
    "final_judge_safe",
    "expected_text_length",
    "known_failure_mode_addressed",
    "known_failure_mode_created",
    "test_file_paths",
    "has_tests",
    "evidence_paths",
    "reuse_recommendation",
    "notes",
    "deterministic_outputs",
)

ALLOWED_COMPONENT_TYPES = frozenset(
    {
        "char_ngram",
        "word_ngram",
        "hamming",
        "span_hamming",
        "ecdf_calibrator",
        "combined_scorer",
        "scorer_report",
        "corpus_builder",
        "normaliser",
        "reranker",
        "diagnostic",
    }
)

ALLOWED_REUSE_RECOMMENDATIONS = frozenset(
    {
        "reuse_directly",
        "reuse_as_report_feature",
        "reuse_after_hardening",
        "design_reference_only",
        "discard",
        "unknown_pending_review",
    }
)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
GITHUB_PARENT = (REPO_ROOT / GITHUB_PARENT_REL).resolve()
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


BASE_COMPONENTS: tuple[dict[str, Any], ...] = (
    {
        "component_id": "rdp_numpy_rune_scorer",
        "component_name": "RuneScorer NumPy language-model objective",
        "source_project": "current_rdp",
        "source_path": "src/rune_decrypter_prime/scoring/rune_scorer.py",
        "component_type": "combined_scorer",
        "input_type": "rune plaintext plus optional WLI windows",
        "output_type": "float score plus telemetry",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 1,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 1,
        "inner_loop_safe": 1,
        "reranker_safe": 1,
        "final_judge_safe": 1,
        "expected_text_length": "short_to_long",
        "known_failure_mode_addressed": "char/WLI n-gram language-model ranking and ECDF calibration",
        "known_failure_mode_created": "can over-rank local n-gram smoothness and hide bad windows in aggregate objectives",
        "test_file_paths": "tests/scoring/test_scorer_report_builder.py;tests/scoring/test_score_parity_numpy.py",
        "evidence_paths": "src/rune_decrypter_prime/scoring/rune_scorer.py",
        "reuse_recommendation": "reuse_directly",
        "notes": "Primary current RDP scorer path; inspect component telemetry before changing weights.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "rdp_torch_rune_scorer",
        "component_name": "TorchRuneScorer batch language-model objective",
        "source_project": "current_rdp",
        "source_path": "src/rune_decrypter_prime/scoring/torch_rune_scorer.py",
        "component_type": "combined_scorer",
        "input_type": "batched rune plaintext plus optional WLI windows",
        "output_type": "float score array plus telemetry",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 1,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 1,
        "inner_loop_safe": 1,
        "reranker_safe": 1,
        "final_judge_safe": 1,
        "expected_text_length": "short_to_long",
        "known_failure_mode_addressed": "batched parity path for current language-model score",
        "known_failure_mode_created": "inherits current objective weighting and calibration blind spots",
        "test_file_paths": "tests/scoring/test_score_parity_torch.py;tests/scoring/test_unified_scorer_contract_torch.py",
        "evidence_paths": "src/rune_decrypter_prime/scoring/torch_rune_scorer.py",
        "reuse_recommendation": "reuse_directly",
        "notes": "Useful for report batches if parity tests stay green.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "rdp_lmprime_runtime",
        "component_name": "LanguageModelPrime runtime and ECDF cache",
        "source_project": "current_rdp",
        "source_path": "src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py",
        "component_type": "char_ngram",
        "input_type": "windowed rune and WLI tokens",
        "output_type": "raw logp/stat values and percentile/energy transforms",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 1,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 1,
        "inner_loop_safe": 1,
        "reranker_safe": 1,
        "final_judge_safe": 1,
        "expected_text_length": "windowed_10_ngram",
        "known_failure_mode_addressed": "char and WLI n-gram scoring with ECDF-normalized objective support",
        "known_failure_mode_created": "local n-gram overfit if used without span or worst-window checks",
        "test_file_paths": "tests/scoring/test_scorer_pct_edges_and_clamps.py;tests/scoring/test_scorer_kaeding_style_avg_logp.py",
        "evidence_paths": "src/rune_decrypter_prime/scoring/language_model/language_model_prime_runtime.py",
        "reuse_recommendation": "reuse_directly",
        "notes": "Core scoring primitive for current no-WLI score path.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "rdp_span_hamming_backend",
        "component_name": "SpanHammingBackend approximate dictionary span scorer",
        "source_project": "current_rdp",
        "source_path": "src/rune_decrypter_prime/scoring/span_hamming/backend.py",
        "component_type": "span_hamming",
        "input_type": "rune plaintext spans",
        "output_type": "span coverage and quality stats",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 0,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 1,
        "inner_loop_safe": 0,
        "reranker_safe": 1,
        "final_judge_safe": 1,
        "expected_text_length": "medium_to_long",
        "known_failure_mode_addressed": "missing word/span structure and bad local lexical islands",
        "known_failure_mode_created": "dictionary-span bias can reward plausible islands in globally wrong text",
        "test_file_paths": "tests/tools/benchmarks/span_hamming_nose/test_span_hamming_nose_suite.py",
        "evidence_paths": "src/rune_decrypter_prime/scoring/span_hamming/backend.py",
        "reuse_recommendation": "reuse_as_report_feature",
        "notes": "Best initial use is report-only component evidence for Stage 2/3.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "rdp_hamming_backend",
        "component_name": "HammingBackend wordlist Hamming scorer",
        "source_project": "current_rdp",
        "source_path": "src/rune_decrypter_prime/scoring/hamming/backend.py",
        "component_type": "hamming",
        "input_type": "rune plaintext plus WLI word positions",
        "output_type": "minimum Hamming distance stats",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 1,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 1,
        "inner_loop_safe": 1,
        "reranker_safe": 1,
        "final_judge_safe": 0,
        "expected_text_length": "short_to_long",
        "known_failure_mode_addressed": "wordlist-proximity evidence for WLI-aware plaintext",
        "known_failure_mode_created": "requires built extension and wordlist policy; can over-favor dictionary fragments",
        "test_file_paths": "tests/scoring/test_scorer_smoothing_effect.py",
        "evidence_paths": "src/rune_decrypter_prime/scoring/hamming/backend.py",
        "reuse_recommendation": "reuse_after_hardening",
        "notes": "Already integrated as optional scorer signal, but extension availability must be explicit.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "rdp_word_ngram_judge",
        "component_name": "Rune token word n-gram judge",
        "source_project": "current_rdp",
        "source_path": "src/rune_decrypter_prime/scoring/word_ngrams/scorer.py",
        "component_type": "word_ngram",
        "input_type": "segmented rune-token words",
        "output_type": "cross-entropy, backoff, miss-rate, and trust stats",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 1,
        "needs_word_boundaries": 1,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 1,
        "inner_loop_safe": 0,
        "reranker_safe": 1,
        "final_judge_safe": 1,
        "expected_text_length": "medium_to_long",
        "known_failure_mode_addressed": "missing word-order evidence in char n-gram score",
        "known_failure_mode_created": "inactive or noisy on text without reliable word segmentation",
        "test_file_paths": "tests/tools/test_no_wli_iteration_runtime_word_ngram_sidechannel.py",
        "evidence_paths": "src/rune_decrypter_prime/scoring/word_ngrams/scorer.py;tools/benchmarks/periodic_sub_trans/no_wli/word_ngram_report.py",
        "reuse_recommendation": "reuse_as_report_feature",
        "notes": "Stage 2 should record whether word-ngram report fields are present before considering rerank use.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "rdp_scorer_report_builder",
        "component_name": "Scorer report builder and JSON sidecar",
        "source_project": "current_rdp",
        "source_path": "src/rune_decrypter_prime/scoring/scorer_report_builder.py",
        "component_type": "scorer_report",
        "input_type": "scorer object, score, telemetry, extra metrics",
        "output_type": "JSON-safe scorer report",
        "needs_plaintext": 0,
        "needs_runes": 0,
        "needs_spaces": 0,
        "needs_word_boundaries": 0,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 1,
        "inner_loop_safe": 0,
        "reranker_safe": 0,
        "final_judge_safe": 0,
        "expected_text_length": "not_applicable",
        "known_failure_mode_addressed": "missing component-level scorer evidence",
        "known_failure_mode_created": "none directly; report-only",
        "test_file_paths": "tests/scoring/test_scorer_report_builder.py;tests/tools/test_benchmark_scorer_report_sidecar_smoke.py",
        "evidence_paths": "src/rune_decrypter_prime/scoring/scorer_report_builder.py;src/rune_decrypter_prime/scoring/scorer_report.py",
        "reuse_recommendation": "reuse_directly",
        "notes": "Useful scaffolding for Stage 2 missing-component-score audit and later Stage 3 reports.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "no_wli_phasec_truth_gap_dataset",
        "component_name": "Phase-C truth-gap dataset exporter",
        "source_project": "current_rdp",
        "source_path": "tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_gap_dataset.py",
        "component_type": "diagnostic",
        "input_type": "retained final instance artifacts with truth reporting",
        "output_type": "truth-gap rows",
        "needs_plaintext": 0,
        "needs_runes": 0,
        "needs_spaces": 0,
        "needs_word_boundaries": 0,
        "uses_truth_or_oracle": 1,
        "runtime_safe": 0,
        "inner_loop_safe": 0,
        "reranker_safe": 0,
        "final_judge_safe": 0,
        "expected_text_length": "not_applicable",
        "known_failure_mode_addressed": "truth-positive present but under-scored diagnosis",
        "known_failure_mode_created": "truth leakage if reused as candidate feature",
        "test_file_paths": "tests/tools/test_no_wli_phasec_truth_gap_dataset.py",
        "evidence_paths": "tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_gap_dataset.py",
        "reuse_recommendation": "reuse_as_report_feature",
        "notes": "Evaluation-only source; must stay separated from candidate features.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "no_wli_truth_diagnostics",
        "component_name": "No-WLI truth diagnostics",
        "source_project": "current_rdp",
        "source_path": "tools/benchmarks/periodic_sub_trans/no_wli/truth_diagnostics.py",
        "component_type": "diagnostic",
        "input_type": "known true key/plaintext plus candidate rows",
        "output_type": "truth match and key-Hamming diagnostics",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 0,
        "uses_truth_or_oracle": 1,
        "runtime_safe": 0,
        "inner_loop_safe": 0,
        "reranker_safe": 0,
        "final_judge_safe": 0,
        "expected_text_length": "not_applicable",
        "known_failure_mode_addressed": "candidate availability versus mis-ranking separation",
        "known_failure_mode_created": "truth leakage if used as scorer input",
        "test_file_paths": "tests/tools/test_no_wli_phasec_slice_signal_analysis.py",
        "evidence_paths": "tools/benchmarks/periodic_sub_trans/no_wli/truth_diagnostics.py",
        "reuse_recommendation": "reuse_as_report_feature",
        "notes": "Evaluation-only diagnostic.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "external_language_model_prime",
        "component_name": "Historical LanguageModelPrime scorer and ECDF builder",
        "source_project": "external_language_model_prime",
        "source_path": "../language_model_prime/language_model_prime.py;../language_model_prime/buildcdf.py;../language_model_prime/lmprime_runtime.py",
        "component_type": "ecdf_calibrator",
        "input_type": "rune/WLI n-gram model windows and score files",
        "output_type": "score, random baseline, ECDF percentile, and energy data",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 1,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 0,
        "inner_loop_safe": 0,
        "reranker_safe": 1,
        "final_judge_safe": 1,
        "expected_text_length": "windowed_10_ngram",
        "known_failure_mode_addressed": "ECDF calibration and raw score interpretability",
        "known_failure_mode_created": "historical path and artifact layout differ from current RDP runtime",
        "test_file_paths": "",
        "evidence_paths": "../language_model_prime/buildcdf.py;../language_model_prime/edf_sanity_check.py;../language_model_prime/get_results_cdf.py",
        "reuse_recommendation": "design_reference_only",
        "notes": "External sibling source; review for calibration design and corpus build assumptions, do not integrate directly.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "external_runeglish_language_models",
        "component_name": "Historical Runeglish n-gram data and Project Runeberg inputs",
        "source_project": "external_runeglish_language_models",
        "source_path": "../runeglish_language_models/",
        "component_type": "corpus_builder",
        "input_type": "Project Runeberg/GNG text and n-gram count files",
        "output_type": "char/WLI n-gram count and transition CSVs",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 1,
        "needs_word_boundaries": 1,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 0,
        "inner_loop_safe": 0,
        "reranker_safe": 0,
        "final_judge_safe": 0,
        "expected_text_length": "corpus",
        "known_failure_mode_addressed": "corpus provenance and Project Runeberg calibration coverage",
        "known_failure_mode_created": "old data formats need provenance checks before reuse",
        "test_file_paths": "",
        "evidence_paths": "../runeglish_language_models/projectRuneberg_2022.zip;../runeglish_language_models/get_char_ngrams_from_2grams.py",
        "reuse_recommendation": "design_reference_only",
        "notes": "External source material for corpus/calibration review only.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "external_runeglish_score_tests",
        "component_name": "Historical Runeglish corruption/score tests",
        "source_project": "external_runeglish_score_tests",
        "source_path": "../runeglish_score_tests/",
        "component_type": "diagnostic",
        "input_type": "corruption ladder CSVs and score-test scripts",
        "output_type": "score-test logs and per-error-count rows",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 0,
        "uses_truth_or_oracle": 1,
        "runtime_safe": 0,
        "inner_loop_safe": 0,
        "reranker_safe": 0,
        "final_judge_safe": 0,
        "expected_text_length": "short",
        "known_failure_mode_addressed": "controlled corruption ladder and false-positive calibration",
        "known_failure_mode_created": "historical truth-labeled tests are evaluation-only",
        "test_file_paths": "",
        "evidence_paths": "../runeglish_score_tests/runeglish_tests.py;../runeglish_score_tests/len20_10errors_1.csv",
        "reuse_recommendation": "design_reference_only",
        "notes": "Candidate Stage 3 evaluation design reference after Stage 1/2 review.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "external_is_it_runeglish",
        "component_name": "Historical isItRuneglish log-probability score artifacts",
        "source_project": "external_isItRuneglish",
        "source_path": "../isItRuneglish/",
        "component_type": "char_ngram",
        "input_type": "rune text and n-gram log-probability tables",
        "output_type": "Runeglish score CSVs",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 0,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 0,
        "inner_loop_safe": 0,
        "reranker_safe": 1,
        "final_judge_safe": 0,
        "expected_text_length": "short_to_medium",
        "known_failure_mode_addressed": "older n-gram score thresholds and score distributions",
        "known_failure_mode_created": "old scoring scale is not directly compatible with current RDP objective",
        "test_file_paths": "",
        "evidence_paths": "../isItRuneglish/ngRB2LogProb.csv;../isItRuneglish/ngRB3LogProbA.csv",
        "reuse_recommendation": "design_reference_only",
        "notes": "External comparison material only.",
        "deterministic_outputs": 1,
    },
    {
        "component_id": "external_rune_decrypting_dev_ga_lm",
        "component_name": "Historical GA language-model scorer code",
        "source_project": "external_rune_decrypting_dev",
        "source_path": "../rune-decrypting-dev-/",
        "component_type": "char_ngram",
        "input_type": "rune text scored in GA loops",
        "output_type": "language-model fitness score",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 1,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 0,
        "inner_loop_safe": 0,
        "reranker_safe": 0,
        "final_judge_safe": 0,
        "expected_text_length": "short_to_medium",
        "known_failure_mode_addressed": "old inner-loop language model fitness choices",
        "known_failure_mode_created": "legacy code and data paths are not compatible with current RDP contracts",
        "test_file_paths": "",
        "evidence_paths": "../rune-decrypting-dev-/DEAP_GA_BISUB_LM2/language_model.py;../rune-decrypting-dev-/Basic_GeneticAlgo_Bi-gram_Sub/language_model.py",
        "reuse_recommendation": "design_reference_only",
        "notes": "Use only to understand historical scorer choices.",
        "deterministic_outputs": 1,
    },
)


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        try:
            return "../" + path.resolve().relative_to(GITHUB_PARENT).as_posix()
        except ValueError:
            return path.as_posix().replace("\\", "/")


def _path_exists(path_text: str) -> bool:
    text = str(path_text or "").strip()
    if not text:
        return False
    if text.startswith("../"):
        return (REPO_ROOT / text).resolve().exists()
    return (REPO_ROOT / text).exists()


def _split_paths(value: Any) -> list[str]:
    return [
        part.strip()
        for part in str(value or "").replace("\n", ";").split(";")
        if part.strip()
    ]


def _missing_paths(value: Any) -> list[str]:
    return [path for path in _split_paths(value) if not _path_exists(path)]


def _normalize_bool(value: Any) -> int:
    return int(1 if bool(value) else 0)


def build_inventory_rows(
    component_defs: Sequence[Mapping[str, Any]] = BASE_COMPONENTS,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in component_defs:
        row = {field: item.get(field, "") for field in REQUIRED_FIELDS}
        for field in (
            "needs_plaintext",
            "needs_runes",
            "needs_spaces",
            "needs_word_boundaries",
            "uses_truth_or_oracle",
            "runtime_safe",
            "inner_loop_safe",
            "reranker_safe",
            "final_judge_safe",
            "deterministic_outputs",
        ):
            row[field] = _normalize_bool(row.get(field))
        row["source_path_exists"] = int(
            any(_path_exists(path) for path in _split_paths(row.get("source_path")))
        )
        row["missing_test_file_paths"] = ";".join(_missing_paths(row.get("test_file_paths")))
        row["missing_evidence_paths"] = ";".join(_missing_paths(row.get("evidence_paths")))
        row["has_tests"] = int(
            bool(_split_paths(row.get("test_file_paths")))
            and not bool(row["missing_test_file_paths"])
        )
        if str(row["component_type"]) not in ALLOWED_COMPONENT_TYPES:
            raise ValueError(f"Unknown component_type: {row['component_type']}")
        if str(row["reuse_recommendation"]) not in ALLOWED_REUSE_RECOMMENDATIONS:
            raise ValueError(f"Unknown reuse_recommendation: {row['reuse_recommendation']}")
        if int(row["runtime_safe"]) and int(row["uses_truth_or_oracle"]):
            raise ValueError(f"runtime_safe component uses truth/oracle: {row['component_id']}")
        if int(row["inner_loop_safe"]) and not int(row["deterministic_outputs"]):
            raise ValueError(f"inner_loop_safe component is not deterministic: {row['component_id']}")
        rows.append(row)
    return rows


def summarize_inventory(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    row_list = [dict(row) for row in rows]

    def count_reuse(value: str) -> int:
        return sum(1 for row in row_list if str(row.get("reuse_recommendation")) == value)

    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "component_count": len(row_list),
        "current_rdp_component_count": sum(
            1 for row in row_list if str(row.get("source_project")) == "current_rdp"
        ),
        "old_project_component_count": sum(
            1 for row in row_list if str(row.get("source_project")) != "current_rdp"
        ),
        "reuse_directly_count": count_reuse("reuse_directly"),
        "reuse_as_report_feature_count": count_reuse("reuse_as_report_feature"),
        "reuse_after_hardening_count": count_reuse("reuse_after_hardening"),
        "design_reference_only_count": count_reuse("design_reference_only"),
        "discard_count": count_reuse("discard"),
        "unknown_pending_review_count": count_reuse("unknown_pending_review"),
        "inner_loop_safe_count": sum(int(row.get("inner_loop_safe", 0) or 0) for row in row_list),
        "reranker_safe_count": sum(int(row.get("reranker_safe", 0) or 0) for row in row_list),
        "final_judge_safe_count": sum(int(row.get("final_judge_safe", 0) or 0) for row in row_list),
        "runtime_safe_count": sum(int(row.get("runtime_safe", 0) or 0) for row in row_list),
        "uses_truth_or_oracle_count": sum(
            int(row.get("uses_truth_or_oracle", 0) or 0) for row in row_list
        ),
        "components_missing_tests_count": sum(
            1 for row in row_list if not int(row.get("has_tests", 0) or 0)
        ),
        "components_with_tests_count": sum(
            1 for row in row_list if int(row.get("has_tests", 0) or 0)
        ),
        "components_missing_evidence_paths": [
            {
                "component_id": str(row.get("component_id", "")),
                "missing_evidence_paths": str(row.get("missing_evidence_paths", "")),
            }
            for row in row_list
            if str(row.get("missing_evidence_paths", "") or "")
        ],
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(REQUIRED_FIELDS) + [
        "source_path_exists",
        "missing_test_file_paths",
        "missing_evidence_paths",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=True, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _section(lines: list[str], title: str, rows: Sequence[Mapping[str, Any]]) -> None:
    lines.extend(["", f"## {title}", ""])
    if not rows:
        lines.append("- None.")
        return
    for row in rows:
        lines.append(
            "- `{component_id}` - {name} ({kind}); {note}".format(
                component_id=str(row.get("component_id", "")),
                name=str(row.get("component_name", "")),
                kind=str(row.get("component_type", "")),
                note=str(row.get("known_failure_mode_addressed", "")),
            )
        )


def build_readout(rows: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> str:
    row_list = [dict(row) for row in rows]
    lines = [
        "# Scorer Component Inventory v1",
        "",
        "## Summary",
        "",
        f"- components: `{summary['component_count']}`",
        f"- current RDP components: `{summary['current_rdp_component_count']}`",
        f"- old/external project components: `{summary['old_project_component_count']}`",
        f"- runtime-safe components: `{summary['runtime_safe_count']}`",
        f"- reranker-safe components: `{summary['reranker_safe_count']}`",
        f"- truth/oracle-only or evaluation components: `{summary['uses_truth_or_oracle_count']}`",
        f"- components with tests: `{summary['components_with_tests_count']}`",
        f"- components missing tests: `{summary['components_missing_tests_count']}`",
    ]
    _section(
        lines,
        "Components recommended for direct reuse",
        [row for row in row_list if row.get("reuse_recommendation") == "reuse_directly"],
    )
    _section(
        lines,
        "Components recommended as report-only features",
        [row for row in row_list if row.get("reuse_recommendation") == "reuse_as_report_feature"],
    )
    _section(
        lines,
        "Components requiring hardening",
        [row for row in row_list if row.get("reuse_recommendation") == "reuse_after_hardening"],
    )
    _section(
        lines,
        "Components that must not be used at runtime",
        [
            row
            for row in row_list
            if int(row.get("runtime_safe", 0) or 0) == 0
            or int(row.get("uses_truth_or_oracle", 0) or 0) == 1
        ],
    )
    lines.extend(["", "## Missing tests / documentation", ""])
    missing_test_rows = [row for row in row_list if not int(row.get("has_tests", 0) or 0)]
    if not missing_test_rows:
        lines.append("- None.")
    for row in missing_test_rows:
        lines.append(
            f"- `{row.get('component_id', '')}`: tests pending or external-only review material."
        )
    lines.extend(
        [
            "",
            "## Recommended scorer-failure study inputs",
            "",
            "- `no_wli_phasec_truth_gap_dataset` for evaluation-only pair selection.",
            "- `rdp_numpy_rune_scorer` and `rdp_lmprime_runtime` for current score context.",
            "- `rdp_span_hamming_backend` and `rdp_word_ngram_judge` as report-only component clues.",
            "- Historical `language_model_prime`, `runeglish_language_models`, and `runeglish_score_tests` only as design references.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_inventory_outputs(
    *,
    rows: Sequence[Mapping[str, Any]],
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Any]:
    resolved_output = output_dir.resolve()
    try:
        resolved_output.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Output directory must stay under repo root: {output_dir}") from exc
    resolved_output.mkdir(parents=True, exist_ok=True)
    row_list = [dict(row) for row in rows]
    summary = summarize_inventory(row_list)
    summary["output_dir"] = _repo_rel(resolved_output)
    _write_csv(resolved_output / "scorer_component_inventory_rows.csv", row_list)
    _write_jsonl(resolved_output / "scorer_component_inventory_rows.jsonl", row_list)
    _write_json(resolved_output / "scorer_component_inventory_summary.json", summary)
    (resolved_output / "scorer_component_inventory_readout.md").write_text(
        build_readout(row_list, summary),
        encoding="utf-8",
    )
    return summary


def run_study() -> dict[str, Any]:
    started = time.perf_counter()
    rows = build_inventory_rows()
    summary = write_inventory_outputs(rows=rows)
    summary["elapsed_seconds"] = float(time.perf_counter() - started)
    _write_json(OUTPUT_DIR / "scorer_component_inventory_summary.json", summary)
    print(
        "[scorer_component_inventory_v1] "
        f"components={summary['component_count']} "
        f"output_dir={summary['output_dir']}",
        flush=True,
    )
    return summary


def main() -> None:
    run_study()


if __name__ == "__main__":
    main()
