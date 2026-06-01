from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.bridge import (  # noqa: E402
    bridge_profile_specs,
    candidate_summary_rows,
    cluster_hits_overlap_touch,
    cluster_rows,
    pair_ledger_row,
    profile_manifest_hash,
    profile_manifest_rows,
    score_candidate_profile_ids,
    zero_hit_audit_row,
)
from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseHit  # noqa: E402


RUN_LABEL = "phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1"
)
NO_REAL_CANDIDATE_SCAN = True
NO_PRODUCTION_SCORER_CHANGES = True
CLUSTER_SCOPE_ALL = "all_profile_overlap_touch_cluster"
CLUSTER_SCOPE_SCORE = "score_candidate_overlap_touch_cluster"


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def synthetic_hit(
    *,
    candidate_id: str,
    chunk_id: str,
    profile_id: str,
    order: int,
    cut: str,
    phrase_id: str,
    start: int,
    end: int,
    total_hd: int,
) -> PhraseHit:
    length = end - start
    return PhraseHit(
        candidate_id=candidate_id,
        chunk_id=chunk_id,
        damage_level="synthetic",
        profile_id=profile_id,
        ngram_order=order,
        dictionary_cut=cut,
        phrase_id=phrase_id,
        phrase_count=1,
        phrase_log_count=1.0,
        phrase_token_length=length,
        word_lengths=(length,),
        word_hds=(total_hd,),
        total_phrase_hd=total_hd,
        max_word_hd=total_hd,
        mean_word_hd=float(total_hd),
        normalised_phrase_hd=total_hd / length,
        hit_start=start,
        hit_end=end,
    )


def synthetic_hits() -> tuple[PhraseHit, ...]:
    return (
        synthetic_hit(
            candidate_id="better",
            chunk_id="chunk-a",
            profile_id="BR_O3_conservative",
            order=3,
            cut="normal",
            phrase_id="p-best",
            start=0,
            end=8,
            total_hd=0,
        ),
        synthetic_hit(
            candidate_id="better",
            chunk_id="chunk-a",
            profile_id="BR_O2_soft",
            order=2,
            cut="normal",
            phrase_id="p-diag",
            start=8,
            end=14,
            total_hd=1,
        ),
        synthetic_hit(
            candidate_id="worse",
            chunk_id="chunk-a",
            profile_id="BR_O3_conservative",
            order=3,
            cut="strict",
            phrase_id="p-weak",
            start=20,
            end=28,
            total_hd=2,
        ),
    )


def run_synthetic_contract_smoke(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    specs = bridge_profile_specs()
    hits = synthetic_hits()
    score_ids = score_candidate_profile_ids(specs)
    all_clusters = cluster_hits_overlap_touch(hits, cluster_scope=CLUSTER_SCOPE_ALL)
    score_clusters = cluster_hits_overlap_touch(
        hits,
        cluster_scope=CLUSTER_SCOPE_SCORE,
        allowed_profile_ids=score_ids,
    )
    all_cluster_rows = cluster_rows(all_clusters, run_id=RUN_LABEL)
    score_cluster_rows = cluster_rows(score_clusters, run_id=RUN_LABEL)
    all_candidate_rows = candidate_summary_rows(
        hits,
        all_clusters,
        specs,
        expected_cluster_scope=CLUSTER_SCOPE_ALL,
    )
    score_candidate_rows = candidate_summary_rows(
        (hit for hit in hits if hit.profile_id in score_ids),
        score_clusters,
        specs,
        expected_cluster_scope=CLUSTER_SCOPE_SCORE,
    )
    better_order3 = next(
        row
        for row in score_candidate_rows
        if row["candidate_id"] == "better" and row["profile_id"] == "BR_O3_conservative"
    )
    worse_order3 = next(
        row
        for row in score_candidate_rows
        if row["candidate_id"] == "worse" and row["profile_id"] == "BR_O3_conservative"
    )
    pair_rows = [
        pair_ledger_row(
            pair_id="synthetic-pair-1",
            expected_better_id="better",
            expected_worse_id="worse",
            baseline_winner="",
            phrase_tuple_winner="better",
            order3_tuple_better=better_order3,
            order3_tuple_worse=worse_order3,
            normal_support_delta=1.0,
            strict_support_delta=-1.0,
            first_diff_component="BR_O3_conservative",
            outcome_label="synthetic_contract_only",
            panel_rescue_flag=False,
            unsafe_interpretation_flags=("synthetic_fixture",),
        )
    ]
    zero_hit_rows = [
        zero_hit_audit_row(
            pair_id="synthetic-pair-1",
            candidate_id="worse",
            role="expected_worse",
            chunk_id="chunk-b",
            ngram_hit_count_by_order={2: 0, 3: 0},
            phrase_opportunity_count_by_order={2: 3, 3: 2},
            likely_no_hit_reason="synthetic no-hit cell",
        )
    ]
    profile_rows = profile_manifest_rows(specs)
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "no_real_candidate_scan": NO_REAL_CANDIDATE_SCAN,
        "no_production_scorer_changes": NO_PRODUCTION_SCORER_CHANGES,
        "profile_manifest_hash": profile_manifest_hash(specs),
        "profile_count": len(profile_rows),
        "raw_hit_count": len(hits),
        "all_cluster_count": len(all_cluster_rows),
        "score_cluster_count": len(score_cluster_rows),
        "all_candidate_summary_row_count": len(all_candidate_rows),
        "score_candidate_summary_row_count": len(score_candidate_rows),
        "candidate_summary_row_count": len(score_candidate_rows),
        "pair_ledger_row_count": len(pair_rows),
        "zero_hit_audit_row_count": len(zero_hit_rows),
    }
    write_json(selected_output_dir / "synthetic_contract_manifest.json", manifest)
    write_csv(selected_output_dir / "profile_manifest_rows.csv", profile_rows)
    write_csv(selected_output_dir / "all_cluster_rows.csv", all_cluster_rows)
    write_csv(selected_output_dir / "score_candidate_cluster_rows.csv", score_cluster_rows)
    write_csv(selected_output_dir / "all_profile_candidate_summary_rows.csv", all_candidate_rows)
    write_csv(selected_output_dir / "score_candidate_candidate_summary_rows.csv", score_candidate_rows)
    write_csv(selected_output_dir / "pair_ledger_rows.csv", pair_rows)
    write_csv(selected_output_dir / "zero_hit_audit_rows.csv", zero_hit_rows)
    write_readout(selected_output_dir / "readout.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] raw_hit_count={manifest['raw_hit_count']}")
    return manifest


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Bridge Lane 2 Synthetic Contract Smoke v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- no real candidate scan: `{manifest['no_real_candidate_scan']}`",
        f"- production scorer changes: `{not manifest['no_production_scorer_changes']}`",
        f"- raw hit count: `{manifest['raw_hit_count']}`",
        f"- all-cluster count: `{manifest['all_cluster_count']}`",
        f"- score-candidate cluster count: `{manifest['score_cluster_count']}`",
        f"- all-profile candidate summary rows: `{manifest['all_candidate_summary_row_count']}`",
        f"- score-candidate candidate summary rows: `{manifest['score_candidate_summary_row_count']}`",
        f"- pair ledger rows: `{manifest['pair_ledger_row_count']}`",
        f"- zero-hit audit rows: `{manifest['zero_hit_audit_row_count']}`",
        "",
        "This smoke uses synthetic hits only. It exercises Lane 2 output schemas",
        "without reading full raw assets or scanning real candidates.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    run_synthetic_contract_smoke()


if __name__ == "__main__":
    main()
