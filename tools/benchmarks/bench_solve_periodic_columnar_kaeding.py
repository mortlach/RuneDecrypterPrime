"""
End-to-end benchmark: seed pool -> Kaeding solver (PeriodicColumnar).

Purpose
-------
We already have a seed-quality benchmark (`bench_seed_periodic_columnar.py`) that
measures raw_fulltext (unwindowed avg logp over the whole text) and reports
PCT/ECDF transfer diagnostics.

This benchmark answers the next question:
  "Do these seeds actually improve Kaeding Stage-1 outcomes under the real engine?"

Notes
-----
* Kaeding in the engine operates on the scorer's objective (typically PCT) but can
  optimise "raw" when available via evaluate_keys_with_raw(). In the current engine,
  that "raw" is the win=10 windowed mean-per-ngram stat (diagnostic here as raw_native_win10).
* We intentionally report:
    - raw_fulltext (primary, Kaeding-original-style)
    - raw_native_win10 (engine raw)
    - pct_ecdf (engine objective)
  so we can see transfer and/or mismatch.
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
from typing import Any, Dict, Iterable, List, Tuple

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
        entry = dict(
            tier=tier,
            budget=budget,
            mode=mode,
            n=len(items),
            sol_raw_full=_percentiles([r["sol_raw_full"] for r in items]),
            sol_raw_native=_percentiles([r["sol_raw_native"] for r in items]),
            sol_pct=_percentiles([r["sol_pct"] for r in items]),
            match_ratio=_percentiles([r["match_ratio"] for r in items]),
            evals=_percentiles([float(r.get("evals", 0) or 0) for r in items]),
            seconds=_percentiles([float(r.get("seconds", 0.0) or 0.0) for r in items]),
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


def _require_assets(direction: Direction, *, ns: Tuple[int, ...]) -> Path:
    # Reuse the strict test guard; if it's not importable, fail loudly.
    from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
    root, _ = require_full_lm_assets(
        models=("char",),
        modes=(direction.value,),
        poses=("nose",),
        ns=ns,
        ecdf_stats=("logp",),
    )
    return root


def _encode_long_plaintext(direction: Direction) -> np.ndarray:
    pt_idx, _wli, _runes = Runeglish.encode_english_to_runes(long_plaintext_string.strip(), direction=direction.value)
    return np.asarray(pt_idx, dtype=np.uint8)


def _slice_pt(pt_base: np.ndarray, length: int, offset: int) -> np.ndarray:
    if pt_base.size == 0:
        raise ValueError("Encoded plaintext is empty")
    needed = offset + length
    if pt_base.size < needed:
        reps = int(np.ceil(needed / pt_base.size))
        pt_base = np.tile(pt_base, reps)
    return np.ascontiguousarray(pt_base[offset:offset + length], dtype=np.uint8)


class RawFulltextScorer:
    def __init__(self, *, model_root: Path, direction: Direction, weights: Dict[int, float]):
        self.direction = direction
        self.lm = LanguageModelPrime(
            lm_root=model_root,
            smoothing="auto_gt",
            alpha=0.5,
            oov_policy="floor_min_seen",
            include_char=True,
        )
        self.weights = {int(n): float(w) for n, w in weights.items() if int(n) > 0 and float(w) > 0.0}
        if not self.weights:
            raise ValueError("RawFulltextScorer requires at least one positive n-gram weight")

    def score(self, pt: Iterable[int]) -> float:
        seq = np.asarray(list(pt), dtype=np.uint8).reshape(-1).tolist()
        L = len(seq)
        if L <= 0:
            return float("-inf")
        total_w = float(sum(self.weights.values()))
        acc = 0.0
        for n, w in self.weights.items():
            total_eval = L - int(n) + 1
            if total_eval <= 0:
                return float("-inf")
            res = self.lm.score([seq], None, direction=self.direction.value, se="nose", n=int(n), model="char")[0]
            acc += float(w) * (float(res.logprob_sum) / float(total_eval))
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

    required_ns = tuple(sorted({*raw_weights.keys(), *pct_weights.keys()}))
    lm_root = _require_assets(direction, ns=required_ns)

    raw_full_scorer = RawFulltextScorer(model_root=lm_root, direction=direction, weights=raw_weights)
    pct_scorer = _pct_scorer(direction, model_root=lm_root, char_weights=pct_weights)

    pt_base = _encode_long_plaintext(direction)
    if pt_base.size == 0:
        raise RuntimeError("[bench_solve] encoded plaintext is empty")

    rows: List[dict] = []
    t0_all = time.time()

    # Each instance is solved in 3 modes: no seeds, raw seeds, pct-reranked seeds.
    seed_modes = ["none", "seed_raw", "seed_pct_rerank"]
    total_instances = len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS) * len(SOLVER_BUDGETS)
    total_solves = total_instances * len(seed_modes)
    done_solves = 0

    # Create output dir up-front so long runs produce partial results even if interrupted.
    run_dir = _write_reports(rows=[], summary={"tiers": {}})
    rel = run_dir.relative_to(_repo_root())
    print(f"[bench_solve] Reports will be written to {rel}", flush=True)
    print(f"[bench_solve] Starting {total_solves} solves ({total_instances} instances x {len(seed_modes)} modes)", flush=True)

    for tier in TIERS:
        for text_id, offset in enumerate(TEXT_OFFSETS):
            pt_idx = _slice_pt(pt_base, tier.length, offset)
            for key_seed in KEY_SEEDS:
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

                # Quick sanity: oracle should beat random under all three metrics.
                random_raw_full = []
                random_pct = []
                random_raw_native = []
                for _ in range(RANDOM_KEYS_SANITY):
                    k = keyops.random(rng).astype(np.int16, copy=False)
                    pt_rand = cipher.decrypt_single(ciphertext=ct_idx, key=k)
                    r_full, r_pct, r_nat = _score_pt(pt_rand, raw_full_scorer=raw_full_scorer, pct_scorer=pct_scorer)
                    random_raw_full.append(r_full)
                    random_pct.append(r_pct)
                    random_raw_native.append(r_nat)
                if not (oracle_raw_full > float(np.max(random_raw_full))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_raw_fulltext <= best_random_raw_fulltext")
                if not (oracle_pct > float(np.max(random_pct))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_pct <= best_random_pct")
                if not (oracle_raw_native > float(np.max(random_raw_native))):
                    raise RuntimeError("[bench_solve] sanity failure: oracle_raw_native <= best_random_raw_native")

                for budget in SOLVER_BUDGETS:
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
                                key_seed=int(key_seed),
                                oracle_raw_full=oracle_raw_full,
                                oracle_raw_native=oracle_raw_native,
                                oracle_pct=oracle_pct,
                                sol_score=float(getattr(sol, "score", float("nan"))),
                                sol_raw_full=sol_raw_full,
                                sol_raw_native=sol_raw_native,
                                sol_pct=sol_pct,
                                match_ratio=match,
                                evals=int(work.get("evals", 0) or 0),
                                tokens=int(work.get("tokens", 0) or 0),
                                seconds=round(dt, 3),
                            )
                        )

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
                f"evals_p50={e['evals']['p50']:.0f}"
            )


if __name__ == "__main__":
    main()
