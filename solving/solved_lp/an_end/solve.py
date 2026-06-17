from __future__ import annotations

"""Structured AN END solve attempt using sequence-shape diagnostics."""

import importlib.util
import csv
import json
import math
import sys
from collections.abc import Callable, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.core.types import Direction  # noqa: E402
from rune_decrypter_prime.data import liber_primus as lp  # noqa: E402
from rune_decrypter_prime.data.wordlists.loaders import load_short_word_dictionary  # noqa: E402
from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402


SOURCE_LABEL = "an_end"
RECIPE_LABEL = "recipe.an_end.stream_sequence_interruptors"
ALIASES = ["an_end", "p56", "56.jpg", "canon.56"]
MODULUS = 29

CANDIDATE_PHRASE_STARTS = [
    "AN END",
    "OF THE",
    "IN THE",
    "TO THE",
    "IS THE",
    "OF ALL",
    "IN ALL",
    "WE ARE",
    "IT IS",
    "SO IT",
]

ENCODING_DIRECTION = Direction.LTR
MAX_SEQUENCE_OFFSET = 200
GENERATED_PHRASE_LIMIT = 40
SHAPE_MATCH_KEEP = 120
FULL_ATTEMPT_SHAPE_TOP_N = 12
TOP_ATTEMPT_KEEP = 200
TOP_ATTEMPT_PRINT_COUNT = 20
EVIDENCE_DIR = ROOT / "output" / "solved_lp" / SOURCE_LABEL
EVIDENCE_PATH = EVIDENCE_DIR / "latest_solve_evidence.json"

DERIVE_MODES = ("ct_minus_pt", "pt_minus_ct")
STREAM_MODES = ("ct_minus_key", "ct_plus_key")
INTERRUPTER_SEMANTICS = ("reinsert_cipher_symbol", "remove_null")
SEQUENCE_FAMILY_ORDER = ("primes_minus_1", "primes", "fibonacci", "triangular", "squares")


def word_lengths_from_wli(wli: Sequence[Sequence[int]]) -> list[int]:
    lengths: list[int] = []
    cursor = 0
    while cursor < len(wli):
        _pos, length = wli[cursor]
        lengths.append(int(length))
        cursor += int(length)
    return lengths


def candidate_to_idx(text: str) -> list[int]:
    idx, _wli, _runes = Runeglish.encode_english_to_runes(text, direction=ENCODING_DIRECTION.value)
    return [int(value) for value in idx]


def candidate_word_lengths(text: str) -> list[int]:
    _idx, wli, _runes = Runeglish.encode_english_to_runes(text, direction=ENCODING_DIRECTION.value)
    return word_lengths_from_wli(wli)


def load_generated_phrase_starts() -> list[str]:
    try:
        tables = load_short_word_dictionary(lengths=(2, 3), direction=ENCODING_DIRECTION)
    except (FileNotFoundError, ValueError):
        tables = load_short_word_dictionary_loose(lengths=(2, 3))

    len2 = tables.get(2, {})
    len3 = tables.get(3, {})
    weighted: list[tuple[float, str]] = []
    for first, first_weight in len2.items():
        for second, second_weight in len3.items():
            weighted.append((float(first_weight) + float(second_weight), f"{first} {second}"))
    weighted.sort(key=lambda item: (-item[0], item[1]))
    return [phrase for _weight, phrase in weighted[:GENERATED_PHRASE_LIMIT]]


def load_short_word_dictionary_loose(lengths: Sequence[int]) -> dict[int, dict[str, float]]:
    tables: dict[int, dict[str, float]] = {}
    for length in lengths:
        path = ROOT / "assets" / "wordlists" / f"short_words_{ENCODING_DIRECTION.value}_len{int(length)}.csv"
        if not path.exists():
            continue
        table: dict[str, float] = {}
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                latin = (row.get("latin_word") or "").strip().upper()
                if not latin:
                    continue
                weight = float(row.get("weight", 0.0) or 0.0)
                table[latin] = table.get(latin, 0.0) + weight
        if table:
            tables[int(length)] = table
    return tables


def load_short_word_index_weights() -> dict[tuple[int, ...], float]:
    weights: dict[tuple[int, ...], float] = {}
    for length in (1, 2, 3):
        path = ROOT / "assets" / "wordlists" / f"short_words_{ENCODING_DIRECTION.value}_len{length}.csv"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                raw_indices = (row.get("rune_indices") or "").strip()
                if not raw_indices:
                    continue
                indices = tuple(int(tok) for tok in raw_indices.split())
                weight = float(row.get("weight", 0.0) or 0.0)
                weights[indices] = weights.get(indices, 0.0) + weight
    return weights


def build_candidate_phrases(word_lengths: Sequence[int]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    phrases: list[str] = []
    for phrase in [*CANDIDATE_PHRASE_STARTS, *load_generated_phrase_starts()]:
        normalized = " ".join(phrase.upper().split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            phrases.append(normalized)

    candidates: list[dict[str, Any]] = []
    for phrase in phrases:
        idx = candidate_to_idx(phrase)
        lengths = candidate_word_lengths(phrase)
        if lengths == list(word_lengths[: len(lengths)]):
            candidates.append(
                {
                    "candidate_phrase": phrase,
                    "candidate_word_lengths": lengths,
                    "candidate_idx": idx,
                }
            )
    return candidates


def primes(n: int) -> list[int]:
    out: list[int] = []
    candidate = 2
    while len(out) < n:
        is_prime = True
        for p in out:
            if p * p > candidate:
                break
            if candidate % p == 0:
                is_prime = False
                break
        if is_prime:
            out.append(candidate)
        candidate += 1
    return out


def primes_minus_one_mod_29(count: int) -> list[int]:
    return [(p - 1) % MODULUS for p in primes(count)]


def primes_mod_29(count: int) -> list[int]:
    return [p % MODULUS for p in primes(count)]


def fibonacci_mod_29(count: int) -> list[int]:
    out: list[int] = []
    a, b = 0, 1
    for _ in range(count):
        out.append(a % MODULUS)
        a, b = b, a + b
    return out


def triangular_mod_29(count: int) -> list[int]:
    return [((n * (n + 1)) // 2) % MODULUS for n in range(count)]


def squares_mod_29(count: int) -> list[int]:
    return [(n * n) % MODULUS for n in range(count)]


def sequence_families(count: int) -> dict[str, list[int]]:
    return {
        "primes_minus_1": primes_minus_one_mod_29(count),
        "primes": primes_mod_29(count),
        "fibonacci": fibonacci_mod_29(count),
        "triangular": triangular_mod_29(count),
        "squares": squares_mod_29(count),
    }


def zero_shift(values: Sequence[int]) -> list[int]:
    if not values:
        return []
    base = int(values[0])
    return [(int(value) - base) % MODULUS for value in values]


def derive_key(ct_prefix: Sequence[int], pt_prefix: Sequence[int], mode: str) -> list[int]:
    if mode == "ct_minus_pt":
        return [(int(c) - int(p)) % MODULUS for c, p in zip(ct_prefix, pt_prefix)]
    if mode == "pt_minus_ct":
        return [(int(p) - int(c)) % MODULUS for c, p in zip(ct_prefix, pt_prefix)]
    raise ValueError(f"unknown derive mode: {mode}")


def shape_match_count(left: Sequence[int], right: Sequence[int]) -> int:
    return sum(1 for a, b in zip(left, right) if int(a) == int(b))


def remove_positions(values: Sequence[Any], positions: set[int]) -> list[Any]:
    return [value for index, value in enumerate(values) if index not in positions]


def reinsert_values(core: Sequence[int], original: Sequence[int], positions: Sequence[int]) -> list[int]:
    out = list(core)
    for removed_count, pos in enumerate(sorted(positions)):
        core_pos = int(pos) - removed_count
        out.insert(core_pos, int(original[pos]))
    return out


def decrypt_stream_ct_minus_key(ct_core: Sequence[int], stream: Sequence[int]) -> list[int]:
    return [(int(c) - int(k)) % MODULUS for c, k in zip(ct_core, stream)]


def decrypt_stream_ct_plus_key(ct_core: Sequence[int], stream: Sequence[int]) -> list[int]:
    return [(int(c) + int(k)) % MODULUS for c, k in zip(ct_core, stream)]


def match_ratio(candidate: Sequence[int], reference: Sequence[int] | None) -> float | None:
    if reference is None:
        return None
    if not candidate and not reference:
        return 1.0
    denom = max(len(candidate), len(reference))
    if denom == 0:
        return 0.0
    matches = sum(1 for a, b in zip(candidate, reference) if int(a) == int(b))
    return matches / denom


def load_reference_idx() -> list[int] | None:
    reference_path = Path(__file__).with_name("reference.py")
    if not reference_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("an_end_reference", reference_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = getattr(module, "CANONICAL_AN_END_IDX", None)
    if value is None:
        return None
    return [int(item) for item in value]


def plaintext_word_tuples(values: Sequence[int], wli: Sequence[Sequence[int]]) -> list[tuple[int, ...]]:
    words: list[tuple[int, ...]] = []
    cur: list[int] = []
    for index, value in enumerate(values):
        cur.append(int(value))
        if index < len(wli) and int(wli[index][0]) == int(wli[index][1]) - 1:
            words.append(tuple(cur))
            cur = []
    if cur:
        words.append(tuple(cur))
    return words


def score_plaintext_idx(
    plaintext_idx: Sequence[int],
    render_wli: Sequence[Sequence[int]],
    word_weights: dict[tuple[int, ...], float],
) -> float | None:
    if not word_weights:
        return None
    words = plaintext_word_tuples(plaintext_idx, render_wli)
    if not words:
        return 0.0
    hit_weight = sum(float(word_weights.get(word, 0.0)) for word in words)
    hit_count = sum(1 for word in words if word in word_weights)
    return (hit_count / len(words)) + (0.01 * hit_weight)


def render_latin(values: Sequence[int], wli: Sequence[Sequence[int]], limit: int | None = None) -> str:
    return Runeglish.to_rune_latin([int(value) for value in values], wli, limit=limit)


def render_runes(values: Sequence[int], wli: Sequence[Sequence[int]], limit: int | None = None) -> str:
    return Runeglish.to_rune([int(value) for value in values], wli, limit=limit)


def all_subsets(values: Sequence[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for count in range(0, len(values) + 1):
        for subset in combinations(values, count):
            out.append([int(value) for value in subset])
    return out


def shape_sort_key(record: dict[str, Any]) -> tuple[float, int, int]:
    family_priority = -SEQUENCE_FAMILY_ORDER.index(record["sequence_family"])
    return (float(record["shape_match_ratio"]), int(record["shape_match_count"]), family_priority)


def keep_top(
    records: list[dict[str, Any]],
    record: dict[str, Any],
    *,
    limit: int,
    key: Callable[[dict[str, Any]], tuple[Any, ...]],
) -> None:
    records.append(record)
    if len(records) > limit * 4:
        records.sort(key=key, reverse=True)
        del records[limit:]


def build_shape_records(
    *,
    ct_idx: Sequence[int],
    candidates: Sequence[dict[str, Any]],
    sequences: dict[str, list[int]],
) -> list[dict[str, Any]]:
    top: list[dict[str, Any]] = []
    for candidate in candidates:
        pt_prefix = candidate["candidate_idx"]
        ct_prefix = ct_idx[: len(pt_prefix)]
        for derive_mode in DERIVE_MODES:
            derived_key = derive_key(ct_prefix, pt_prefix, derive_mode)
            derived_shape = zero_shift(derived_key)
            if not derived_shape:
                continue
            for family_name in SEQUENCE_FAMILY_ORDER:
                sequence = sequences[family_name]
                for offset in range(MAX_SEQUENCE_OFFSET + 1):
                    segment = sequence[offset : offset + len(derived_key)]
                    if len(segment) != len(derived_key):
                        continue
                    sequence_shape = zero_shift(segment)
                    count = shape_match_count(derived_shape, sequence_shape)
                    ratio = count / len(derived_shape)
                    record = {
                        "candidate_phrase": candidate["candidate_phrase"],
                        "candidate_word_lengths": candidate["candidate_word_lengths"],
                        "derive_mode": derive_mode,
                        "derived_key": derived_key,
                        "derived_key_zero_shifted": derived_shape,
                        "sequence_family": family_name,
                        "sequence_offset": offset,
                        "sequence_segment": list(segment),
                        "sequence_segment_zero_shifted": sequence_shape,
                        "shape_match_count": count,
                        "shape_match_ratio": ratio,
                    }
                    keep_top(top, record, limit=SHAPE_MATCH_KEEP, key=shape_sort_key)
    top.sort(key=shape_sort_key, reverse=True)
    return top[:SHAPE_MATCH_KEEP]


def attempt_sort_key_with_reference(record: dict[str, Any]) -> tuple[float, float, float, int]:
    match = -1.0 if record["match_ratio"] is None else float(record["match_ratio"])
    language = -math.inf if record["language_score"] is None else float(record["language_score"])
    return (match, float(record["shape_match_ratio"]), language, -int(record["interrupter_count"]))


def attempt_sort_key_without_reference(record: dict[str, Any]) -> tuple[float, float, int]:
    language = -math.inf if record["language_score"] is None else float(record["language_score"])
    return (language, float(record["shape_match_ratio"]), -int(record["interrupter_count"]))


def build_attempt_records(
    *,
    ct_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
    shape_records: Sequence[dict[str, Any]],
    sequences: dict[str, list[int]],
    interruptor_pool: Sequence[int],
    reference_idx: Sequence[int] | None,
    word_weights: dict[tuple[int, ...], float],
) -> list[dict[str, Any]]:
    top: list[dict[str, Any]] = []
    subsets = all_subsets(interruptor_pool)
    sort_key = attempt_sort_key_with_reference if reference_idx is not None else attempt_sort_key_without_reference

    for shape in shape_records[:FULL_ATTEMPT_SHAPE_TOP_N]:
        sequence = sequences[shape["sequence_family"]]
        offset = int(shape["sequence_offset"])
        for interrupters in subsets:
            interruptor_set = set(interrupters)
            ct_core = [int(value) for value in remove_positions(ct_idx, interruptor_set)]
            wli_core = remove_positions(wli, interruptor_set)
            base_sequence = sequence[offset : offset + len(ct_core)]
            if len(base_sequence) != len(ct_core):
                continue
            for absolute_shift in range(MODULUS):
                stream = [(int(value) + absolute_shift) % MODULUS for value in base_sequence]
                for stream_mode in STREAM_MODES:
                    if stream_mode == "ct_minus_key":
                        pt_core = decrypt_stream_ct_minus_key(ct_core, stream)
                    elif stream_mode == "ct_plus_key":
                        pt_core = decrypt_stream_ct_plus_key(ct_core, stream)
                    else:
                        raise ValueError(f"unknown stream mode: {stream_mode}")

                    for semantics in INTERRUPTER_SEMANTICS:
                        if semantics == "reinsert_cipher_symbol":
                            plaintext_idx = reinsert_values(pt_core, ct_idx, interrupters)
                            render_wli = wli
                        elif semantics == "remove_null":
                            plaintext_idx = list(pt_core)
                            render_wli = wli_core
                        else:
                            raise ValueError(f"unknown interrupter semantics: {semantics}")

                        ratio = match_ratio(plaintext_idx, reference_idx)
                        lang = score_plaintext_idx(plaintext_idx, render_wli, word_weights)
                        status = "candidate"
                        if ratio is not None and ratio >= 1.0:
                            status = "solved"

                        record = {
                            "candidate_phrase": shape["candidate_phrase"],
                            "candidate_word_lengths": shape["candidate_word_lengths"],
                            "derive_mode": shape["derive_mode"],
                            "derived_key": shape["derived_key"],
                            "derived_key_zero_shifted": shape["derived_key_zero_shifted"],
                            "sequence_family": shape["sequence_family"],
                            "sequence_offset": offset,
                            "sequence_segment": shape["sequence_segment"],
                            "sequence_segment_zero_shifted": shape["sequence_segment_zero_shifted"],
                            "shape_match_count": shape["shape_match_count"],
                            "shape_match_ratio": shape["shape_match_ratio"],
                            "absolute_shift": absolute_shift,
                            "stream_mode": stream_mode,
                            "interrupter_semantics": semantics,
                            "interrupters": interrupters,
                            "interrupter_count": len(interrupters),
                            "core_length": len(ct_core),
                            "candidate_plaintext_length": len(plaintext_idx),
                            "match_ratio": ratio,
                            "language_score": lang,
                            "_plaintext_idx": plaintext_idx,
                            "_render_wli": render_wli,
                            "status": status,
                        }
                        keep_top(top, record, limit=TOP_ATTEMPT_KEEP, key=sort_key)

    top.sort(key=sort_key, reverse=True)
    return attach_attempt_previews(top[:TOP_ATTEMPT_KEEP])


def attach_attempt_previews(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for record in records:
        clean = dict(record)
        plaintext_idx = clean.pop("_plaintext_idx")
        render_wli = clean.pop("_render_wli")
        clean["plaintext_latin_preview"] = render_latin(plaintext_idx, render_wli, limit=180)
        clean["plaintext_runes_preview"] = render_runes(plaintext_idx, render_wli, limit=180)
        out.append(clean)
    return out


def print_block(title: str, fields: Sequence[tuple[str, Any]]) -> None:
    print(f"\n{title}_BEGIN")
    for key, value in fields:
        print(f"{key}:", value)
    print(f"{title}_END")


def print_shape_records(records: Sequence[dict[str, Any]], limit: int = 20) -> None:
    print("\nLP_AN_END_SEQUENCE_SHAPE_SEARCH_BEGIN")
    for rank, record in enumerate(records[:limit], start=1):
        print(
            "rank:",
            rank,
            "candidate_phrase:",
            record["candidate_phrase"],
            "candidate_word_lengths:",
            record["candidate_word_lengths"],
            "derive_mode:",
            record["derive_mode"],
            "derived_key:",
            record["derived_key"],
            "derived_key_zero_shifted:",
            record["derived_key_zero_shifted"],
            "sequence_family:",
            record["sequence_family"],
            "sequence_offset:",
            record["sequence_offset"],
            "sequence_segment_zero_shifted:",
            record["sequence_segment_zero_shifted"],
            "shape_match_ratio:",
            f"{record['shape_match_ratio']:.3f}",
        )
    print("LP_AN_END_SEQUENCE_SHAPE_SEARCH_END")


def print_top_attempts(records: Sequence[dict[str, Any]], limit: int = TOP_ATTEMPT_PRINT_COUNT) -> None:
    print("\nLP_AN_END_TOP_ATTEMPTS_BEGIN")
    for rank, record in enumerate(records[:limit], start=1):
        print(
            "rank:",
            rank,
            "candidate_phrase:",
            record["candidate_phrase"],
            "derive_mode:",
            record["derive_mode"],
            "sequence_family:",
            record["sequence_family"],
            "sequence_offset:",
            record["sequence_offset"],
            "absolute_shift:",
            record["absolute_shift"],
            "stream_mode:",
            record["stream_mode"],
            "shape_match_ratio:",
            f"{record['shape_match_ratio']:.3f}",
            "interrupter_semantics:",
            record["interrupter_semantics"],
            "interrupters:",
            record["interrupters"],
            "interrupter_count:",
            record["interrupter_count"],
            "match_ratio:",
            record["match_ratio"],
            "language_score:",
            record["language_score"],
            "plaintext_latin_preview:",
            record["plaintext_latin_preview"],
        )
    print("LP_AN_END_TOP_ATTEMPTS_END")


def main() -> int:
    payload = lp.payload_from_label(SOURCE_LABEL)
    recipe = lp.resolve_solve_recipe_label(RECIPE_LABEL)
    ct_idx = [int(value) for value in payload.ct_idx]
    wli = [list(pair) for pair in payload.wli]
    metadata = payload.metadata
    main_page_start = metadata.get("main_page_start")
    main_page_end = metadata.get("main_page_end")
    word_lengths = word_lengths_from_wli(wli)
    zero_positions = [index for index, value in enumerate(ct_idx) if int(value) == 0]
    candidates = build_candidate_phrases(word_lengths)
    reference_idx = load_reference_idx()
    max_sequence_count = MAX_SEQUENCE_OFFSET + len(ct_idx) + 1
    sequences = sequence_families(max_sequence_count)
    word_weights = load_short_word_index_weights()

    run_config = {
        "source_label": SOURCE_LABEL,
        "resolved_source_label": metadata["source_label"],
        "aliases": ALIASES,
        "main_page_start": main_page_start,
        "main_page_end": main_page_end,
        "ciphertext_length": len(ct_idx),
        "wli_length": len(wli),
        "word_lengths": word_lengths,
        "ciphertext_zero_count": len(zero_positions),
        "ciphertext_zero_positions": zero_positions,
        "recipe": recipe.recipe_label,
        "cipher_family": recipe.cipher_family,
        "recipe_hint": recipe.reference_key_or_shift,
        "method": "zero_shifted_sequence_shape_search_with_zero_position_interruptors",
        "candidate_phrase_count": len(candidates),
        "curated_candidate_phrase_count": len(CANDIDATE_PHRASE_STARTS),
        "generated_phrase_limit": GENERATED_PHRASE_LIMIT,
        "prime_offset_max": MAX_SEQUENCE_OFFSET,
        "sequence_offset_max": MAX_SEQUENCE_OFFSET,
        "sequence_families_tested": list(SEQUENCE_FAMILY_ORDER),
        "derive_modes_tested": list(DERIVE_MODES),
        "stream_modes_tested": list(STREAM_MODES),
        "interrupter_pool_strategy": "ciphertext_zero_positions",
        "interrupter_semantics_tested": list(INTERRUPTER_SEMANTICS),
        "canonical_reference_available": reference_idx is not None,
    }

    print_block(
        "LP_AN_END_RUN_CONFIG",
        [
            ("source_label", run_config["source_label"]),
            ("resolved_source_label", run_config["resolved_source_label"]),
            ("aliases", run_config["aliases"]),
            ("main_page_start", run_config["main_page_start"]),
            ("main_page_end", run_config["main_page_end"]),
            ("ciphertext_length", run_config["ciphertext_length"]),
            ("wli_length", run_config["wli_length"]),
            ("word_lengths", run_config["word_lengths"]),
            ("ciphertext_zero_count", run_config["ciphertext_zero_count"]),
            ("ciphertext_zero_positions", run_config["ciphertext_zero_positions"]),
            ("recipe", run_config["recipe"]),
            ("cipher_family", run_config["cipher_family"]),
            ("recipe_hint", run_config["recipe_hint"]),
            ("candidate_phrase_count", run_config["candidate_phrase_count"]),
            ("prime_offset_max", run_config["prime_offset_max"]),
            ("sequence_offset_max", run_config["sequence_offset_max"]),
            ("sequence_families_tested", run_config["sequence_families_tested"]),
            ("interrupter_pool_strategy", run_config["interrupter_pool_strategy"]),
            ("interrupter_semantics_tested", run_config["interrupter_semantics_tested"]),
        ],
    )

    shape_records = build_shape_records(ct_idx=ct_idx, candidates=candidates, sequences=sequences)
    print_shape_records(shape_records)

    top_attempts = build_attempt_records(
        ct_idx=ct_idx,
        wli=wli,
        shape_records=shape_records,
        sequences=sequences,
        interruptor_pool=zero_positions,
        reference_idx=reference_idx,
        word_weights=word_weights,
    )
    print_top_attempts(top_attempts)

    best = top_attempts[0] if top_attempts else {}
    solved = bool(best) and best.get("match_ratio") is not None and float(best["match_ratio"]) >= 1.0
    final = {
        "source_label": SOURCE_LABEL,
        "resolved_source_label": metadata["source_label"],
        "aliases": ALIASES,
        "main_page_start": main_page_start,
        "main_page_end": main_page_end,
        "recipe": recipe.recipe_label,
        "cipher_family": recipe.cipher_family,
        "method": run_config["method"],
        "candidate_phrase": best.get("candidate_phrase"),
        "derive_mode": best.get("derive_mode"),
        "sequence_family": best.get("sequence_family"),
        "sequence_offset": best.get("sequence_offset"),
        "absolute_shift": best.get("absolute_shift"),
        "stream_mode": best.get("stream_mode"),
        "interrupter_semantics": best.get("interrupter_semantics"),
        "found_interruptors": best.get("interrupters", []),
        "found_interrupter_count": best.get("interrupter_count", 0),
        "match_ratio": best.get("match_ratio"),
        "best_match_ratio": best.get("match_ratio"),
        "best_shape_match_ratio": best.get("shape_match_ratio"),
        "best_candidate_phrase": best.get("candidate_phrase"),
        "best_sequence_family": best.get("sequence_family"),
        "best_sequence_offset": best.get("sequence_offset"),
        "best_interrupters": best.get("interrupters", []),
        "status": "solved" if solved else "diagnostic_not_yet_solved",
        "notes": None
        if solved
        else "structured zero-shifted sequence/interrupter search did not reach exact reference match",
        "plaintext_latin": best.get("plaintext_latin_preview"),
        "plaintext_runes": best.get("plaintext_runes_preview"),
    }

    print_block(
        "LP_AN_END_FINAL_RESULT",
        [
            ("source_label", final["source_label"]),
            ("resolved_source_label", final["resolved_source_label"]),
            ("aliases", final["aliases"]),
            ("main_page_start", final["main_page_start"]),
            ("main_page_end", final["main_page_end"]),
            ("recipe", final["recipe"]),
            ("cipher_family", final["cipher_family"]),
            ("method", final["method"]),
            ("candidate_phrase", final["candidate_phrase"]),
            ("derive_mode", final["derive_mode"]),
            ("sequence_family", final["sequence_family"]),
            ("sequence_offset", final["sequence_offset"]),
            ("absolute_shift", final["absolute_shift"]),
            ("stream_mode", final["stream_mode"]),
            ("interrupter_semantics", final["interrupter_semantics"]),
            ("found_interruptors", final["found_interruptors"]),
            ("found_interrupter_count", final["found_interrupter_count"]),
            ("match_ratio", final["match_ratio"]),
            ("best_match_ratio", final["best_match_ratio"]),
            ("best_shape_match_ratio", final["best_shape_match_ratio"]),
            ("best_candidate_phrase", final["best_candidate_phrase"]),
            ("best_sequence_family", final["best_sequence_family"]),
            ("best_sequence_offset", final["best_sequence_offset"]),
            ("best_interrupters", final["best_interrupters"]),
            ("status", final["status"]),
            ("notes", final["notes"]),
            ("plaintext_latin", final["plaintext_latin"]),
            ("plaintext_runes", final["plaintext_runes"]),
        ],
    )

    evidence = {
        "source_label": SOURCE_LABEL,
        "resolved_source_label": metadata["source_label"],
        "recipe": recipe.recipe_label,
        "cipher_family": recipe.cipher_family,
        "run_config": run_config,
        "sequence_shape_search": shape_records,
        "top_attempts": top_attempts[:TOP_ATTEMPT_PRINT_COUNT],
        "best_attempt": best,
        "final": final,
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
