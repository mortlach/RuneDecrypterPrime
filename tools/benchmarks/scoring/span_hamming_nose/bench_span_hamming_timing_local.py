from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable
import sys

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_ROOT.exists() and str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext
from rune_decrypter_prime.scoring.span_hamming import SpanHammingBackend, SpanHammingConfig

# Optional override. Keep as None to use packaged wordlists.
WORDLIST_DIR: Path | str | None = None
REQUIRE_SELECTED = True

# Span backend knobs.
LEN_MIN = 3
LEN_MAX = 14
MAX_HD = 2
START_STRIDE = 1
MAX_WINDOWS_TOTAL = 0
MAX_CANDIDATES_PER_WINDOW = 256
MAX_INTERVALS_PER_START = 4
MIN_QUALITY_THRESHOLD = 1e-9

# Timing workload knobs.
TEXT_LENGTH = 1000
N_REAL_SAMPLES = 3
N_SHUFFLE_SAMPLES = 3
N_RANDOM_SAMPLES = 3
ALPHABET_SIZE = 29
RNG_SEED = 12345
WARMUP_ITERS = 1
TIMED_ITERS = 5

WRITE_REPORT_FILE = False
REPORT_OUTPUT_PATH = Path("output/tools/benchmarks/scoring/span_hamming_nose/span_hamming_timing_local.txt")


@dataclass(frozen=True)
class TimingCase:
    family: str
    text: np.ndarray
    label: str


def _resolve_repo_path(path_like: Path | str | None) -> Path | None:
    if path_like is None:
        return None
    p = Path(path_like).expanduser()
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def _build_backend() -> SpanHammingBackend:
    cfg = SpanHammingConfig(
        len_min=int(LEN_MIN),
        len_max=int(LEN_MAX),
        max_hd=int(MAX_HD),
        start_stride=int(START_STRIDE),
        max_windows_total=int(MAX_WINDOWS_TOTAL),
        max_candidates_per_window=int(MAX_CANDIDATES_PER_WINDOW),
        max_intervals_considered_per_start=int(MAX_INTERVALS_PER_START),
        min_quality_threshold=float(MIN_QUALITY_THRESHOLD),
    )
    wl_dir = _resolve_repo_path(WORDLIST_DIR)
    return SpanHammingBackend(
        config=cfg,
        wordlist_dir=wl_dir,
        require_selected=bool(REQUIRE_SELECTED),
    )


def _make_real_samples(base_text: np.ndarray, n_samples: int, text_length: int) -> list[np.ndarray]:
    if n_samples <= 0:
        return []
    max_start = int(base_text.size) - int(text_length)
    if max_start < 0:
        raise ValueError(f"TEXT_LENGTH={text_length} exceeds available base text length={base_text.size}")
    if n_samples == 1 or max_start == 0:
        starts = [0]
    else:
        starts = np.linspace(0, max_start, num=n_samples, dtype=np.int32).tolist()
    out: list[np.ndarray] = []
    for s in starts:
        e = int(s) + int(text_length)
        out.append(np.asarray(base_text[int(s):e], dtype=np.uint8).copy())
    return out


def _build_cases() -> list[TimingCase]:
    rng = np.random.default_rng(int(RNG_SEED))
    base = np.asarray(long_plaintext, dtype=np.uint8).reshape(-1)
    real_samples = _make_real_samples(
        base_text=base,
        n_samples=int(N_REAL_SAMPLES),
        text_length=int(TEXT_LENGTH),
    )
    cases: list[TimingCase] = []
    for i, pt in enumerate(real_samples, start=1):
        cases.append(TimingCase(family="REAL", text=pt, label=f"real_{i}"))

    for i in range(int(N_SHUFFLE_SAMPLES)):
        if not real_samples:
            break
        src = real_samples[i % len(real_samples)]
        shuffled = np.asarray(rng.permutation(src), dtype=np.uint8)
        cases.append(TimingCase(family="SHUFFLE", text=shuffled, label=f"shuffle_{i + 1}"))

    for i in range(int(N_RANDOM_SAMPLES)):
        random_text = rng.integers(0, int(ALPHABET_SIZE), size=int(TEXT_LENGTH), dtype=np.uint8)
        cases.append(TimingCase(family="RANDOM", text=random_text, label=f"random_{i + 1}"))

    return cases


def _summarize_times(times: Iterable[float]) -> dict[str, float]:
    arr = np.asarray(list(times), dtype=np.float64)
    if arr.size == 0:
        return {
            "n_calls": 0.0,
            "mean_ms": float("nan"),
            "median_ms": float("nan"),
            "p90_ms": float("nan"),
            "min_ms": float("nan"),
            "max_ms": float("nan"),
        }
    ms = arr * 1000.0
    return {
        "n_calls": float(arr.size),
        "mean_ms": float(np.mean(ms)),
        "median_ms": float(np.median(ms)),
        "p90_ms": float(np.percentile(ms, 90.0)),
        "min_ms": float(np.min(ms)),
        "max_ms": float(np.max(ms)),
    }


def _fmt(v: float) -> str:
    if not np.isfinite(v):
        return "nan"
    return f"{v:.3f}"


def run_timing() -> str:
    backend = _build_backend()
    cases = _build_cases()
    if not cases:
        raise RuntimeError("No timing cases were generated")

    lines: list[str] = []
    lines.append(f"repo_root={REPO_ROOT}")
    lines.append(
        "config "
        f"wordlist_dir={_resolve_repo_path(WORDLIST_DIR)} require_selected={int(bool(REQUIRE_SELECTED))} "
        f"len=[{int(LEN_MIN)},{int(LEN_MAX)}] max_hd={int(MAX_HD)} "
        f"start_stride={int(START_STRIDE)} max_windows_total={int(MAX_WINDOWS_TOTAL)} "
        f"max_candidates_per_window={int(MAX_CANDIDATES_PER_WINDOW)} "
        f"max_intervals_per_start={int(MAX_INTERVALS_PER_START)} "
        f"text_length={int(TEXT_LENGTH)} warmup={int(WARMUP_ITERS)} timed={int(TIMED_ITERS)} "
        f"samples(real/shuffle/random)={int(N_REAL_SAMPLES)}/{int(N_SHUFFLE_SAMPLES)}/{int(N_RANDOM_SAMPLES)} "
        f"seed={int(RNG_SEED)}"
    )
    lines.append(f"cases_total={len(cases)}")

    family_times: dict[str, list[float]] = {}
    family_stats: dict[str, list[Any]] = {}

    for case in cases:
        for _ in range(int(WARMUP_ITERS)):
            backend.score(case.text)
        case_times: list[float] = []
        last_stats = None
        for _ in range(int(TIMED_ITERS)):
            t0 = perf_counter()
            last_stats = backend.score(case.text)
            case_times.append(float(perf_counter() - t0))

        family_times.setdefault(case.family, []).extend(case_times)
        if last_stats is not None:
            family_stats.setdefault(case.family, []).append(last_stats)

        case_summary = _summarize_times(case_times)
        lines.append(
            f"case family={case.family} label={case.label} "
            f"mean_ms={_fmt(case_summary['mean_ms'])} "
            f"median_ms={_fmt(case_summary['median_ms'])} "
            f"p90_ms={_fmt(case_summary['p90_ms'])}"
        )

    for family in ("REAL", "SHUFFLE", "RANDOM"):
        f_times = family_times.get(family, [])
        if not f_times:
            continue
        summary = _summarize_times(f_times)
        lines.append(
            f"family family={family} n_calls={int(summary['n_calls'])} "
            f"mean_ms={_fmt(summary['mean_ms'])} median_ms={_fmt(summary['median_ms'])} "
            f"p90_ms={_fmt(summary['p90_ms'])} min_ms={_fmt(summary['min_ms'])} max_ms={_fmt(summary['max_ms'])}"
        )

        stats_rows = family_stats.get(family, [])
        if stats_rows:
            span_raw_mean = float(np.mean([float(s.span_raw) for s in stats_rows]))
            coverage_mean = float(np.mean([float(s.coverage) for s in stats_rows]))
            quality_mean = float(np.mean([float(s.quality) for s in stats_rows]))
            windows_scored_mean = float(np.mean([float(s.n_windows_scored) for s in stats_rows]))
            candidates_mean = float(np.mean([float(s.n_candidates_considered) for s in stats_rows]))
            candidates_pruned_mean = float(np.mean([float(s.n_candidates_pruned_cap) for s in stats_rows]))
            lines.append(
                f"family_stats family={family} "
                f"span_raw_mean={_fmt(span_raw_mean)} coverage_mean={_fmt(coverage_mean)} "
                f"quality_mean={_fmt(quality_mean)} windows_scored_mean={_fmt(windows_scored_mean)} "
                f"candidates_mean={_fmt(candidates_mean)} "
                f"candidates_pruned_mean={_fmt(candidates_pruned_mean)}"
            )

    report = "\n".join(lines)
    return report


def main() -> None:
    report = run_timing()
    print(report, flush=True)

    if bool(WRITE_REPORT_FILE):
        out = _resolve_repo_path(REPORT_OUTPUT_PATH)
        if out is None:
            raise ValueError("REPORT_OUTPUT_PATH resolved to None")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report + "\n", encoding="utf-8")
        print(f"wrote_report={out}", flush=True)


if __name__ == "__main__":
    main()
