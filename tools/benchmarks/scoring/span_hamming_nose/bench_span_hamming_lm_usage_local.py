from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Iterable

import numpy as np

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parents[4]
    _SRC = _ROOT / "src"
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    if _SRC.exists() and str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.data.cipher_tests.plaintext import (
    long_plaintext,
    plaintext1,
    plaintext1_rev,
    plaintext_english_string,
)
from rune_decrypter_prime.scoring.span_hamming import (
    SpanCalibratedAssets,
    SpanHammingBackend,
    SpanHammingConfig,
    SpanHammingLmAssetsV2,
)
from rune_decrypter_prime.utils.runeglish import Runeglish
from tools.benchmarks.scoring.span_hamming_nose.usage_benchmark_common import (
    SpanHammingBenchmarkRuntimeConfig,
    corrupt_with_random,
    make_block_shuffle,
    make_fragment_soup,
    make_random_text,
    make_repeated_motif,
    score_text_with_assets,
    summarize_numeric,
)


REPO_ROOT = Path(__file__).resolve().parents[4]

# Config block: edit constants, no CLI.
SPAN_ASSETS_DIR = Path("output/tools/benchmarks/scoring/span_hamming_nose_assets_v1")
LM_ASSETS_JSON = Path(
    "output/tools/benchmarks/scoring/span_hamming_nose_assets_wordlen_v1/"
    "20260304T053856Z__span_hamming_nose_assets_wordlen_v1/"
    "span_hamming_nose_assets_wordlen_v1.json"
)
OUTPUT_ROOT = Path("output/tools/benchmarks/scoring/span_hamming_nose_usage_local")
RUN_LABEL = "span_hamming_lm_usage_local"
BENCH_PROFILE = "hours"  # edit this constant to switch profiles

DIRECTION = "ltr"
CLAMP_MIN = 1e-6
CLAMP_MAX = 1.0 - 1e-6
LM_WEIGHT = 0.75
LM_WEIGHT_MARGIN = 1.0
LM_WEIGHT_MEAN_BIN_INDEX = 1.0
LM_WEIGHT_MEAN_BIN_LENGTH = 1.0
LM_WEIGHT_TAIL_MASS = 1.0
LM_PROFILE_SOURCE = "span_raw_by_len"
LM_TAIL_START_INDEX = 5
OBJECTIVE_FAMILY = "pct"
SPAN_HAMMING_COVERAGE_MIN = 0.0
SPAN_HAMMING_QUALITY_MIN = 0.0
SPAN_HAMMING_SPAN_PCT_MIN = 0.98
SPAN_HAMMING_CHAR_PCT_MIN = None
SPAN_HAMMING_COMBINE_MODE = "min"
SPAN_HAMMING_WEIGHT_SPAN = 1.0
SPAN_HAMMING_WEIGHT_CHAR = 0.0
SPAN_HAMMING_USE_CHAR_CHANNEL = False
SPAN_HAMMING_GATE_FAIL_POLICY = "score_floor"
SPAN_HAMMING_GATE_SCORE_FLOOR = None
SUMMARY_CHECKPOINT_EVERY_ROWS = 500
PROGRESS_PRINT_EVERY_ROWS = 100

MOTIF = [4, 24, 16, 18]
SHORT_FRAGMENT_LENGTHS = [3, 4, 5]
BLOCK_SHUFFLE_BLOCK_SIZE = 4

SPAN_CONFIG = SpanHammingConfig()

PROFILE_CONFIGS = {
    "quick": {
        "lengths": [100, 200, 400],
        "n_real_samples_per_length": 4,
        "corruption_pcts": [0, 10, 20, 40, 60, 80, 100],
        "random_seeds": list(range(6)),
        "use_corpora": [
            "alice_well_native",
            "mad_tea_native",
            "mad_tea_native_rev",
            "mad_tea_runeglish",
            "bench_manual_signal",
        ],
    },
    "long": {
        "lengths": [100, 200, 400, 800, 1200, 1600, 2000],
        "n_real_samples_per_length": 8,
        "corruption_pcts": [0, 5, 10, 20, 30, 40, 60, 80, 100],
        "random_seeds": list(range(14)),
        "use_corpora": [
            "alice_well_native",
            "mad_tea_native",
            "mad_tea_native_rev",
            "mad_tea_runeglish",
            "bench_manual_signal",
            "bench_manual_observatory",
            "bench_manual_repetition",
            "bench_manual_engineering",
            "bench_manual_archives",
            "bench_manual_compendium_a",
            "bench_manual_compendium_b",
        ],
    },
    "hours": {
        "lengths": [100, 200, 400, 800, 1200, 1600, 2000],
        "n_real_samples_per_length": 16,
        "corruption_pcts": [0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "random_seeds": list(range(48)),
        "use_corpora": [
            "alice_well_native",
            "mad_tea_native",
            "mad_tea_native_rev",
            "mad_tea_runeglish",
            "bench_manual_signal",
            "bench_manual_observatory",
            "bench_manual_repetition",
            "bench_manual_engineering",
            "bench_manual_archives",
            "bench_manual_coast",
            "bench_manual_instrument",
            "bench_manual_compendium_a",
            "bench_manual_compendium_b",
            "bench_manual_compendium_c",
            "bench_manual_compendium_d",
            "bench_manual_compendium_e",
        ],
    },
}

ENGLISH_BENCH_TEXTS = {
    "bench_manual_signal": (
        "The lantern room stayed silent while the sea pressed against the cliff below. "
        "Each watcher wrote the same report in a different hand, and every copy drifted "
        "toward a different conclusion. A pattern that looked convincing at first broke "
        "apart once the longer phrases were compared side by side. The short fragments "
        "still matched, but the shape of the language no longer held."
    ),
    "bench_manual_observatory": (
        "At the old observatory the tables were crowded with brass tools, cracked charts, "
        "and notebooks full of careful revisions. The apprentice trusted the first strong "
        "signal, but the archivist kept asking whether the good spans belonged to a real "
        "message or only to a clever accident repeated across the page. When they measured "
        "the lengths of the surviving phrases, the impostor text began to reveal itself."
    ),
    "bench_manual_repetition": (
        "A false chant can sound persuasive when the same bright cluster returns again and "
        "again. It borrows rhythm from meaning without carrying meaning forward. The opening "
        "beats feel stable, the local pieces seem plausible, and yet the sequence never learns "
        "how to grow. A real passage bends, varies, and keeps enough long structure to resist "
        "the trap of easy repetition. The moment you compare several windows of the text, "
        "the counterfeit begins to reveal how narrow its vocabulary and transitions really are."
    ),
    "bench_manual_engineering": (
        "Every test bench in the workshop had its own habits, and each habit produced a different "
        "kind of mistake. One table favoured neat fragments that looked plausible in isolation. "
        "Another amplified repeated clusters until they felt authoritative. The useful notes were "
        "never the loudest notes. They were the ones that remained coherent after the whole passage "
        "was inspected, from the short joins to the longest surviving spans. When the team reviewed "
        "the results, they learned to trust evidence that stayed stable under corruption, shuffling, "
        "and deliberate interference rather than evidence that only dazzled at first contact. "
        "A scoring system that cannot survive those comparisons is not ready to guide a search. "
        "It must separate tidy local imitation from genuine structure over many independent samples."
    ),
    "bench_manual_archives": (
        "The archive room was built to preserve variation, not just repetition. Shelves held reports, "
        "letters, field journals, draft translations, and corrections written years apart. A careless "
        "reader could find the same short pattern in dozens of places and convince himself that the work "
        "was complete. A careful reader compared the changing structure of the text across long passages, "
        "not only the easy local echoes. Whenever the assistants tested a suspicious manuscript, they asked "
        "whether the long bins still carried weight, whether the middle ranges were balanced, and whether "
        "the tail behaviour looked like genuine language instead of an engineered imitation. Those habits "
        "saved them from elegant frauds more than once. The archives rewarded patience because shallow "
        "similarity was cheap but sustained consistency was rare."
    ),
    "bench_manual_coast": (
        "By the coast the signal station watched weather, traffic, and the long silence between storms. "
        "Operators copied incoming marks into ledgers and compared them against prior weeks of traffic. "
        "A forged report could imitate a few local turns of phrase, especially if the forger had seen the "
        "latest bulletins, but it usually failed in the longer arcs. The sequence of names, warnings, and "
        "measured responses lost its natural shape. Experienced clerks noticed that the false messages either "
        "collapsed into short recycled fragments or drifted toward mechanical repetition. The best checks were "
        "not decorative. They were the checks that held when the message was damaged, partially shuffled, or "
        "stretched beyond the easy patterns the forger expected to exploit."
    ),
    "bench_manual_instrument": (
        "An instrument log tells the truth slowly. It records calibrations, failures, resets, and the small "
        "adjustments that keep a system stable over time. In the laboratory, the staff learned that an invented "
        "log often looked strongest in short windows because the author overused familiar terminology and repeated "
        "the same compact structures. The authentic log wandered more naturally through setup, observation, and "
        "revision. It returned to the important terms when necessary, but it also carried enough long-span variation "
        "to remain informative after the obvious phrases were discounted. Robust scoring should reward that balance "
        "instead of treating every high-frequency fragment as evidence of real structure. A practical benchmark should "
        "therefore compare many slices, many corruption levels, and many independent random draws before trusting a gain."
    ),
    "bench_manual_compendium_a": (
        "The lantern room stayed silent while the sea pressed against the cliff below. "
        "Each watcher wrote the same report in a different hand, and every copy drifted "
        "toward a different conclusion. A pattern that looked convincing at first broke "
        "apart once the longer phrases were compared side by side. The short fragments "
        "still matched, but the shape of the language no longer held. "
        "At the old observatory the tables were crowded with brass tools, cracked charts, "
        "and notebooks full of careful revisions. The apprentice trusted the first strong "
        "signal, but the archivist kept asking whether the good spans belonged to a real "
        "message or only to a clever accident repeated across the page. When they measured "
        "the lengths of the surviving phrases, the impostor text began to reveal itself. "
        "Every test bench in the workshop had its own habits, and each habit produced a different "
        "kind of mistake. One table favoured neat fragments that looked plausible in isolation. "
        "Another amplified repeated clusters until they felt authoritative. The useful notes were "
        "never the loudest notes. They were the ones that remained coherent after the whole passage "
        "was inspected, from the short joins to the longest surviving spans. When the team reviewed "
        "the results, they learned to trust evidence that stayed stable under corruption, shuffling, "
        "and deliberate interference rather than evidence that only dazzled at first contact. "
        "By the coast the signal station watched weather, traffic, and the long silence between storms. "
        "Operators copied incoming marks into ledgers and compared them against prior weeks of traffic. "
        "A forged report could imitate a few local turns of phrase, especially if the forger had seen the "
        "latest bulletins, but it usually failed in the longer arcs. The sequence of names, warnings, and "
        "measured responses lost its natural shape."
    ),
    "bench_manual_compendium_b": (
        "The archive room was built to preserve variation, not just repetition. Shelves held reports, "
        "letters, field journals, draft translations, and corrections written years apart. A careless "
        "reader could find the same short pattern in dozens of places and convince himself that the work "
        "was complete. A careful reader compared the changing structure of the text across long passages, "
        "not only the easy local echoes. Whenever the assistants tested a suspicious manuscript, they asked "
        "whether the long bins still carried weight, whether the middle ranges were balanced, and whether "
        "the tail behaviour looked like genuine language instead of an engineered imitation. "
        "A false chant can sound persuasive when the same bright cluster returns again and again. "
        "It borrows rhythm from meaning without carrying meaning forward. The opening beats feel stable, "
        "the local pieces seem plausible, and yet the sequence never learns how to grow. "
        "An instrument log tells the truth slowly. It records calibrations, failures, resets, and the small "
        "adjustments that keep a system stable over time. In the laboratory, the staff learned that an invented "
        "log often looked strongest in short windows because the author overused familiar terminology and repeated "
        "the same compact structures. The authentic log wandered more naturally through setup, observation, and "
        "revision. It returned to the important terms when necessary, but it also carried enough long-span variation "
        "to remain informative after the obvious phrases were discounted. Robust scoring should reward that balance "
        "instead of treating every high-frequency fragment as evidence of real structure."
    ),
    "bench_manual_compendium_c": (
        "The lantern room stayed silent while the sea pressed against the cliff below. "
        "Each watcher wrote the same report in a different hand, and every copy drifted toward a different conclusion. "
        "A pattern that looked convincing at first broke apart once the longer phrases were compared side by side. "
        "The short fragments still matched, but the shape of the language no longer held. "
        "At the old observatory the tables were crowded with brass tools, cracked charts, and notebooks full of careful revisions. "
        "The apprentice trusted the first strong signal, but the archivist kept asking whether the good spans belonged to a real "
        "message or only to a clever accident repeated across the page. "
        "Every test bench in the workshop had its own habits, and each habit produced a different kind of mistake. "
        "One table favoured neat fragments that looked plausible in isolation. Another amplified repeated clusters until they felt "
        "authoritative. The useful notes were never the loudest notes. They were the ones that remained coherent after the whole "
        "passage was inspected, from the short joins to the longest surviving spans. "
        "The archive room was built to preserve variation, not just repetition. Shelves held reports, letters, field journals, "
        "draft translations, and corrections written years apart. A careless reader could find the same short pattern in dozens "
        "of places and convince himself that the work was complete. "
        "By the coast the signal station watched weather, traffic, and the long silence between storms. Operators copied incoming "
        "marks into ledgers and compared them against prior weeks of traffic. A forged report could imitate a few local turns of "
        "phrase, but it usually failed in the longer arcs. "
        "An instrument log tells the truth slowly. It records calibrations, failures, resets, and the small adjustments that keep "
        "a system stable over time. In the laboratory, the staff learned that an invented log often looked strongest in short windows "
        "because the author overused familiar terminology and repeated the same compact structures."
    ),
    "bench_manual_compendium_d": (
        "A false chant can sound persuasive when the same bright cluster returns again and again. It borrows rhythm from meaning without "
        "carrying meaning forward. The opening beats feel stable, the local pieces seem plausible, and yet the sequence never learns how to grow. "
        "The archive room was built to preserve variation, not just repetition. Shelves held reports, letters, field journals, draft translations, "
        "and corrections written years apart. Whenever the assistants tested a suspicious manuscript, they asked whether the long bins still carried "
        "weight, whether the middle ranges were balanced, and whether the tail behaviour looked like genuine language instead of an engineered imitation. "
        "By the coast the signal station watched weather, traffic, and the long silence between storms. Experienced clerks noticed that the false messages "
        "either collapsed into short recycled fragments or drifted toward mechanical repetition. "
        "Every test bench in the workshop had its own habits, and each habit produced a different kind of mistake. One table favoured neat fragments "
        "that looked plausible in isolation. Another amplified repeated clusters until they felt authoritative. A scoring system that cannot survive "
        "comparisons across corruption, shuffling, and repeated interference is not ready to guide a real search. "
        "An instrument log tells the truth slowly. The authentic log wandered more naturally through setup, observation, and revision. It returned to the "
        "important terms when necessary, but it also carried enough long-span variation to remain informative after the obvious phrases were discounted. "
        "The strongest test was never a single bright score. It was the ability of the message to remain coherent after the easy local evidence had been "
        "discounted and the long structure had to carry more of the weight."
    ),
    "bench_manual_compendium_e": (
        "The lantern room stayed silent while the sea pressed against the cliff below. Each watcher wrote the same report in a different hand, and every copy drifted toward a different conclusion. "
        "At the old observatory the tables were crowded with brass tools, cracked charts, and notebooks full of careful revisions. The apprentice trusted the first strong signal, but the archivist kept asking whether the good spans belonged to a real message or only to a clever accident repeated across the page. "
        "Every test bench in the workshop had its own habits, and each habit produced a different kind of mistake. One table favoured neat fragments that looked plausible in isolation. Another amplified repeated clusters until they felt authoritative. The useful notes were never the loudest notes. They were the ones that remained coherent after the whole passage was inspected, from the short joins to the longest surviving spans. "
        "The archive room was built to preserve variation, not just repetition. Shelves held reports, letters, field journals, draft translations, and corrections written years apart. A careless reader could find the same short pattern in dozens of places and convince himself that the work was complete. A careful reader compared the changing structure of the text across long passages, not only the easy local echoes. "
        "By the coast the signal station watched weather, traffic, and the long silence between storms. Operators copied incoming marks into ledgers and compared them against prior weeks of traffic. A forged report could imitate a few local turns of phrase, especially if the forger had seen the latest bulletins, but it usually failed in the longer arcs. The sequence of names, warnings, and measured responses lost its natural shape. "
        "An instrument log tells the truth slowly. It records calibrations, failures, resets, and the small adjustments that keep a system stable over time. In the laboratory, the staff learned that an invented log often looked strongest in short windows because the author overused familiar terminology and repeated the same compact structures. The authentic log wandered more naturally through setup, observation, and revision. "
        "A false chant can sound persuasive when the same bright cluster returns again and again. It borrows rhythm from meaning without carrying meaning forward. The opening beats feel stable, the local pieces seem plausible, and yet the sequence never learns how to grow. A real passage bends, varies, and keeps enough long structure to resist the trap of easy repetition. "
        "Robust scoring should reward balance instead of treating every high-frequency fragment as evidence of real structure. A practical benchmark should compare many slices, many corruption levels, and many independent random draws before trusting a gain."
    ),
}


def _resolve_repo_path(path_like: Path | str) -> Path:
    p = Path(path_like).expanduser()
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def _utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _select_profile() -> dict:
    try:
        return dict(PROFILE_CONFIGS[str(BENCH_PROFILE)])
    except KeyError as exc:
        raise ValueError(
            f"Unknown BENCH_PROFILE {BENCH_PROFILE!r}; expected one of {sorted(PROFILE_CONFIGS)}"
        ) from exc


def _pick_real_slices(corpus: np.ndarray, length: int, count: int) -> list[np.ndarray]:
    max_start = corpus.size - int(length)
    if max_start < 0:
        raise ValueError(f"Requested length {length} exceeds corpus size {corpus.size}")
    if max_start == 0:
        return [corpus.copy()]
    starts = np.linspace(0, max_start, num=int(count), dtype=np.int64)
    return [corpus[int(start) : int(start) + int(length)].copy() for start in starts]


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _open_csv_writer(path: Path, fieldnames: list[str]) -> tuple[object, csv.DictWriter]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    writer.writeheader()
    fh.flush()
    return fh, writer


def _english_to_indices(text: str) -> np.ndarray:
    idx, _wli, _rune_str = Runeglish.encode_english_to_runes(text, direction=DIRECTION)
    return np.asarray(idx, dtype=np.uint8)


def _iter_corpus_specs() -> Iterable[dict]:
    yield {
        "name": "alice_well_native",
        "kind": "repo_native",
        "text": np.asarray(long_plaintext, dtype=np.uint8),
    }
    yield {
        "name": "mad_tea_native",
        "kind": "repo_native",
        "text": np.asarray(plaintext1, dtype=np.uint8),
    }
    yield {
        "name": "mad_tea_native_rev",
        "kind": "repo_native",
        "text": np.asarray(plaintext1_rev, dtype=np.uint8),
    }
    yield {
        "name": "mad_tea_runeglish",
        "kind": "runeglish_english",
        "text": _english_to_indices(plaintext_english_string),
    }
    for name, english in ENGLISH_BENCH_TEXTS.items():
        yield {
            "name": str(name),
            "kind": "runeglish_english",
            "text": _english_to_indices(english),
        }


def _build_enabled_corpora(profile: dict) -> list[dict]:
    wanted = {str(name) for name in profile["use_corpora"]}
    corpora = [spec for spec in _iter_corpus_specs() if str(spec["name"]) in wanted]
    found = {str(spec["name"]) for spec in corpora}
    missing = sorted(wanted - found)
    if missing:
        raise ValueError(f"Unknown corpus names in profile {BENCH_PROFILE!r}: {missing}")
    return corpora


def _build_summary_rows(rows: list[dict], corpora: list[dict], profile: dict) -> list[dict]:
    out_rows: list[dict] = []
    grouped: dict[tuple[str, str, str, int], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                str(row["corpus_name"]),
                str(row["family"]),
                str(row["condition"]),
                int(row["length"]),
            )
        ].append(row)

    clean_refs: dict[tuple[str, int], dict[str, float]] = {}
    for corpus_spec in corpora:
        corpus_name = str(corpus_spec["name"])
        for length in profile["lengths"]:
            clean_rows = grouped.get((corpus_name, "corruption_curve", "corrupt_000", int(length)), [])
            if not clean_rows:
                continue
            clean_refs[(corpus_name, int(length))] = {
                "span_pct_mean": summarize_numeric(float(r["span_pct"]) for r in clean_rows)["mean"],
                "lm_profile_pct_mean": summarize_numeric(
                    float(r["lm_profile_pct"])
                    for r in clean_rows
                    if r["lm_profile_pct"] not in ("", "None")
                )["mean"],
                "lm_margin_pct_mean": summarize_numeric(
                    float(r["lm_profile_margin_l1_pct_noise"])
                    for r in clean_rows
                    if r["lm_profile_margin_l1_pct_noise"] not in ("", "None")
                )["mean"],
                "lm_mean_bin_index_pct_mean": summarize_numeric(
                    float(r["lm_mean_bin_index_pct_noise"])
                    for r in clean_rows
                    if r["lm_mean_bin_index_pct_noise"] not in ("", "None")
                )["mean"],
                "lm_mean_bin_length_pct_mean": summarize_numeric(
                    float(r["lm_mean_bin_length_pct_noise"])
                    for r in clean_rows
                    if r["lm_mean_bin_length_pct_noise"] not in ("", "None")
                )["mean"],
                "lm_tail_mass_pct_mean": summarize_numeric(
                    float(r["lm_tail_mass_pct_noise"])
                    for r in clean_rows
                    if r["lm_tail_mass_pct_noise"] not in ("", "None")
                )["mean"],
                "pre_gate_total_pct_mean": summarize_numeric(float(r["pre_gate_total_pct"]) for r in clean_rows)["mean"],
                "runtime_total_pct_mean": summarize_numeric(float(r["runtime_total_pct"]) for r in clean_rows)["mean"],
                "final_pct_mean": summarize_numeric(float(r["final_pct"]) for r in clean_rows)["mean"],
            }

    for (corpus_name, family, condition, length), bucket_rows in sorted(grouped.items()):
        base_stats = summarize_numeric(float(r["span_pct"]) for r in bucket_rows)
        lm_profile_stats = summarize_numeric(
            float(r["lm_profile_pct"])
            for r in bucket_rows
            if r["lm_profile_pct"] not in ("", "None")
        )
        lm_margin_stats = summarize_numeric(
            float(r["lm_profile_margin_l1_pct_noise"])
            for r in bucket_rows
            if r["lm_profile_margin_l1_pct_noise"] not in ("", "None")
        )
        lm_mean_bin_index_stats = summarize_numeric(
            float(r["lm_mean_bin_index_pct_noise"])
            for r in bucket_rows
            if r["lm_mean_bin_index_pct_noise"] not in ("", "None")
        )
        lm_mean_bin_length_stats = summarize_numeric(
            float(r["lm_mean_bin_length_pct_noise"])
            for r in bucket_rows
            if r["lm_mean_bin_length_pct_noise"] not in ("", "None")
        )
        lm_tail_mass_stats = summarize_numeric(
            float(r["lm_tail_mass_pct_noise"])
            for r in bucket_rows
            if r["lm_tail_mass_pct_noise"] not in ("", "None")
        )
        pre_gate_stats = summarize_numeric(float(r["pre_gate_total_pct"]) for r in bucket_rows)
        runtime_stats = summarize_numeric(float(r["runtime_total_pct"]) for r in bucket_rows)
        final_stats = summarize_numeric(float(r["final_pct"]) for r in bucket_rows)
        gate_failed_stats = summarize_numeric(float(bool(r["gate_failed"])) for r in bucket_rows)
        lm_applied_stats = summarize_numeric(float(bool(r["lm_applied_to_score"])) for r in bucket_rows)
        clean_ref = clean_refs.get((corpus_name, int(length)), {})
        out_rows.append(
            {
                "corpus_name": corpus_name,
                "corpus_kind": str(bucket_rows[0]["corpus_kind"]),
                "family": family,
                "condition": condition,
                "length": int(length),
                "n": int(base_stats["n"]),
                "span_pct_mean": base_stats["mean"],
                "span_pct_std": base_stats["std"],
                "span_pct_p05": base_stats["p05"],
                "span_pct_median": base_stats["median"],
                "span_pct_p95": base_stats["p95"],
                "lm_profile_pct_mean": lm_profile_stats["mean"],
                "lm_profile_pct_std": lm_profile_stats["std"],
                "lm_profile_pct_p05": lm_profile_stats["p05"],
                "lm_profile_pct_median": lm_profile_stats["median"],
                "lm_profile_pct_p95": lm_profile_stats["p95"],
                "lm_margin_pct_mean": lm_margin_stats["mean"],
                "lm_margin_pct_std": lm_margin_stats["std"],
                "lm_margin_pct_p05": lm_margin_stats["p05"],
                "lm_margin_pct_median": lm_margin_stats["median"],
                "lm_margin_pct_p95": lm_margin_stats["p95"],
                "lm_mean_bin_index_pct_mean": lm_mean_bin_index_stats["mean"],
                "lm_mean_bin_index_pct_std": lm_mean_bin_index_stats["std"],
                "lm_mean_bin_index_pct_p05": lm_mean_bin_index_stats["p05"],
                "lm_mean_bin_index_pct_median": lm_mean_bin_index_stats["median"],
                "lm_mean_bin_index_pct_p95": lm_mean_bin_index_stats["p95"],
                "lm_mean_bin_length_pct_mean": lm_mean_bin_length_stats["mean"],
                "lm_mean_bin_length_pct_std": lm_mean_bin_length_stats["std"],
                "lm_mean_bin_length_pct_p05": lm_mean_bin_length_stats["p05"],
                "lm_mean_bin_length_pct_median": lm_mean_bin_length_stats["median"],
                "lm_mean_bin_length_pct_p95": lm_mean_bin_length_stats["p95"],
                "lm_tail_mass_pct_mean": lm_tail_mass_stats["mean"],
                "lm_tail_mass_pct_std": lm_tail_mass_stats["std"],
                "lm_tail_mass_pct_p05": lm_tail_mass_stats["p05"],
                "lm_tail_mass_pct_median": lm_tail_mass_stats["median"],
                "lm_tail_mass_pct_p95": lm_tail_mass_stats["p95"],
                "pre_gate_total_pct_mean": pre_gate_stats["mean"],
                "pre_gate_total_pct_std": pre_gate_stats["std"],
                "pre_gate_total_pct_p05": pre_gate_stats["p05"],
                "pre_gate_total_pct_median": pre_gate_stats["median"],
                "pre_gate_total_pct_p95": pre_gate_stats["p95"],
                "runtime_total_pct_mean": runtime_stats["mean"],
                "runtime_total_pct_std": runtime_stats["std"],
                "runtime_total_pct_p05": runtime_stats["p05"],
                "runtime_total_pct_median": runtime_stats["median"],
                "runtime_total_pct_p95": runtime_stats["p95"],
                "final_pct_mean": final_stats["mean"],
                "final_pct_std": final_stats["std"],
                "final_pct_p05": final_stats["p05"],
                "final_pct_median": final_stats["median"],
                "final_pct_p95": final_stats["p95"],
                "gate_failed_rate": gate_failed_stats["mean"],
                "lm_applied_rate": lm_applied_stats["mean"],
                "delta_span_vs_clean_real": (
                    float(base_stats["mean"] - clean_ref["span_pct_mean"])
                    if clean_ref else 0.0
                ),
                "delta_lm_profile_vs_clean_real": (
                    float(lm_profile_stats["mean"] - clean_ref["lm_profile_pct_mean"])
                    if clean_ref else 0.0
                ),
                "delta_lm_margin_vs_clean_real": (
                    float(lm_margin_stats["mean"] - clean_ref["lm_margin_pct_mean"])
                    if clean_ref else 0.0
                ),
                "delta_lm_mean_bin_index_vs_clean_real": (
                    float(lm_mean_bin_index_stats["mean"] - clean_ref["lm_mean_bin_index_pct_mean"])
                    if clean_ref else 0.0
                ),
                "delta_lm_mean_bin_length_vs_clean_real": (
                    float(lm_mean_bin_length_stats["mean"] - clean_ref["lm_mean_bin_length_pct_mean"])
                    if clean_ref else 0.0
                ),
                "delta_lm_tail_mass_vs_clean_real": (
                    float(lm_tail_mass_stats["mean"] - clean_ref["lm_tail_mass_pct_mean"])
                    if clean_ref else 0.0
                ),
                "delta_pre_gate_vs_clean_real": (
                    float(pre_gate_stats["mean"] - clean_ref["pre_gate_total_pct_mean"])
                    if clean_ref else 0.0
                ),
                "delta_runtime_vs_clean_real": (
                    float(runtime_stats["mean"] - clean_ref["runtime_total_pct_mean"])
                    if clean_ref else 0.0
                ),
                "delta_final_vs_clean_real": (
                    float(final_stats["mean"] - clean_ref["final_pct_mean"])
                    if clean_ref else 0.0
                ),
            }
        )
    return out_rows


def main() -> None:
    profile = _select_profile()
    span_assets_dir = _resolve_repo_path(SPAN_ASSETS_DIR)
    lm_assets_json = _resolve_repo_path(LM_ASSETS_JSON)
    output_root = _resolve_repo_path(OUTPUT_ROOT)
    run_dir = output_root / f"{_utc_now_label()}__{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print("[span_hamming_lm_usage_local] loading assets...")
    span_assets = SpanCalibratedAssets.load(span_assets_dir)
    lm_assets = SpanHammingLmAssetsV2.load(lm_assets_json)
    backend = SpanHammingBackend(config=SPAN_CONFIG)
    corpora = _build_enabled_corpora(profile)
    alphabet_size = int(Runeglish.size())
    runtime_cfg = SpanHammingBenchmarkRuntimeConfig(
        objective_family=OBJECTIVE_FAMILY,
        coverage_min=float(SPAN_HAMMING_COVERAGE_MIN),
        quality_min=float(SPAN_HAMMING_QUALITY_MIN),
        span_pct_min=SPAN_HAMMING_SPAN_PCT_MIN,
        char_pct_min=SPAN_HAMMING_CHAR_PCT_MIN,
        combine_mode=str(SPAN_HAMMING_COMBINE_MODE),
        weight_span=float(SPAN_HAMMING_WEIGHT_SPAN),
        weight_char=float(SPAN_HAMMING_WEIGHT_CHAR),
        use_char_channel=bool(SPAN_HAMMING_USE_CHAR_CHANNEL),
        gate_fail_policy=str(SPAN_HAMMING_GATE_FAIL_POLICY),
        gate_score_floor=SPAN_HAMMING_GATE_SCORE_FLOOR,
        lm_weight=float(LM_WEIGHT),
        lm_weight_margin=float(LM_WEIGHT_MARGIN),
        lm_weight_mean_bin_index=float(LM_WEIGHT_MEAN_BIN_INDEX),
        lm_weight_mean_bin_length=float(LM_WEIGHT_MEAN_BIN_LENGTH),
        lm_weight_tail_mass=float(LM_WEIGHT_TAIL_MASS),
        lm_profile_source=str(LM_PROFILE_SOURCE),
        lm_tail_start_index=int(LM_TAIL_START_INDEX),
    )
    rows: list[dict] = []
    samples_csv = run_dir / "samples.csv"
    summary_csv = run_dir / "summary.csv"
    sample_fh = None
    sample_writer: csv.DictWriter | None = None

    def emit_row(row: dict) -> None:
        nonlocal sample_fh, sample_writer
        rows.append(row)
        if sample_writer is None or sample_fh is None:
            sample_fh, sample_writer = _open_csv_writer(samples_csv, list(row.keys()))
        sample_writer.writerow(row)
        sample_fh.flush()

    def write_summary_checkpoint() -> None:
        if not rows:
            return
        summary_rows = _build_summary_rows(rows, corpora, profile)
        _write_csv(summary_csv, summary_rows, fieldnames=list(summary_rows[0].keys()))
        print(
            f"[span_hamming_lm_usage_local] checkpoint rows={len(rows)} "
            f"summary_rows={len(summary_rows)}"
        )

    print("[span_hamming_lm_usage_local] generating benchmark cases...")
    try:
        for corpus_spec in corpora:
            corpus_name = str(corpus_spec["name"])
            corpus_kind = str(corpus_spec["kind"])
            corpus = np.asarray(corpus_spec["text"], dtype=np.uint8).reshape(-1)
            print(
                f"[span_hamming_lm_usage_local] corpus={corpus_name} "
                f"kind={corpus_kind} runes={int(corpus.size)}"
            )
            for length in profile["lengths"]:
                if int(corpus.size) < int(length):
                    print(
                        f"  skip length={int(length)} corpus={corpus_name} "
                        f"(needs {int(length)}, has {int(corpus.size)})"
                    )
                    continue
                print(
                    f"  length={int(length)} real_slices={int(profile['n_real_samples_per_length'])} "
                    f"corruptions={len(profile['corruption_pcts'])} adversarial_seeds={len(profile['random_seeds'])}"
                )
                real_slices = _pick_real_slices(
                    corpus,
                    length=length,
                    count=int(profile["n_real_samples_per_length"]),
                )
                for real_idx, real_text in enumerate(real_slices):
                    for corruption_pct in profile["corruption_pcts"]:
                        rate = float(int(corruption_pct) / 100.0)
                        seed_base = (
                            (int(length) * 1_000_000)
                            + (sum(ord(ch) for ch in corpus_name) * 100)
                            + (int(real_idx) * 1_000)
                            + int(corruption_pct)
                        )
                        rng = np.random.default_rng(seed_base)
                        sample = corrupt_with_random(real_text, rate, alphabet_size, rng)
                        scored = score_text_with_assets(
                            sample,
                            backend=backend,
                            span_assets=span_assets,
                            lm_assets=lm_assets,
                            direction=DIRECTION,
                            clamp_min=CLAMP_MIN,
                            clamp_max=CLAMP_MAX,
                            runtime_config=runtime_cfg,
                        )
                        emit_row(
                            {
                                "corpus_name": corpus_name,
                                "corpus_kind": corpus_kind,
                                "family": "corruption_curve",
                                "condition": f"corrupt_{int(corruption_pct):03d}",
                                "length": int(length),
                                "seed": int(seed_base),
                                "real_slice_index": int(real_idx),
                                **scored.asdict(),
                            }
                        )
                        if len(rows) % int(PROGRESS_PRINT_EVERY_ROWS) == 0:
                            print(
                                f"    progress rows={len(rows)} corpus={corpus_name} "
                                f"length={int(length)} family=corruption_curve "
                                f"condition=corrupt_{int(corruption_pct):03d}"
                            )
                        if len(rows) % int(SUMMARY_CHECKPOINT_EVERY_ROWS) == 0:
                            write_summary_checkpoint()

                for seed in profile["random_seeds"]:
                    rng = np.random.default_rng(
                        (int(length) * 10_000_000)
                        + (sum(ord(ch) for ch in corpus_name) * 10)
                        + int(seed)
                    )
                    random_text = make_random_text(length, alphabet_size, rng)
                    fragment_soup = make_fragment_soup(
                        corpus,
                        length,
                        rng,
                        chunk_lengths=SHORT_FRAGMENT_LENGTHS,
                    )
                    block_shuffle = make_block_shuffle(
                        real_slices[int(seed % len(real_slices))],
                        rng,
                        block_size=BLOCK_SHUFFLE_BLOCK_SIZE,
                    )
                    repeated_motif = make_repeated_motif(length, MOTIF)

                    for condition, sample in (
                        ("random_uniform", random_text),
                        ("fragment_soup", fragment_soup),
                        ("block_shuffle", block_shuffle),
                        ("repeated_motif", repeated_motif),
                    ):
                        scored = score_text_with_assets(
                            sample,
                            backend=backend,
                            span_assets=span_assets,
                            lm_assets=lm_assets,
                            direction=DIRECTION,
                            clamp_min=CLAMP_MIN,
                            clamp_max=CLAMP_MAX,
                            runtime_config=runtime_cfg,
                        )
                        emit_row(
                            {
                                "corpus_name": corpus_name,
                                "corpus_kind": corpus_kind,
                                "family": "adversarial_and_random",
                                "condition": condition,
                                "length": int(length),
                                "seed": int(seed),
                                "real_slice_index": -1,
                                **scored.asdict(),
                            }
                        )
                        if len(rows) % int(PROGRESS_PRINT_EVERY_ROWS) == 0:
                            print(
                                f"    progress rows={len(rows)} corpus={corpus_name} "
                                f"length={int(length)} family=adversarial_and_random "
                                f"condition={condition}"
                            )
                        if len(rows) % int(SUMMARY_CHECKPOINT_EVERY_ROWS) == 0:
                            write_summary_checkpoint()
                print(f"  completed length={int(length)} corpus={corpus_name} rows={len(rows)}")
            print(f"[span_hamming_lm_usage_local] completed corpus={corpus_name} rows={len(rows)}")
    finally:
        if sample_fh is not None:
            sample_fh.close()

    summary_rows = _build_summary_rows(rows, corpora, profile)
    config_json = run_dir / "run_config.json"
    _write_csv(summary_csv, summary_rows, fieldnames=list(summary_rows[0].keys()))
    config_json.write_text(
        json.dumps(
            {
                "run_label": RUN_LABEL,
                "bench_profile": BENCH_PROFILE,
                "direction": DIRECTION,
                "clamp_min": CLAMP_MIN,
                "clamp_max": CLAMP_MAX,
                "lm_weight": LM_WEIGHT,
                "lm_weight_margin": LM_WEIGHT_MARGIN,
                "lm_weight_mean_bin_index": LM_WEIGHT_MEAN_BIN_INDEX,
                "lm_weight_mean_bin_length": LM_WEIGHT_MEAN_BIN_LENGTH,
                "lm_weight_tail_mass": LM_WEIGHT_TAIL_MASS,
                "lm_profile_source": LM_PROFILE_SOURCE,
                "lm_tail_start_index": LM_TAIL_START_INDEX,
                "objective_family": OBJECTIVE_FAMILY,
                "span_hamming_coverage_min": SPAN_HAMMING_COVERAGE_MIN,
                "span_hamming_quality_min": SPAN_HAMMING_QUALITY_MIN,
                "span_hamming_span_pct_min": SPAN_HAMMING_SPAN_PCT_MIN,
                "span_hamming_char_pct_min": SPAN_HAMMING_CHAR_PCT_MIN,
                "span_hamming_combine_mode": SPAN_HAMMING_COMBINE_MODE,
                "span_hamming_weight_span": SPAN_HAMMING_WEIGHT_SPAN,
                "span_hamming_weight_char": SPAN_HAMMING_WEIGHT_CHAR,
                "span_hamming_use_char_channel": SPAN_HAMMING_USE_CHAR_CHANNEL,
                "span_hamming_gate_fail_policy": SPAN_HAMMING_GATE_FAIL_POLICY,
                "span_hamming_gate_score_floor": SPAN_HAMMING_GATE_SCORE_FLOOR,
                "summary_checkpoint_every_rows": SUMMARY_CHECKPOINT_EVERY_ROWS,
                "span_assets_dir": str(span_assets_dir),
                "lm_assets_json": str(lm_assets_json),
                "lengths": list(profile["lengths"]),
                "corruption_pcts": list(profile["corruption_pcts"]),
                "random_seeds": list(profile["random_seeds"]),
                "motif": list(MOTIF),
                "short_fragment_lengths": list(SHORT_FRAGMENT_LENGTHS),
                "block_shuffle_block_size": BLOCK_SHUFFLE_BLOCK_SIZE,
                "corpora": [
                    {
                        "name": str(spec["name"]),
                        "kind": str(spec["kind"]),
                        "length": int(np.asarray(spec["text"]).size),
                    }
                    for spec in corpora
                ],
            },
            indent=2,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    print(f"  wrote samples: {samples_csv}")
    print(f"  wrote summary: {summary_csv}")
    print(f"  wrote config: {config_json}")
    print("[span_hamming_lm_usage_local] done")


if __name__ == "__main__":
    main()
