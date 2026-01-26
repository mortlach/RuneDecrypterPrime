"""
Tutorial: Periodic Columnar (hard, period=13, columns=13)

Strategy:
  1) Run periodic substitution with a unigram-only objective to seed candidates.
     If Kaeding plateaus, run Hybrid cleanup seeded by Kaeding + seed pool.
  2) Decrypt to an intermediate columnar text.
  3) Solve the columnar permutation on the intermediate text.
  4) Refine substitution with columnar fixed, then do a short columnar polish.

We use order="col_then_sub" so the periodic structure is preserved in the ciphertext.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Sequence

import numpy as np

# Ensure repo root on sys.path so "python tutorials/v1/..." works
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name, cipher_instance
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALPHABET = 29
PERIOD = 13
COLUMNS = 13
ORDER = "col_then_sub"
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345

USE_SEEDS = True
BLOCK_SEEDS = 12
SEED_KEYS = 128
SEED_SWAPS = 2

PLATEAU_PCT = 0.10
PLATEAU_MIN_DELTA = 1e-4

RUN_HYBRID = True
HYBRID_TRIGGER_PCT = None
HYBRID_SEED_KEYS = 48
HYBRID_MAX_KEYS = 256
NEIGHBOR_KEYS = 128
NEIGHBOR_CROSS_KEYS = 32
TOP_STAGE1_KEYS = 32
HYBRID_PCT_GAP_EPS = 1e-3
HYBRID_ORACLE_GUARD_FRAC = 0.7
PHASE_TOP_K = 3

SOLVER_SUB: Dict[str, int | float | str | bool] = dict(
    steps=4000,
    restarts=6,
    inner_batch=128,
    slip_every=0,
    slip_blocks=1,
    slip_policy="stall",
    stall_rounds=200,
    stall_slip_limit=2,
    slip_swaps=20,
    stall_stop_on_limit=True,
    slip_follow_steps=200,
    block_schedule="round_robin",
    use_raw_score=False,
    raw_accept_min_delta=1e-6,
    pct_plateau_min_delta=1e-4,
    delta_window=200,
    top_k=TOP_STAGE1_KEYS,
    stop_score=0.5,
    progress_pct=2,
    print_progress=True,
    seed=TUTORIAL_SEED,
)


def _preview(text: str, n: int = 120) -> str:
    return text if len(text) <= n else text[:n] + "..."


def _phase_counts(ct_idx: np.ndarray, period: int) -> list[int]:
    return [int(len(ct_idx[r::period])) for r in range(period)]


def _score_test_key(
    *,
    text: list[int],
    cipher_spec,
    key_spec,
    key: Sequence[int],
    scorer_params: dict,
    wli: Sequence[Sequence[int]],
    direction: Direction,
):
    solver = SolverSpec.beam(
        beam_width=1,
        test_key=list(key),
        verbose=False,
        print_progress=False,
        seed=TUTORIAL_SEED,
    )
    return run(
        text=text,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
    )


def _attach_col_tail(sub_keys: Sequence[Sequence[int]], col_tail: Sequence[int]) -> list[list[int]]:
    tail = [int(x) for x in col_tail]
    return [list(k) + tail for k in sub_keys]


def _objective_fields(sol) -> dict:
    meta = getattr(sol, "meta", None)
    if not isinstance(meta, dict):
        return {}
    tel = meta.get("telemetry", {})
    if not isinstance(tel, dict):
        return {}
    obj = tel.get("objective")
    if isinstance(obj, dict):
        return obj
    obj = tel.get("objective_stats")
    return obj if isinstance(obj, dict) else {}


def _solution_penalized_mean(sol) -> float | None:
    obj = _objective_fields(sol)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key.endswith("_mean_per_ngram_penalized"):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    pass
    meta = getattr(sol, "meta", None)
    if isinstance(meta, dict):
        tel = meta.get("telemetry", {})
        if isinstance(tel, dict):
            stat_penalized = tel.get("stat.mean_per_ngram_penalized")
            if stat_penalized is not None:
                try:
                    return float(stat_penalized)
                except (TypeError, ValueError):
                    pass
            kaeding = tel.get("kaeding")
            if isinstance(kaeding, dict):
                legacy = kaeding.get("best_raw")
                if legacy is not None:
                    try:
                        return float(legacy)
                    except (TypeError, ValueError):
                        pass
    return None


def _format_scores(sol) -> str:
    pct = float(getattr(sol, "score", 0.0) or 0.0)
    penalized_mean = _solution_penalized_mean(sol)
    penalized_str = f"{penalized_mean:.6f}" if penalized_mean is not None else "N/A"
    return f"pct_lm={pct:.6f} penalized_mean={penalized_str}"


def _print_scorer_params(label: str, params: dict) -> None:
    objective = params.get("objective", "N/A")
    include_char = params.get("include_char")
    use_word_breaks = params.get("use_word_breaks")
    char_weights = params.get("char_weights")
    wli_weights = params.get("wli_weights")
    encoding_dir = params.get("encoding_dir")
    print(
        f"{label} objective: {objective} | include_char={include_char} "
        f"use_word_breaks={use_word_breaks} | char_weights={char_weights} "
        f"wli_weights={wli_weights} | encoding_dir={encoding_dir}"
    )


def _print_solver_cfg(label: str, cfg: dict) -> None:
    keys = [
        "steps",
        "restarts",
        "inner_batch",
        "block_schedule",
        "use_raw_score",
        "stop_score",
        "slip_policy",
        "slip_blocks",
        "slip_swaps",
        "stall_rounds",
        "stall_slip_limit",
        "slip_follow_steps",
        "delta_window",
        "pct_plateau_min_delta",
        "raw_accept_min_delta",
        "progress_pct",
        "print_progress",
    ]
    alias = {
        "use_raw_score": "use_penalized_score",
        "raw_accept_min_delta": "penalized_min_delta",
    }
    parts = [f"{alias.get(k, k)}={cfg.get(k)}" for k in keys if k in cfg]
    print(f"{label} solver config: " + ", ".join(parts))


def _print_hybrid_cfg(label: str, cfg: dict) -> None:
    keys = [
        "use_beam",
        "beam_width",
        "rounds",
        "expand_mode",
        "sample_per_parent",
        "top_parents_factor",
        "stop_score",
        "progress_pct",
        "print_progress",
        "seed",
        "log_interval",
    ]
    parts = [f"{k}={cfg.get(k)}" for k in keys if k in cfg]
    print(f"{label} hybrid config: " + ", ".join(parts))
    ga = cfg.get("ga", {})
    if isinstance(ga, dict):
        ga_keys = [
            "pop_size",
            "generations",
            "elite_frac",
            "cx_frac",
            "mut_prob",
            "tournament_k",
            "plateau_rounds",
            "stop_score",
        ]
        ga_parts = [f"{k}={ga.get(k)}" for k in ga_keys if k in ga]
        print(f"{label} GA config: " + ", ".join(ga_parts))
    sa = cfg.get("sa", {})
    if isinstance(sa, dict):
        sa_keys = [
            "sa_iters",
            "sa_init_temp",
            "sa_min_temp",
            "sa_cooling",
            "plateau_rounds",
            "local_improve_on_accept",
            "stop_score",
        ]
        sa_parts = [f"{k}={sa.get(k)}" for k in sa_keys if k in sa]
        print(f"{label} SA config: " + ", ".join(sa_parts))


def _print_optimizer_scalar(label: str, use_raw: bool, objective: str) -> None:
    scalar = "penalized_mean" if use_raw else "pct_lm"
    print(f"{label} optimizer scalar: {scalar} (objective={objective})")


def _phase_accuracy_report(
    *,
    true_key: Sequence[int],
    test_key: Sequence[int],
    pt_idx: Sequence[int],
    period: int,
    alphabet_size: int,
    top_k: int,
) -> None:
    sub_len = int(period) * int(alphabet_size)
    if not true_key or not test_key or len(test_key) < sub_len or len(true_key) < sub_len:
        return
    true_blocks = np.asarray(true_key[:sub_len], dtype=np.int16).reshape(period, alphabet_size)
    test_blocks = np.asarray(test_key[:sub_len], dtype=np.int16).reshape(period, alphabet_size)
    pt = np.asarray(pt_idx, dtype=np.int64).reshape(-1)

    print("Stage 1 per-phase accuracy (top1=space-like, topK=top runes):")
    top1_hits = 0
    topk_hits = 0
    for r in range(period):
        phase_pt = pt[r::period]
        counts = np.bincount(phase_pt, minlength=alphabet_size)
        top = np.argsort(counts)[::-1][: max(1, int(top_k))]
        inv_true = np.empty((alphabet_size,), dtype=np.int16)
        inv_true[true_blocks[r]] = np.arange(alphabet_size, dtype=np.int16)
        top1 = int(top[0])
        c_true = int(inv_true[top1])
        top1_ok = int(test_blocks[r, c_true] == top1)
        correct = 0
        for p in top:
            p_int = int(p)
            c_p = int(inv_true[p_int])
            if int(test_blocks[r, c_p]) == p_int:
                correct += 1
        top1_hits += top1_ok
        topk_hits += correct
        print(f"  phase {r:02d}: top1_ok={top1_ok} top{len(top)}_ok={correct}/{len(top)}")

    topk_total = int(period) * max(1, int(top_k))
    topk_rate = float(topk_hits) / float(topk_total) if topk_total else 0.0
    print(f"Stage 1 top1_ok phases: {top1_hits}/{period} | top{top_k}_avg={topk_rate:.3f}")


def _apply_plateau(params: Dict[str, int | float | str | bool]) -> Dict[str, int | float | str | bool]:
    out = dict(params)
    total_steps = int(out.get("steps", 0)) * int(out.get("restarts", 0))
    if PLATEAU_PCT > 0 and total_steps > 0:
        out["plateau_rounds"] = max(1, int(total_steps * PLATEAU_PCT))
        out["plateau_min_delta"] = float(PLATEAU_MIN_DELTA)
    return out


def _stopped_on_plateau(sol) -> bool:
    reason = getattr(sol, "stop_reason", None)
    meta = getattr(sol, "meta", None)
    if not reason and isinstance(meta, dict):
        tel = meta.get("telemetry", {})
        if isinstance(tel, dict):
            run = tel.get("run", {})
            if isinstance(run, dict):
                result = run.get("result", {})
                if isinstance(result, dict):
                    reason = result.get("reason") or result.get("stop_reason")
    if not reason:
        return False
    return str(reason).startswith("no_improve_")


def _make_periodic_key(period: int, alphabet_size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    blocks = [rng.permutation(alphabet_size).astype(np.int16) for _ in range(period)]
    return np.concatenate(blocks, axis=0).astype(np.int16, copy=False)


def _make_columnar_key(columns: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.permutation(columns).astype(np.int16)


def _make_periodic_seeds(
    ct_idx: np.ndarray,
    *,
    period: int,
    direction: Direction,
    seed: int,
    n_block_seeds: int,
    total_seeds: int,
    swaps_per_block: int,
) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    block_seeds: list[list[list[int]]] = []
    for r in range(period):
        phase_idx = ct_idx[r::period]
        phase_runes = Runeglish.to_rune(phase_idx.tolist(), wli=None)
        seeds = make_seeds_from_freq(
            phase_runes,
            n_keys=n_block_seeds,
            swaps_per_key=swaps_per_block,
            seed=seed + r,
            A=ALPHABET,
            direction=direction.value,
        )
        block_seeds.append(seeds)

    def _concat(blocks: list[list[int]]) -> list[int]:
        out: list[int] = []
        for block in blocks:
            out.extend(block)
        return out

    keys: list[list[int]] = []
    base = _concat([seeds[0] for seeds in block_seeds])
    keys.append(base)
    for _ in range(max(0, total_seeds - 1)):
        pick = [_s[int(rng.integers(0, len(_s)))] for _s in block_seeds]
        keys.append(_concat(pick))
    return keys


def _merge_seed_keys(
    primary: Sequence[int] | None,
    extras: Sequence[Sequence[int]] | None,
    limit: int,
) -> list[list[int]]:
    keys: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    if primary:
        t = tuple(int(x) for x in primary)
        keys.append(list(t))
        seen.add(t)
    if extras:
        for k in extras:
            t = tuple(int(x) for x in k)
            if t in seen:
                continue
            keys.append(list(t))
            seen.add(t)
            if len(keys) >= limit:
                break
    return keys


def _neighbor_cloud(
    primary: Sequence[int] | None,
    *,
    period: int,
    alphabet_size: int,
    seed: int,
    total_keys: int,
    cross_keys: int,
) -> list[list[int]]:
    if primary is None:
        return []
    rng = np.random.default_rng(seed)
    base = np.asarray(primary, dtype=np.int16).reshape(-1)
    out: list[list[int]] = []
    per_phase_keys = max(0, int(total_keys) - int(cross_keys))
    for _ in range(per_phase_keys):
        k = base.copy()
        n_phases = int(rng.integers(1, 4))
        phases = rng.choice(period, size=min(period, n_phases), replace=False)
        for p in phases:
            swaps = int(rng.integers(1, 3))
            start = int(p) * alphabet_size
            for _ in range(swaps):
                a = int(rng.integers(0, alphabet_size))
                b = int(rng.integers(0, alphabet_size - 1))
                if b >= a:
                    b += 1
                i1 = start + a
                i2 = start + b
                k[i1], k[i2] = k[i2], k[i1]
        out.append(k.astype(np.int16, copy=False).tolist())
    for _ in range(max(0, int(cross_keys))):
        k = base.copy()
        phase = int(rng.integers(0, period))
        other = int((phase + 1) % period)
        a = int(rng.integers(0, alphabet_size))
        b = int(rng.integers(0, alphabet_size - 1))
        if b >= a:
            b += 1
        for p in (phase, other):
            start = int(p) * alphabet_size
            i1 = start + a
            i2 = start + b
            k[i1], k[i2] = k[i2], k[i1]
        out.append(k.astype(np.int16, copy=False).tolist())
    return out


def _build_hybrid_keys(
    primary: Sequence[int] | None,
    seed_keys: Sequence[Sequence[int]] | None,
    neighbor_keys: Sequence[Sequence[int]] | None,
    limit: int,
) -> list[list[int]]:
    keys: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()

    def _add(k: Sequence[int] | None) -> None:
        if not k:
            return
        t = tuple(int(x) for x in k)
        if t in seen:
            return
        keys.append(list(t))
        seen.add(t)

    _add(primary)
    if seed_keys:
        for k in seed_keys:
            _add(k)
            if len(keys) >= limit:
                return keys
    if neighbor_keys:
        for k in neighbor_keys:
            _add(k)
            if len(keys) >= limit:
                return keys
    return keys


def _extract_top_keys(sol, limit: int) -> list[list[int]]:
    meta = getattr(sol, "meta", None)
    if not isinstance(meta, dict):
        return []
    tel = meta.get("telemetry", {})
    if not isinstance(tel, dict):
        return []
    kaeding = tel.get("kaeding", {})
    if not isinstance(kaeding, dict):
        return []
    keys = kaeding.get("top_keys")
    if not isinstance(keys, list):
        return []
    out = []
    for k in keys:
        if not isinstance(k, list):
            continue
        out.append(k)
        if len(out) >= limit:
            break
    return out


def _extract_top_scores(sol) -> tuple[list[float], list[float]]:
    meta = getattr(sol, "meta", None)
    if not isinstance(meta, dict):
        return [], []
    tel = meta.get("telemetry", {})
    if not isinstance(tel, dict):
        return [], []
    kaeding = tel.get("kaeding", {})
    if not isinstance(kaeding, dict):
        return [], []
    top_raw = kaeding.get("top_raw")
    top_pct = kaeding.get("top_pct")
    if not isinstance(top_raw, list):
        top_raw = []
    if not isinstance(top_pct, list):
        top_pct = []
    return top_raw, top_pct


def _make_columnar_seeds(columns: int, seed: int, n_keys: int) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    out = [list(range(columns))]
    for _ in range(max(0, n_keys - 1)):
        out.append(rng.permutation(columns).astype(np.int16).tolist())
    return out


def _build_ciphertext(pt_idx: np.ndarray, wli: Sequence[Sequence[int]]) -> tuple[np.ndarray, str, np.ndarray]:
    sub_key = _make_periodic_key(PERIOD, ALPHABET, CIPHERTEXT_SEED + PERIOD)
    col_key = _make_columnar_key(COLUMNS, CIPHERTEXT_SEED + COLUMNS)
    key = np.concatenate([sub_key, col_key], axis=0).astype(np.int16, copy=False)

    cipher_spec = by_name.cipher(
        "periodic_columnar",
        period=PERIOD,
        columns=COLUMNS,
        order=ORDER,
        alphabet_size=ALPHABET,
    )
    cipher = cipher_instance(cipher_spec)
    ct_idx = cipher.encrypt_single(plaintext=pt_idx, key=key)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    return ct_idx, ct_runes, key


def main() -> None:
    direction = Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        long_plaintext_string,
        direction=direction.value,
    )
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)

    print("Plaintext preview:", _preview(pt_runes))

    ct_idx, ct_runes, key = _build_ciphertext(pt_idx_arr, wli)
    print("=" * 72)
    print(f"Scenario: hard (period={PERIOD}, columns={COLUMNS}, order={ORDER})")
    print("Ciphertext preview:", _preview(ct_runes))

    ct_len = int(ct_idx.size)
    phase_counts = _phase_counts(ct_idx, PERIOD)
    print(f"Ciphertext runes: {ct_len}")
    print(
        "Phase rune counts: "
        f"min={min(phase_counts)} mean={float(np.mean(phase_counts)):.1f} max={max(phase_counts)}"
    )

    scorer_params_full = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={3: 0.3, 4: 0.7},
        wli_weights={3: 0.4, 4: 0.6},
        encoding_dir=direction,
    )
    scorer_params_stage1 = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,
        char_weights={1: 1.0},
        wli_weights={},
        encoding_dir=direction,
    )
    _print_scorer_params("Full scorer", scorer_params_full)
    _print_scorer_params("Stage 1 scorer", scorer_params_stage1)

    cipher_full = by_name.cipher(
        "periodic_columnar",
        period=PERIOD,
        columns=COLUMNS,
        order=ORDER,
        alphabet_size=ALPHABET,
    )
    key_full = KeySpec.periodic_columnar(period=PERIOD, columns=COLUMNS, alphabet_size=ALPHABET)
    cipher_sub = by_name.cipher("periodic_substitution", period=PERIOD, alphabet_size=ALPHABET)
    key_sub = KeySpec.periodic_substitution(period=PERIOD, alphabet_size=ALPHABET)
    cipher_col = by_name.cipher("columnar", key_length=COLUMNS)
    key_col = KeySpec.permutation(len=COLUMNS)

    true_sub_key = key[: PERIOD * ALPHABET].tolist()
    true_col_key = key[PERIOD * ALPHABET :].tolist()
    rand_sub_key = _make_periodic_key(PERIOD, ALPHABET, CIPHERTEXT_SEED + 901).tolist()
    rand_col_key = _make_columnar_key(COLUMNS, CIPHERTEXT_SEED + 902).tolist()

    print("Oracle scores (full objective):")
    sol_true = _score_test_key(
        text=ct_idx.tolist(),
        cipher_spec=cipher_full,
        key_spec=key_full,
        key=true_sub_key + true_col_key,
        scorer_params=scorer_params_full,
        wli=wli,
        direction=direction,
    )
    print(f"  true_sub + true_col: {_format_scores(sol_true)}")
    sol_true_rand_col = _score_test_key(
        text=ct_idx.tolist(),
        cipher_spec=cipher_full,
        key_spec=key_full,
        key=true_sub_key + rand_col_key,
        scorer_params=scorer_params_full,
        wli=wli,
        direction=direction,
    )
    print(f"  true_sub + rand_col: {_format_scores(sol_true_rand_col)}")
    sol_rand_sub_true = _score_test_key(
        text=ct_idx.tolist(),
        cipher_spec=cipher_full,
        key_spec=key_full,
        key=rand_sub_key + true_col_key,
        scorer_params=scorer_params_full,
        wli=wli,
        direction=direction,
    )
    print(f"  rand_sub + true_col: {_format_scores(sol_rand_sub_true)}")

    sub_cipher = cipher_instance(cipher_sub)
    inter_true = sub_cipher.decrypt_single(ciphertext=ct_idx, key=true_sub_key)
    identity_col = list(range(COLUMNS))
    sol_stage1_only = _score_test_key(
        text=inter_true.tolist(),
        cipher_spec=cipher_col,
        key_spec=key_col,
        key=identity_col,
        scorer_params=scorer_params_full,
        wli=wli,
        direction=direction,
    )
    print(f"  stage1-only (true_sub, col scrambled): {_format_scores(sol_stage1_only)}")

    sol_stage1_oracle = _score_test_key(
        text=ct_idx.tolist(),
        cipher_spec=cipher_sub,
        key_spec=key_sub,
        key=true_sub_key,
        scorer_params=scorer_params_stage1,
        wli=wli,
        direction=direction,
    )
    stage1_oracle_pct = float(sol_stage1_oracle.score)
    print(f"Stage 1 oracle (unigram): {_format_scores(sol_stage1_oracle)}")
    print("Stage 1 note: unigram pct_lm ignores order; high pct_lm does not imply readable plaintext.")

    # --- Stage 1: periodic substitution ---
    seed_keys = None
    if USE_SEEDS:
        seed_keys = _make_periodic_seeds(
            ct_idx,
            period=PERIOD,
            direction=direction,
            seed=TUTORIAL_SEED + PERIOD,
            n_block_seeds=BLOCK_SEEDS,
            total_seeds=SEED_KEYS,
            swaps_per_block=SEED_SWAPS,
        )
        print(
            f"Seed pool: {len(seed_keys)} keys "
            f"(blocks={BLOCK_SEEDS}, total={SEED_KEYS}, swaps_per_block={SEED_SWAPS})"
        )

    solver_sub_cfg = _apply_plateau(SOLVER_SUB)
    _print_solver_cfg("Stage 1 Kaeding", solver_sub_cfg)
    _print_optimizer_scalar("Stage 1 Kaeding", bool(solver_sub_cfg.get("use_raw_score")), scorer_params_stage1["objective"])
    solver_sub = SolverSpec.kaeding(**solver_sub_cfg)

    sol_sub = run(
        text=ct_idx.tolist(),
        cipher=cipher_sub,
        key=key_sub,
        solver=solver_sub,
        scorer_params=dict(scorer_params_stage1),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        **({} if seed_keys is None else {"initial_keys": seed_keys}),
    )
    print("Stage 1 recovered preview:", _preview(str(getattr(sol_sub, "plaintext_rune", ""))))
    kaeding_top_keys = _extract_top_keys(sol_sub, TOP_STAGE1_KEYS)
    _, top_pct = _extract_top_scores(sol_sub)
    gap_pct = None
    if top_pct:
        nth_idx = min(len(top_pct) - 1, TOP_STAGE1_KEYS - 1)
        if nth_idx > 0:
            gap_pct = float(top_pct[0]) - float(top_pct[nth_idx])
            print(
                f"Stage 1 top-{nth_idx + 1} pct_lm gap: {gap_pct:.6f} "
                f"(best={float(top_pct[0]):.6f}, nth={float(top_pct[nth_idx]):.6f})"
            )
        else:
            print(f"Stage 1 top pct_lm best={float(top_pct[0]):.6f}")

    score_sub_pct = float(getattr(sol_sub, "score", 0.0) or 0.0)
    plateau_hit = _stopped_on_plateau(sol_sub)
    gap_str = f"{gap_pct:.6f}" if gap_pct is not None else "N/A"
    print(
        "Stage 1 summary: "
        f"pct_lm={score_sub_pct:.6f} plateau={plateau_hit} "
        f"gap_pct={gap_str} trigger={HYBRID_TRIGGER_PCT} "
        f"oracle_pct={stage1_oracle_pct:.6f}"
    )
    hybrid_reasons: list[str] = []
    if plateau_hit:
        hybrid_reasons.append("plateau")
    if HYBRID_TRIGGER_PCT is not None and score_sub_pct < float(HYBRID_TRIGGER_PCT):
        hybrid_reasons.append(f"pct_lm<{float(HYBRID_TRIGGER_PCT):.3f}")
    if gap_pct is not None and gap_pct < float(HYBRID_PCT_GAP_EPS):
        hybrid_reasons.append(f"low_gap<{float(HYBRID_PCT_GAP_EPS):.4f}")
    if stage1_oracle_pct and score_sub_pct < stage1_oracle_pct * float(HYBRID_ORACLE_GUARD_FRAC):
        hybrid_reasons.append("oracle_guard")

    if RUN_HYBRID and hybrid_reasons:
        print(f"Stage 1 hybrid trigger: {', '.join(hybrid_reasons)}")
        neighbors = _neighbor_cloud(
            getattr(sol_sub, "key", None),
            period=PERIOD,
            alphabet_size=ALPHABET,
            seed=TUTORIAL_SEED + 991,
            total_keys=NEIGHBOR_KEYS,
            cross_keys=NEIGHBOR_CROSS_KEYS,
        )
        hybrid_keys = _build_hybrid_keys(
            getattr(sol_sub, "key", None),
            seed_keys,
            neighbors,
            HYBRID_MAX_KEYS,
        )
        if hybrid_keys:
            print(f"Hybrid seed pool: {len(hybrid_keys)} keys")

        hybrid_cfg = dict(
            use_beam=True,
            beam_width=96,
            rounds=6,
            expand_mode="sample",
            sample_per_parent=64,
            top_parents_factor=0.4,
            progress_pct=2,
            print_progress=True,
            ga=dict(
                pop_size=160,
                generations=120,
                elite_frac=0.1,
                cx_frac=0.85,
                mut_prob=0.25,
                tournament_k=3,
                plateau_rounds=24,
                stop_score=0.5,
                print_progress=True,
            ),
            sa=dict(
                sa_iters=4000,
                sa_init_temp=0.95,
                sa_min_temp=1e-4,
                sa_cooling=0.997,
                plateau_rounds=400,
                local_improve_on_accept=True,
                stop_score=0.5,
                print_progress=True,
            ),
            seed=TUTORIAL_SEED,
            verbose=True,
            log_interval=10,
            stop_score=0.6,
        )
        _print_hybrid_cfg("Stage 1 hybrid", hybrid_cfg)
        _print_optimizer_scalar("Stage 1 hybrid", False, scorer_params_stage1["objective"])
        hybrid = SolverSpec.hybrid(**hybrid_cfg)

        sol_h = run(
            text=ct_idx.tolist(),
            cipher=cipher_sub,
            key=key_sub,
            solver=hybrid,
            scorer_params=dict(scorer_params_stage1),
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=True,
            **({} if not hybrid_keys else {"initial_keys": hybrid_keys}),
        )
        print("Stage 1 hybrid preview:", _preview(str(getattr(sol_h, "plaintext_rune", ""))))
        sub_pct = float(getattr(sol_sub, "score", 0.0) or 0.0)
        h_pct = float(getattr(sol_h, "score", 0.0) or 0.0)
        if h_pct > sub_pct:
            print(f"Stage 1 hybrid improved (pct_lm): {sub_pct:.6f} -> {h_pct:.6f}")
            sol_sub = sol_h

    # Decrypt to intermediate text (columnar ciphertext) for top Stage-1 candidates
    stage1_keys = list(kaeding_top_keys)
    final_sub_key = list(getattr(sol_sub, "key", []) or [])
    if final_sub_key:
        if final_sub_key not in stage1_keys:
            stage1_keys.append(final_sub_key)
    if not stage1_keys and final_sub_key:
        stage1_keys = [final_sub_key]
    stage1_keys = stage1_keys[:max(1, TOP_STAGE1_KEYS)]
    if len(stage1_keys) < 2 and final_sub_key:
        extra = _neighbor_cloud(
            final_sub_key,
            period=PERIOD,
            alphabet_size=ALPHABET,
            seed=TUTORIAL_SEED + 777,
            total_keys=1,
            cross_keys=0,
        )
        for k in extra:
            if k not in stage1_keys:
                stage1_keys.append(k)
    if len(stage1_keys) < 2:
        fallback = _make_periodic_key(PERIOD, ALPHABET, TUTORIAL_SEED + 778).tolist()
        if fallback not in stage1_keys:
            stage1_keys.append(fallback)

    # --- Stage 2: columnar transposition ---
    solver_col_cfg = dict(
        use_beam=True,
        beam_width=128,
        rounds=8,
        expand_mode="sample",
        sample_per_parent=64,
        top_parents_factor=0.4,
        progress_pct=2,
        print_progress=True,
        ga=dict(
            pop_size=180,
            generations=120,
            elite_frac=0.1,
            cx_frac=0.85,
            mut_prob=0.3,
            tournament_k=3,
            plateau_rounds=30,
            stop_score=0.48,
            print_progress=True,
        ),
        sa=dict(
            sa_iters=4000,
            sa_init_temp=0.95,
            sa_min_temp=1e-4,
            sa_cooling=0.997,
            plateau_rounds=400,
            local_improve_on_accept=True,
            stop_score=0.48,
            print_progress=True,
        ),
        seed=TUTORIAL_SEED,
        verbose=True,
        log_interval=10,
        stop_score=0.6,
    )
    _print_hybrid_cfg("Stage 2 columnar", solver_col_cfg)
    _print_optimizer_scalar("Stage 2 columnar", False, scorer_params_full["objective"])
    solver_col = SolverSpec.hybrid(**solver_col_cfg)

    col_seeds = _make_columnar_seeds(COLUMNS, TUTORIAL_SEED, n_keys=16)
    best_full = None
    sol_full = None
    for i, sub_key in enumerate(stage1_keys):
        print(f"Stage 2 attempt {i + 1}/{len(stage1_keys)}")
        inter_idx = sub_cipher.decrypt_single(ciphertext=ct_idx, key=sub_key)
        sol_col = run(
            text=inter_idx.tolist(),
            cipher=cipher_col,
            key=key_col,
            solver=solver_col,
            scorer_params=dict(scorer_params_full),
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=True,
            initial_keys=col_seeds,
        )
        print("Stage 2 recovered preview:", _preview(str(getattr(sol_col, "plaintext_rune", ""))))

        # Verify combined key on original ciphertext.
        col_key = list(getattr(sol_col, "key", []))
        full_key = list(sub_key) + list(col_key)
        print(f"Stage 2 verify Kaeding: test_key_len={len(full_key)}")
        _print_optimizer_scalar("Stage 2 verify Kaeding", False, scorer_params_full["objective"])
        solver_verify = SolverSpec.kaeding(
            test_key=full_key,
            verbose=False,
            print_progress=False,
            seed=TUTORIAL_SEED,
        )
        sol_full = run(
            text=ct_idx.tolist(),
            cipher=cipher_full,
            key=key_full,
            solver=solver_verify,
            scorer_params=dict(scorer_params_full),
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=False,
        )
        if best_full is None or float(sol_full.score) > float(best_full.score):
            best_full = sol_full

    if best_full is None and sol_full is not None:
        best_full = sol_full

    refined_key = None
    if best_full is not None and getattr(best_full, "key", None):
        best_key = list(getattr(best_full, "key"))
        sub_len = PERIOD * ALPHABET
        best_sub = best_key[:sub_len]
        best_col = best_key[sub_len:]

        print("Stage 3: substitution refinement (columnar fixed)")
        refine_neighbors = _neighbor_cloud(
            best_sub,
            period=PERIOD,
            alphabet_size=ALPHABET,
            seed=TUTORIAL_SEED + 778,
            total_keys=64,
            cross_keys=16,
        )
        refine_sub_keys = [best_sub] + refine_neighbors
        refine_keys = _attach_col_tail(refine_sub_keys, best_col)
        solver_sub_refine_cfg = dict(
            steps=2500,
            restarts=1,
            inner_batch=128,
            slip_every=0,
            slip_blocks=1,
            slip_policy="stall",
            stall_rounds=200,
            stall_slip_limit=2,
            slip_swaps=20,
            stall_stop_on_limit=True,
            slip_follow_steps=200,
            block_schedule="round_robin",
            use_raw_score=False,
            raw_accept_min_delta=1e-6,
            pct_plateau_min_delta=1e-4,
            delta_window=200,
            col_every=0,
            stop_score=0.5,
            progress_pct=2,
            print_progress=True,
            seed=TUTORIAL_SEED,
        )
        _print_solver_cfg("Stage 3 refine Kaeding", solver_sub_refine_cfg)
        _print_optimizer_scalar("Stage 3 refine Kaeding", False, scorer_params_full["objective"])
        solver_sub_refine = SolverSpec.kaeding(**solver_sub_refine_cfg)
        sol_refine = run(
            text=ct_idx.tolist(),
            cipher=cipher_full,
            key=key_full,
            solver=solver_sub_refine,
            scorer_params=dict(scorer_params_full),
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=True,
            initial_keys=refine_keys,
        )
        print("Stage 3 recovered preview:", _preview(str(getattr(sol_refine, "plaintext_rune", ""))))
        if best_full is None or float(sol_refine.score) > float(best_full.score):
            best_full = sol_refine
        refined_key = list(getattr(sol_refine, "key", best_key))

    if refined_key:
        print("Stage 4: columnar polish")
        sub_len = PERIOD * ALPHABET
        ref_sub = refined_key[:sub_len]
        ref_col = refined_key[sub_len:]
        inter_idx = sub_cipher.decrypt_single(ciphertext=ct_idx, key=ref_sub)
        solver_col_polish_cfg = dict(
            use_beam=True,
            beam_width=96,
            rounds=4,
            expand_mode="sample",
            sample_per_parent=48,
            top_parents_factor=0.4,
            progress_pct=2,
            print_progress=True,
            ga=dict(
                pop_size=120,
                generations=60,
                elite_frac=0.1,
                cx_frac=0.85,
                mut_prob=0.3,
                tournament_k=3,
                plateau_rounds=20,
                stop_score=0.48,
                print_progress=True,
            ),
            sa=dict(
                sa_iters=2000,
                sa_init_temp=0.95,
                sa_min_temp=1e-4,
                sa_cooling=0.997,
                plateau_rounds=200,
                local_improve_on_accept=True,
                stop_score=0.48,
                print_progress=True,
            ),
            seed=TUTORIAL_SEED,
            verbose=True,
            log_interval=10,
            stop_score=0.6,
        )
        _print_hybrid_cfg("Stage 4 columnar polish", solver_col_polish_cfg)
        _print_optimizer_scalar("Stage 4 columnar polish", False, scorer_params_full["objective"])
        solver_col_polish = SolverSpec.hybrid(**solver_col_polish_cfg)
        polish_keys = _merge_seed_keys(ref_col, col_seeds, limit=16)
        sol_col_polish = run(
            text=inter_idx.tolist(),
            cipher=cipher_col,
            key=key_col,
            solver=solver_col_polish,
            scorer_params=dict(scorer_params_full),
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=True,
            initial_keys=polish_keys,
        )
        print("Stage 4 recovered preview:", _preview(str(getattr(sol_col_polish, "plaintext_rune", ""))))
        full_polish_key = list(ref_sub) + list(getattr(sol_col_polish, "key", []))
        sol_full_polish = _score_test_key(
            text=ct_idx.tolist(),
            cipher_spec=cipher_full,
            key_spec=key_full,
            key=full_polish_key,
            scorer_params=scorer_params_full,
            wli=wli,
            direction=direction,
        )
        if best_full is None or float(sol_full_polish.score) > float(best_full.score):
            best_full = sol_full_polish

    print_run_report(
        title="periodic-columnar-hard",
        cipher="periodic_columnar",
        solution=best_full,
        match_ok=None,
        app_version="tutorial-1.0",
        key_idx=key.tolist(),
        key_len=int(key.size),
        ct_idx=ct_idx.tolist(),
        ct_rune=ct_runes,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
        wli=wli,
    )


if __name__ == "__main__":
    main()
