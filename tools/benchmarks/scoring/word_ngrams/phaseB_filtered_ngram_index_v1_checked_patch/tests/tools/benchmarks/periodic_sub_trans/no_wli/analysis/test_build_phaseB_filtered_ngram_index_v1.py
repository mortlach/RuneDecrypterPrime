from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[6]
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "build_phaseB_filtered_ngram_index_v1.py"
)

spec = importlib.util.spec_from_file_location("build_phaseB_filtered_ngram_index_v1", SCRIPT)
assert spec is not None and spec.loader is not None
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


def _write_policy(path: Path, words: list[str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    fp = path / "raw1grams_01.csv"
    with fp.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        for word in words:
            writer.writerow([word, "1", "1", "ᚠ", "dummyhash"])


def _read_gzip_csv(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_parser_accepts_plain_rows_and_rejects_tags_and_punctuation() -> None:
    ok = builder.parse_ngram_line("state university 123", expected_n=2, require_plain_words=True)
    assert ok is not None
    assert ok.words == ("state", "university")
    assert ok.count == 123

    assert builder.parse_ngram_line("state university _end_ 123", expected_n=3, require_plain_words=True) is None
    assert builder.parse_ngram_line("don't believe 123", expected_n=2, require_plain_words=True) is None
    assert builder.parse_ngram_line('state " 123', expected_n=2, require_plain_words=True) is None
    assert builder.parse_ngram_line("state 7 123", expected_n=2, require_plain_words=True) is None


def test_forward_and_reverse_encoding_are_separate() -> None:
    fwd = builder.encode_phrase(("the", "state"), direction="fwd")
    rev = builder.encode_phrase(("the", "state"), direction="rev")

    assert fwd.key != rev.key
    assert fwd.rune_words != rev.rune_words
    assert len(fwd.wli) == len(fwd.rune_token_ids)
    assert len(rev.wli) == len(rev.rune_token_ids)


def test_builder_filters_four_cut_direction_outputs(tmp_path: Path) -> None:
    raw_root = tmp_path / "ngrams"
    raw_root.mkdir()
    n2 = raw_root / "2grams.txt"
    n3 = raw_root / "3grams.txt"
    n2.write_text(
        "state university 10\n"
        "local government 11\n"
        "water conservation 7\n"
        "state _end_ 99\n"
        "don't believe 5\n"
        "the state 3\n",
        encoding="utf-8",
    )
    n3.write_text(
        "would undoubtedly have 13\n"
        "state university _end_ 99\n"
        "water conservation fund 17\n",
        encoding="utf-8",
    )

    strict_dir = tmp_path / "dict" / "strict"
    normal_dir = tmp_path / "dict" / "normal"
    _write_policy(strict_dir, ["state", "university", "local", "government", "would", "undoubtedly", "have", "the"])
    _write_policy(
        normal_dir,
        [
            "state",
            "university",
            "local",
            "government",
            "would",
            "undoubtedly",
            "have",
            "the",
            "water",
            "conservation",
            "fund",
        ],
    )

    config = builder.BuildConfig(
        repo_root=tmp_path,
        raw_ngram_root=raw_root,
        raw_ngram_files_by_order={2: [n2], 3: [n3]},
        raw_ngram_globs_by_order={2: [], 3: []},
        dictionary_dirs_by_cut={"strict": strict_dir, "normal": normal_dir},
        output_root=tmp_path / "out",
        enabled_orders=(2, 3),
        enabled_cuts=("strict", "normal"),
        enabled_directions=("fwd", "rev"),
        run_mode="full",
        create_timestamped_run_dir=False,
        sample_line_limit_per_order=0,
        progress_every_lines=0,
    )
    out_dir = builder.build_filtered_ngram_indexes(config)

    expected = [
        out_dir / "strict_fwd" / "ngram2.csv.gz",
        out_dir / "strict_rev" / "ngram2.csv.gz",
        out_dir / "normal_fwd" / "ngram2.csv.gz",
        out_dir / "normal_rev" / "ngram2.csv.gz",
        out_dir / "strict_fwd" / "ngram3.csv.gz",
        out_dir / "normal_fwd" / "ngram3.csv.gz",
    ]
    for fp in expected:
        assert fp.exists(), fp

    strict_n2 = _read_gzip_csv(out_dir / "strict_fwd" / "ngram2.csv.gz")
    normal_n2 = _read_gzip_csv(out_dir / "normal_fwd" / "ngram2.csv.gz")
    strict_n3 = _read_gzip_csv(out_dir / "strict_fwd" / "ngram3.csv.gz")
    normal_n3 = _read_gzip_csv(out_dir / "normal_fwd" / "ngram3.csv.gz")

    assert {row["top_latin_ngram"] for row in strict_n2} == {"state university", "local government", "the state"}
    assert {row["top_latin_ngram"] for row in normal_n2} == {
        "state university",
        "local government",
        "water conservation",
        "the state",
    }
    assert {row["top_latin_ngram"] for row in strict_n3} == {"would undoubtedly have"}
    assert {row["top_latin_ngram"] for row in normal_n3} == {"would undoubtedly have", "water conservation fund"}

    fwd_the = [row for row in normal_n2 if row["top_latin_ngram"] == "the state"][0]
    rev_rows = _read_gzip_csv(out_dir / "normal_rev" / "ngram2.csv.gz")
    rev_the = [row for row in rev_rows if row["top_latin_ngram"] == "the state"][0]
    assert fwd_the["rune_key_hex"] != rev_the["rune_key_hex"]

    summary = (out_dir / "filtered_ngram_summary.csv").read_text(encoding="utf-8")
    assert "strict" in summary
    assert "normal" in summary

    manifest = json.loads((out_dir / "dictionary_manifest.json").read_text(encoding="utf-8"))
    assert manifest["strict"]["selected_plain_words"] == 8
    assert manifest["normal"]["selected_plain_words"] == 11



def test_builder_writes_empty_outputs_when_no_rows_survive(tmp_path: Path) -> None:
    raw_root = tmp_path / "ngrams"
    raw_root.mkdir()
    n2 = raw_root / "2grams.txt"
    n2.write_text(
        "state _end_ 99\n"
        "don't believe 5\n"
        "state 7 3\n",
        encoding="utf-8",
    )

    strict_dir = tmp_path / "dict" / "strict"
    normal_dir = tmp_path / "dict" / "normal"
    _write_policy(strict_dir, ["state", "believe"])
    _write_policy(normal_dir, ["state", "believe"])

    config = builder.BuildConfig(
        repo_root=tmp_path,
        raw_ngram_root=raw_root,
        raw_ngram_files_by_order={2: [n2]},
        raw_ngram_globs_by_order={2: []},
        dictionary_dirs_by_cut={"strict": strict_dir, "normal": normal_dir},
        output_root=tmp_path / "out",
        enabled_orders=(2,),
        enabled_cuts=("strict", "normal"),
        enabled_directions=("fwd", "rev"),
        run_mode="full",
        create_timestamped_run_dir=False,
        sample_line_limit_per_order=0,
        progress_every_lines=0,
    )
    out_dir = builder.build_filtered_ngram_indexes(config)

    for family in ["strict_fwd", "strict_rev", "normal_fwd", "normal_rev"]:
        fp = out_dir / family / "ngram2.csv.gz"
        assert fp.exists(), fp
        assert _read_gzip_csv(fp) == []

    summary = (out_dir / "filtered_ngram_summary.csv").read_text(encoding="utf-8")
    assert ",0,0,0," in summary or "dictionary_kept_rows" in summary

    inventory = (out_dir / "raw_ngram_inventory.csv").read_text(encoding="utf-8")
    assert "rejected_non_plain" in inventory
