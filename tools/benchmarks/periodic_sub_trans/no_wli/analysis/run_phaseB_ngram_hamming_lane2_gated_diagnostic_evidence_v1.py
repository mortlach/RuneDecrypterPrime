from __future__ import annotations

import csv
import gzip
import hashlib
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.bridge import (  # noqa: E402
    NgramProfileSpec,
    best_hit_signature,
    bridge_profile_specs,
    cluster_hits_overlap_touch,
    profile_manifest_hash,
    profile_manifest_rows,
    score_candidate_profile_ids,
)
from rune_decrypter_prime.scoring.ngram_hamming.reference import (  # noqa: E402
    PhraseEntry,
    PhraseHit,
    PhraseProfile,
    phrase_entry_from_asset_row,
    scan_chunk_reference,
)


RUN_LABEL = "phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1"
)
ASSET_HOME_REL = "assets/ngram_hamming/phaseB_full_raw_v1"
LANE1_ASSET_ID = "phaseB_ngram_hamming_full_raw_v1"
PROFILE_IDS = (
    "BR_O2_soft",
    "BR_O2_len8_conservative",
    "BR_O2_len10_long",
    "BR_O3_soft",
    "BR_O3_conservative",
)
CLUSTER_SCOPE_ALL = "all_profiles_diagnostic"
CLUSTER_SCOPE_SCORE = "score_candidate_view"
ALPHABET_SIZE = 29
MAX_ASSET_ROWS_PER_ORDER_CUT = 3
HIT_SAMPLE_LIMIT = 200
RUN_SCOPE = "post_review_microbatch"
RUN_AUTHORITY = "diagnostic_only"
CONTROLLED_EVAL_CORPUS_SCAN_STARTED = True
REAL_CANDIDATE_SCAN_STARTED = False
BROAD_CANDIDATE_SCAN_STARTED = False
PRODUCTION_SCORER_CHANGE = False


@dataclass(frozen=True)
class EvalCase:
    candidate_id: str
    case_family: str
    damage_rate: float
    damage_mode: str
    seed: int
    tokens: tuple[int, ...]
    source_case_id: str
    expected_role: str
    source_kind: str
    damage_positions_sha256: str = ""


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    ensure_under_repo(path)
    lines = [json.dumps(dict(row), sort_keys=True, separators=(",", ":")) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def selected_profile_specs() -> tuple[NgramProfileSpec, ...]:
    specs = {spec.profile_id: spec for spec in bridge_profile_specs()}
    return tuple(specs[profile_id] for profile_id in PROFILE_IDS)


def phrase_profile_from_spec(spec: NgramProfileSpec) -> PhraseProfile:
    return PhraseProfile(
        profile_id=spec.profile_id,
        direction=spec.direction,
        orders=spec.orders,
        dictionary_cuts=spec.cuts,
        min_phrase_token_length=spec.min_phrase_token_length,
        max_total_phrase_hd=spec.max_total_phrase_hd,
        max_word_hd=spec.max_word_hd,
        normalised_hd_ceiling=spec.normalised_hd_ceiling,
    )


def validate_profile_specs_for_lane2(specs: Iterable[NgramProfileSpec]) -> None:
    for spec in specs:
        if not spec.profile_origin:
            raise ValueError(f"{spec.profile_id} missing profile_origin")
        if spec.profile_id in {"BR_O2_soft", "BR_O3_soft", "BR_O3_conservative"} and not spec.canonical_profile_id:
            raise ValueError(f"{spec.profile_id} missing canonical_profile_id")
        if not spec.score_authority:
            raise ValueError(f"{spec.profile_id} missing score_authority")
        if spec.profile_id == "BR_O3_conservative" and "strict" in spec.cuts:
            if spec.canonical_profile_id == "S3W":
                raise ValueError("BR_O3_conservative strict must not be labelled S3W")
        if spec.profile_id == "S34C_main" and spec.min_phrase_token_length != 10:
            raise ValueError("S34C_main length broadened silently")


def positions_hash(positions: Sequence[int]) -> str:
    payload = json.dumps(list(positions), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def deterministic_damage(
    tokens: Sequence[int],
    *,
    damage_rate: float,
    seed: int,
    alphabet_size: int = ALPHABET_SIZE,
    damage_mode: str = "substitute",
) -> tuple[tuple[int, ...], dict[str, Any]]:
    if damage_mode != "substitute":
        raise ValueError("first diagnostic evidence runner only enables substitute damage")
    rng = random.Random(seed)
    token_list = list(tokens)
    damage_count = int(round(len(token_list) * damage_rate))
    damage_count = max(0, min(len(token_list), damage_count))
    positions = tuple(sorted(rng.sample(range(len(token_list)), damage_count))) if damage_count else ()
    for pos in positions:
        original = token_list[pos]
        replacement = rng.randrange(alphabet_size - 1)
        if replacement >= original:
            replacement += 1
        token_list[pos] = replacement
    manifest = {
        "damage_mode": damage_mode,
        "damage_rate": damage_rate,
        "seed": seed,
        "alphabet_size": alphabet_size,
        "input_token_count": len(tokens),
        "damaged_token_count": damage_count,
        "damage_positions_sha256": positions_hash(positions),
    }
    return tuple(token_list), manifest


def load_lane1_asset_entries() -> tuple[PhraseEntry, ...]:
    manifest_path = REPO_ROOT / ASSET_HOME_REL / "asset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries: list[PhraseEntry] = []
    for order in (2, 3):
        for cut in ("normal", "strict"):
            files = [
                row
                for row in manifest.get("files", [])
                if row.get("ngram_order") == order
                and row.get("dictionary_cut") == cut
                and row.get("direction") == "fwd"
                and int(row.get("aggregate_rows", 0)) > 0
            ]
            for file_row in sorted(files, key=lambda row: (int(row.get("bytes", 0)), str(row.get("path", "")))):
                entries.extend(read_phrase_entries_from_payload(file_row["path"], MAX_ASSET_ROWS_PER_ORDER_CUT - count_entries(entries, order, cut)))
                if count_entries(entries, order, cut) >= MAX_ASSET_ROWS_PER_ORDER_CUT:
                    break
    if not entries:
        raise RuntimeError("no Lane 1 phrase entries were loaded for diagnostic evidence")
    return tuple(entries)


def count_entries(entries: Sequence[PhraseEntry], order: int, cut: str) -> int:
    return sum(1 for entry in entries if entry.ngram_order == order and entry.dictionary_cut == cut)


def read_phrase_entries_from_payload(path_rel: str, limit: int) -> list[PhraseEntry]:
    if limit <= 0:
        return []
    out: list[PhraseEntry] = []
    with gzip.open(REPO_ROOT / path_rel, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            entry = phrase_entry_from_asset_row(row)
            if entry.phrase_token_length < 7:
                continue
            out.append(entry)
            if len(out) >= limit:
                break
    return out


def separator_tokens(index: int) -> tuple[int, ...]:
    return (28, (index * 7 + 3) % 29, 28)


def base_positive_tokens(entries: Sequence[PhraseEntry]) -> tuple[int, ...]:
    tokens: list[int] = []
    selected = sorted(entries, key=lambda entry: (entry.ngram_order, entry.dictionary_cut, entry.phrase_id))
    for idx, entry in enumerate(selected):
        tokens.extend(entry.rune_token_ids)
        tokens.extend(separator_tokens(idx))
    return tuple(tokens)


def build_eval_cases(entries: Sequence[PhraseEntry]) -> tuple[EvalCase, ...]:
    base_tokens = base_positive_tokens(entries)
    cases: list[EvalCase] = [
        EvalCase(
            candidate_id="positive_clean_000",
            case_family="positive_clean",
            damage_rate=0.0,
            damage_mode="none",
            seed=0,
            tokens=base_tokens,
            source_case_id="asset_phrase_sample_000",
            expected_role="positive",
            source_kind="generated_from_permanent_lane1_asset_tokens",
        )
    ]
    for rate, seed in ((0.20, 202620), (0.35, 202635), (0.50, 202650)):
        damaged, manifest = deterministic_damage(base_tokens, damage_rate=rate, seed=seed)
        cases.append(
            EvalCase(
                candidate_id=f"positive_damaged_{int(rate * 100):02d}_000",
                case_family=f"positive_damaged_{int(rate * 100):02d}",
                damage_rate=rate,
                damage_mode="substitute",
                seed=seed,
                tokens=damaged,
                source_case_id="positive_clean_000",
                expected_role="positive",
                source_kind="generated_from_permanent_lane1_asset_tokens",
                damage_positions_sha256=manifest["damage_positions_sha256"],
            )
        )
    for rate in (0.0, 0.20, 0.35, 0.50):
        seed_base = int(300000 + rate * 1000)
        cases.extend(
            (
                EvalCase(
                    candidate_id=f"matched_random_same_length_{int(rate * 100):02d}_000",
                    case_family="matched_random_same_length",
                    damage_rate=rate,
                    damage_mode="matched_null",
                    seed=seed_base,
                    tokens=random_tokens_same_length(len(base_tokens), seed=seed_base),
                    source_case_id=f"positive_rate_{rate:.2f}",
                    expected_role="null",
                    source_kind="synthetic_matched_null",
                ),
                EvalCase(
                    candidate_id=f"matched_shuffle_same_tokens_{int(rate * 100):02d}_000",
                    case_family="matched_shuffle_same_tokens",
                    damage_rate=rate,
                    damage_mode="matched_null",
                    seed=seed_base + 1,
                    tokens=shuffled_tokens(base_tokens, seed=seed_base + 1),
                    source_case_id=f"positive_rate_{rate:.2f}",
                    expected_role="null",
                    source_kind="synthetic_matched_null",
                ),
                EvalCase(
                    candidate_id=f"matched_wordlike_wrong_order_{int(rate * 100):02d}_000",
                    case_family="matched_wordlike_wrong_order",
                    damage_rate=rate,
                    damage_mode="matched_null",
                    seed=seed_base + 2,
                    tokens=wrong_order_tokens(entries),
                    source_case_id=f"positive_rate_{rate:.2f}",
                    expected_role="null",
                    source_kind="synthetic_matched_null",
                ),
            )
        )
    cases.extend(
        (
            EvalCase(
                candidate_id="hard_negative_book_text_000",
                case_family="hard_negative_book_text",
                damage_rate=0.0,
                damage_mode="none",
                seed=400000,
                tokens=hard_negative_tokens(len(base_tokens)),
                source_case_id="synthetic_public_domain_style_surrogate",
                expected_role="null",
                source_kind="synthetic_surrogate_not_book_text",
            ),
            EvalCase(
                candidate_id="boundary_too_short_000",
                case_family="boundary_cases",
                damage_rate=0.0,
                damage_mode="none",
                seed=500000,
                tokens=(1, 2, 3, 4, 5, 6),
                source_case_id="boundary_short",
                expected_role="boundary",
                source_kind="synthetic_boundary",
            ),
            EvalCase(
                candidate_id="boundary_repeated_tokens_000",
                case_family="boundary_cases",
                damage_rate=0.0,
                damage_mode="none",
                seed=500001,
                tokens=tuple([7] * len(base_tokens)),
                source_case_id="boundary_repeated",
                expected_role="boundary",
                source_kind="synthetic_boundary",
            ),
            EvalCase(
                candidate_id="boundary_dominant_region_000",
                case_family="boundary_cases",
                damage_rate=0.0,
                damage_mode="none",
                seed=500002,
                tokens=tuple(list(entries[0].rune_token_ids) * 6),
                source_case_id="boundary_dominant_region",
                expected_role="boundary",
                source_kind="synthetic_boundary",
            ),
        )
    )
    return tuple(cases)


def random_tokens_same_length(length: int, *, seed: int) -> tuple[int, ...]:
    rng = random.Random(seed)
    return tuple(rng.randrange(ALPHABET_SIZE) for _idx in range(length))


def shuffled_tokens(tokens: Sequence[int], *, seed: int) -> tuple[int, ...]:
    rng = random.Random(seed)
    out = list(tokens)
    rng.shuffle(out)
    return tuple(out)


def wrong_order_tokens(entries: Sequence[PhraseEntry]) -> tuple[int, ...]:
    tokens: list[int] = []
    for idx, entry in enumerate(reversed(entries)):
        for word in reversed(entry.word_token_ids):
            tokens.extend(word)
        tokens.extend(separator_tokens(idx + 100))
    return tuple(tokens)


def hard_negative_tokens(length: int) -> tuple[int, ...]:
    pattern = (0, 4, 8, 12, 16, 20, 24, 3, 7, 11, 15, 19, 23, 27)
    return tuple(pattern[idx % len(pattern)] for idx in range(length))


def case_row(case: EvalCase) -> dict[str, Any]:
    return {
        "candidate_id": case.candidate_id,
        "case_family": case.case_family,
        "damage_rate": case.damage_rate,
        "damage_mode": case.damage_mode,
        "seed": case.seed,
        "alphabet_size": ALPHABET_SIZE,
        "input_token_count": len(case.tokens),
        "damaged_token_count": int(round(len(case.tokens) * case.damage_rate)) if case.damage_mode == "substitute" else 0,
        "damage_positions_sha256": case.damage_positions_sha256,
        "source_case_id": case.source_case_id,
        "expected_role": case.expected_role,
        "source_kind": case.source_kind,
        "token_ids": list(case.tokens),
    }


def scan_cases(
    cases: Sequence[EvalCase],
    entries: Sequence[PhraseEntry],
    specs: Sequence[NgramProfileSpec],
) -> tuple[list[PhraseHit], list[dict[str, Any]]]:
    hits: list[PhraseHit] = []
    scan_rows: list[dict[str, Any]] = []
    for case in cases:
        for spec in specs:
            profile = phrase_profile_from_spec(spec)
            result = scan_chunk_reference(
                case.tokens,
                entries,
                profile,
                candidate_id=case.candidate_id,
                chunk_id="chunk_000",
                damage_level=f"{case.case_family}:{case.damage_rate:.2f}",
            )
            hits.extend(result.phrase_hits)
            for cut in spec.cuts:
                for order in spec.orders:
                    scan_rows.append(
                        {
                            "candidate_id": case.candidate_id,
                            "profile_id": spec.profile_id,
                            "cut": cut,
                            "ngram_order": order,
                            "case_family": case.case_family,
                            "damage_rate": case.damage_rate,
                            "phrase_entries_considered": result.phrase_entries_considered,
                            "candidate_tokens_scanned": result.candidate_tokens_scanned,
                            "candidate_start_offsets_considered": result.candidate_start_offsets_considered,
                            "phrase_verification_attempts": result.phrase_verification_attempts,
                            "phrase_verification_passes": result.phrase_verification_passes,
                            "opportunity_count": result.opportunity_count,
                            "positive_start_offset_count": result.positive_start_offset_count,
                        }
                    )
    return hits, scan_rows


def clusters_for_hits(
    hits: Sequence[PhraseHit],
    specs: Sequence[NgramProfileSpec],
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    score_ids = score_candidate_profile_ids(specs)
    all_clusters = cluster_hits_overlap_touch(hits, cluster_scope=CLUSTER_SCOPE_ALL)
    score_clusters = cluster_hits_overlap_touch(hits, cluster_scope=CLUSTER_SCOPE_SCORE, allowed_profile_ids=score_ids)
    return all_clusters, score_clusters


def summary_rows_for_scope(
    *,
    cases: Sequence[EvalCase],
    hits: Sequence[PhraseHit],
    clusters: Sequence[Any],
    specs: Sequence[NgramProfileSpec],
    cluster_scope: str,
    score_only: bool,
) -> list[dict[str, Any]]:
    score_ids = score_candidate_profile_ids(specs)
    allowed_specs = [spec for spec in specs if not score_only or spec.profile_id in score_ids]
    hit_groups: dict[tuple[str, str, str, int], list[PhraseHit]] = defaultdict(list)
    for hit in hits:
        if score_only and hit.profile_id not in score_ids:
            continue
        hit_groups[(hit.candidate_id, hit.profile_id, hit.dictionary_cut, hit.ngram_order)].append(hit)
    cluster_groups: dict[tuple[str, str, str, int], list[Any]] = defaultdict(list)
    for cluster in clusters:
        for key in {
            (hit.candidate_id, hit.profile_id, hit.dictionary_cut, hit.ngram_order)
            for hit in cluster.hits
            if not score_only or hit.profile_id in score_ids
        }:
            cluster_groups[key].append(cluster)
    rows: list[dict[str, Any]] = []
    for case in cases:
        for spec in allowed_specs:
            for cut in spec.cuts:
                for order in spec.orders:
                    key = (case.candidate_id, spec.profile_id, cut, order)
                    group_hits = hit_groups.get(key, [])
                    group_clusters = cluster_groups.get(key, [])
                    rows.append(candidate_profile_summary_row(case, spec, cut, order, group_hits, group_clusters, cluster_scope))
    return sorted(rows, key=lambda row: (row["candidate_id"], row["cluster_scope"], row["profile_id"], row["cut"], row["ngram_order"]))


def candidate_profile_summary_row(
    case: EvalCase,
    spec: NgramProfileSpec,
    cut: str,
    order: int,
    hits: Sequence[PhraseHit],
    clusters: Sequence[Any],
    cluster_scope: str,
) -> dict[str, Any]:
    raw_hit_count = len(hits)
    cluster_count = len(clusters)
    phrase_counter = Counter(hit.phrase_id for hit in hits)
    start_counter = Counter(hit.hit_start for hit in hits)
    exact_hit_count = sum(1 for hit in hits if hit.total_phrase_hd == 0)
    exact_cluster_count = sum(1 for cluster in clusters if any(hit.total_phrase_hd == 0 for hit in cluster.hits))
    return {
        "candidate_id": case.candidate_id,
        "case_family": case.case_family,
        "damage_rate": case.damage_rate,
        "profile_id": spec.profile_id,
        "profile_origin": spec.profile_origin,
        "canonical_profile_id": spec.canonical_profile_id,
        "parameter_status": spec.parameter_status,
        "score_authority": spec.score_authority,
        "cut": cut,
        "direction": spec.direction,
        "ngram_order": order,
        "cluster_scope": cluster_scope,
        "cluster_count": cluster_count,
        "exact_cluster_count": exact_cluster_count,
        "hit_count": raw_hit_count,
        "exact_hit_count": exact_hit_count,
        "dominant_cluster_hit_fraction": max((cluster.raw_hit_count for cluster in clusters), default=0) / raw_hit_count if raw_hit_count else 0.0,
        "dominant_phrase_hit_fraction": max(phrase_counter.values(), default=0) / raw_hit_count if raw_hit_count else 0.0,
        "distinct_phrase_count": len(phrase_counter),
        "distinct_start_count": len(start_counter),
        "best_hit_signature": best_hit_signature(hits),
    }


def cluster_summary_rows(clusters: Sequence[Any], *, run_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cluster in clusters:
        case_family = ""
        damage_rate: float | str = ""
        if cluster.hits:
            damage_parts = cluster.hits[0].damage_level.split(":")
            case_family = damage_parts[0]
            damage_rate = float(damage_parts[1]) if len(damage_parts) > 1 else ""
        rows.append(
            {
                "run_id": run_id,
                "cluster_scope": cluster.cluster_scope,
                "candidate_id": cluster.candidate_id,
                "chunk_id": cluster.chunk_id,
                "case_family": case_family,
                "damage_rate": damage_rate,
                "cluster_id": cluster.cluster_id,
                "start_offset": cluster.start_offset,
                "end_offset": cluster.end_offset,
                "profiles_present": json.dumps(list(cluster.profiles_present), separators=(",", ":")),
                "cuts_present": json.dumps(list(cluster.cuts_present), separators=(",", ":")),
                "orders_present": json.dumps(list(cluster.orders_present), separators=(",", ":")),
                "raw_hit_count": cluster.raw_hit_count,
                "unique_phrase_id_count": cluster.unique_phrase_id_count,
                "unique_start_count": cluster.unique_start_count,
                "exact_hit_present": cluster.exact_hit_present,
                "exact_hit_count": cluster.exact_hit_count,
                "best_hit_signature": cluster.best_hit_signature,
            }
        )
    return sorted(rows, key=lambda row: (row["cluster_scope"], row["candidate_id"], row["cluster_id"]))


def build_summary_rows(
    cases: Sequence[EvalCase],
    hits: Sequence[PhraseHit],
    specs: Sequence[NgramProfileSpec],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    all_clusters, score_clusters = clusters_for_hits(hits, specs)
    all_rows = summary_rows_for_scope(
        cases=cases,
        hits=hits,
        clusters=all_clusters,
        specs=specs,
        cluster_scope=CLUSTER_SCOPE_ALL,
        score_only=False,
    )
    score_rows = summary_rows_for_scope(
        cases=cases,
        hits=hits,
        clusters=score_clusters,
        specs=specs,
        cluster_scope=CLUSTER_SCOPE_SCORE,
        score_only=True,
    )
    cluster_rows = cluster_summary_rows((*all_clusters, *score_clusters), run_id=RUN_LABEL)
    return all_rows, score_rows, cluster_rows


def concentration_rows(summary_rows: Sequence[Mapping[str, Any]], hits: Sequence[PhraseHit]) -> list[dict[str, Any]]:
    hit_lookup: dict[tuple[str, str, str, int], list[PhraseHit]] = defaultdict(list)
    for hit in hits:
        hit_lookup[(hit.candidate_id, hit.profile_id, hit.dictionary_cut, hit.ngram_order)].append(hit)
    rows: list[dict[str, Any]] = []
    for row in summary_rows:
        key = (str(row["candidate_id"]), str(row["profile_id"]), str(row["cut"]), int(row["ngram_order"]))
        group_hits = hit_lookup.get(key, [])
        phrase_counter = Counter(hit.phrase_id for hit in group_hits)
        start_counter = Counter(hit.hit_start for hit in group_hits)
        hit_count = len(group_hits)
        top5_phrase = sum(count for _phrase, count in phrase_counter.most_common(5))
        flags = concentration_flags(row, group_hits, phrase_counter, start_counter)
        rows.append(
            {
                "candidate_id": row["candidate_id"],
                "case_family": row["case_family"],
                "damage_rate": row["damage_rate"],
                "profile_id": row["profile_id"],
                "cut": row["cut"],
                "direction": row["direction"],
                "ngram_order": row["ngram_order"],
                "cluster_scope": row["cluster_scope"],
                "dominant_phrase_hit_fraction": max(phrase_counter.values(), default=0) / hit_count if hit_count else 0.0,
                "dominant_cluster_hit_fraction": row["dominant_cluster_hit_fraction"],
                "dominant_start_hit_fraction": max(start_counter.values(), default=0) / hit_count if hit_count else 0.0,
                "top_5_phrase_hit_fraction": top5_phrase / hit_count if hit_count else 0.0,
                "top_5_cluster_hit_fraction": row["dominant_cluster_hit_fraction"],
                "warning_flags": json.dumps(flags, separators=(",", ":")),
            }
        )
    return sorted(rows, key=lambda row: (row["candidate_id"], row["cluster_scope"], row["profile_id"], row["cut"], row["ngram_order"]))


def concentration_flags(
    row: Mapping[str, Any],
    hits: Sequence[PhraseHit],
    phrase_counter: Counter[str],
    start_counter: Counter[int],
) -> list[str]:
    flags: list[str] = []
    hit_count = len(hits)
    if not hit_count:
        return flags
    if max(phrase_counter.values(), default=0) / hit_count >= 0.75:
        flags.append("one_phrase_dominates")
    if max(start_counter.values(), default=0) / hit_count >= 0.75:
        flags.append("one_start_position_dominates")
    if float(row["dominant_cluster_hit_fraction"]) >= 0.75:
        flags.append("one_cluster_dominates")
    if int(row["ngram_order"]) == 2 and int(row["hit_count"]) > 0:
        flags.append("order2_support_diagnostic_only")
    return sorted(flags)


def null_comparison_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    positives = [row for row in rows if str(row["case_family"]).startswith("positive")]
    nulls = [row for row in rows if str(row["case_family"]).startswith("matched_")]
    groups: dict[tuple[float, str, str, int, str], dict[str, list[Mapping[str, Any]]]] = defaultdict(lambda: {"positive": [], "null": []})
    for row in positives:
        key = (float(row["damage_rate"]), str(row["profile_id"]), str(row["cut"]), int(row["ngram_order"]), str(row["cluster_scope"]))
        groups[key]["positive"].append(row)
    for row in nulls:
        key = (float(row["damage_rate"]), str(row["profile_id"]), str(row["cut"]), int(row["ngram_order"]), str(row["cluster_scope"]))
        groups[key]["null"].append(row)
    out: list[dict[str, Any]] = []
    for key, grouped in sorted(groups.items()):
        damage_rate, profile_id, cut, order, scope = key
        pos = grouped["positive"]
        nul = grouped["null"]
        pos_cluster = [float(row["cluster_count"]) for row in pos]
        null_cluster = [float(row["cluster_count"]) for row in nul]
        pos_exact_cluster = [float(row["exact_cluster_count"]) for row in pos]
        null_exact_cluster = [float(row["exact_cluster_count"]) for row in nul]
        pos_hit = [float(row["hit_count"]) for row in pos]
        null_hit = [float(row["hit_count"]) for row in nul]
        threshold = min(pos_cluster) if pos_cluster else 0.0
        out.append(
            {
                "damage_rate": damage_rate,
                "profile_id": profile_id,
                "cut": cut,
                "direction": "fwd",
                "ngram_order": order,
                "cluster_scope": scope,
                "positive_case_count": len(pos),
                "matched_null_case_count": len(nul),
                "positive_cluster_count_median": median(pos_cluster),
                "null_cluster_count_median": median(null_cluster),
                "positive_exact_cluster_count_median": median(pos_exact_cluster),
                "null_exact_cluster_count_median": median(null_exact_cluster),
                "positive_hit_count_median": median(pos_hit),
                "null_hit_count_median": median(null_hit),
                "lift_cluster_count": lift(median(pos_cluster), median(null_cluster)),
                "lift_exact_cluster_count": lift(median(pos_exact_cluster), median(null_exact_cluster)),
                "overlap_rate": overlap_rate(pos_cluster, null_cluster),
                "false_positive_rate_at_positive_threshold": (
                    sum(1 for value in null_cluster if value >= threshold) / len(null_cluster) if null_cluster else 0.0
                ),
            }
        )
    return out


def median(values: Sequence[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def lift(positive: float, null: float) -> float:
    return positive / null if null else (positive if positive else 0.0)


def overlap_rate(positive: Sequence[float], null: Sequence[float]) -> float:
    if not positive or not null:
        return 0.0
    positive_min = min(positive)
    positive_max = max(positive)
    return sum(1 for value in null if positive_min <= value <= positive_max) / len(null)


def damage_tier_summary_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, float, str, str, int, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row["case_family"]),
            float(row["damage_rate"]),
            str(row["profile_id"]),
            str(row["cut"]),
            int(row["ngram_order"]),
            str(row["cluster_scope"]),
        )
        groups[key].append(row)
    out: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        family, damage_rate, profile_id, cut, order, scope = key
        out.append(
            {
                "case_family": family,
                "damage_rate": damage_rate,
                "profile_id": profile_id,
                "cut": cut,
                "direction": "fwd",
                "ngram_order": order,
                "cluster_scope": scope,
                "case_count": len(group),
                "cluster_count_median": median([float(row["cluster_count"]) for row in group]),
                "exact_cluster_count_median": median([float(row["exact_cluster_count"]) for row in group]),
                "hit_count_median": median([float(row["hit_count"]) for row in group]),
                "dominant_phrase_hit_fraction_median": median([float(row["dominant_phrase_hit_fraction"]) for row in group]),
            }
        )
    return out


def sampled_hit_rows(hits: Sequence[PhraseHit], case_by_id: Mapping[str, EvalCase]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hit in sorted(hits, key=lambda item: (item.candidate_id, item.profile_id, item.dictionary_cut, item.ngram_order, item.hit_start, item.phrase_id))[:HIT_SAMPLE_LIMIT]:
        case = case_by_id[hit.candidate_id]
        rows.append(
            {
                "candidate_id": hit.candidate_id,
                "case_family": case.case_family,
                "damage_rate": case.damage_rate,
                "profile_id": hit.profile_id,
                "cut": hit.dictionary_cut,
                "direction": "fwd",
                "ngram_order": hit.ngram_order,
                "phrase_id": hit.phrase_id,
                "phrase_token_length": hit.phrase_token_length,
                "word_lengths": json.dumps(list(hit.word_lengths), separators=(",", ":")),
                "word_hds": json.dumps(list(hit.word_hds), separators=(",", ":")),
                "total_phrase_hd": hit.total_phrase_hd,
                "max_word_hd": hit.max_word_hd,
                "normalised_phrase_hd": hit.normalised_phrase_hd,
                "hit_start": hit.hit_start,
                "hit_end": hit.hit_end,
            }
        )
    return rows


def corpus_manifest(cases: Sequence[EvalCase], entries: Sequence[PhraseEntry]) -> dict[str, Any]:
    return {
        "phase": RUN_LABEL,
        "corpus_status": "generated",
        "source_policy": "repo_safe_synthetic_and_permanent_lane1_asset_tokens_only",
        "committed_text": False,
        "public_domain_text_committed": False,
        "copyrighted_book_text_committed": False,
        "private_local_text_committed": False,
        "uses_permanent_lane1_asset": True,
        "lane1_asset_id": LANE1_ASSET_ID,
        "case_count": len(cases),
        "case_families": sorted({case.case_family for case in cases}),
        "phrase_entry_count": len(entries),
        "orders": sorted({entry.ngram_order for entry in entries}),
        "cuts": sorted({entry.dictionary_cut for entry in entries}),
    }


def run_manifest(
    *,
    cases: Sequence[EvalCase],
    entries: Sequence[PhraseEntry],
    specs: Sequence[NgramProfileSpec],
    hits: Sequence[PhraseHit],
    output_dir: Path,
) -> dict[str, Any]:
    return {
        "phase": RUN_LABEL,
        "run_label": RUN_LABEL,
        "run_scope": RUN_SCOPE,
        "run_authority": RUN_AUTHORITY,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "production_scorer_change": PRODUCTION_SCORER_CHANGE,
        "real_candidate_scan_started": REAL_CANDIDATE_SCAN_STARTED,
        "broad_candidate_scan_started": BROAD_CANDIDATE_SCAN_STARTED,
        "controlled_eval_corpus_scan_started": CONTROLLED_EVAL_CORPUS_SCAN_STARTED,
        "uses_permanent_lane1_asset": True,
        "lane1_asset_id": LANE1_ASSET_ID,
        "asset_home": ASSET_HOME_REL,
        "orders": [2, 3],
        "cuts": ["normal", "strict"],
        "directions": ["fwd"],
        "omitted_orders": [4, 5],
        "why_omitted": {
            "4": "not present in current Lane 1 asset tranche",
            "5": "future diagnostic only",
        },
        "unsafe_interpretations": [
            "does not approve production ranking",
            "does not prove order 4 unnecessary",
            "does not promote order 2 to score-bearing",
            "does not use count/log-count weighting",
            "does not approve a broad candidate search",
        ],
        "output_dir": repo_rel(output_dir),
        "profile_manifest_hash": profile_manifest_hash(specs),
        "profile_count": len(specs),
        "case_count": len(cases),
        "phrase_entry_count": len(entries),
        "raw_hit_count": len(hits),
        "hit_rows_are_sampled": len(hits) > HIT_SAMPLE_LIMIT,
        "hit_sample_limit": HIT_SAMPLE_LIMIT,
    }


def write_readout(path: Path, manifest: Mapping[str, Any], null_rows: Sequence[Mapping[str, Any]]) -> None:
    ensure_under_repo(path)
    order3_lifts = [
        row
        for row in null_rows
        if int(row["ngram_order"]) == 3
        and str(row["cluster_scope"]) == CLUSTER_SCOPE_SCORE
        and str(row["cut"]) == "normal"
    ]
    best_lift = max((float(row["lift_cluster_count"]) for row in order3_lifts), default=0.0)
    lines = [
        "# Phase B Lane 2 Gated Diagnostic Scoring Evidence v1",
        "",
        f"Status: `diagnostic_evidence_ready_for_review`",
        "",
        f"- phase: `{manifest['phase']}`",
        f"- run scope: `{manifest['run_scope']}`",
        f"- run authority: `{manifest['run_authority']}`",
        f"- controlled eval corpus scan started: `{manifest['controlled_eval_corpus_scan_started']}`",
        f"- real candidate scan started: `{manifest['real_candidate_scan_started']}`",
        f"- broad candidate scan started: `{manifest['broad_candidate_scan_started']}`",
        f"- production scorer change: `{manifest['production_scorer_change']}`",
        f"- Lane 1 asset id: `{manifest['lane1_asset_id']}`",
        f"- profile count: `{manifest['profile_count']}`",
        f"- case count: `{manifest['case_count']}`",
        f"- phrase entry count: `{manifest['phrase_entry_count']}`",
        f"- raw hit count: `{manifest['raw_hit_count']}`",
        f"- best normal order-3 score-view cluster lift in this microbatch: `{best_lift}`",
        "",
        "This is controlled diagnostic evidence only. It does not approve production",
        "ranking changes, broad candidate scans, order-2 score authority, or any claim",
        "that order 4 is unnecessary.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_lane2_gated_diagnostic_evidence(
    output_dir: Path | None = None,
    phrase_entries: Sequence[PhraseEntry] | None = None,
) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    specs = selected_profile_specs()
    validate_profile_specs_for_lane2(specs)
    entries = tuple(phrase_entries) if phrase_entries is not None else load_lane1_asset_entries()
    cases = build_eval_cases(entries)
    hits, scan_rows = scan_cases(cases, entries, specs)
    all_summary_rows, score_summary_rows, cluster_rows = build_summary_rows(cases, hits, specs)
    combined_summary_rows = [*all_summary_rows, *score_summary_rows]
    concentration = concentration_rows(combined_summary_rows, hits)
    null_rows = null_comparison_rows(combined_summary_rows)
    damage_rows = damage_tier_summary_rows(combined_summary_rows)
    case_by_id = {case.candidate_id: case for case in cases}
    manifest = run_manifest(cases=cases, entries=entries, specs=specs, hits=hits, output_dir=selected_output_dir)

    write_json(selected_output_dir / "run_manifest.json", manifest)
    write_json(selected_output_dir / "corpus_manifest.json", corpus_manifest(cases, entries))
    write_jsonl(selected_output_dir / "positive_passages.jsonl", (case_row(case) for case in cases if case.expected_role == "positive"))
    write_jsonl(selected_output_dir / "null_passages.jsonl", (case_row(case) for case in cases if case.expected_role == "null"))
    write_jsonl(selected_output_dir / "damaged_cases.jsonl", (case_row(case) for case in cases if case.damage_mode == "substitute"))
    write_csv(selected_output_dir / "profile_manifest_rows.csv", profile_manifest_rows(specs))
    write_csv(selected_output_dir / "candidate_profile_summary_rows.csv", combined_summary_rows)
    write_csv(selected_output_dir / "candidate_cluster_summary_rows.csv", cluster_rows)
    write_csv(selected_output_dir / "sampled_hit_rows.csv", sampled_hit_rows(hits, case_by_id))
    write_csv(selected_output_dir / "null_comparison_rows.csv", null_rows)
    write_csv(selected_output_dir / "concentration_rows.csv", concentration)
    write_csv(selected_output_dir / "damage_tier_summary_rows.csv", damage_rows)
    write_csv(selected_output_dir / "scan_diagnostic_rows.csv", scan_rows)
    write_readout(selected_output_dir / "review_readout.md", manifest, null_rows)
    print(f"[{RUN_LABEL}] status=diagnostic_evidence_ready_for_review")
    print(f"[{RUN_LABEL}] output_dir={manifest['output_dir']}")
    print(f"[{RUN_LABEL}] cases={manifest['case_count']} hits={manifest['raw_hit_count']}")
    return manifest


def main() -> None:
    run_lane2_gated_diagnostic_evidence()


if __name__ == "__main__":
    main()
