from __future__ import annotations

"""
Known-correctness calibration runner skeleton for strict O3 anchor diagnostics.

This file is intentionally a skeleton because the production integration must
call the existing strict O3 hit-generation path after making each damaged/null
variant. The damage/null generation is concrete and deterministic; the hook that
turns a token stream into strict O3 hit rows is deliberately explicit.

Do not use this as a production score. It is a report-only calibration harness.
"""

import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
OUTPUT_DIR = ANALYSIS_ROOT / "phaseB_strict_o3_anchor_known_damage_calibration_v1"
for path in (REPO_ROOT, REPO_ROOT / "src", SCRIPT_PATH.parent):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from damage_models_reference_v1 import make_variant, empirical_probs, stable_int_seed, GLOBAL_SEED  # noqa: E402
from strict_o3_anchor_reference_v1 import HitRow, summarise_candidate  # noqa: E402


RUN_LABEL = "phaseB_strict_o3_anchor_known_damage_calibration_v1"
REPORT_ONLY = True
REQUIRE_FWD_ONLY = True

DAMAGE_LEVELS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60)
DAMAGE_MODELS = (
    "independent_substitution",
    "frequency_matched_global",
    "frequency_matched_book",
    "word_local_substitution",
    "burst_substitution",
    "lane_period_substitution",
)
NULL_MODELS = (
    "uniform_random",
    "global_frequency_random",
    "within_chunk_shuffle",
    "block_shuffle_10",
    "block_shuffle_25",
    "block_shuffle_50",
)
REPEATS = 3
LENSES = (
    {"lens_name": "HD0_L10", "max_hd": 0, "min_phrase_length": 10},
    {"lens_name": "HD0_L12", "max_hd": 0, "min_phrase_length": 12},
    {"lens_name": "HD1_L12", "max_hd": 1, "min_phrase_length": 12},
    {"lens_name": "HD2_L15", "max_hd": 2, "min_phrase_length": 15},
)


@dataclass(frozen=True)
class CalibrationChunk:
    chunk_id: str
    book: str
    direction: str
    tokens: tuple[int, ...]
    wli: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class CalibrationSample:
    sample_id: str
    chunk_id: str
    source_kind: str
    model_name: str
    damage_level: str
    repeat_index: int
    seed: int
    changed_fraction: float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def changed_fraction(clean: Sequence[int], variant: Sequence[int]) -> float:
    if len(clean) != len(variant):
        raise ValueError("variant length changed")
    if not clean:
        return 0.0
    changed = sum(1 for a, b in zip(clean, variant) if int(a) != int(b))
    return changed / float(len(clean))


def make_calibration_samples(
    chunks: Sequence[CalibrationChunk],
    *,
    hit_generator: Callable[[str, Sequence[int]], list[HitRow]],
) -> list[dict[str, object]]:
    """Generate damaged/null variants and score them through a supplied hook.

    hit_generator(sample_id, tokens) must return strict O3/N3C FWD hit rows for
    that exact token stream. In repo integration, this should call the same code
    path used by the failed-decryption strict hit-row builder.
    """
    rows: list[dict[str, object]] = []
    all_tokens = [token for chunk in chunks for token in chunk.tokens]
    global_probs = empirical_probs(all_tokens)

    for chunk in chunks:
        if REQUIRE_FWD_ONLY and chunk.direction != "fwd":
            raise ValueError(f"calibration requires FWD chunks only; got {chunk.direction!r}")
        book_probs = empirical_probs(chunk.tokens)
        variants: list[tuple[str, str, str, int, tuple[int, ...], int]] = []
        variants.append(("clean", "none", "", 0, chunk.tokens, stable_int_seed(GLOBAL_SEED, chunk.chunk_id, "clean")))
        for repeat in range(REPEATS):
            for level in DAMAGE_LEVELS:
                for model in DAMAGE_MODELS:
                    seed = stable_int_seed(GLOBAL_SEED, chunk.chunk_id, model, f"{level:.2f}", repeat)
                    tokens = make_variant(
                        chunk.tokens,
                        model_name=model,
                        damage_level=level,
                        seed=seed,
                        wli=chunk.wli,
                        global_probs=global_probs,
                        book_probs=book_probs,
                    )
                    variants.append(("damaged", model, f"{level:.2f}", repeat, tokens, seed))
            for model in NULL_MODELS:
                seed = stable_int_seed(GLOBAL_SEED, chunk.chunk_id, model, repeat)
                tokens = make_variant(
                    chunk.tokens,
                    model_name=model,
                    damage_level=None,
                    seed=seed,
                    wli=chunk.wli,
                    global_probs=global_probs,
                    book_probs=book_probs,
                )
                variants.append(("null", model, "", repeat, tokens, seed))

        for source_kind, model, level, repeat, tokens, seed in variants:
            sample_id = f"{chunk.chunk_id}|{source_kind}|{model}|{level}|r{repeat}"
            hits = hit_generator(sample_id, tokens)
            for lens in LENSES:
                summary, _regions = summarise_candidate(
                    hits,
                    candidate_id=sample_id,
                    trial_id=chunk.chunk_id,
                    min_phrase_length=int(lens["min_phrase_length"]),
                    max_hd=int(lens["max_hd"]),
                )
                rows.append(
                    {
                        "run_label": RUN_LABEL,
                        "created_utc": utc_now(),
                        "chunk_id": chunk.chunk_id,
                        "book": chunk.book,
                        "direction": chunk.direction,
                        "sample_id": sample_id,
                        "source_kind": source_kind,
                        "model_name": model,
                        "damage_level": level,
                        "repeat_index": repeat,
                        "seed": seed,
                        "token_count": len(tokens),
                        "changed_fraction": changed_fraction(chunk.tokens, tokens),
                        "lens_name": lens["lens_name"],
                        **asdict(summary),
                    }
                )
    return rows


def unimplemented_hit_generator(sample_id: str, tokens: Sequence[int]) -> list[HitRow]:
    raise NotImplementedError(
        "Wire this hook to the repo's strict O3/N3C hit-row generator. "
        "The hook must return FWD-only HitRow objects for the supplied token stream."
    )


def write_manifest(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": utc_now(),
        "report_only": REPORT_ONLY,
        "require_fwd_only": REQUIRE_FWD_ONLY,
        "damage_models": list(DAMAGE_MODELS),
        "null_models": list(NULL_MODELS),
        "damage_levels": list(DAMAGE_LEVELS),
        "repeats": REPEATS,
        "lenses": list(LENSES),
        "required_hook": "hit_generator(sample_id, tokens) -> list[HitRow]",
    }
    (output_dir / "known_damage_calibration_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )


if __name__ == "__main__":
    write_manifest(OUTPUT_DIR)
    print("Wrote manifest. Wire hit_generator before running calibration samples.")
