"""
Seed generator benchmark for PeriodicColumnar (Kaeding-aligned).

Primary metric: raw average log-prob (Kaeding-style).
Secondary: PCT/ECDF transfer analysis (reported only).
Also report "native raw" (win=10 windowed mean-per-ngram) from the engine scorer.

Outputs JSON/CSV under output/tools/benchmarks/<timestamp>__bench__<git>/.
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
from typing import Dict, Iterable, List, Tuple, Any

import numpy as np

from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Direction, Device, ObjectiveFamily, ObjectiveSpec, SeMode, Stat, ScorerImpl
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils_periodic_columnar import SeedPlan, generate_seed_keys_periodic_columnar
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string

ALPHABET_SIZE = 29


@dataclass(frozen=True)
class Tier:
    name: str
    period: int
    columns: int
    length: int


@dataclass(frozen=True)
class Budget:
    name: str
    plan: SeedPlan
    n_keys: int


TIERS: List[Tier] = [
    Tier(name="easy", period=5, columns=7, length=500),
    Tier(name="medium", period=7, columns=11, length=800),
    Tier(name="hard", period=9, columns=13, length=1200),
    # Goalward tiers (aspiration: P=13, C=13, L≈300) — ratchet in stages.
    Tier(name="goal_p11_c13_l600", period=11, columns=13, length=600),
    Tier(name="goal_p13_c13_l450", period=13, columns=13, length=450),
    Tier(name="goal_p13_c13_l300", period=13, columns=13, length=300),
]

RAW_SPECS: List[Tuple[str, Dict[int, float]]] = [
    # Primary objective: unwindowed avg logp across the full text.
    ("char34", {3: 0.5, 4: 0.5}),
    # Optional variants (enable if you want to test n=2/n=1 stability on short texts):
    # ("char234", {2: 0.2, 3: 0.4, 4: 0.4}),
    # ("char1234", {1: 0.1, 2: 0.2, 3: 0.35, 4: 0.35}),
]

PCT_CHAR_WEIGHTS: Dict[int, float] = {3: 0.5, 4: 0.5}

BUDGETS: List[Budget] = [
    Budget(name="small", plan=SeedPlan(n_block_seeds=6, n_tail_seeds=6, n_starts=24, refine_steps=200), n_keys=24),
    Budget(name="medium", plan=SeedPlan(n_block_seeds=8, n_tail_seeds=8, n_starts=64, refine_steps=800), n_keys=64),
    Budget(name="large", plan=SeedPlan(n_block_seeds=10, n_tail_seeds=12, n_starts=128, refine_steps=2000), n_keys=128),
]

KEY_SEEDS = [111, 222, 333, 444, 555]
TEXT_OFFSETS = [0, 211, 433]
RANDOM_KEYS = 80
ORDER_MAIN = ["col_then_sub"]
RUN_SUB_THEN_COL_DIAGNOSTIC = False
SANITY_EPS = 1e-9
ABLATION_KEYS = 80  # used for "fixed blocks + random tails" and "fixed tail + random blocks"


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
    run_dir = out_root / f"{stamp}__bench__{_git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "instances.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_csv(run_dir / "instances.csv", rows)
    return run_dir


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
    try:
        from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
        root, _ = require_full_lm_assets(
            models=("char",),
            modes=(direction.value,),
            poses=("nose",),
            ns=ns,
            ecdf_stats=("logp",),
        )
        return root
    except Exception as exc:
        raise RuntimeError(f"LM assets missing or incomplete: {exc}") from exc


def _encode_long_plaintext(direction: Direction) -> np.ndarray:
    rg = Runeglish()
    pt_idx, _wli, _runes = rg.encode_english_to_runes(long_plaintext_string.strip(), direction=direction.value)
    return np.asarray(pt_idx, dtype=np.uint8)


def _slice_pt(pt_base: np.ndarray, length: int, offset: int) -> np.ndarray:
    if pt_base.size == 0:
        raise ValueError("Encoded plaintext is empty")
    needed = offset + length
    if pt_base.size < needed:
        reps = int(np.ceil(needed / pt_base.size))
        pt_base = np.tile(pt_base, reps)
    return np.ascontiguousarray(pt_base[offset:offset + length], dtype=np.uint8)


def _pct_scorer(direction: Direction, *, model_root: Path) -> Any:
    cfg = ScoringConfig(
        model_root=model_root,
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        se_mode=SeMode.NOSE,
        encoding_dir=direction,
        include_char=True,
        use_word_breaks=False,
        char_weights=dict(PCT_CHAR_WEIGHTS),
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
        order="col_then_sub",
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    return build_scorer(dummy_cipher_cfg, cfg)


class RawCharScorer:
    def __init__(self, *, model_root: Path, direction: Direction, weights: Dict[int, float] | None = None):
        self.direction = direction
        self.lm = LanguageModelPrime(
            lm_root=model_root,
            smoothing="auto_gt",
            alpha=0.5,
            oov_policy="floor_min_seen",
            include_char=True,
        )
        w = weights or {3: 0.5, 4: 0.5}
        self.weights = {int(n): float(wt) for n, wt in w.items() if int(n) > 0 and float(wt) > 0.0}
        if not self.weights:
            raise ValueError("RawCharScorer requires at least one positive n-gram weight")

    def score(self, pt: np.ndarray) -> float:
        pt = np.asarray(pt, dtype=np.uint8).reshape(-1)
        if pt.size == 0:
            return float("-inf")
        total_w = float(sum(self.weights.values()))
        acc = 0.0
        L = int(pt.size)
        for n, w in self.weights.items():
            n = int(n)
            total_eval = L - n + 1
            if total_eval <= 0:
                return float("-inf")
            res = self.lm.score([pt.tolist()], None, direction=self.direction.value, se="nose", n=n, model="char")[0]
            avg = float(res.logprob_sum) / float(total_eval)
            acc += float(w) * avg
        return acc / total_w


def _score_key(
    key: np.ndarray,
    *,
    ct_idx: np.ndarray,
    cipher: PeriodicColumnarCipher,
    raw_scorer: RawCharScorer,
    pct_scorer: Any,
) -> Tuple[float, float, float]:
    pt = cipher.decrypt_single(ciphertext=ct_idx, key=key)
    raw = float(raw_scorer.score(pt))
    pct, raw_native = pct_scorer.score_with_raw(pt, None)
    return raw, float(pct), float(raw_native)


def _assert_finite(name: str, value: float) -> None:
    if not np.isfinite(float(value)):
        raise RuntimeError(f"[bench] non-finite {name}: {value!r}")


def _hard_abort_sanity(
    *,
    tier: Tier,
    order: str,
    text_id: int,
    key_seed: int,
    oracle_raw_full: float,
    oracle_pct: float,
    oracle_raw_native: float,
    best_random_raw_full: float,
    best_random_pct: float,
    best_random_raw_native: float,
    label: str,
) -> None:
    """
    Abort early if the benchmark is clearly wired wrong.

    We intentionally keep this strict: for Runeglish plaintext, the true plaintext
    should be substantially more likely under the LM than random decrypts.
    """
    # Finite checks
    for nm, v in (
        ("oracle_raw_fulltext", oracle_raw_full),
        ("oracle_pct_ecdf", oracle_pct),
        ("oracle_raw_native_win10", oracle_raw_native),
        ("best_random_raw_fulltext", best_random_raw_full),
        ("best_random_pct_ecdf", best_random_pct),
        ("best_random_raw_native_win10", best_random_raw_native),
    ):
        _assert_finite(nm, float(v))

    ctx = f"tier={tier.name} P={tier.period} C={tier.columns} L={tier.length} order={order} text={text_id} key_seed={key_seed} label={label}"

    if not (oracle_raw_full > (best_random_raw_full + SANITY_EPS)):
        raise RuntimeError(
            "[bench] sanity failure: oracle_raw_fulltext <= best_random_raw_fulltext. "
            f"{ctx} oracle={oracle_raw_full:.6f} best_random={best_random_raw_full:.6f}"
        )
    if not (oracle_raw_native > (best_random_raw_native + SANITY_EPS)):
        raise RuntimeError(
            "[bench] sanity failure: oracle_raw_native_win10 <= best_random_raw_native_win10. "
            f"{ctx} oracle={oracle_raw_native:.6f} best_random={best_random_raw_native:.6f}"
        )
    if not (oracle_pct > (best_random_pct + SANITY_EPS)):
        raise RuntimeError(
            "[bench] sanity failure: oracle_pct_ecdf <= best_random_pct_ecdf. "
            f"{ctx} oracle={oracle_pct:.6f} best_random={best_random_pct:.6f}"
        )


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


def _tail_hamming_median(keys: List[np.ndarray], *, columns: int, best_key: np.ndarray) -> float:
    if not keys or columns <= 0:
        return 0.0
    tails = [k[-columns:] for k in keys]
    best_tail = best_key[-columns:]
    dists = [float(np.sum(t != best_tail)) for t in tails]
    return float(np.median(dists)) if dists else 0.0


def _tail_hamming_to_oracle(key: np.ndarray, *, oracle_key: np.ndarray, columns: int) -> int:
    if columns <= 0:
        return 0
    t = np.asarray(key[-columns:], dtype=np.int16)
    o = np.asarray(oracle_key[-columns:], dtype=np.int16)
    return int(np.sum(t != o))


def _tail_hamming_min_to_oracle(keys: List[np.ndarray], *, oracle_key: np.ndarray, columns: int) -> int:
    if not keys or columns <= 0:
        return 0
    oracle_tail = np.asarray(oracle_key[-columns:], dtype=np.int16)
    best = columns
    for k in keys:
        t = np.asarray(k[-columns:], dtype=np.int16)
        best = min(best, int(np.sum(t != oracle_tail)))
        if best == 0:
            break
    return int(best)


def _best_score_fixed_blocks_random_tails(
    *,
    blocks: np.ndarray,
    tails: List[np.ndarray],
    ct_idx: np.ndarray,
    cipher: PeriodicColumnarCipher,
    raw_scorer: RawCharScorer,
) -> float:
    if not tails:
        key = np.concatenate([np.asarray(blocks, dtype=np.int16).reshape(-1), np.zeros(1, dtype=np.int16)]).astype(np.int16)
        pt = cipher.decrypt_single(ciphertext=ct_idx, key=key)
        return float(raw_scorer.score(pt))

    best = float("-inf")
    b = np.asarray(blocks, dtype=np.int16).reshape(-1)
    for tail in tails:
        tail = np.asarray(tail, dtype=np.int16).reshape(-1)
        key = np.concatenate([b, tail]).astype(np.int16, copy=False)
        pt = cipher.decrypt_single(ciphertext=ct_idx, key=key)
        s = float(raw_scorer.score(pt))
        if s > best:
            best = s
    return best


def _best_score_fixed_tail_random_blocks(
    *,
    tail: np.ndarray,
    heads: List[np.ndarray],
    ct_idx: np.ndarray,
    cipher: PeriodicColumnarCipher,
    raw_scorer: RawCharScorer,
) -> float:
    t = np.asarray(tail, dtype=np.int16).reshape(-1)
    best = float("-inf")
    for head in heads:
        head = np.asarray(head, dtype=np.int16).reshape(-1)
        key = np.concatenate([head, t]).astype(np.int16, copy=False)
        pt = cipher.decrypt_single(ciphertext=ct_idx, key=key)
        s = float(raw_scorer.score(pt))
        if s > best:
            best = s
    return best


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
    required_ns = sorted({*PCT_CHAR_WEIGHTS.keys(), *[n for _, w in RAW_SPECS for n in w.keys()]})
    lm_root = _require_assets(direction, ns=tuple(int(n) for n in required_ns))
    pct_scorer = _pct_scorer(direction, model_root=lm_root)

    pt_base = _encode_long_plaintext(direction)
    if pt_base.ndim != 1:
        raise RuntimeError(f"[bench] plaintext must be 1D rune indices; got shape={tuple(pt_base.shape)}")
    if pt_base.size == 0:
        raise RuntimeError("[bench] encoded plaintext is empty")
    if int(pt_base.min()) < 0 or int(pt_base.max()) >= ALPHABET_SIZE:
        raise RuntimeError("[bench] plaintext contains out-of-range rune indices")
    if float(np.std(pt_base.astype(np.float64))) <= 0.0:
        raise RuntimeError("[bench] plaintext has zero variance (unexpected)")
    orders = list(ORDER_MAIN)
    if RUN_SUB_THEN_COL_DIAGNOSTIC:
        orders.append("sub_then_col")

    rows: List[dict] = []
    t0_all = time.time()
    total_runs = len(orders) * len(RAW_SPECS) * len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS) * len(BUDGETS)
    run_idx = 0
    print(
        f"[bench] Starting {total_runs} runs "
        f"(orders={len(orders)} raw_specs={len(RAW_SPECS)} tiers={len(TIERS)} texts={len(TEXT_OFFSETS)} seeds={len(KEY_SEEDS)} budgets={len(BUDGETS)})"
    )
    print(f"[bench] Random baseline keys: {RANDOM_KEYS} | Ablation keys: {ABLATION_KEYS}")
    for b in BUDGETS:
        est = int(int(b.plan.n_starts) * (int(b.plan.refine_steps) + 1))
        print(f"[bench] Budget {b.name}: n_keys={b.n_keys} n_starts={b.plan.n_starts} refine_steps={b.plan.refine_steps} est_seed_evals~{est}")

    for order in orders:
        for raw_name, raw_weights in RAW_SPECS:
            raw_scorer = RawCharScorer(model_root=lm_root, direction=direction, weights=raw_weights)
            for tier in TIERS:
                for text_id, offset in enumerate(TEXT_OFFSETS):
                    pt_idx = _slice_pt(pt_base, tier.length, offset)
                    for key_seed in KEY_SEEDS:
                        key_len = tier.period * ALPHABET_SIZE + tier.columns
                        rng = np.random.default_rng(int(key_seed))
                        keyops = PeriodicStructuredMatrixKeyOps(
                            K=key_len, period=tier.period, A=ALPHABET_SIZE, columns=tier.columns
                        )
                        key_true = keyops.random(rng)
                        cipher_cfg = CipherConfig(
                            name="periodic_columnar",
                            ciphertext=[],
                            period=tier.period,
                            columns=tier.columns,
                            alphabet_size=ALPHABET_SIZE,
                            order=order,
                            encoding_dir=direction,
                            key_length=key_len,
                            wli_data=[],
                            device=Device.CPU,
                        )
                        cipher = PeriodicColumnarCipher(cipher_cfg)
                        ct_idx = cipher.encrypt_single(plaintext=pt_idx, key=key_true)

                        if ct_idx.size == 0:
                            raise RuntimeError("[bench] ciphertext is empty")
                        if int(np.min(ct_idx)) < 0 or int(np.max(ct_idx)) >= ALPHABET_SIZE:
                            raise RuntimeError("[bench] ciphertext contains out-of-range rune indices")

                        oracle_raw_full, oracle_pct, oracle_raw_native = _score_key(
                            key_true,
                            ct_idx=ct_idx,
                            cipher=cipher,
                            raw_scorer=raw_scorer,
                            pct_scorer=pct_scorer,
                        )
                        print(
                            f"[bench]   oracle scores: raw_full={oracle_raw_full:.4f} raw_native={oracle_raw_native:.4f} pct={oracle_pct:.4f}"
                        )

                        # Random baseline
                        random_scores_raw_full: List[float] = []
                        random_scores_raw_native: List[float] = []
                        random_scores_pct: List[float] = []
                        for i in range(RANDOM_KEYS):
                            k = keyops.random(rng)
                            raw_full, pct, raw_native = _score_key(
                                k, ct_idx=ct_idx, cipher=cipher, raw_scorer=raw_scorer, pct_scorer=pct_scorer
                            )
                            random_scores_raw_full.append(raw_full)
                            random_scores_raw_native.append(raw_native)
                            random_scores_pct.append(pct)
                        best_random_raw_full = float(np.max(random_scores_raw_full))
                        best_random_raw_native = float(np.max(random_scores_raw_native))
                        best_random_pct = float(np.max(random_scores_pct))

                        if float(np.std(np.asarray(random_scores_raw_full, dtype=np.float64))) <= 1e-9:
                            raise RuntimeError("[bench] sanity failure: random raw_fulltext collapsed to ~constant")
                        if float(np.std(np.asarray(random_scores_pct, dtype=np.float64))) <= 1e-12:
                            raise RuntimeError("[bench] sanity failure: random pct collapsed to ~constant")
                        if float(np.std(np.asarray(random_scores_raw_native, dtype=np.float64))) <= 1e-9:
                            raise RuntimeError("[bench] sanity failure: random raw_native_win10 collapsed to ~constant")

                        _hard_abort_sanity(
                            tier=tier,
                            order=order,
                            text_id=text_id,
                            key_seed=int(key_seed),
                            oracle_raw_full=oracle_raw_full,
                            oracle_pct=oracle_pct,
                            oracle_raw_native=oracle_raw_native,
                            best_random_raw_full=best_random_raw_full,
                            best_random_pct=best_random_pct,
                            best_random_raw_native=best_random_raw_native,
                            label="baseline_random",
                        )
                        print(
                            f"[bench]   baseline random done: best_raw_full={best_random_raw_full:.4f} best_raw_native={best_random_raw_native:.4f} best_pct={best_random_pct:.4f}"
                        )

                        for budget in BUDGETS:
                            t0 = time.time()
                            print(
                                f"[bench] starting run {run_idx + 1}/{total_runs} "
                                f"tier={tier.name} order={order} raw={raw_name} budget={budget.name} "
                                f"text={text_id} key_seed={key_seed}"
                            )
                            seed_cfg = ScoringConfig(
                                model_root=lm_root,
                                encoding_dir=direction,
                                include_char=True,
                                use_word_breaks=False,
                                char_weights=dict(raw_weights),
                                wli_weights={},
                                impl=ScorerImpl.NUMPY,
                            )
                            print("[bench]   generating seed pool...")
                            t_seed = time.time()
                            seed_keys = generate_seed_keys_periodic_columnar(
                                ct_idx,
                                period=tier.period,
                                columns=tier.columns,
                                order=order,
                                direction=direction,
                                seed=2026 + int(key_seed),
                                scoring_cfg=seed_cfg,
                                n_keys=budget.n_keys,
                                plan=budget.plan,
                                refine=True,
                            )
                            print(f"[bench]   seed pool generated: {len(seed_keys)} keys in {_format_seconds(time.time() - t_seed)}")
                            seed_keys_arr = [np.asarray(k, dtype=np.int16) for k in seed_keys]
                            print("[bench]   scoring seed pool...")
                            seed_raw_fulls: List[float] = []
                            seed_raw_natives: List[float] = []
                            seed_pcts: List[float] = []
                            for k in seed_keys_arr:
                                raw_full, pct, raw_native = _score_key(
                                    k, ct_idx=ct_idx, cipher=cipher, raw_scorer=raw_scorer, pct_scorer=pct_scorer
                                )
                                seed_raw_fulls.append(raw_full)
                                seed_raw_natives.append(raw_native)
                                seed_pcts.append(pct)
                            best_seed_raw_full = float(np.max(seed_raw_fulls))
                            best_seed_raw_native = float(np.max(seed_raw_natives))
                            best_seed_pct = float(np.max(seed_pcts))
                            unique_keys = len({k.tobytes() for k in seed_keys_arr})
                            unique_tails = len({k[-tier.columns:].tobytes() for k in seed_keys_arr}) if tier.columns > 0 else 1
                            best_idx = int(np.argmax(seed_raw_fulls))
                            best_seed_key = seed_keys_arr[best_idx]
                            tail_hamming_p50 = _tail_hamming_median(seed_keys_arr, columns=tier.columns, best_key=seed_keys_arr[best_idx])
                            tail_hd_best = _tail_hamming_to_oracle(best_seed_key, oracle_key=key_true, columns=tier.columns)
                            tail_hd_min = _tail_hamming_min_to_oracle(seed_keys_arr, oracle_key=key_true, columns=tier.columns)

                            # Phase-2 ablations (diagnostics): explicitly define "good blocks/tail"
                            # as the blocks/tail taken from the best-seed-by-raw_fulltext key.
                            # This answers "is the tail dominating hardness, or the blocks?"
                            sub_len = tier.period * ALPHABET_SIZE
                            good_blocks = best_seed_key[:sub_len]
                            good_tail = best_seed_key[sub_len:]
                            oracle_blocks = key_true[:sub_len]
                            oracle_tail = key_true[sub_len:]

                            seed_ab = (
                                123_000_000
                                + 1_000_000 * int(TIERS.index(tier))
                                + 10_000 * int(text_id)
                                + 100 * int(BUDGETS.index(budget))
                                + int(key_seed)
                            )
                            rng_tail = np.random.default_rng(int(seed_ab + 1))
                            rng_blocks = np.random.default_rng(int(seed_ab + 2))

                            tails = (
                                [rng_tail.permutation(tier.columns).astype(np.int16, copy=False) for _ in range(int(ABLATION_KEYS))]
                                if tier.columns >= 2
                                else []
                            )
                            heads = [
                                np.concatenate(
                                    [rng_blocks.permutation(ALPHABET_SIZE).astype(np.int16, copy=False) for _ in range(int(tier.period))]
                                ).astype(np.int16, copy=False)
                                for _ in range(int(ABLATION_KEYS))
                            ]

                            best_raw_good_blocks_rand_tail = _best_score_fixed_blocks_random_tails(
                                blocks=good_blocks,
                                tails=tails,
                                ct_idx=ct_idx,
                                cipher=cipher,
                                raw_scorer=raw_scorer,
                            )
                            best_raw_good_tail_rand_blocks = _best_score_fixed_tail_random_blocks(
                                tail=good_tail,
                                heads=heads,
                                ct_idx=ct_idx,
                                cipher=cipher,
                                raw_scorer=raw_scorer,
                            )
                            best_raw_oracle_blocks_rand_tail = _best_score_fixed_blocks_random_tails(
                                blocks=oracle_blocks,
                                tails=tails,
                                ct_idx=ct_idx,
                                cipher=cipher,
                                raw_scorer=raw_scorer,
                            )
                            best_raw_oracle_tail_rand_blocks = _best_score_fixed_tail_random_blocks(
                                tail=oracle_tail,
                                heads=heads,
                                ct_idx=ct_idx,
                                cipher=cipher,
                                raw_scorer=raw_scorer,
                            )
                            dt = time.time() - t0

                            _hard_abort_sanity(
                                tier=tier,
                                order=order,
                                text_id=text_id,
                                key_seed=int(key_seed),
                                oracle_raw_full=oracle_raw_full,
                                oracle_pct=oracle_pct,
                                oracle_raw_native=oracle_raw_native,
                                best_random_raw_full=best_random_raw_full,
                                best_random_pct=best_random_pct,
                                best_random_raw_native=best_random_raw_native,
                                label=f"post_seed budget={budget.name}",
                            )

                            rows.append(
                                dict(
                                    tier=tier.name,
                                    order=order,
                                    raw_spec=raw_name,
                                    budget=budget.name,
                                    period=tier.period,
                                    columns=tier.columns,
                                    length=tier.length,
                                    text_id=text_id,
                                    key_seed=int(key_seed),
                                    best_random_raw_full=best_random_raw_full,
                                    best_seed_raw_full=best_seed_raw_full,
                                    oracle_raw_full=oracle_raw_full,
                                    best_random_raw_native=best_random_raw_native,
                                    best_seed_raw_native=best_seed_raw_native,
                                    oracle_raw_native=oracle_raw_native,
                                    best_random_pct=best_random_pct,
                                    best_seed_pct=best_seed_pct,
                                    oracle_pct=oracle_pct,
                                    unique_keys=unique_keys,
                                    unique_tails=unique_tails,
                                    tail_hamming_p50=round(tail_hamming_p50, 3),
                                    tail_hd_best=int(tail_hd_best),
                                    tail_hd_min=int(tail_hd_min),
                                    best_raw_good_blocks_rand_tail=float(best_raw_good_blocks_rand_tail),
                                    best_raw_good_tail_rand_blocks=float(best_raw_good_tail_rand_blocks),
                                    best_raw_oracle_blocks_rand_tail=float(best_raw_oracle_blocks_rand_tail),
                                    best_raw_oracle_tail_rand_blocks=float(best_raw_oracle_tail_rand_blocks),
                                    evals_ablations=int(ABLATION_KEYS),
                                    evals_random=int(RANDOM_KEYS),
                                    evals_seed_out=int(len(seed_keys_arr)),
                                    evals_seed_refine_est=int(int(budget.plan.n_starts) * (int(budget.plan.refine_steps) + 1)),
                                    seconds=round(dt, 3),
                                )
                            )
                            run_idx += 1
                            elapsed = time.time() - t0_all
                            avg = elapsed / float(run_idx) if run_idx else 0.0
                            eta = avg * float(total_runs - run_idx)
                            print(
                                f"[bench] {run_idx}/{total_runs} "
                                f"tier={tier.name} order={order} raw={raw_name} budget={budget.name} "
                                f"text={text_id} key_seed={key_seed} "
                                f"run={_format_seconds(dt)} elapsed={_format_seconds(elapsed)} "
                                f"eta={_format_seconds(eta)}"
                            )

    summary = _summarize(rows)
    run_dir = _write_reports(rows, summary)
    rel = run_dir.relative_to(_repo_root())
    total = time.time() - t0_all
    print(f"[bench] Completed in {total:.1f}s. Reports written to {rel}")
    _print_summary(summary)


def _summarize(rows: List[dict]) -> dict:
    summary: dict = {"tiers": {}}
    groups: Dict[Tuple[str, str, str, str], List[dict]] = {}
    for row in rows:
        key = (row["tier"], row["order"], row.get("raw_spec", "char34"), row["budget"])
        groups.setdefault(key, []).append(row)

    for (tier, order, raw_spec, budget), items in groups.items():
        best_random_raw_full = [r["best_random_raw_full"] for r in items]
        best_seed_raw_full = [r["best_seed_raw_full"] for r in items]
        oracle_raw_full = [r["oracle_raw_full"] for r in items]

        best_random_raw_native = [r["best_random_raw_native"] for r in items]
        best_seed_raw_native = [r["best_seed_raw_native"] for r in items]
        oracle_raw_native = [r["oracle_raw_native"] for r in items]

        best_random_pct = [r["best_random_pct"] for r in items]
        best_seed_pct = [r["best_seed_pct"] for r in items]
        oracle_pct = [r["oracle_pct"] for r in items]

        tail_hd_best = [r.get("tail_hd_best", 0) for r in items]
        tail_hd_min = [r.get("tail_hd_min", 0) for r in items]

        best_raw_good_blocks_rand_tail = [r.get("best_raw_good_blocks_rand_tail", float("nan")) for r in items]
        best_raw_good_tail_rand_blocks = [r.get("best_raw_good_tail_rand_blocks", float("nan")) for r in items]

        def _gap_frac(br: float, bs: float, o: float) -> float:
            denom = float(o - br)
            if denom <= 0.0:
                return float("nan")
            return float((bs - br) / denom)

        gap_frac_raw_full = [_gap_frac(r["best_random_raw_full"], r["best_seed_raw_full"], r["oracle_raw_full"]) for r in items]
        gap_frac_raw_native = [_gap_frac(r["best_random_raw_native"], r["best_seed_raw_native"], r["oracle_raw_native"]) for r in items]
        gap_frac_pct = [_gap_frac(r["best_random_pct"], r["best_seed_pct"], r["oracle_pct"]) for r in items]

        success_rate = float(np.mean([r["best_seed_raw_full"] > r["best_random_raw_full"] for r in items])) if items else 0.0
        entry = {
            "tier": tier,
            "order": order,
            "raw_spec": raw_spec,
            "budget": budget,
            "n": len(items),
            "success_rate_raw": success_rate,
            "best_random_raw_full": _percentiles(best_random_raw_full),
            "best_seed_raw_full": _percentiles(best_seed_raw_full),
            "oracle_raw_full": _percentiles(oracle_raw_full),
            "gap_frac_raw_full": _percentiles(gap_frac_raw_full),

            "best_random_raw_native": _percentiles(best_random_raw_native),
            "best_seed_raw_native": _percentiles(best_seed_raw_native),
            "oracle_raw_native": _percentiles(oracle_raw_native),
            "gap_frac_raw_native": _percentiles(gap_frac_raw_native),

            "best_random_pct": _percentiles(best_random_pct),
            "best_seed_pct": _percentiles(best_seed_pct),
            "oracle_pct": _percentiles(oracle_pct),
            "gap_frac_pct": _percentiles(gap_frac_pct),

            "tail_hd_best": _percentiles(tail_hd_best),
            "tail_hd_min": _percentiles(tail_hd_min),
            "best_raw_good_blocks_rand_tail": _percentiles(best_raw_good_blocks_rand_tail),
            "best_raw_good_tail_rand_blocks": _percentiles(best_raw_good_tail_rand_blocks),
        }
        summary["tiers"].setdefault(tier, []).append(entry)
    return summary


def _print_summary(summary: dict) -> None:
    print("\n[bench] Raw(fulltext) score percentiles by tier (primary)")
    for tier, entries in summary.get("tiers", {}).items():
        print(f"\nTier: {tier}")
        for entry in entries:
            print(f"  Order={entry['order']} Raw={entry.get('raw_spec','?')} Budget={entry['budget']} N={entry['n']} SuccessRate={entry['success_rate_raw']:.2f}")
            for label in ("best_random_raw_full", "best_seed_raw_full", "oracle_raw_full", "gap_frac_raw_full"):
                stats = entry[label]
                line = (
                    f"    {label}: "
                    f"p10={stats['p10']:.4f} p25={stats['p25']:.4f} p50={stats['p50']:.4f} "
                    f"p75={stats['p75']:.4f} p90={stats['p90']:.4f} p95={stats['p95']:.4f}"
                )
                print(line)

    print("\n[bench] Transfer diagnostics (native raw win10, pct/ecdf)")
    for tier, entries in summary.get("tiers", {}).items():
        print(f"\nTier: {tier}")
        for entry in entries:
            print(f"  Order={entry['order']} Raw={entry.get('raw_spec','?')} Budget={entry['budget']} N={entry['n']}")
            for label in ("gap_frac_raw_native", "gap_frac_pct"):
                stats = entry[label]
                line = (
                    f"    {label}: "
                    f"p10={stats['p10']:.4f} p25={stats['p25']:.4f} p50={stats['p50']:.4f} "
                    f"p75={stats['p75']:.4f} p90={stats['p90']:.4f} p95={stats['p95']:.4f}"
                )
                print(line)

    print("\n[bench] Tail + Ablation Diagnostics (raw_fulltext)")
    for tier, entries in summary.get("tiers", {}).items():
        print(f"\nTier: {tier}")
        for entry in entries:
            print(f"  Order={entry['order']} Raw={entry.get('raw_spec','?')} Budget={entry['budget']} N={entry['n']}")
            hd_best = entry.get("tail_hd_best")
            hd_min = entry.get("tail_hd_min")
            if hd_best and hd_min:
                print(
                    "    tail_hd_best(p50/p90)="
                    f"{hd_best['p50']:.2f}/{hd_best['p90']:.2f}  "
                    "tail_hd_min(p50/p90)="
                    f"{hd_min['p50']:.2f}/{hd_min['p90']:.2f}"
                )
            ab_b = entry.get("best_raw_good_blocks_rand_tail")
            ab_t = entry.get("best_raw_good_tail_rand_blocks")
            if ab_b and ab_t:
                print(
                    "    ablation_best_raw (good_blocks+rand_tail) p50="
                    f"{ab_b['p50']:.4f}  "
                    "ablation_best_raw (good_tail+rand_blocks) p50="
                    f"{ab_t['p50']:.4f}"
                )


if __name__ == "__main__":
    main()
