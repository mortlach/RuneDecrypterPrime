"""
Tutorial: Periodic Substitution (hard, period=13)

- Uses the full plaintext sample from data.
- Period 13 means 13 mixed alphabets (one per phase).
- Heavy Kaeding budget + per-phase frequency seeds + hybrid cleanup.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Sequence, Tuple

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

SOLVER_CFG: Dict[str, int | float | str | bool] = dict(
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


def _solution_raw(sol) -> float | None:
    meta = getattr(sol, "meta", None)
    raw = None
    if isinstance(meta, dict):
        tel = meta.get("telemetry", {})
        if isinstance(tel, dict):
            obj = tel.get("objective")
            if isinstance(obj, dict):
                raw = obj.get("raw")
            if raw is None:
                kaeding = tel.get("kaeding")
                if isinstance(kaeding, dict):
                    raw = kaeding.get("best_raw")
    if raw is None:
        return None
    try:
        raw_f = float(raw)
    except (TypeError, ValueError):
        return None
    score = getattr(sol, "score", None)
    if score is not None:
        try:
            if abs(raw_f - float(score)) < 1e-12:
                return None
        except (TypeError, ValueError):
            pass
    return raw_f


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


def _build_ciphertext(
    pt_idx: np.ndarray,
    wli: list[list[int]],
    *,
    period: int,
    alphabet_size: int,
    seed: int,
) -> Tuple[np.ndarray, str, np.ndarray]:
    key = _make_periodic_key(period, alphabet_size, seed)
    cipher_spec = by_name.cipher(
        "periodic_substitution",
        period=period,
        alphabet_size=alphabet_size,
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

    ct_idx, ct_runes, key = _build_ciphertext(
        pt_idx_arr,
        wli,
        period=PERIOD,
        alphabet_size=ALPHABET,
        seed=CIPHERTEXT_SEED + PERIOD,
    )

    print("=" * 72)
    print(f"Scenario: hard (period={PERIOD})")
    print("Ciphertext preview:", _preview(ct_runes))

    ct_len = int(ct_idx.size)
    phase_counts = _phase_counts(ct_idx, PERIOD)
    print(f"Ciphertext runes: {ct_len}")
    print(
        "Phase rune counts: "
        f"min={min(phase_counts)} mean={float(np.mean(phase_counts)):.1f} max={max(phase_counts)}"
    )

    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={3: 0.3, 4: 0.7},
        wli_weights={3: 0.4, 4: 0.6},
        encoding_dir=direction,
    )

    cipher_spec = by_name.cipher(
        "periodic_substitution",
        period=PERIOD,
        alphabet_size=ALPHABET,
    )
    key_spec = KeySpec.periodic_substitution(period=PERIOD, alphabet_size=ALPHABET)

    true_key = key.tolist()
    rand_key = _make_periodic_key(PERIOD, ALPHABET, CIPHERTEXT_SEED + 901).tolist()
    print("Oracle scores (full objective):")
    sol_true = _score_test_key(
        text=ct_idx.tolist(),
        cipher_spec=cipher_spec,
        key_spec=key_spec,
        key=true_key,
        scorer_params=scorer_params,
        wli=wli,
        direction=direction,
    )
    oracle_pct = float(sol_true.score)
    oracle_raw = _solution_raw(sol_true)
    oracle_raw_str = f"{oracle_raw:.6f}" if oracle_raw is not None else "N/A"
    print(f"  true_key: pct={oracle_pct:.6f} raw={oracle_raw_str}")
    sol_rand = _score_test_key(
        text=ct_idx.tolist(),
        cipher_spec=cipher_spec,
        key_spec=key_spec,
        key=rand_key,
        scorer_params=scorer_params,
        wli=wli,
        direction=direction,
    )
    rand_pct = float(sol_rand.score)
    rand_raw = _solution_raw(sol_rand)
    rand_raw_str = f"{rand_raw:.6f}" if rand_raw is not None else "N/A"
    print(f"  rand_key: pct={rand_pct:.6f} raw={rand_raw_str}")

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
        print(f"Seed pool: {len(seed_keys)} keys")

    solver = SolverSpec.kaeding(**_apply_plateau(SOLVER_CFG))

    sol = run(
        text=ct_runes,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        **({} if seed_keys is None else {"initial_keys": seed_keys}),
    )

    recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")
    print("Recovered preview:", _preview(str(recovered)))

    final_sol = sol
    score_pct = float(getattr(sol, "score", 0.0) or 0.0)
    plateau_hit = _stopped_on_plateau(sol)
    _, top_pct = _extract_top_scores(sol)
    gap_pct = None
    if top_pct:
        nth_idx = min(len(top_pct) - 1, TOP_STAGE1_KEYS - 1)
        if nth_idx > 0:
            gap_pct = float(top_pct[0]) - float(top_pct[nth_idx])
            print(
                f"Stage 1 top-{nth_idx + 1} pct gap: {gap_pct:.6f} "
                f"(best={float(top_pct[0]):.6f}, nth={float(top_pct[nth_idx]):.6f})"
            )
        else:
            print(f"Stage 1 top pct best={float(top_pct[0]):.6f}")

    hybrid_reasons: list[str] = []
    if plateau_hit:
        hybrid_reasons.append("plateau")
    if HYBRID_TRIGGER_PCT is not None and score_pct < float(HYBRID_TRIGGER_PCT):
        hybrid_reasons.append(f"pct<{float(HYBRID_TRIGGER_PCT):.3f}")
    if gap_pct is not None and gap_pct < float(HYBRID_PCT_GAP_EPS):
        hybrid_reasons.append(f"low_gap<{float(HYBRID_PCT_GAP_EPS):.4f}")
    if oracle_pct and score_pct < oracle_pct * float(HYBRID_ORACLE_GUARD_FRAC):
        hybrid_reasons.append("oracle_guard")

    if RUN_HYBRID and hybrid_reasons:
        print(f"Kaeding hybrid trigger: {', '.join(hybrid_reasons)}")
        neighbors = _neighbor_cloud(
            getattr(sol, "key", None),
            period=PERIOD,
            alphabet_size=ALPHABET,
            seed=TUTORIAL_SEED + 991,
            total_keys=NEIGHBOR_KEYS,
            cross_keys=NEIGHBOR_CROSS_KEYS,
        )
        hybrid_keys = _build_hybrid_keys(
            getattr(sol, "key", None),
            seed_keys,
            neighbors,
            HYBRID_MAX_KEYS,
        )
        if hybrid_keys:
            print(f"Hybrid seed pool: {len(hybrid_keys)} keys")

        hybrid = SolverSpec.hybrid(
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

        sol_h = run(
            text=ct_runes,
            cipher=cipher_spec,
            key=key_spec,
            solver=hybrid,
            scorer_params=dict(scorer_params),
            wli_data=wli,
            encoding_dir=direction,
            telemetry_on=True,
            **({} if not hybrid_keys else {"initial_keys": hybrid_keys}),
        )
        recovered_h = getattr(sol_h, "plaintext_rune", "") or getattr(sol_h, "plaintext_str", "")
        print("Hybrid recovered preview:", _preview(str(recovered_h)))

        if float(sol_h.score) > float(final_sol.score):
            print(f"Hybrid improved score: {float(sol.score):.6f} -> {float(sol_h.score):.6f}")
            final_sol = sol_h
        else:
            print("Hybrid did not improve score.")

    print_run_report(
        title="periodic-substitution-hard",
        cipher="periodic_substitution",
        solution=final_sol,
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
