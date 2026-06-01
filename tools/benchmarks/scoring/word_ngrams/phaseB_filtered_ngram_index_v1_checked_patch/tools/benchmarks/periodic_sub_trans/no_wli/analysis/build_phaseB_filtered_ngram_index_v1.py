from __future__ import annotations

"""
Build filtered rune-token n-gram indexes from cleaned Google n-gram text files.

This is deliberately an IDE-friendly script: edit the config block below and run
main(). There are no command-line arguments.

The first contract is conservative for the no-WLI scorer:
- input rows are whitespace text of the form: word ... word count
- rows containing punctuation, digits, quotes, or start/end marker tokens are rejected
- every phrase word must be selected by the chosen dictionary cut
- forward and reverse encodings are built separately and must not be mixed
"""

import csv
import gzip
import hashlib
import json
import math
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence


# Set this only when running the script from an unpacked patch folder rather than
# from its final location inside the repo. Leave as None for normal repo runs.
REPO_ROOT_OVERRIDE: Path | None = None


def find_repo_root(start: Path) -> Path:
    """Find the real repo root, even if this file is run from a nested patch folder."""
    candidates = [start, *start.parents]
    for candidate in candidates:
        if (candidate / "src" / "rune_decrypter_prime").is_dir() and (candidate / "assets").is_dir():
            return candidate
    # Fallback for normal in-repo placement:
    return start.parents[5]


REPO_ROOT = REPO_ROOT_OVERRIDE or find_repo_root(Path(__file__).resolve())
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402


# =============================================================================
# Config block. Edit here for local runs. No CLI.
# =============================================================================

RUN_LABEL = "phaseB_filtered_ngram_index_v1"
RUN_MODE = "full"  # "sample" or "full"

# Root is optional. Paths below may be absolute or relative to REPO_ROOT.
RAW_NGRAM_ROOT = Path("data/scoring/google_ngrams_Version-20200217")

# Use explicit per-order files for the five-file layout. Example:
# RAW_NGRAM_FILES_BY_ORDER = {
#     1: [Path("1grams.txt")],
#     2: [Path("2grams.txt")],
#     3: [Path("3grams.txt")],
#     4: [Path("4grams.txt")],
#     5: [Path("5grams.txt")],
# }
RAW_NGRAM_FILES_BY_ORDER: dict[int, list[Path]] = {
    1: [],
    2: [],
    3: [],
    4: [],
    5: [],
}

# Optional fallback for split-folder layouts. These are resolved under
# RAW_NGRAM_ROOT unless absolute.
RAW_NGRAM_GLOBS_BY_ORDER: dict[int, list[str]] = {
    1: ["1-grams/*"],
    2: ["2-grams/*"],
    3: ["3-grams/*"],
    4: ["4-grams/*"],
    5: ["5-grams/*"],
}

# Current scoring plan uses 2..5. Keep 1 available for inventory/sanity checks.
ENABLED_ORDERS = (2, 3, 4, 5)
ENABLED_CUTS = ("strict", "normal")
ENABLED_DIRECTIONS = ("fwd", "rev")

DICTIONARY_DIRS_BY_CUT = {
    "strict": Path("assets/hamming_dictionary_policies_phaseA_v0_14/strict/hamming_raw_1g"),
    "normal": Path("assets/hamming_dictionary_policies_phaseA_v0_14/normal/hamming_raw_1g"),
}

OUTPUT_ROOT = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_index_v1"
)
CREATE_TIMESTAMPED_RUN_DIR = True

# Safety limits for first local runs. FULL mode ignores SAMPLE_LINE_LIMIT_PER_ORDER.
SAMPLE_LINE_LIMIT_PER_ORDER = 25_000
PROGRESS_EVERY_LINES = 250_000

# No-WLI n-gram scorer contract: reject start/end tags and punctuation rows.
REQUIRE_PLAIN_LOWERCASE_WORDS = True
PLAIN_WORD_RE = re.compile(r"^[a-z]+$")

# Aggregation is useful because different Latin spellings can collapse onto the
# same rune-token key through RDP normalisation rules.
AGGREGATE_DUPLICATE_RUNE_KEYS = True
KEEP_LATIN_EXAMPLES_PER_KEY = 3

WORD_SEP_BYTE = 0xFF
KEY_SEP = bytes([WORD_SEP_BYTE])


# =============================================================================
# Data shapes
# =============================================================================


@dataclass(frozen=True)
class ParsedNgramLine:
    words: tuple[str, ...]
    count: int


@dataclass(frozen=True)
class EncodedPhrase:
    latin_words: tuple[str, ...]
    rune_token_ids: tuple[int, ...]
    wli: tuple[tuple[int, int], ...]
    rune_words: tuple[str, ...]
    word_token_ids: tuple[tuple[int, ...], ...]
    key: bytes

    @property
    def rune_joined(self) -> str:
        return "".join(self.rune_words)

    @property
    def rune_lengths(self) -> tuple[int, ...]:
        return tuple(len(word) for word in self.rune_words)


@dataclass
class AggregateRow:
    encoded: EncodedPhrase
    count_sum: int = 0
    phrase_count: int = 0
    top_latin_ngram: str = ""
    top_latin_count: int = 0
    first_source_file: str = ""
    latin_examples: list[str] = field(default_factory=list)

    def add(self, latin_ngram: str, count: int, source_file: str) -> None:
        c = int(count)
        self.count_sum += c
        self.phrase_count += 1
        if c > self.top_latin_count or (c == self.top_latin_count and latin_ngram < self.top_latin_ngram):
            self.top_latin_ngram = latin_ngram
            self.top_latin_count = c
        if not self.first_source_file:
            self.first_source_file = source_file
        if latin_ngram not in self.latin_examples and len(self.latin_examples) < KEEP_LATIN_EXAMPLES_PER_KEY:
            self.latin_examples.append(latin_ngram)


@dataclass
class SourceStats:
    n: int
    source_file: str
    bytes_total: int = 0
    lines_seen: int = 0
    valid_format_rows: int = 0
    rejected_bad_count: int = 0
    rejected_wrong_order: int = 0
    rejected_non_plain: int = 0
    rejected_empty_encoding: int = 0


@dataclass
class OutputStats:
    n: int
    dictionary_cut: str
    encoding_direction: str
    input_rows_seen: int = 0
    valid_format_rows: int = 0
    dictionary_kept_rows: int = 0
    dictionary_rejected_rows: int = 0
    aggregate_rows: int = 0
    count_sum: int = 0
    output_file: str = ""


@dataclass(frozen=True)
class BuildConfig:
    repo_root: Path = REPO_ROOT
    raw_ngram_root: Path = RAW_NGRAM_ROOT
    raw_ngram_files_by_order: Mapping[int, Sequence[Path]] = field(default_factory=lambda: RAW_NGRAM_FILES_BY_ORDER)
    raw_ngram_globs_by_order: Mapping[int, Sequence[str]] = field(default_factory=lambda: RAW_NGRAM_GLOBS_BY_ORDER)
    dictionary_dirs_by_cut: Mapping[str, Path] = field(default_factory=lambda: DICTIONARY_DIRS_BY_CUT)
    output_root: Path = OUTPUT_ROOT
    enabled_orders: Sequence[int] = ENABLED_ORDERS
    enabled_cuts: Sequence[str] = ENABLED_CUTS
    enabled_directions: Sequence[str] = ENABLED_DIRECTIONS
    run_mode: str = RUN_MODE
    create_timestamped_run_dir: bool = CREATE_TIMESTAMPED_RUN_DIR
    sample_line_limit_per_order: int = SAMPLE_LINE_LIMIT_PER_ORDER
    progress_every_lines: int = PROGRESS_EVERY_LINES
    require_plain_lowercase_words: bool = REQUIRE_PLAIN_LOWERCASE_WORDS
    aggregate_duplicate_rune_keys: bool = AGGREGATE_DUPLICATE_RUNE_KEYS


# =============================================================================
# Path and manifest helpers
# =============================================================================


def utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "unknown"
    total = int(seconds)
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{sec:02d}s"
    return f"{minutes}m{sec:02d}s"


def resolve_path(path_like: Path | str, *, repo_root: Path, base: Path | None = None) -> Path:
    p = Path(path_like).expanduser()
    if p.is_absolute():
        return p.resolve()
    if base is not None:
        return (base / p).resolve()
    return (repo_root / p).resolve()


def run_output_dir(config: BuildConfig) -> Path:
    base = resolve_path(config.output_root, repo_root=config.repo_root)
    if not config.create_timestamped_run_dir:
        return base
    return base / f"{utc_label()}__{RUN_LABEL}"


def expand_ngram_paths(config: BuildConfig, n: int) -> list[Path]:
    out: list[Path] = []

    for p in config.raw_ngram_files_by_order.get(int(n), ()):  # explicit five-file layout
        out.append(resolve_path(p, repo_root=config.repo_root, base=config.raw_ngram_root))

    root = resolve_path(config.raw_ngram_root, repo_root=config.repo_root)
    for pattern in config.raw_ngram_globs_by_order.get(int(n), ()):  # split-folder layout
        pat = str(pattern).strip()
        if not pat:
            continue
        p = Path(pat).expanduser()
        if p.is_absolute():
            matches = sorted(p.parent.glob(p.name))
        else:
            matches = sorted(root.glob(pat))
        out.extend(m for m in matches if m.is_file())

    # Deterministic de-duplication preserving sorted path order.
    return sorted({p.resolve() for p in out})


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def jsonable_config(config: BuildConfig) -> dict[str, object]:
    return {
        "run_label": RUN_LABEL,
        "run_mode": config.run_mode,
        "raw_ngram_root": str(config.raw_ngram_root),
        "raw_ngram_files_by_order": {
            str(k): [str(p) for p in v] for k, v in sorted(config.raw_ngram_files_by_order.items())
        },
        "raw_ngram_globs_by_order": {
            str(k): [str(p) for p in v] for k, v in sorted(config.raw_ngram_globs_by_order.items())
        },
        "dictionary_dirs_by_cut": {k: str(v) for k, v in sorted(config.dictionary_dirs_by_cut.items())},
        "enabled_orders": [int(v) for v in config.enabled_orders],
        "enabled_cuts": list(config.enabled_cuts),
        "enabled_directions": list(config.enabled_directions),
        "sample_line_limit_per_order": (
            None if config.sample_line_limit_per_order is None else int(config.sample_line_limit_per_order)
        ),
        "require_plain_lowercase_words": bool(config.require_plain_lowercase_words),
        "aggregate_duplicate_rune_keys": bool(config.aggregate_duplicate_rune_keys),
        "word_sep_byte": int(WORD_SEP_BYTE),
    }


# =============================================================================
# Dictionary loading
# =============================================================================


def is_plain_word(word: str) -> bool:
    return bool(PLAIN_WORD_RE.fullmatch(word))


def normalise_source_word(word: str) -> str:
    return str(word).strip().lower()


def iter_dictionary_csv_files(path: Path) -> Iterator[Path]:
    if path.is_file():
        yield path
        return
    yield from sorted(path.glob("raw1grams_*.csv"))
    yield from sorted(path.glob("*.csv"))
    yield from sorted(path.glob("*.txt"))


def load_selected_word_set(path_like: Path | str, *, repo_root: Path) -> set[str]:
    path = resolve_path(path_like, repo_root=repo_root)
    if not path.exists():
        raise FileNotFoundError(f"Dictionary path not found: {path}")

    selected: set[str] = set()
    files = list(iter_dictionary_csv_files(path))
    if not files:
        raise FileNotFoundError(f"No dictionary files found under: {path}")

    for fp in files:
        suffix = fp.suffix.lower()
        with fp.open("r", encoding="utf-8", newline="") as fh:
            if suffix == ".csv":
                reader = csv.reader(fh)
                for row in reader:
                    if not row:
                        continue
                    # Phase-A raw1grams CSV contract observed in tests:
                    # word,count,selected,runes,row_hash,...
                    if len(row) >= 3 and row[2].strip() in {"0", "1"}:
                        if row[2].strip() != "1":
                            continue
                        word = normalise_source_word(row[0])
                    else:
                        # Conservative fallback for simple CSV word lists.
                        word = normalise_source_word(row[0])
                    if word and is_plain_word(word):
                        selected.add(word)
            else:
                for line in fh:
                    text = line.strip()
                    if not text:
                        continue
                    word = normalise_source_word(text.split()[0])
                    if word and is_plain_word(word):
                        selected.add(word)
    return selected


def load_dictionary_sets(config: BuildConfig) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for cut in config.enabled_cuts:
        if cut not in config.dictionary_dirs_by_cut:
            raise KeyError(f"Missing dictionary path for cut={cut!r}")
        out[cut] = load_selected_word_set(config.dictionary_dirs_by_cut[cut], repo_root=config.repo_root)
    return out


# =============================================================================
# N-gram parsing and encoding
# =============================================================================


def parse_ngram_line(line: str, *, expected_n: int, require_plain_words: bool) -> ParsedNgramLine | None:
    text = line.strip()
    if not text:
        return None
    parts = text.split()
    if len(parts) < 2:
        return None
    try:
        count = int(parts[-1])
    except ValueError:
        return None

    words = tuple(normalise_source_word(part) for part in parts[:-1])
    if len(words) != int(expected_n):
        return None
    if require_plain_words and any(not is_plain_word(w) for w in words):
        return None
    return ParsedNgramLine(words=words, count=count)


def parse_ngram_line_with_reason(
    line: str,
    *,
    expected_n: int,
    require_plain_words: bool,
) -> tuple[ParsedNgramLine | None, str]:
    text = line.strip()
    if not text:
        return None, "blank"
    parts = text.split()
    if len(parts) < 2:
        return None, "bad_count"
    try:
        count = int(parts[-1])
    except ValueError:
        return None, "bad_count"
    words = tuple(normalise_source_word(part) for part in parts[:-1])
    if len(words) != int(expected_n):
        return None, "wrong_order"
    if require_plain_words and any(not is_plain_word(w) for w in words):
        return None, "non_plain"
    return ParsedNgramLine(words=words, count=count), "ok"


def split_idx_by_wli(idx: Sequence[int], wli: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    if len(idx) != len(wli):
        raise ValueError("idx and wli must have the same length")
    words: list[tuple[int, ...]] = []
    cur: list[int] = []
    for sym, pair in zip(idx, wli):
        if len(pair) != 2:
            raise ValueError("WLI entries must be [pos_in_word, word_len]")
        pos_in_word = int(pair[0])
        word_len = int(pair[1])
        cur.append(int(sym))
        if pos_in_word == word_len - 1:
            words.append(tuple(cur))
            cur = []
    if cur:
        raise ValueError("WLI ended with an incomplete word")
    return tuple(words)


def make_key_from_word_token_ids(word_token_ids: Sequence[Sequence[int]]) -> bytes:
    tokens: list[bytes] = []
    for word in word_token_ids:
        b = bytes(int(v) for v in word)
        if WORD_SEP_BYTE in b:
            raise ValueError("Separator byte appears in rune token ids")
        tokens.append(b)
    return KEY_SEP.join(tokens)


def encode_phrase(words: Sequence[str], *, direction: str) -> EncodedPhrase:
    direction_key = str(direction).strip().lower()
    if direction_key == "fwd":
        runeglish_direction = "ltr"
    elif direction_key == "rev":
        runeglish_direction = "rtl"
    else:
        raise ValueError(f"Unknown encoding direction: {direction!r}")

    phrase = " ".join(str(w) for w in words)
    idx, wli, rune_str = Runeglish.encode_english_to_runes(phrase, direction=runeglish_direction)
    rune_words = tuple(rune_str.split())
    word_token_ids = split_idx_by_wli(idx, wli)
    if len(rune_words) != len(words) or len(word_token_ids) != len(words):
        raise ValueError(f"Encoding word-count mismatch for phrase={phrase!r} direction={direction_key!r}")
    key = make_key_from_word_token_ids(word_token_ids)
    return EncodedPhrase(
        latin_words=tuple(str(w) for w in words),
        rune_token_ids=tuple(int(v) for v in idx),
        wli=tuple((int(a), int(b)) for a, b in wli),
        rune_words=rune_words,
        word_token_ids=word_token_ids,
        key=key,
    )


def log_count(count: int) -> float:
    return math.log(float(count)) if int(count) > 0 else float("-inf")


# =============================================================================
# Build logic
# =============================================================================


def scan_sources_for_order(
    *,
    n: int,
    paths: Sequence[Path],
    dictionary_sets: Mapping[str, set[str]],
    config: BuildConfig,
) -> tuple[dict[tuple[int, str, str], dict[bytes, AggregateRow]], list[SourceStats], list[OutputStats]]:
    aggregates: dict[tuple[int, str, str], dict[bytes, AggregateRow]] = {
        (int(n), cut, direction): {}
        for cut in config.enabled_cuts
        for direction in config.enabled_directions
    }
    output_stats: dict[tuple[int, str, str], OutputStats] = {
        (int(n), cut, direction): OutputStats(n=int(n), dictionary_cut=cut, encoding_direction=direction)
        for cut in config.enabled_cuts
        for direction in config.enabled_directions
    }
    source_stats: list[SourceStats] = []

    max_lines = None if config.run_mode == "full" else int(config.sample_line_limit_per_order)
    total_lines_for_order = 0
    total_files = len(paths)
    total_bytes = sum(int(path.stat().st_size) for path in paths if path.exists())
    completed_bytes = 0
    order_started = time.monotonic()

    for file_index, fp in enumerate(paths, start=1):
        if not fp.exists():
            raise FileNotFoundError(f"N-gram source file not found: {fp}")
        stat = SourceStats(n=int(n), source_file=str(fp), bytes_total=int(fp.stat().st_size))
        source_stats.append(stat)
        file_started = time.monotonic()
        with fp.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if max_lines is not None and total_lines_for_order >= max_lines:
                    break
                total_lines_for_order += 1
                stat.lines_seen += 1
                parsed, reason = parse_ngram_line_with_reason(
                    line,
                    expected_n=int(n),
                    require_plain_words=config.require_plain_lowercase_words,
                )
                for out_stat in output_stats.values():
                    if out_stat.n == int(n):
                        out_stat.input_rows_seen += 1
                if parsed is None:
                    if reason == "bad_count":
                        stat.rejected_bad_count += 1
                    elif reason == "wrong_order":
                        stat.rejected_wrong_order += 1
                    elif reason == "non_plain":
                        stat.rejected_non_plain += 1
                    continue

                stat.valid_format_rows += 1
                for cut in config.enabled_cuts:
                    selected_words = dictionary_sets[cut]
                    cut_keeps = all(word in selected_words for word in parsed.words)
                    for direction in config.enabled_directions:
                        out_key = (int(n), cut, direction)
                        out_stat = output_stats[out_key]
                        out_stat.valid_format_rows += 1
                        if not cut_keeps:
                            out_stat.dictionary_rejected_rows += 1
                            continue
                        encoded = encode_phrase(parsed.words, direction=direction)
                        if not encoded.rune_token_ids:
                            stat.rejected_empty_encoding += 1
                            continue
                        latin_ngram = " ".join(parsed.words)
                        bucket = aggregates[out_key]
                        row = bucket.get(encoded.key)
                        if row is None:
                            row = AggregateRow(encoded=encoded)
                            bucket[encoded.key] = row
                        row.add(latin_ngram=latin_ngram, count=parsed.count, source_file=fp.name)
                        out_stat.dictionary_kept_rows += 1
                        out_stat.count_sum += int(parsed.count)

                if config.progress_every_lines > 0 and total_lines_for_order % int(config.progress_every_lines) == 0:
                    elapsed = time.monotonic() - order_started
                    completed_fraction = completed_bytes / total_bytes if total_bytes else 0.0
                    eta = (elapsed / completed_fraction - elapsed) if completed_fraction > 0 else None
                    line_rate = total_lines_for_order / elapsed if elapsed > 0 else 0.0
                    print(
                        f"[{RUN_LABEL}] n={n} files_completed={file_index - 1}/{total_files} "
                        f"completed_bytes={completed_bytes:,}/{total_bytes:,} "
                        f"lines={total_lines_for_order:,} current_file={fp.name} "
                        f"elapsed={format_duration(elapsed)} eta_by_completed_bytes={format_duration(eta)} "
                        f"lines_per_sec={line_rate:,.1f}",
                        flush=True,
                    )
        completed_bytes += stat.bytes_total
        elapsed = time.monotonic() - order_started
        completed_fraction = completed_bytes / total_bytes if total_bytes else 0.0
        eta = (elapsed / completed_fraction - elapsed) if completed_fraction > 0 else None
        print(
            f"[{RUN_LABEL}] n={n} files_completed={file_index}/{total_files} "
            f"completed_bytes={completed_bytes:,}/{total_bytes:,} "
            f"file_elapsed={format_duration(time.monotonic() - file_started)} "
            f"elapsed={format_duration(elapsed)} eta_by_completed_bytes={format_duration(eta)}",
            flush=True,
        )
        if max_lines is not None and total_lines_for_order >= max_lines:
            break

    for key, bucket in aggregates.items():
        output_stats[key].aggregate_rows = len(bucket)
    return aggregates, source_stats, list(output_stats.values())


def write_aggregate_csv(path: Path, rows: Iterable[AggregateRow], *, n: int, cut: str, direction: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "n",
        "dictionary_cut",
        "encoding_direction",
        "rune_key_hex",
        "rune_joined",
        "rune_words",
        "rune_lengths",
        "rune_token_ids",
        "word_token_ids",
        "wli",
        "count",
        "log_count",
        "phrase_count",
        "top_latin_ngram",
        "top_latin_count",
        "latin_examples",
        "source_file",
    ]
    sorted_rows = sorted(
        rows,
        key=lambda r: (-int(r.count_sum), r.encoded.key.hex(), r.top_latin_ngram),
    )
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted_rows:
            encoded = row.encoded
            writer.writerow(
                {
                    "n": int(n),
                    "dictionary_cut": cut,
                    "encoding_direction": direction,
                    "rune_key_hex": encoded.key.hex(),
                    "rune_joined": encoded.rune_joined,
                    "rune_words": json.dumps(list(encoded.rune_words), ensure_ascii=False),
                    "rune_lengths": json.dumps(list(encoded.rune_lengths)),
                    "rune_token_ids": json.dumps(list(encoded.rune_token_ids)),
                    "word_token_ids": json.dumps([list(x) for x in encoded.word_token_ids]),
                    "wli": json.dumps([list(x) for x in encoded.wli]),
                    "count": int(row.count_sum),
                    "log_count": log_count(row.count_sum),
                    "phrase_count": int(row.phrase_count),
                    "top_latin_ngram": row.top_latin_ngram,
                    "top_latin_count": int(row.top_latin_count),
                    "latin_examples": json.dumps(row.latin_examples, ensure_ascii=False),
                    "source_file": row.first_source_file,
                }
            )


def write_source_inventory(path: Path, rows: Sequence[SourceStats]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "n",
                "source_file",
                "bytes_total",
                "lines_seen",
                "valid_format_rows",
                "rejected_bad_count",
                "rejected_wrong_order",
                "rejected_non_plain",
                "rejected_empty_encoding",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r.__dict__)


def write_filtered_summary(path: Path, rows: Sequence[OutputStats]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "n",
                "dictionary_cut",
                "encoding_direction",
                "input_rows_seen",
                "valid_format_rows",
                "dictionary_kept_rows",
                "dictionary_rejected_rows",
                "aggregate_rows",
                "count_sum",
                "output_file",
            ],
        )
        writer.writeheader()
        for r in sorted(rows, key=lambda x: (x.n, x.dictionary_cut, x.encoding_direction)):
            writer.writerow(r.__dict__)


def write_readout(path: Path, *, config: BuildConfig, output_stats: Sequence[OutputStats], dictionary_sets: Mapping[str, set[str]]) -> None:
    lines = [
        f"# {RUN_LABEL}",
        "",
        f"Run mode: `{config.run_mode}`",
        "",
        "## Dictionary cuts",
        "",
    ]
    for cut in sorted(dictionary_sets):
        lines.append(f"- `{cut}`: {len(dictionary_sets[cut]):,} selected plain words")
    lines.extend(["", "## Outputs", ""])
    for row in sorted(output_stats, key=lambda x: (x.n, x.dictionary_cut, x.encoding_direction)):
        lines.append(
            f"- n={row.n} `{row.dictionary_cut}_{row.encoding_direction}`: "
            f"kept rows={row.dictionary_kept_rows:,}, aggregate rows={row.aggregate_rows:,}, "
            f"count_sum={row.count_sum:,}"
        )
    lines.extend(
        [
            "",
            "## Contract notes",
            "",
            "- Rows are parsed as `word ... word count`.",
            "- Rows with punctuation, quotes, digits, or start/end marker tokens are rejected before dictionary filtering.",
            "- `fwd` uses `Runeglish.encode_english_to_runes(..., direction=\"ltr\")`.",
            "- `rev` uses `Runeglish.encode_english_to_runes(..., direction=\"rtl\")`.",
            "- The `rune_key_hex` column is a byte key with `0xff` between rune-token words.",
            "- Outputs are sorted deterministically by descending aggregate count, then rune key.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_filtered_ngram_indexes(config: BuildConfig) -> Path:
    out_dir = run_output_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)

    dictionary_sets = load_dictionary_sets(config)
    write_json(out_dir / "config.json", jsonable_config(config))
    write_json(out_dir / "dictionary_manifest.json", {k: {"selected_plain_words": len(v)} for k, v in dictionary_sets.items()})

    all_source_stats: list[SourceStats] = []
    all_output_stats: list[OutputStats] = []

    for n in [int(v) for v in config.enabled_orders]:
        paths = expand_ngram_paths(config, n)
        if not paths:
            raise FileNotFoundError(
                f"No n-gram input files configured for n={n}. "
                "Set RAW_NGRAM_FILES_BY_ORDER or RAW_NGRAM_GLOBS_BY_ORDER in the config block."
            )
        print(f"[{RUN_LABEL}] n={n} source_files={len(paths)}", flush=True)
        aggregates, source_stats, output_stats = scan_sources_for_order(
            n=n,
            paths=paths,
            dictionary_sets=dictionary_sets,
            config=config,
        )
        all_source_stats.extend(source_stats)

        for stat in output_stats:
            bucket = aggregates[(stat.n, stat.dictionary_cut, stat.encoding_direction)]
            rel = Path(f"{stat.dictionary_cut}_{stat.encoding_direction}") / f"ngram{stat.n}.csv.gz"
            fp = out_dir / rel
            write_aggregate_csv(
                fp,
                bucket.values(),
                n=stat.n,
                cut=stat.dictionary_cut,
                direction=stat.encoding_direction,
            )
            stat.output_file = str(rel)
            all_output_stats.append(stat)

    write_source_inventory(out_dir / "raw_ngram_inventory.csv", all_source_stats)
    write_filtered_summary(out_dir / "filtered_ngram_summary.csv", all_output_stats)
    write_readout(out_dir / "readout.md", config=config, output_stats=all_output_stats, dictionary_sets=dictionary_sets)

    try:
        display_out_dir = out_dir.resolve().relative_to(config.repo_root.resolve()).as_posix()
    except ValueError:
        display_out_dir = str(out_dir)
    print(f"[{RUN_LABEL}] wrote: {display_out_dir}", flush=True)
    return out_dir


def main() -> None:
    build_filtered_ngram_indexes(BuildConfig())


if __name__ == "__main__":
    main()
