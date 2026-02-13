"""
End-to-end benchmark: seed pool -> Kaeding solver (PeriodicColumnar).

Purpose
-------
We already have a seed-quality benchmark (`bench_seed_periodic_columnar.py`) that
measures raw_fulltext (unwindowed avg logp over the whole text) and reports
PCT/ECDF transfer diagnostics.

This benchmark answers the next questions:
  1) Do these seeds improve Kaeding Stage-1 outcomes under the real engine?
  2) If Kaeding emits a top-K candidate set, can WLI-2 rerank "snap" us closer to truth
     (measured by best-1 / best-K match_ratio), without letting WLI steer the optimiser yet?

Notes
-----
* Kaeding in the engine operates on the scorer's objective (typically PCT) but can
  optimise "raw" when available via evaluate_keys_with_raw(). In the current engine,
  that "raw" is the win=10 windowed mean-per-ngram stat (diagnostic here as raw_native_win10).
* We intentionally report:
    - raw_fulltext_char (primary, Kaeding-original-style)
    - raw_fulltext_wli1/wli2 (Stage-2 rerank metrics; full-stream and within-word variants)
    - raw_native_win10 (engine raw)
    - pct_ecdf (engine objective)
  so we can see transfer and objective mismatch.
* WLI is only used for reranking here; Stage-1 solver runs with WLI disabled.
"""

from __future__ import annotations

import sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, ObjectiveFamily, ObjectiveSpec, SeMode, Stat, ScorerImpl
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils_periodic_columnar import SeedPlan, generate_seed_keys_periodic_columnar
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string

ALPHABET_SIZE = 29
ORDER = "col_then_sub"

# How many random keys to sample for a quick "is the oracle sane?" guard.
RANDOM_KEYS_SANITY = 32
TOP_K = 64  # candidate retention / rerank pool size

# Optional resume mode
# - Set to a previous benchmark output folder to continue only missing runs.
# - Keep as None for a fresh run.
#
# Example:
# RESUME_FROM_RUN_DIR = r"output/tools/benchmarks/20260213T062803Z__bench_solve__82e3c05"
RESUME_FROM_RUN_DIR: str | None = None#r"output/tools/benchmarks/20260213T062803Z__bench_solve__82e3c05"


@dataclass(frozen=True)
class Tier:
    name: str
    period: int
    columns: int
    length: int


@dataclass(frozen=True)
class Budget:
    name: str
    solver: SolverSpec
    seed_plan: SeedPlan
    n_seed_keys: int


TIERS: List[Tier] = [
    Tier(name="hard_p9_c13_l1200", period=9, columns=13, length=1200),
    Tier(name="goal_p13_c13_l300", period=13, columns=13, length=300),
]

TEXT_OFFSETS = [0, 211]
KEY_SEEDS = [111, 222]

# Keep Kaeding budgets modest; this tool is meant to be run often.
# If you want "real solve" budgets, edit these up.
SOLVER_BUDGETS: List[Budget] = [
    Budget(
        name="small",
        solver=SolverSpec.kaeding(
            # NOTE: This benchmark is meant to be run often. Keep the default
            # budget low enough that a full grid run completes in hours, not days.
            # Increase these deliberately when you want a "real solve" run.
            steps=300,
            restarts=2,
            inner_batch=128,
            col_every=10,
            col_batch=64,
            slip_every=60,
            slip_blocks=1,
            slip_policy="stall",
            stall_rounds=250,
            stall_slip_limit=3,
            slip_swaps=40,
            use_raw_score=True,
            top_k=TOP_K,
            progress_pct=10,
            print_progress=True,
            seed=2026,
        ),
        seed_plan=SeedPlan(n_block_seeds=8, n_tail_seeds=8, n_starts=64, refine_steps=800),
        n_seed_keys=64,
    ),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_short_hash() -> str:
    try:
        value = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=_repo_root()).decode().strip()
        return value or "nogit"
    except Exception:
        return "nogit"


def _write_reports(rows: List[dict], summary: dict) -> Path:
    root = _repo_root()
    out_root = root / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"{stamp}__bench_solve__{_git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "instances.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_csv(run_dir / "instances.csv", rows)
    return run_dir


def _row_id(row: dict) -> tuple[str, str, str, int, int]:
    return (
        str(row["tier"]),
        str(row["budget"]),
        str(row["mode"]),
        int(row["text_id"]),
        int(row["key_seed"]),
    )


def _load_resume_rows(run_dir: Path) -> List[dict]:
    p = run_dir / "instances.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError(f"[bench_solve] resume file is not a row list: {p}")
    out: List[dict] = []
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            raise RuntimeError(f"[bench_solve] resume row {i} is not an object")
        out.append(row)
    return out


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _compute_summary(rows: List[dict]) -> dict:
    # Summary: percentiles by (tier,budget,mode)
    summary: dict = {"tiers": {}}
    groups: Dict[Tuple[str, str, str], List[dict]] = {}
    for row in rows:
        groups.setdefault((row["tier"], row["budget"], row["mode"]), []).append(row)

    for (tier, budget, mode), items in groups.items():
        # Objective misalignment diagnostics: how often does the optimiser beat the oracle?
        pct_gap = [float(r["sol_pct"]) - float(r["oracle_pct"]) for r in items]
        raw_full_gap = [float(r["sol_raw_full"]) - float(r["oracle_raw_full"]) for r in items]
        raw_native_gap = [float(r["sol_raw_native"]) - float(r["oracle_raw_native"]) for r in items]
        entry = dict(
            tier=tier,
            budget=budget,
            mode=mode,
            n=len(items),
            sol_raw_full=_percentiles([r["sol_raw_full"] for r in items]),
            sol_raw_native=_percentiles([r["sol_raw_native"] for r in items]),
            sol_pct=_percentiles([r["sol_pct"] for r in items]),
            match_ratio=_percentiles([r["match_ratio"] for r in items]),
            bestk_match_ratio=_percentiles([float(r.get("bestk_match_ratio", float("nan"))) for r in items]),
            pick_wli1_match_ratio=_percentiles([float(r.get("pick_wli1_match_ratio", float("nan"))) for r in items]),
            pick_wli2_full_match_ratio=_percentiles([float(r.get("pick_wli2_full_match_ratio", float("nan"))) for r in items]),
            pick_wli2_within_match_ratio=_percentiles([float(r.get("pick_wli2_within_match_ratio", float("nan"))) for r in items]),
            evals=_percentiles([float(r.get("evals", 0) or 0) for r in items]),
            seconds=_percentiles([float(r.get("seconds", 0.0) or 0.0) for r in items]),
            oracle_gap_pct=_percentiles(pct_gap),
            oracle_gap_raw_full=_percentiles(raw_full_gap),
            oracle_gap_raw_native=_percentiles(raw_native_gap),
            rate_sol_gt_oracle_pct=float(np.mean(np.asarray(pct_gap, dtype=np.float64) > 0.0)),
            rate_sol_gt_oracle_raw_full=float(np.mean(np.asarray(raw_full_gap, dtype=np.float64) > 0.0)),
            rate_sol_gt_oracle_raw_native=float(np.mean(np.asarray(raw_native_gap, dtype=np.float64) > 0.0)),
        )
        summary["tiers"].setdefault(tier, []).append(entry)

    return summary


def _checkpoint(run_dir: Path, *, rows: List[dict]) -> dict:
    # Rows are small (tens), so rewriting is cheap and avoids jsonl parsing.
    summary = _compute_summary(rows)
    _atomic_write_text(run_dir / "instances.json", json.dumps(rows, indent=2))
    _atomic_write_text(run_dir / "summary.json", json.dumps(summary, indent=2))
    _write_csv(run_dir / "instances.csv", rows)
    return summary


def _write_csv(path: Path, rows: List[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    lines = [",".join(keys)]
    for row in rows:
        lines.append(",".join(str(row.get(k, "")) for k in keys))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _require_assets(direction: Direction, *, ns: Tuple[int, ...], need_wli: bool) -> Path:
    # Reuse the strict test guard; if it's not importable, fail loudly.
    from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
    models = ("char", "wli") if need_wli else ("char",)
    try:
        root, _ = require_full_lm_assets(
            models=models,
            modes=(direction.value,),
            poses=("nose",),
            ns=ns,
            ecdf_stats=("logp",),
        )
        return root
    except Exception as exc:
        raise RuntimeError(f"LM assets missing or incomplete: {exc}") from exc


def _encode_long_plaintext(direction: Direction) -> tuple[np.ndarray, np.ndarray]:
    pt_idx, wli, _runes = Runeglish.encode_english_to_runes(long_plaintext_string.strip(), direction=direction.value)
    pt_u8 = np.asarray(pt_idx, dtype=np.uint8)
    wli_u8 = np.asarray(wli, dtype=np.uint8)
    if wli_u8.ndim != 2 or wli_u8.shape[1] != 2 or wli_u8.shape[0] != pt_u8.size:
        raise RuntimeError("[bench_solve] Runeglish returned WLI with unexpected shape")
    return pt_u8, wli_u8


def _tile_stream(pt_base: np.ndarray, wli_base: np.ndarray, needed: int) -> tuple[np.ndarray, np.ndarray]:
    if pt_base.size == 0:
        raise ValueError("Encoded plaintext is empty")
    if wli_base.shape[0] != pt_base.size:
        raise ValueError("pt_base and wli_base length mismatch")
    if pt_base.size >= needed:
        return pt_base, wli_base
    reps = int(np.ceil(needed / pt_base.size))
    pt_t = np.tile(pt_base, reps)
    wli_t = np.tile(wli_base, (reps, 1))
    return np.ascontiguousarray(pt_t, dtype=np.uint8), np.ascontiguousarray(wli_t, dtype=np.uint8)


def _slice_word_aligned(
    pt_base: np.ndarray,
    wli_base: np.ndarray,
    *,
    length: int,
    offset_hint: int,
    max_scan: int = 50_000,
) -> tuple[np.ndarray, List[List[int]], int]:
    """
    Return a (pt_idx, wli_list, offset_used) slice of exact token length that starts and ends
    on word boundaries so WLI remains valid for the slice.

    This is a hard requirement for any benchmark that uses WLI scoring.
    """
    length = int(length)
    offset_hint = int(offset_hint)
    if length <= 0:
        raise ValueError("length must be > 0")
    if offset_hint < 0:
        raise ValueError("offset_hint must be >= 0")

    # Ensure we have room to scan without worrying about wrap.
    pt_t, wli_t = _tile_stream(pt_base, wli_base, needed=offset_hint + length + max_scan + 4)

    start_min = offset_hint
    start_max = offset_hint + max_scan
    L = int(pt_t.size)
    for s in range(start_min, min(start_max, L)):
        if int(wli_t[s, 0]) != 0:
            continue
        e = s + length - 1
        if e >= L:
            break
        pos_e = int(wli_t[e, 0])
        len_e = int(wli_t[e, 1])
        if pos_e != (len_e - 1):
            continue
        pt = np.ascontiguousarray(pt_t[s : s + length], dtype=np.uint8)
        wli = [[int(a), int(b)] for a, b in wli_t[s : s + length].tolist()]
        return pt, wli, int(s)

    raise RuntimeError(f"[bench_solve] could not find word-aligned slice length={length} near offset={offset_hint}")


def _word_spans_from_wli(wli: Sequence[Sequence[int]]) -> List[Tuple[int, int]]:
    """Return (start,end) spans (end exclusive) for each word based on wli pairs."""
    spans: List[Tuple[int, int]] = []
    start = 0
    for i, pair in enumerate(wli):
        pos = int(pair[0])
        ln = int(pair[1])
        if pos == 0:
            start = int(i)
        if pos == ln - 1:
            spans.append((start, int(i) + 1))
    return spans


class RawFulltextScorer:
    """
    Unwindowed avg logp over the *entire text* (Kaeding-style).

    Supports:
      - char n-grams via LMPrime model="char"
      - wli n-grams via LMPrime model="wli" (requires WLI stream)

    For WLI-2 we benchmark two definitions:
      - full-stream: score over the entire stream (includes cross-word n-grams)
      - within-word: score each word independently and average across within-word n-grams only
    """

    def __init__(
        self,
        *,
        lm: LanguageModelPrime,
        direction: Direction,
        model: str,
        weights: Dict[int, float],
        within_word: bool = False,
    ):
        self.direction = direction
        self.lm = lm
        self.model = str(model).lower()
        if self.model not in {"char", "wli"}:
            raise ValueError("model must be 'char' or 'wli'")
        self.within_word = bool(within_word)
        self.weights = {int(n): float(w) for n, w in weights.items() if int(n) > 0 and float(w) > 0.0}
        if not self.weights:
            raise ValueError("RawFulltextScorer requires at least one positive n-gram weight")

    def score(self, pt: np.ndarray, wli: Sequence[Sequence[int]] | None = None, *, word_spans: List[Tuple[int, int]] | None = None) -> float:
        pt_u8 = np.asarray(pt, dtype=np.uint8).reshape(-1)
        L = int(pt_u8.size)
        if L <= 0:
            return float("-inf")

        total_w = float(sum(self.weights.values()))
        acc = 0.0

        if self.model == "char":
            seq = pt_u8.tolist()
            for n, w in self.weights.items():
                n = int(n)
                total_eval = L - n + 1
                if total_eval <= 0:
                    return float("-inf")
                res = self.lm.score([seq], None, direction=self.direction.value, se="nose", n=n, model="char")[0]
                acc += float(w) * (float(res.logprob_sum) / float(total_eval))
            return acc / total_w

        # model == "wli"
        if wli is None:
            raise ValueError("wli is required when model='wli'")
        if len(wli) != L:
            raise ValueError("wli length must match plaintext length")

        if not self.within_word:
            seq = pt_u8.tolist()
            wli_sent = [[int(a), int(b)] for a, b in wli]
            for n, w in self.weights.items():
                n = int(n)
                total_eval = L - n + 1
                if total_eval <= 0:
                    return float("-inf")
                res = self.lm.score([seq], [wli_sent], direction=self.direction.value, se="nose", n=n, model="wli")[0]
                acc += float(w) * (float(res.logprob_sum) / float(total_eval))
            return acc / total_w

        # within-word scoring
        spans = word_spans if word_spans is not None else _word_spans_from_wli(wli)
        for n, w in self.weights.items():
            n = int(n)
            total_eval = 0
            total_logp = 0.0
            for s, e in spans:
                wlen = int(e - s)
                if wlen < n:
                    continue
                pt_word = pt_u8[s:e].tolist()
                wli_word = [[int(a), int(b)] for a, b in wli[s:e]]
                res = self.lm.score([pt_word], [wli_word], direction=self.direction.value, se="nose", n=n, model="wli")[0]
                total_logp += float(res.logprob_sum)
                total_eval += int(wlen - n + 1)
            if total_eval <= 0:
                return float("-inf")
            acc += float(w) * (total_logp / float(total_eval))
        return acc / total_w


def _pct_scorer(direction: Direction, *, model_root: Path, char_weights: Dict[int, float]) -> Any:
    cfg = ScoringConfig(
        model_root=model_root,
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        se_mode=SeMode.NOSE,
        encoding_dir=direction,
        include_char=True,
        use_word_breaks=False,
        char_weights=dict(char_weights),
        wli_weights={},
        impl=ScorerImpl.NUMPY,
    )
    dummy_cipher_cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=5,
        columns=7,
        alphabet_size=ALPHABET_SIZE,
        key_length=5 * ALPHABET_SIZE + 7,
        order=ORDER,
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    return build_scorer(dummy_cipher_cfg, cfg)


def _score_pt(pt: np.ndarray, *, raw_full_scorer: RawFulltextScorer, pct_scorer: Any) -> Tuple[float, float, float]:
    raw_full = float(raw_full_scorer.score(pt))
    pct, raw_native = pct_scorer.score_with_raw(pt, None)
    return raw_full, float(pct), float(raw_native)


def _match_ratio(a: Sequence[int], b: Sequence[int]) -> float:
    aa = np.asarray(a, dtype=np.int64).reshape(-1)
    bb = np.asarray(b, dtype=np.int64).reshape(-1)
    n = min(int(aa.size), int(bb.size))
    if n <= 0:
        return 0.0
    return float(np.mean(aa[:n] == bb[:n]))


def _percentiles(values: Iterable[float], pcts: Tuple[int, ...] = (10, 25, 50, 75, 90, 95)) -> Dict[str, float]:
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.size == 0:
        return {f"p{p}": float("nan") for p in pcts}
    out = {}
    for p in pcts:
        out[f"p{p}"] = float(np.percentile(arr, p))
    out["mean"] = float(np.mean(arr))
    out["std"] = float(np.std(arr))
    return out


def _oracle_vs_random_stats(oracle: float, random_scores: Sequence[float]) -> dict:
    """
    Return cheap discrimination stats.

    * oracle_pctile: fraction of random scores strictly below oracle (empirical CDF)
    * rand_mean/std: baseline distribution moments
    * sep_z: (oracle-mean)/std (nan when std==0)
    """
    arr = np.asarray(list(random_scores), dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return {"oracle_pctile": float("nan"), "rand_mean": float("nan"), "rand_std": float("nan"), "sep_z": float("nan")}
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    pctile = float(np.mean(arr < float(oracle)))
    sep_z = float((float(oracle) - mean) / std) if std > 0 else float("nan")
    return {"oracle_pctile": pctile, "rand_mean": mean, "rand_std": std, "sep_z": sep_z}


def _format_seconds(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, sec = divmod(seconds, 60.0)
    if minutes < 60:
        return f"{int(minutes)}m{sec:04.1f}s"
    hours, minutes = divmod(minutes, 60.0)
    return f"{int(hours)}h{int(minutes):02d}m"


def main() -> None:
    direction = Direction.LTR
    raw_weights = {3: 0.5, 4: 0.5}
    pct_weights = {3: 0.5, 4: 0.5}
    wli1_weights = {1: 1.0}
    wli2_weights = {2: 1.0}

    required_ns = tuple(sorted({*raw_weights.keys(), *pct_weights.keys(), *wli1_weights.keys(), *wli2_weights.keys()}))
    lm_root = _require_assets(direction, ns=required_ns, need_wli=True)

    lm = LanguageModelPrime(
        lm_root=lm_root,
        smoothing="auto_gt",
        alpha=0.5,
        oov_policy="floor_min_seen",
        include_char=True,
    )
    raw_full_scorer = RawFulltextScorer(lm=lm, direction=direction, model="char", weights=raw_weights)
    wli1_scorer = RawFulltextScorer(lm=lm, direction=direction, model="wli", weights=wli1_weights, within_word=False)
    wli2_full_scorer = RawFulltextScorer(lm=lm, direction=direction, model="wli", weights=wli2_weights, within_word=False)
    wli2_within_scorer = RawFulltextScorer(lm=lm, direction=direction, model="wli", weights=wli2_weights, within_word=True)
    pct_scorer = _pct_scorer(direction, model_root=lm_root, char_weights=pct_weights)

    pt_base, wli_base = _encode_long_plaintext(direction)
    if pt_base.size == 0 or wli_base.size == 0:
        raise RuntimeError("[bench_solve] encoded plaintext is empty")

    rows: List[dict] = []
    t0_all = time.time()

    # Each instance is solved in 3 modes: no seeds, raw seeds, pct-reranked seeds.
    seed_modes = ["none", "seed_raw", "seed_pct_rerank"]
    total_instances = len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS) * len(SOLVER_BUDGETS)
    total_solves = total_instances * len(seed_modes)
    # Resume support (no CLI): continue only missing (tier,budget,mode,text_id,key_seed).
    if RESUME_FROM_RUN_DIR:
        run_dir = Path(RESUME_FROM_RUN_DIR)
        if not run_dir.is_absolute():
            run_dir = (_repo_root() / run_dir).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
        rows = _load_resume_rows(run_dir)
        completed = {_row_id(r) for r in rows}
        done_solves = len(completed)
        print(
            f"[bench_solve] Resuming from {run_dir.relative_to(_repo_root())} "
            f"with {done_solves}/{total_solves} completed solves",
            flush=True,
        )
        # Re-write summary/csv once on startup so files are consistent with loaded rows.
        _checkpoint(run_dir, rows=rows)
    else:
        done_solves = 0
        run_dir = _write_reports(rows=[], summary={"tiers": {}})
        completed = set()

    rel = run_dir.relative_to(_repo_root())
    print(f"[bench_solve] Reports will be written to {rel}", flush=True)
    print(f"[bench_solve] Starting {total_solves} solves ({total_instances} instances x {len(seed_modes)} modes)", flush=True)

    for tier in TIERS:
        for text_id, offset in enumerate(TEXT_OFFSETS):
            pt_idx, wli_list, offset_used = _slice_word_aligned(
                pt_base,
                wli_base,
                length=tier.length,
                offset_hint=offset,
            )
            word_spans = _word_spans_from_wli(wli_list)
            for key_seed in KEY_SEEDS:
                # Skip expensive setup when this entire (tier,text,key_seed) instance is already complete.
                pending_instance = False
                for _budget in SOLVER_BUDGETS:
                    for _mode in seed_modes:
                        rid = (tier.name, _budget.name, _mode, int(text_id), int(key_seed))
                        if rid not in completed:
                            pending_instance = True
                            break
                    if pending_instance:
                        break
                if not pending_instance:
                    continue

                key_len = tier.period * ALPHABET_SIZE + tier.columns
                rng = np.random.default_rng(int(key_seed))
                keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=tier.period, A=ALPHABET_SIZE, columns=tier.columns)
                key_true = keyops.random(rng).astype(np.int16, copy=False)

                cipher_cfg = CipherConfig(
                    name="periodic_columnar",
                    ciphertext=[],
                    period=tier.period,
                    columns=tier.columns,
                    alphabet_size=ALPHABET_SIZE,
                    key_length=key_len,
                    order=ORDER,
                    encoding_dir=direction,
                    wli_data=[],
                    device=Device.CPU,
                )
                cipher = PeriodicColumnarCipher(cipher_cfg)
                ct_idx = cipher.encrypt_single(plaintext=pt_idx, key=key_true)

                oracle_raw_full, oracle_pct, oracle_raw_native = _score_pt(pt_idx, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer)
                oracle_wli1 = float(wli1_scorer.score(pt_idx, wli_list))
                oracle_wli2_full = float(wli2_full_scorer.score(pt_idx, wli_list))
                oracle_wli2_within = float(wli2_within_scorer.score(pt_idx, wli_list, word_spans=word_spans))

                # Quick sanity: oracle should beat random under all primary metrics.
                random_raw_full = []
                random_pct = []
                random_raw_native = []
                random_wli1 = []
                random_wli2_full = []
                random_wli2_within = []
                for _ in range(RANDOM_KEYS_SANITY):
                    k = keyops.random(rng).astype(np.int16, copy=False)
                    pt_rand = cipher.decrypt_single(ciphertext=ct_idx, key=k)
                    r_full, r_pct, r_nat = _score_pt(pt_rand, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer)
                    random_raw_full.append(r_full)
                    random_pct.append(r_pct)
                    random_raw_native.append(r_nat)
                    random_wli1.append(float(wli1_scorer.score(pt_rand, wli_list)))
                    random_wli2_full.append(float(wli2_full_scorer.score(pt_rand, wli_list)))
                    random_wli2_within.append(float(wli2_within_scorer.score(pt_rand, wli_list, word_spans=word_spans)))
                if not (oracle_raw_full > float(np.max(random_raw_full))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_raw_fulltext <= best_random_raw_fulltext")
                if not (oracle_pct > float(np.max(random_pct))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_pct <= best_random_pct")
                if not (oracle_raw_native > float(np.max(random_raw_native))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_raw_native <= best_random_raw_native")
                if not (oracle_wli1 > float(np.max(random_wli1))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_wli1 <= best_random_wli1 (WLI wiring likely wrong)")

                disc_char = _oracle_vs_random_stats(oracle_raw_full, random_raw_full)
                disc_wli1 = _oracle_vs_random_stats(oracle_wli1, random_wli1)
                disc_wli2_full = _oracle_vs_random_stats(oracle_wli2_full, random_wli2_full)
                disc_wli2_within = _oracle_vs_random_stats(oracle_wli2_within, random_wli2_within)

                for budget in SOLVER_BUDGETS:
                    budget_pending = any(
                        (tier.name, budget.name, m, int(text_id), int(key_seed)) not in completed for m in seed_modes
                    )
                    if not budget_pending:
                        continue

                    # Seed generator configs (for the two seed modes)
                    seed_cfg = ScoringConfig(
                        model_root=lm_root,
                        encoding_dir=direction,
                        include_char=True,
                        use_word_breaks=False,
                        char_weights=dict(raw_weights),
                        wli_weights={},
                        impl=ScorerImpl.NUMPY,
                    )
                    rerank_cfg = ScoringConfig(
                        model_root=lm_root,
                        encoding_dir=direction,
                        include_char=True,
                        use_word_breaks=False,
                        char_weights=dict(pct_weights),
                        wli_weights={},
                        impl=ScorerImpl.NUMPY,
                        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
                    )

                    seed_pool_raw = None
                    seed_pool_pct = None

                    for mode in seed_modes:
                        row_id = (tier.name, budget.name, mode, int(text_id), int(key_seed))
                        if row_id in completed:
                            continue

                        t0 = time.time()
                        seed_keys = None
                        if mode == "seed_raw":
                            if seed_pool_raw is None:
                                seed_pool_raw = generate_seed_keys_periodic_columnar(
                                    ct_idx,
                                    period=tier.period,
                                    columns=tier.columns,
                                    order=ORDER,
                                    direction=direction,
                                    seed=2026 + int(key_seed),
                                    scoring_cfg=seed_cfg,
                                    n_keys=budget.n_seed_keys,
                                    plan=budget.seed_plan,
                                    refine=True,
                                    rerank_cfg=None,
                                )
                            seed_keys = seed_pool_raw
                        elif mode == "seed_pct_rerank":
                            if seed_pool_pct is None:
                                seed_pool_pct = generate_seed_keys_periodic_columnar(
                                    ct_idx,
                                    period=tier.period,
                                    columns=tier.columns,
                                    order=ORDER,
                                    direction=direction,
                                    seed=2026 + int(key_seed),
                                    scoring_cfg=seed_cfg,
                                    n_keys=budget.n_seed_keys,
                                    plan=budget.seed_plan,
                                    refine=True,
                                    rerank_cfg=rerank_cfg,
                                )
                            seed_keys = seed_pool_pct

                        scorer_params = dict(
                            objective="pct.logp.win10",
                            include_char=True,
                            use_word_breaks=False,
                            char_weights=dict(pct_weights),
                            wli_weights={},
                            encoding_dir=direction,
                            impl=ScorerImpl.NUMPY,
                        )

                        cipher_spec = by_name.cipher(
                            "periodic_columnar",
                            period=tier.period,
                            columns=tier.columns,
                            alphabet_size=ALPHABET_SIZE,
                            order=ORDER,
                        )
                        key_spec = KeySpec.periodic_columnar(
                            period=tier.period,
                            columns=tier.columns,
                            alphabet_size=ALPHABET_SIZE,
                        )

                        sol = run(
                            text=ct_idx.tolist(),
                            cipher=cipher_spec,
                            key=key_spec,
                            solver=budget.solver,
                            device=Device.CPU,
                            scorer_params=scorer_params,
                            telemetry_on=True,
                            encoding_dir=direction,
                            force_no_wli=True,
                            **({} if seed_keys is None else {"initial_keys": seed_keys}),
                        )

                        pt_sol = np.asarray(getattr(sol, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                        sol_raw_full, sol_pct, sol_raw_native = _score_pt(pt_sol, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer)
                        match = _match_ratio(pt_sol.tolist(), pt_idx.tolist())

                        tel = getattr(sol, "meta", {}).get("telemetry", {}) if hasattr(sol, "meta") else {}
                        work = getattr(sol, "meta", {}).get("work", {}) if hasattr(sol, "meta") else {}

                        # ---------------- Stage-2 diagnostics: candidate retention + WLI rerank ----------------
                        stage2_t0 = time.time()

                        cand_keys: List[List[int]] = []
                        try:
                            k_meta = tel.get("kaeding", {}) if isinstance(tel, dict) else {}
                            top_keys = k_meta.get("top_keys", None) if isinstance(k_meta, dict) else None
                            if isinstance(top_keys, list):
                                cand_keys.extend([list(map(int, row)) for row in top_keys])
                        except Exception:
                            cand_keys = []
                        try:
                            k_best = getattr(sol, "key", None)
                            if k_best is not None:
                                cand_keys.append(list(map(int, list(k_best))))
                        except Exception:
                            pass

                        # Stable de-dup while preserving order.
                        seen: set[tuple[int, ...]] = set()
                        cand_keys_u: List[List[int]] = []
                        for k in cand_keys:
                            t = tuple(int(x) for x in k)
                            if t in seen:
                                continue
                            seen.add(t)
                            cand_keys_u.append(list(k))
                        cand_keys = cand_keys_u[:TOP_K]

                        # Persist candidate set for auditability / recomputation.
                        cand_dir = run_dir / "candidates"
                        cand_dir.mkdir(parents=True, exist_ok=True)
                        cand_name = f"{tier.name}__{budget.name}__{mode}__text{text_id}__seed{key_seed}.json"
                        cand_path = cand_dir / cand_name
                        _atomic_write_text(cand_path, json.dumps({"keys": cand_keys}, indent=2))

                        bestk_match = float(match)
                        pick_wli1_match = float(match)
                        pick_wli2_full_match = float(match)
                        pick_wli2_within_match = float(match)

                        if cand_keys:
                            bestk_match = 0.0
                            cand_matches: List[float] = []

                            best_idx_wli1 = None
                            best_idx_wli2_full = None
                            best_idx_wli2_within = None
                            best_score_wli1 = float("-inf")
                            best_score_wli2_full = float("-inf")
                            best_score_wli2_within = float("-inf")

                            for i, k_list in enumerate(cand_keys):
                                k_arr = np.asarray(k_list, dtype=np.int16)
                                pt_c = cipher.decrypt_single(ciphertext=ct_idx, key=k_arr)
                                m = float(_match_ratio(pt_c.tolist(), pt_idx.tolist()))
                                cand_matches.append(m)
                                if m > bestk_match:
                                    bestk_match = m

                                s1 = float(wli1_scorer.score(pt_c, wli_list))
                                s2f = float(wli2_full_scorer.score(pt_c, wli_list))
                                s2w = float(wli2_within_scorer.score(pt_c, wli_list, word_spans=word_spans))
                                if s1 > best_score_wli1:
                                    best_score_wli1 = s1
                                    best_idx_wli1 = i
                                if s2f > best_score_wli2_full:
                                    best_score_wli2_full = s2f
                                    best_idx_wli2_full = i
                                if s2w > best_score_wli2_within:
                                    best_score_wli2_within = s2w
                                    best_idx_wli2_within = i

                            if best_idx_wli1 is not None:
                                pick_wli1_match = float(cand_matches[best_idx_wli1])
                            if best_idx_wli2_full is not None:
                                pick_wli2_full_match = float(cand_matches[best_idx_wli2_full])
                            if best_idx_wli2_within is not None:
                                pick_wli2_within_match = float(cand_matches[best_idx_wli2_within])

                        stage2_seconds = float(time.time() - stage2_t0)

                        dt = time.time() - t0
                        rows.append(
                            dict(
                                tier=tier.name,
                                budget=budget.name,
                                mode=mode,
                                period=tier.period,
                                columns=tier.columns,
                                length=tier.length,
                                text_id=int(text_id),
                                offset_hint=int(offset),
                                offset_used=int(offset_used),
                                key_seed=int(key_seed),
                                oracle_raw_full=oracle_raw_full,
                                oracle_raw_native=oracle_raw_native,
                                oracle_pct=oracle_pct,
                                oracle_wli1=oracle_wli1,
                                oracle_wli2_full=oracle_wli2_full,
                                oracle_wli2_within=oracle_wli2_within,
                                best_random_raw_full=float(np.max(random_raw_full)),
                                best_random_pct=float(np.max(random_pct)),
                                best_random_raw_native=float(np.max(random_raw_native)),
                                best_random_wli1=float(np.max(random_wli1)),
                                best_random_wli2_full=float(np.max(random_wli2_full)),
                                best_random_wli2_within=float(np.max(random_wli2_within)),
                                disc_char_oracle_pctile=float(disc_char["oracle_pctile"]),
                                disc_char_sep_z=float(disc_char["sep_z"]),
                                disc_wli1_oracle_pctile=float(disc_wli1["oracle_pctile"]),
                                disc_wli1_sep_z=float(disc_wli1["sep_z"]),
                                disc_wli2_full_oracle_pctile=float(disc_wli2_full["oracle_pctile"]),
                                disc_wli2_full_sep_z=float(disc_wli2_full["sep_z"]),
                                disc_wli2_within_oracle_pctile=float(disc_wli2_within["oracle_pctile"]),
                                disc_wli2_within_sep_z=float(disc_wli2_within["sep_z"]),
                                sol_score=float(getattr(sol, "score", float("nan"))),
                                sol_raw_full=sol_raw_full,
                                sol_raw_native=sol_raw_native,
                                sol_pct=sol_pct,
                                match_ratio=match,
                                bestk_match_ratio=bestk_match,
                                pick_wli1_match_ratio=pick_wli1_match,
                                pick_wli2_full_match_ratio=pick_wli2_full_match,
                                pick_wli2_within_match_ratio=pick_wli2_within_match,
                                evals=int(work.get("evals", 0) or 0),
                                tokens=int(work.get("tokens", 0) or 0),
                                seconds=round(dt, 3),
                                stage2_seconds=round(stage2_seconds, 3),
                                candidates=int(len(cand_keys)),
                                candidate_file=str(cand_path.relative_to(run_dir)).replace("\\", "/"),
                            )
                        )
                        completed.add(row_id)

                        done_solves += 1
                        elapsed = time.time() - t0_all
                        avg = elapsed / float(done_solves) if done_solves else 0.0
                        eta = avg * float(total_solves - done_solves)
                        _checkpoint(run_dir, rows=rows)
                        print(
                            f"[bench_solve] {done_solves}/{total_solves} "
                            f"tier={tier.name} budget={budget.name} mode={mode} "
                            f"text={text_id} key_seed={key_seed} "
                            f"run={_format_seconds(dt)} elapsed={_format_seconds(elapsed)} eta={_format_seconds(eta)}"
                            , flush=True
                        )

    summary = _checkpoint(run_dir, rows=rows)
    total = time.time() - t0_all
    print(f"[bench_solve] Completed in {total:.1f}s. Reports written to {rel}", flush=True)
    print("\n[bench_solve] Summary (p50) by tier/budget/mode")
    for tier, entries in summary.get("tiers", {}).items():
        print(f"\nTier: {tier}")
        for e in entries:
            print(
                f"  Budget={e['budget']} Mode={e['mode']} N={e['n']} "
                f"raw_full_p50={e['sol_raw_full']['p50']:.4f} "
                f"raw_native_p50={e['sol_raw_native']['p50']:.4f} "
                f"pct_p50={e['sol_pct']['p50']:.4f} "
                f"match_p50={e['match_ratio']['p50']:.3f} "
                f"bestk_match_p50={e['bestk_match_ratio']['p50']:.3f} "
                f"pick_wli2_full_p50={e['pick_wli2_full_match_ratio']['p50']:.3f} "
                f"pick_wli2_within_p50={e['pick_wli2_within_match_ratio']['p50']:.3f} "
                f"rate_pct>oracle={e['rate_sol_gt_oracle_pct']:.2f} "
                f"evals_p50={e['evals']['p50']:.0f}"
            )


if __name__ == "__main__":
    main()
