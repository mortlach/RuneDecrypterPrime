from __future__ import annotations

import gzip
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.reference import (  # noqa: E402
    PhraseEntry,
    PhraseProfile,
    scan_chunk_reference,
)


RUN_LABEL = "phaseB_ngram_hamming_reference_smoke_v1"
PHRASE_INDEX_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_phrase_index_v1/phrase_index.jsonl.gz"
CANDIDATE_TEXTS_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1/candidate_full_texts.jsonl.gz"
OUTPUT_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_reference_smoke_v1"
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


def hit_to_json(hit: Any) -> dict[str, Any]:
    return {
        "candidate_id": hit.candidate_id,
        "chunk_id": hit.chunk_id,
        "profile_id": hit.profile_id,
        "phrase_id": hit.phrase_id,
        "ngram_order": hit.ngram_order,
        "dictionary_cut": hit.dictionary_cut,
        "phrase_token_length": hit.phrase_token_length,
        "word_lengths": list(hit.word_lengths),
        "word_hds": list(hit.word_hds),
        "total_phrase_hd": hit.total_phrase_hd,
        "hit_start": hit.hit_start,
        "hit_end": hit.hit_end,
    }


def run_smoke() -> dict[str, Any]:
    started = time.perf_counter()
    entries = load_smoke_entries()
    positive_tokens = [0] + list(entries[0].rune_token_ids) + [0]
    positive_result = scan_chunk_reference(
        positive_tokens,
        entries,
        PROFILE,
        candidate_id="positive_control_from_phrase_index",
        chunk_id="positive_control",
        damage_level="none",
        debug_example_limit=DEBUG_EXAMPLE_LIMIT,
    )
    elapsed_after_positive = time.perf_counter() - started
    if elapsed_after_positive > MAX_WALLCLOCK_SECONDS:
        status = "blocked"
        blocked_reason = "positive control exceeded smoke wallclock budget"
        real_result = None
        real_candidate_id = ""
        real_tokens = []
    else:
        real_candidate_id, real_tokens = load_real_candidate_tokens()
        real_result = scan_chunk_reference(
            real_tokens,
            entries,
            PROFILE,
            candidate_id=real_candidate_id,
            chunk_id="real_candidate_first_tokens",
            damage_level="candidate_text",
            debug_example_limit=DEBUG_EXAMPLE_LIMIT,
        )
        status = "pass" if positive_result.phrase_hits else "blocked"
        blocked_reason = "" if status == "pass" else "positive control produced no phrase hits"

    elapsed_total = time.perf_counter() - started
    if elapsed_total > MAX_WALLCLOCK_SECONDS:
        status = "blocked"
        blocked_reason = f"smoke exceeded {MAX_WALLCLOCK_SECONDS:.1f}s wallclock budget"

    manifest: dict[str, Any] = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "blocked_reason": blocked_reason,
        "backend_impl": "python_reference",
        "broad_python_pilot": False,
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
        "positive_control": {
            "candidate_tokens_scanned": positive_result.candidate_tokens_scanned,
            "phrase_entries_considered": positive_result.phrase_entries_considered,
            "phrase_verification_attempts": positive_result.phrase_verification_attempts,
            "phrase_verification_passes": positive_result.phrase_verification_passes,
            "phrase_hits": len(positive_result.phrase_hits),
            "opportunity_count": positive_result.opportunity_count,
            "phrase_hits_per_opportunity": positive_result.phrase_hits_per_opportunity,
            "positive_start_offset_fraction": positive_result.positive_start_offset_fraction,
            "debug_examples": [hit_to_json(hit) for hit in positive_result.debug_examples],
        },
        "real_candidate": {
            "candidate_id": real_candidate_id,
            "candidate_tokens_scanned": len(real_tokens),
            "phrase_entries_considered": real_result.phrase_entries_considered if real_result else 0,
            "phrase_verification_attempts": real_result.phrase_verification_attempts if real_result else 0,
            "phrase_verification_passes": real_result.phrase_verification_passes if real_result else 0,
            "phrase_hits": len(real_result.phrase_hits) if real_result else 0,
            "opportunity_count": real_result.opportunity_count if real_result else 0,
            "phrase_hits_per_opportunity": real_result.phrase_hits_per_opportunity if real_result else 0.0,
            "positive_start_offset_fraction": real_result.positive_start_offset_fraction if real_result else 0.0,
            "debug_examples": [hit_to_json(hit) for hit in real_result.debug_examples] if real_result else [],
        },
    }
    return manifest


def write_outputs(manifest: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    ensure_under_repo(output_dir / "reference_smoke_manifest.json")
    (output_dir / "reference_smoke_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    readout = [
        "# PhaseB N-Gram Hamming Reference Smoke v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- backend: `{manifest['backend_impl']}`",
        f"- broad Python pilot: `{manifest['broad_python_pilot']}`",
        f"- loaded entries: `{manifest['loaded_entry_count']}`",
        f"- elapsed seconds: `{manifest['elapsed_seconds']:.3f}`",
        f"- positive-control hits: `{manifest['positive_control']['phrase_hits']}`",
        f"- real-candidate hits: `{manifest['real_candidate']['phrase_hits']}`",
        "",
        "## Files",
        "",
        "- `reference_smoke_manifest.json`",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def main() -> None:
    manifest = run_smoke()
    write_outputs(manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] elapsed_seconds={manifest['elapsed_seconds']:.3f}")


if __name__ == "__main__":
    main()
