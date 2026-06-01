from __future__ import annotations

import gzip
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.fast_backend import (  # noqa: E402
    fast_ngram_hamming_available,
    scan_chunk_fast,
)
from rune_decrypter_prime.scoring.ngram_hamming.reference import (  # noqa: E402
    PhraseEntry,
    PhraseHit,
    PhraseProfile,
    ReferenceScanResult,
    scan_chunk_reference,
)


RUN_LABEL = "phaseB_ngram_hamming_fast_real_index_smoke_v1"
PHRASE_INDEX_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_phrase_index_v1/phrase_index.jsonl.gz"
CANDIDATE_TEXTS_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1/candidate_full_texts.jsonl.gz"
OUTPUT_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_fast_real_index_smoke_v1"
PROFILE = PhraseProfile(
    profile_id="P1_word_analogue_len7_hd2",
    direction="fwd",
    orders=(2,),
    dictionary_cuts=("normal",),
    min_phrase_token_length=7,
    max_total_phrase_hd=2,
    max_word_hd=2,
)
DIRECTION = "fwd"
ENTRY_LIMIT = 2000
REAL_CANDIDATE_TOKEN_LIMIT = 250
MAX_WALLCLOCK_SECONDS = 20.0
DEBUG_EXAMPLE_LIMIT = 5


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def phrase_entry_from_index_row(row: dict[str, Any]) -> PhraseEntry:
    return PhraseEntry(
        phrase_id=str(row["phrase_id"]),
        direction=str(row["direction"]),
        dictionary_cut=str(row["dictionary_cut"]),
        ngram_order=int(row["ngram_order"]),
        word_token_ids=tuple(tuple(int(token) for token in word) for word in row["word_token_ids"]),
        rune_token_ids=tuple(int(token) for token in row["rune_token_ids"]),
        count=float(row.get("count", 0.0) or 0.0),
        log_count=float(row.get("log_count", 0.0) or 0.0),
        phrase_count=int(row.get("phrase_count", 1) or 1),
        top_latin_ngram=str(row.get("top_latin_ngram", "")),
    )


def load_smoke_entries() -> list[PhraseEntry]:
    entries: list[PhraseEntry] = []
    path = REPO_ROOT / PHRASE_INDEX_REL
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("direction") != DIRECTION:
                continue
            if row.get("dictionary_cut") not in PROFILE.dictionary_cuts:
                continue
            if int(row.get("ngram_order", -1)) not in PROFILE.orders:
                continue
            entry = phrase_entry_from_index_row(row)
            if entry.phrase_token_length < PROFILE.min_phrase_token_length:
                continue
            entries.append(entry)
            if len(entries) >= ENTRY_LIMIT:
                break
    if not entries:
        raise RuntimeError("no smoke entries loaded")
    return entries


def load_real_candidate_tokens() -> tuple[str, list[int]]:
    path = REPO_ROOT / CANDIDATE_TEXTS_REL
    selected: dict[str, Any] | None = None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if selected is None or str(row.get("candidate_id", "")) < str(selected.get("candidate_id", "")):
                selected = row
    if selected is None:
        raise RuntimeError("no candidate rows loaded")
    tokens = [int(part) for part in str(selected.get("token_sequence_text", "")).split()]
    return str(selected.get("candidate_id", "")), tokens[:REAL_CANDIDATE_TOKEN_LIMIT]


def hit_payload(hit: PhraseHit | dict[str, Any]) -> dict[str, Any]:
    row = dict(hit) if isinstance(hit, dict) else asdict(hit)
    return {
        "candidate_id": row["candidate_id"],
        "chunk_id": row["chunk_id"],
        "damage_level": row["damage_level"],
        "profile_id": row["profile_id"],
        "ngram_order": int(row["ngram_order"]),
        "dictionary_cut": row["dictionary_cut"],
        "phrase_id": row["phrase_id"],
        "phrase_count": int(row["phrase_count"]),
        "phrase_log_count": float(row["phrase_log_count"]),
        "phrase_token_length": int(row["phrase_token_length"]),
        "word_lengths": [int(value) for value in row["word_lengths"]],
        "word_hds": [int(value) for value in row["word_hds"]],
        "total_phrase_hd": int(row["total_phrase_hd"]),
        "max_word_hd": int(row["max_word_hd"]),
        "mean_word_hd": float(row["mean_word_hd"]),
        "normalised_phrase_hd": float(row["normalised_phrase_hd"]),
        "hit_start": int(row["hit_start"]),
        "hit_end": int(row["hit_end"]),
    }


def reference_payload(result: ReferenceScanResult) -> dict[str, Any]:
    return {
        "phrase_hits": [hit_payload(hit) for hit in result.phrase_hits],
        "candidate_tokens_scanned": result.candidate_tokens_scanned,
        "candidate_start_offsets_considered": result.candidate_start_offsets_considered,
        "phrase_entries_considered": result.phrase_entries_considered,
        "phrase_verification_attempts": result.phrase_verification_attempts,
        "phrase_verification_passes": result.phrase_verification_passes,
        "opportunity_count": result.opportunity_count,
        "positive_start_offset_count": result.positive_start_offset_count,
        "phrase_hits_per_opportunity": result.phrase_hits_per_opportunity,
        "positive_start_offset_fraction": result.positive_start_offset_fraction,
        "debug_examples": [hit_payload(hit) for hit in result.debug_examples],
    }


def fast_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "phrase_hits": [hit_payload(hit) for hit in payload["phrase_hits"]],
        "candidate_tokens_scanned": int(payload["candidate_tokens_scanned"]),
        "candidate_start_offsets_considered": int(payload["candidate_start_offsets_considered"]),
        "phrase_entries_considered": int(payload["phrase_entries_considered"]),
        "phrase_verification_attempts": int(payload["phrase_verification_attempts"]),
        "phrase_verification_passes": int(payload["phrase_verification_passes"]),
        "opportunity_count": int(payload["opportunity_count"]),
        "positive_start_offset_count": int(payload["positive_start_offset_count"]),
        "phrase_hits_per_opportunity": float(payload["phrase_hits_per_opportunity"]),
        "positive_start_offset_fraction": float(payload["positive_start_offset_fraction"]),
        "debug_examples": [hit_payload(hit) for hit in payload["debug_examples"]],
    }


def scan_pair(tokens: list[int], entries: list[PhraseEntry], *, candidate_id: str, chunk_id: str, damage_level: str) -> dict[str, Any]:
    reference = reference_payload(
        scan_chunk_reference(
            tokens,
            entries,
            PROFILE,
            candidate_id=candidate_id,
            chunk_id=chunk_id,
            damage_level=damage_level,
            debug_example_limit=DEBUG_EXAMPLE_LIMIT,
        )
    )
    fast = fast_payload(
        scan_chunk_fast(
            tokens,
            entries,
            PROFILE,
            candidate_id=candidate_id,
            chunk_id=chunk_id,
            damage_level=damage_level,
            debug_example_limit=DEBUG_EXAMPLE_LIMIT,
        )
    )
    return {
        "parity_match": fast == reference,
        "reference": reference,
        "fast": fast,
    }


def exact_selected_phrase_hit_found(hits: list[dict[str, Any]], selected_entry: PhraseEntry) -> bool:
    expected_word_lengths = list(selected_entry.word_lengths)
    expected_word_hds = [0 for _ in selected_entry.word_lengths]
    for hit in hits:
        if (
            hit["phrase_id"] == selected_entry.phrase_id
            and hit["hit_start"] == 1
            and hit["hit_end"] == 1 + selected_entry.phrase_token_length
            and hit["total_phrase_hd"] == 0
            and hit["word_lengths"] == expected_word_lengths
            and hit["word_hds"] == expected_word_hds
        ):
            return True
    return False


def run_smoke() -> dict[str, Any]:
    started = time.perf_counter()
    if not fast_ngram_hamming_available():
        raise RuntimeError("_ngram_hamming_fast extension is not built; no Python fallback is allowed for this smoke")

    entries = load_smoke_entries()
    selected_entry = entries[0]
    positive_tokens = [0] + list(selected_entry.rune_token_ids) + [0]
    positive = scan_pair(
        positive_tokens,
        entries,
        candidate_id="positive_control_from_phrase_index",
        chunk_id="positive_control",
        damage_level="none",
    )
    real_candidate_id, real_tokens = load_real_candidate_tokens()
    real = scan_pair(
        real_tokens,
        entries,
        candidate_id=real_candidate_id,
        chunk_id="real_candidate_first_tokens",
        damage_level="candidate_text",
    )
    elapsed_total = time.perf_counter() - started
    positive_hits = len(positive["fast"]["phrase_hits"])
    selected_phrase_exact_hit = exact_selected_phrase_hit_found(positive["fast"]["phrase_hits"], selected_entry)
    parity_match = bool(positive["parity_match"] and real["parity_match"])
    status = "pass"
    blocked_reason = ""
    if positive_hits <= 0:
        status = "blocked"
        blocked_reason = "positive control produced no phrase hits"
    elif not selected_phrase_exact_hit:
        status = "blocked"
        blocked_reason = "positive control did not include the selected phrase as an exact hit at offset 1"
    elif not parity_match:
        status = "blocked"
        blocked_reason = "C++ fast output differed from Python reference"
    elif elapsed_total > MAX_WALLCLOCK_SECONDS:
        status = "blocked"
        blocked_reason = f"smoke exceeded {MAX_WALLCLOCK_SECONDS:.1f}s wallclock budget"

    return {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "blocked_reason": blocked_reason,
        "backend_impl": "cpp_fast",
        "reference_backend_impl": "python_reference",
        "python_fallback_allowed": False,
        "broad_pilot": False,
        "phrase_index_path": PHRASE_INDEX_REL,
        "candidate_texts_path": CANDIDATE_TEXTS_REL,
        "profile_id": PROFILE.profile_id,
        "direction": DIRECTION,
        "orders": list(PROFILE.orders),
        "dictionary_cuts": list(PROFILE.dictionary_cuts),
        "entry_limit": ENTRY_LIMIT,
        "loaded_entry_count": len(entries),
        "real_candidate_token_limit": REAL_CANDIDATE_TOKEN_LIMIT,
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "elapsed_seconds": elapsed_total,
        "parity_match": parity_match,
        "selected_phrase_control": {
            "phrase_id": selected_entry.phrase_id,
            "expected_hit_start": 1,
            "expected_hit_end": 1 + selected_entry.phrase_token_length,
            "expected_total_phrase_hd": 0,
            "expected_word_hds": [0 for _ in selected_entry.word_lengths],
            "exact_hit_found": selected_phrase_exact_hit,
        },
        "positive_control": positive,
        "real_candidate": {
            "candidate_id": real_candidate_id,
            "tokens_scanned": len(real_tokens),
            **real,
        },
    }


def write_outputs(manifest: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    ensure_under_repo(output_dir / "fast_real_index_smoke_manifest.json")
    (output_dir / "fast_real_index_smoke_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    readout = [
        "# PhaseB N-Gram Hamming Fast Real-Index Smoke v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- backend: `{manifest['backend_impl']}`",
        f"- reference backend: `{manifest['reference_backend_impl']}`",
        f"- Python fallback allowed: `{manifest['python_fallback_allowed']}`",
        f"- broad pilot: `{manifest['broad_pilot']}`",
        f"- loaded entries: `{manifest['loaded_entry_count']}`",
        f"- elapsed seconds: `{manifest['elapsed_seconds']:.3f}`",
        f"- parity match: `{manifest['parity_match']}`",
        f"- selected phrase exact hit found: `{manifest['selected_phrase_control']['exact_hit_found']}`",
        f"- positive-control fast hits: `{len(manifest['positive_control']['fast']['phrase_hits'])}`",
        f"- real-candidate fast hits: `{len(manifest['real_candidate']['fast']['phrase_hits'])}`",
        "",
        "## Files",
        "",
        "- `fast_real_index_smoke_manifest.json`",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def main() -> None:
    manifest = run_smoke()
    write_outputs(manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] parity_match={manifest['parity_match']}")
    print(f"[{RUN_LABEL}] elapsed_seconds={manifest['elapsed_seconds']:.3f}")


if __name__ == "__main__":
    main()
