from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Callable, Sequence

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rune_decrypter_prime.api import (
    Direction,
    KeySpec,
    SolverSpec,
    define_map,
    load_lp_master_section,
    load_lp_section,
    run,
)
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish

"""
Goal: Try a "diff + repeating key" hypothesis on LP 5455 using generic map.

Hypothesis (first pass):
1) Feedback step: C[i] = T[i] + C[i-1] (mod 29).
2) Repeating key (len=13) applied to plaintext: T[i] = P[i] + K[i] (mod 29).
3) Interrupters do NOT advance key phase (ignored in this first pass).

We normalize by computing T[i] = C[i] - C[i-1] (mod 29), then solve for P
using the generic map cipher with a repeating key. We run both RTL and LTR
scoring and test add and multiply maps.
"""

N = 29
KEY_LEN = 13
SEED = 5455
LP_SECTION_ID = 13
LP_SPLIT = "page"
VERIFY_MASTER_MATCH = True
RANDOM_CT = False
RANDOM_CT_SEED = 5455
BASELINE_TRIALS = 100
BASELINE_SEED = 5455
BASELINE_CASES = (("add", Direction.LTR),)
WINDOW_LENGTHS = (104,)  # ~8 periods
WINDOW_STEP = 13
WINDOW_TOP_K = 6
MAX_WINDOWS_PER_CASE = 12
WINDOW_BEAM_WIDTH = 12
WINDOW_MAX_CHILDREN = 8
WINDOW_PLATEAU_ROUNDS = 4
RUN_GLOBAL = False
RUN_WINDOWS = False
DIRECTIONS = (Direction.RTL, Direction.LTR)


def _load_lp_5455(
    *,
    random_ct: bool = False,
    random_seed: int | None = None,
) -> tuple[list[int], list[list[int]]]:
    """Load CT/WLI from Liber Primus section 13 (LP 5455)."""
    ct, wli = load_lp_master_section(LP_SECTION_ID, split=LP_SPLIT)
    if VERIFY_MASTER_MATCH:
        base_ct, base_wli = load_lp_section(LP_SECTION_ID, split=LP_SPLIT)
        if ct != base_ct or wli != base_wli:
            raise ValueError("Master transcript mismatch vs LP_DATA for LP 5455.")
    if random_ct:
        rng = random.Random(random_seed)
        ct = [rng.randrange(N) for _ in range(len(ct))]
    return ct, wli


def _diff_stream(ct: Sequence[int], *, n: int = N) -> list[int]:
    """Compute T[i] = C[i] - C[i-1] mod n, with T[0] = 0 as a placeholder."""
    if not ct:
        return []
    out = [0]
    for i in range(1, len(ct)):
        out.append((int(ct[i]) - int(ct[i - 1])) % n)
    return out


def _preview_runes(idx: Sequence[int], wli: Sequence[Sequence[int]], limit: int = 120) -> str:
    runes = Runeglish.to_rune(idx, wli)
    return runes[:limit] + ("..." if len(runes) > limit else "")


def _key_rot_min(key_list: Sequence[int]) -> list[int] | None:
    if not key_list:
        return None
    k = [int(v) for v in key_list]
    rotations = []
    for shift in range(min(KEY_LEN, len(k))):
        rot = k[shift:] + k[:shift]
        rotations.append(rot)
    return min(rotations) if rotations else None


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (pct / 100.0)
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return xs[f]
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def _run_solver(
    *,
    cipher_map: Callable[[int, int], int],
    t_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
    direction: Direction,
    solver: SolverSpec,
    telemetry_on: bool = True,
) -> object:
    cipher = define_map(function=cipher_map, N=N)
    key_spec = KeySpec.repeat(len=KEY_LEN)
    return run(
        text=list(t_idx),
        cipher=cipher,
        key=key_spec,
        solver=solver,
        scorer_params=dict(
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            include_char=True,
            use_word_breaks=True,
            encoding_dir=direction,
        ),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=telemetry_on,
    )


def _score_with_key(
    *,
    cipher_map: Callable[[int, int], int],
    t_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
    direction: Direction,
    key: Sequence[int],
) -> float | None:
    solver = SolverSpec.beam(
        beam_width=1,
        test_key=[int(v) for v in key],
        verbose=False,
        print_progress=False,
        seed=SEED,
    )
    sol = _run_solver(
        cipher_map=cipher_map,
        t_idx=t_idx,
        wli=wli,
        direction=direction,
        solver=solver,
        telemetry_on=False,
    )
    score = getattr(sol, "score", None)
    if score is None:
        return None
    return float(score)


def _phase_gap(
    *,
    cipher_map: Callable[[int, int], int],
    t_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
    direction: Direction,
    key: Sequence[int],
) -> tuple[float, float, int] | None:
    scores: list[tuple[float, int]] = []
    for shift in range(KEY_LEN):
        k = key[shift:] + key[:shift]
        score = _score_with_key(
            cipher_map=cipher_map,
            t_idx=t_idx,
            wli=wli,
            direction=direction,
            key=k,
        )
        if score is None:
            continue
        scores.append((score, shift))
    if len(scores) < 2:
        return None
    scores.sort(key=lambda x: x[0], reverse=True)
    best, second = scores[0][0], scores[1][0]
    gap = best - second
    return gap, best, scores[0][1]


def _scan_windows_collect(
    *,
    cipher_map: Callable[[int, int], int],
    t_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
    direction: Direction,
    lengths: Sequence[int],
    step: int,
    max_windows_per_len: int | None = None,
) -> list[dict]:
    solver = SolverSpec.beam(
        beam_width=WINDOW_BEAM_WIDTH,
        max_children_per_parent=WINDOW_MAX_CHILDREN,
        plateau_rounds=WINDOW_PLATEAU_ROUNDS,
        plateau_min_delta=1e-4,
        stop_score=0.35,
        verbose=False,
        print_progress=False,
        seed=SEED,
    )
    results: list[dict] = []
    L = len(t_idx)
    for win_len in lengths:
        if win_len <= 0 or win_len >= L:
            continue
        seen = 0
        for start in range(1, L - win_len + 1, step):
            t_win = t_idx[start:start + win_len]
            wli_win = wli[start:start + win_len]
            sol = _run_solver(
                cipher_map=cipher_map,
                t_idx=t_win,
                wli=wli_win,
                direction=direction,
                solver=solver,
                telemetry_on=False,
            )
            score = getattr(sol, "score", None)
            if score is None:
                continue
            key = getattr(sol, "key", None)
            key_rot = _key_rot_min(key) if isinstance(key, (list, tuple)) and key else None
            results.append(
                {
                    "score": float(score),
                    "start": start,
                    "length": win_len,
                    "key": key,
                    "key_rot_min": key_rot,
                }
            )
            seen += 1
            if max_windows_per_len and seen >= max_windows_per_len:
                break
    return results


def _repeat_stats(results: list[dict]) -> tuple[float, int, int]:
    items = [r for r in results if r.get("key_rot_min") is not None]
    items.sort(key=lambda r: r["start"])
    if len(items) < 2:
        return 0.0, 1, len(items)
    repeats = 0
    max_run = 1
    run = 1
    for i in range(1, len(items)):
        if items[i]["key_rot_min"] == items[i - 1]["key_rot_min"]:
            repeats += 1
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    ratio = repeats / float(len(items) - 1)
    return ratio, max_run, len(items)


def _run_random_baseline(
    *,
    label: str,
    cipher_map: Callable[[int, int], int],
    wli: Sequence[Sequence[int]],
    direction: Direction,
    trials: int,
    seed: int,
) -> None:
    rng = random.Random(seed)
    best_scores: list[float] = []
    phase_gaps: list[float] = []
    repeat_ratios: list[float] = []
    max_runs: list[int] = []

    print("-" * 72)
    print(f"Random baseline | {label} | direction={direction.value}")
    print(f"Trials: {trials} (seed={seed})")
    for idx in range(trials):
        ct = [rng.randrange(N) for _ in range(len(wli))]
        t_idx = _diff_stream(ct, n=N)
        results = _scan_windows_collect(
            cipher_map=cipher_map,
            t_idx=t_idx,
            wli=wli,
            direction=direction,
            lengths=WINDOW_LENGTHS,
            step=WINDOW_STEP,
            max_windows_per_len=MAX_WINDOWS_PER_CASE,
        )
        if not results:
            continue
        best = max(results, key=lambda r: r["score"])
        best_scores.append(best["score"])

        start = best["start"]
        win_len = best["length"]
        t_win = t_idx[start:start + win_len]
        wli_win = wli[start:start + win_len]
        key = best.get("key")
        gap_val: float | None = None
        if isinstance(key, (list, tuple)) and key:
            gap_info = _phase_gap(
                cipher_map=cipher_map,
                t_idx=t_win,
                wli=wli_win,
                direction=direction,
                key=[int(v) for v in key],
            )
            if gap_info is not None:
                gap_val = gap_info[0]
                phase_gaps.append(gap_val)

        repeat_ratio, max_run, _count = _repeat_stats(results)
        repeat_ratios.append(repeat_ratio)
        max_runs.append(max_run)
        print(
            f"  trial {idx+1:>2}/{trials}: best={best['score']:.4f} "
            f"gap={'n/a' if gap_val is None else f'{gap_val:.4f}'} "
            f"repeat={repeat_ratio:.2f} max_run={max_run}"
        )

    if not best_scores:
        print("  no baseline results")
        return

    def _fmt(p: float | None) -> str:
        return "n/a" if p is None else f"{p:.4f}"

    print("Baseline summary:")
    print(
        "  best window score p50/p90/p95 = "
        f"{_fmt(_percentile(best_scores, 50))}/"
        f"{_fmt(_percentile(best_scores, 90))}/"
        f"{_fmt(_percentile(best_scores, 95))}"
    )
    if phase_gaps:
        print(
            "  phase gap p50/p90/p95 = "
            f"{_fmt(_percentile(phase_gaps, 50))}/"
            f"{_fmt(_percentile(phase_gaps, 90))}/"
            f"{_fmt(_percentile(phase_gaps, 95))}"
        )
    else:
        print("  phase gap p50/p90/p95 = n/a")
    print(
        "  key_rot_min repeat ratio p50/p90/p95 = "
        f"{_fmt(_percentile(repeat_ratios, 50))}/"
        f"{_fmt(_percentile(repeat_ratios, 90))}/"
        f"{_fmt(_percentile(repeat_ratios, 95))}"
    )
    print(
        "  max run length p50/p90/p95 = "
        f"{_fmt(_percentile([float(v) for v in max_runs], 50))}/"
        f"{_fmt(_percentile([float(v) for v in max_runs], 90))}/"
        f"{_fmt(_percentile([float(v) for v in max_runs], 95))}"
    )
def _run_case(
    *,
    label: str,
    cipher_map: Callable[[int, int], int],
    t_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
    direction: Direction,
) -> None:
    solver = SolverSpec.beam(
        beam_width=32,
        max_children_per_parent=24,
        plateau_rounds=10,
        plateau_min_delta=1e-4,
        stop_score=0.50,
        verbose=True,
        progress_pct=2,
        print_progress=True,
        seed=SEED,
    )

    print("=" * 72)
    print(f"{label} | direction={direction.value}")
    print("Derived T preview:", _preview_runes(t_idx, wli))

    sol = _run_solver(
        cipher_map=cipher_map,
        t_idx=t_idx,
        wli=wli,
        direction=direction,
        solver=solver,
    )

    print_run_report(
        title=f"LP 5455 diff-vig ({label}, {direction.value})",
        cipher="user_map2",
        solution=sol,
        match_ok=None,
        app_version="solve-5455",
        key_len=KEY_LEN,
        wli=wli,
        verbose=True,
    )


def _scan_windows(
    *,
    label: str,
    cipher_map: Callable[[int, int], int],
    t_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
    direction: Direction,
    lengths: Sequence[int],
    step: int,
    top_k: int = WINDOW_TOP_K,
) -> None:
    solver = SolverSpec.beam(
        beam_width=WINDOW_BEAM_WIDTH,
        max_children_per_parent=WINDOW_MAX_CHILDREN,
        plateau_rounds=WINDOW_PLATEAU_ROUNDS,
        plateau_min_delta=1e-4,
        stop_score=0.35,
        verbose=False,
        print_progress=False,
        seed=SEED,
    )
    results: list[dict] = []
    L = len(t_idx)
    print("-" * 72)
    print(f"Window scan | {label} | direction={direction.value}")
    for win_len in lengths:
        if win_len <= 0 or win_len >= L:
            continue
        count = max(0, 1 + (L - win_len) // step)
        print(f"  scanning win_len={win_len} (~{count} windows)")
        seen = 0
        for start in range(1, L - win_len + 1, step):
            t_win = t_idx[start:start + win_len]
            wli_win = wli[start:start + win_len]
            sol = _run_solver(
                cipher_map=cipher_map,
                t_idx=t_win,
                wli=wli_win,
                direction=direction,
                solver=solver,
                telemetry_on=False,
            )
            score = getattr(sol, "score", None)
            if score is None:
                continue
            results.append(
                {
                    "score": float(score),
                    "start": start,
                    "length": win_len,
                    "key": getattr(sol, "key", None),
                    "plaintext_idx": getattr(sol, "plaintext_idx", []),
                    "wli": wli_win,
                }
            )
            seen += 1
            if seen >= MAX_WINDOWS_PER_CASE:
                print(f"  capped at {MAX_WINDOWS_PER_CASE} windows for win_len={win_len}")
                break
    if not results:
        print("  no window results")
        return
    results.sort(key=lambda r: r["score"], reverse=True)
    limit = min(top_k, len(results))
    print(f"Top {limit} windows:")
    for row in results[:limit]:
        preview = _preview_runes(row["plaintext_idx"], row["wli"], limit=90)
        print(
            f"  score={row['score']:.4f} start={row['start']:>3} "
            f"len={row['length']:>3} preview={preview}"
        )
        key = row.get("key") or []
        if isinstance(key, (list, tuple)) and key:
            key_list = [int(v) for v in key]
            print(f"    key={key_list}")
            best_rot = _key_rot_min(key_list)
            if best_rot is not None:
                print(f"    key_rot_min={best_rot}")


def main() -> None:
    ct_idx, wli = _load_lp_5455(random_ct=RANDOM_CT, random_seed=RANDOM_CT_SEED)
    if len(ct_idx) != len(wli):
        raise ValueError(f"CT/WLI length mismatch: {len(ct_idx)} vs {len(wli)}")

    if RANDOM_CT:
        print(f"Using random CT (seed={RANDOM_CT_SEED})")
    print("CT preview:", _preview_runes(ct_idx, wli))
    t_idx = _diff_stream(ct_idx, n=N)

    def add_map(pt: int, k: int) -> int:
        return (pt + k) % N

    def mul_map(pt: int, k: int) -> int:
        return (pt * k) % N

    if BASELINE_TRIALS > 0:
        for label, direction in BASELINE_CASES:
            cmap = add_map if label == "add" else mul_map
            _run_random_baseline(
                label=label,
                cipher_map=cmap,
                wli=wli,
                direction=direction,
                trials=BASELINE_TRIALS,
                seed=BASELINE_SEED,
            )

    for direction in DIRECTIONS:
        if RUN_GLOBAL:
            _run_case(
                label="add",
                cipher_map=add_map,
                t_idx=t_idx,
                wli=wli,
                direction=direction,
            )
            _run_case(
                label="mul",
                cipher_map=mul_map,
                t_idx=t_idx,
                wli=wli,
                direction=direction,
            )
        if RUN_WINDOWS:
            _scan_windows(
                label="add",
                cipher_map=add_map,
                t_idx=t_idx,
                wli=wli,
                direction=direction,
                lengths=WINDOW_LENGTHS,
                step=WINDOW_STEP,
            )
            _scan_windows(
                label="mul",
                cipher_map=mul_map,
                t_idx=t_idx,
                wli=wli,
                direction=direction,
                lengths=WINDOW_LENGTHS,
                step=WINDOW_STEP,
            )


if __name__ == "__main__":
    main()
