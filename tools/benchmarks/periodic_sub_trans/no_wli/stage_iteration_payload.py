from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple


@dataclass(frozen=True)
class IterationPersistencePayload:
    target_key_idx: List[int]
    truth_diagnostics: Dict[str, Any]
    word_ngram_report: Dict[str, Any]
    stage2_topk_word_ngram_report: List[Dict[str, Any]]
    stage3_topk_word_ngram_report: List[Dict[str, Any]]
    stage35_archive_rows: List[Dict[str, Any]]
    stage35_seed_rows: List[Dict[str, Any]]
    stage3_diagnostics: Dict[str, Any]

    @classmethod
    def build(
        cls,
        *,
        target_key_idx: List[int] | None,
        truth_diagnostics: Mapping[str, Any] | None,
        word_ngram_report: Mapping[str, Any] | None,
        stage2_topk_word_ngram_report: List[Mapping[str, Any]] | None,
        stage3_topk_word_ngram_report: List[Mapping[str, Any]] | None,
        stage35_archive_rows: List[Mapping[str, Any]] | None,
        stage35_seed_rows: List[Mapping[str, Any]] | None,
        stage3_diagnostics: Mapping[str, Any] | None,
    ) -> "IterationPersistencePayload":
        return cls(
            target_key_idx=list(map(int, list(target_key_idx or []))),
            truth_diagnostics=dict(truth_diagnostics or {}),
            word_ngram_report=dict(word_ngram_report or {}),
            stage2_topk_word_ngram_report=[
                dict(row) for row in list(stage2_topk_word_ngram_report or [])
            ],
            stage3_topk_word_ngram_report=[
                dict(row) for row in list(stage3_topk_word_ngram_report or [])
            ],
            stage35_archive_rows=[
                dict(row) for row in list(stage35_archive_rows or [])
            ],
            stage35_seed_rows=[dict(row) for row in list(stage35_seed_rows or [])],
            stage3_diagnostics=dict(stage3_diagnostics or {}),
        )

    def instance_fields(self) -> Dict[str, Any]:
        return dict(
            word_ngram_judge_active=bool(
                self.word_ngram_report.get("word_ngram_judge_active", False)
            ),
            word_ngram_judge_n_positions=int(
                self.word_ngram_report.get("word_ngram_judge_n_positions", 0) or 0
            ),
            word_ngram_judge_report_xent=self.word_ngram_report.get(
                "word_ngram_judge_report_xent"
            ),
            word_ngram_judge_trust_score=self.word_ngram_report.get(
                "word_ngram_judge_trust_score"
            ),
            word_ngram_judge_trust_tier=str(
                self.word_ngram_report.get("word_ngram_judge_trust_tier", "") or ""
            ),
            word_ngram_judge_inactive_reason=str(
                self.word_ngram_report.get("word_ngram_judge_inactive_reason", "") or ""
            ),
            truth_diagnostics_available=bool(
                self.truth_diagnostics.get("available", False)
            ),
            truth_key_hamming_total=self.truth_diagnostics.get("key_hamming_total"),
            truth_key_hamming_substitution=self.truth_diagnostics.get(
                "key_hamming_substitution"
            ),
            truth_key_hamming_columns=self.truth_diagnostics.get("key_hamming_columns"),
            truth_worst_substitution_slice=self.truth_diagnostics.get(
                "worst_substitution_slice"
            ),
            truth_worst_substitution_slice_mismatches=self.truth_diagnostics.get(
                "worst_substitution_slice_mismatches"
            ),
            truth_worst_plaintext_period_residue=self.truth_diagnostics.get(
                "worst_plaintext_period_residue"
            ),
            truth_worst_plaintext_period_residue_match_ratio=self.truth_diagnostics.get(
                "worst_plaintext_period_residue_match_ratio"
            ),
            stage35_requested_cfg=int(
                self.stage3_diagnostics.get("stage35_requested_cfg", 0)
            ),
            stage35_proof_valid=int(
                self.stage3_diagnostics.get("stage35_proof_valid", 0)
            ),
            stage35_proof_invalid_reason=str(
                self.stage3_diagnostics.get("stage35_proof_invalid_reason", "")
            ),
            stage35_selected=bool(self.stage3_diagnostics.get("stage35_selected", 0)),
            stage35_archive_count=int(
                self.stage3_diagnostics.get("stage35_archive_count", 0)
            ),
            stage35_rounds_completed=int(
                self.stage3_diagnostics.get("stage35_rounds_completed", 0)
            ),
        )

    def artifact_fields(self) -> Dict[str, Any]:
        return dict(
            stage35_requested_cfg=int(
                self.stage3_diagnostics.get("stage35_requested_cfg", 0)
            ),
            stage35_proof_valid=int(
                self.stage3_diagnostics.get("stage35_proof_valid", 0)
            ),
            stage35_proof_invalid_reason=str(
                self.stage3_diagnostics.get("stage35_proof_invalid_reason", "")
            ),
            target_key_idx=list(self.target_key_idx),
            truth_diagnostics=dict(self.truth_diagnostics),
            word_ngram_report=dict(self.word_ngram_report),
            stage2_topk_word_ngram_report=[
                dict(row) for row in self.stage2_topk_word_ngram_report
            ],
            stage3_topk_word_ngram_report=[
                dict(row) for row in self.stage3_topk_word_ngram_report
            ],
            stage35_archive=[dict(row) for row in self.stage35_archive_rows],
            stage35_seed_rows=[dict(row) for row in self.stage35_seed_rows],
        )


def build_iteration_payloads(
    *,
    tier_name: str,
    period: int,
    columns: int,
    length: int,
    text_id: int,
    key_seed: int,
    offset_hint: int,
    offset_used: int,
    status: str,
    stop_reason: str,
    solve_threshold: float,
    best_stage: str,
    best_match_ratio: float,
    stage1_sub_key_match: float,
    stage2_match_ratio: float,
    stage3_match_ratio: float,
    stage2_gap_to_oracle: float,
    stage3_band: str,
    basin_judge_span_calls_total: int,
    basin_judge_span_calls_active: int,
    basin_judge_span_calls_rejected_or_gated: int,
    basin_judge_span_seconds_total: float,
    basin_judge_unique_end_hash: int,
    oracle_mode: str,
    oracle_consulted_in_decisions: bool,
    total_seconds: float,
    total_evals: int,
    preview_best_latin: str,
    outcome_code: str,
    profile_id: str,
    mode: str,
    direction: str,
    order: str,
    alphabet_size: int,
    best_score: float,
    oracle_scores: Dict[str, float],
    score_minus_oracle: Dict[str, float],
    ciphertext_idx: List[int],
    target_plaintext_idx: List[int],
    final_best_key_idx: List[int],
    final_best_plaintext_idx: List[int],
    stage2_topk: List[Dict[str, Any]],
    stage2_topk_has_best_match: bool,
    stage2_diagnostics: Dict[str, Any],
    stage3_topk: List[Dict[str, Any]],
    stage3_diagnostics: Dict[str, Any],
    stage35_archive: List[Dict[str, Any]] | None = None,
    stage35_seed_rows: List[Dict[str, Any]] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    instance_row: Dict[str, Any] = dict(
        tier=str(tier_name),
        period=int(period),
        columns=int(columns),
        length=int(length),
        text_id=int(text_id),
        key_seed=int(key_seed),
        offset_hint=int(offset_hint),
        offset_used=int(offset_used),
        status=str(status),
        stop_reason=str(stop_reason),
        solve_threshold=float(solve_threshold),
        best_stage=str(best_stage),
        best_match_ratio=float(best_match_ratio),
        stage1_sub_key_match=float(stage1_sub_key_match),
        stage2_match_ratio=float(stage2_match_ratio),
        stage3_match_ratio=float(stage3_match_ratio),
        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
        stage3_band=str(stage3_band),
        basin_judge_span_calls_total=int(basin_judge_span_calls_total),
        basin_judge_span_calls_active=int(basin_judge_span_calls_active),
        basin_judge_span_calls_rejected_or_gated=int(basin_judge_span_calls_rejected_or_gated),
        basin_judge_span_seconds_total=float(basin_judge_span_seconds_total),
        basin_judge_unique_end_hash=int(basin_judge_unique_end_hash),
        oracle_mode=str(oracle_mode),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        total_seconds=float(total_seconds),
        total_evals=int(total_evals),
        preview_best_latin=str(preview_best_latin),
        outcome_code=str(outcome_code),
    )

    artifact_payload: Dict[str, Any] = dict(
        tier=str(tier_name),
        profile_id=str(profile_id),
        mode=str(mode),
        oracle_mode=str(oracle_mode),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        direction=str(direction),
        order=str(order),
        alphabet_size=int(alphabet_size),
        text_id=int(text_id),
        key_seed=int(key_seed),
        offset_hint=int(offset_hint),
        offset_used=int(offset_used),
        period=int(period),
        columns=int(columns),
        length=int(length),
        status=str(status),
        stop_reason=str(stop_reason),
        outcome_code=str(outcome_code),
        best_stage=str(best_stage),
        best_match_ratio=float(best_match_ratio),
        best_score=float(best_score),
        oracle_scores=dict(oracle_scores),
        score_minus_oracle=dict(score_minus_oracle),
        solve_threshold=float(solve_threshold),
        ciphertext_idx=list(map(int, ciphertext_idx)),
        target_plaintext_idx=list(map(int, target_plaintext_idx)),
        final_best_key_idx=list(map(int, final_best_key_idx)),
        final_best_plaintext_idx=list(map(int, final_best_plaintext_idx)),
        stage2_topk=list(stage2_topk),
        stage2_topk_has_best_match=int(1 if bool(stage2_topk_has_best_match) else 0),
        stage2_diagnostics=dict(stage2_diagnostics),
        stage3_topk=list(stage3_topk),
        stage3_diagnostics=dict(stage3_diagnostics),
        stage35_archive=[dict(row) for row in list(stage35_archive or [])],
        stage35_seed_rows=[dict(row) for row in list(stage35_seed_rows or [])],
    )
    return instance_row, artifact_payload
