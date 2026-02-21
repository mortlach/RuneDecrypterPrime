from __future__ import annotations

"""bench_solve_periodic_columnar_pipeline_no_wli

Version 1 (char-only, no WLI) of the proven staged periodic+columnar pipeline.

Intent
------
Keep the *shape* and the “simple knobs” of `bench_solve_periodic_columnar_pipeline.py`,
but remove all WLI dependency so we can tune and measure behaviour that matches the
runic solve setting:

* ~400–520 characters
* unknown (period, columns, order) in the real problem, but here we benchmark on
  synthetic instances with known keys so we can compute match_ratio.
* char-only scoring everywhere (no WLI assets required).

Stages
------
Stage 1: periodic substitution baseline (Kaeding)
Stage 2: exact tail sweep for small columns (C<=7), char-only scoring
Stage 3: full refine on the product cipher (Kaeding), char-only scoring

Notes
-----
* Oracle scores are logged only for benchmark diagnostics; oracle is not used to guide
  stopping by default in this no-WLI version.
* This file is designed to live alongside the other benchmark scripts:
  `tools/benchmarks/bench_solve_periodic_columnar_pipeline_no_wli.py`.
"""

import csv
import json
import subprocess
import sys
import time
from itertools import permutations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np


_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, run
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from rune_decrypter_prime.utils.seed_utils import make_periodic_seed_pool

from tools.benchmarks import bench_solve_periodic_columnar_kaeding as base


ALPHABET_SIZE = 29
ORDER = "col_then_sub"  # keep v1 aligned with the proven pipeline; add both orders in later variants.
PROFILE = "pipeline_no_wli_v1"
PIPELINE_RUN_MODE = "focus_500_nowli"  # "full" | "focus_500_nowli" | "smoke"

SOLVE_MATCH_THRESHOLD = 0.90
STALL_DELTA = 0.002
STALL_STAGE_LIMIT = 1
HEARTBEAT_SECONDS = 900
PREVIEW_CHARS = 240

TEXT_OFFSETS = [0]
KEY_SEEDS = [111]

STAGE1_SUB_CANDIDATES = 16
STAGE3_INITIAL_KEYS = 24

STAGE1_SUB_CANDIDATES_BY_COLUMNS = {1: 6, 3: 10, 5: 12, 7: 14}
STAGE3_INITIAL_KEYS_BY_COLUMNS = {1: 8, 3: 12, 5: 16, 7: 20}

STAGE2_EXACT_MAX_COLUMNS = 7
STAGE2_EXACT_SUB_CANDIDATES = 2
STAGE2_EXACT_TWO_PASS = True
STAGE2_EXACT_PASS1_TOP_TAILS = 256
STAGE2_EXACT_EARLY_SOLVE_BREAK = True
STAGE2_FAST_CHAR_WEIGHTS = {3: 0.5, 4: 0.5}
STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS = {3: 4, 5: 3, 7: 2}
STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS = {3: 72, 5: 128, 7: 192}

# Oracle guide-stop is disabled in this no-WLI version.
STAGE1_USE_ORACLE_GUIDE_STOP = False
STAGE1_ORACLE_STOP_MARGIN = 0.005
STAGE3_USE_ORACLE_GUIDE_STOP = False
STAGE3_ORACLE_STOP_MARGIN = 0.002
STAGE3_ORACLE_STOP_RELAX_FRACTION = 0.0

STAGE1_SEED_RESTARTS = 96
STAGE1_SEED_N_BLOCKS = 18
STAGE1_SEED_TOTAL = 256
STAGE1_SEED_SWAPS = 3

# Stage-3 dynamic budget bands (no-WLI, short text). These are deliberately modest.
STAGE3_DYNAMIC_BANDS = [
    dict(name="very_close", max_gap=0.015, steps=1800, restarts=1, plateau_rounds=220, col_batch=96, inner_batch=128),
    dict(name="close", max_gap=0.040, steps=3200, restarts=1, plateau_rounds=320, col_batch=112, inner_batch=128),
    dict(name="mid", max_gap=0.100, steps=4800, restarts=2, plateau_rounds=420, col_batch=128, inner_batch=128),
    dict(name="far", max_gap=1e9, steps=7200, restarts=2, plateau_rounds=560, col_batch=128, inner_batch=128),
]

# Scorers (char-only everywhere).
SCORER_STAGE1 = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={1: 1.0},
    wli_weights={},
)
SCORER_FULL = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=False,
    char_weights={3: 0.2, 4: 0.8},
    wli_weights={},
)

SOLVER_STAGE1 = dict(
    steps=4200,
    restarts=3,
    inner_batch=128,
    slip_every=0,
    slip_blocks=1,
    slip_policy="stall",
    stall_rounds=250,
    stall_slip_limit=3,
    slip_swaps=24,
    stall_stop_on_limit=True,
    block_schedule="round_robin",
    col_every=0,
    col_batch=0,
    use_raw_score=False,
    raw_accept_min_delta=1e-6,
    pct_plateau_min_delta=1e-4,
    plateau_rounds=420,
    plateau_min_delta=5e-4,
    delta_window=200,
    top_k=64,
    progress_pct=5,
    print_progress=True,
    seed=2026,
    seed_restarts=96,
)

SOLVER_STAGE3 = dict(
    steps=7200,
    restarts=2,
    inner_batch=256,
    col_every=1,
    col_batch=128,
    slip_every=80,
    slip_blocks=1,
    slip_policy="stall",
    stall_rounds=220,
    stall_slip_limit=4,
    slip_swaps=40,
    use_raw_score=False,
    raw_accept_min_delta=1e-6,
    pct_plateau_min_delta=1e-4,
    plateau_rounds=720,
    plateau_min_delta=2e-4,
    delta_window=200,
    top_k=32,
    progress_pct=5,
    print_progress=True,
    seed=2026,
)


@dataclass(frozen=True)
class Tier:
    name: str
    period: int
    columns: int
    length: int


TIERS: List[Tier] = [
    # Default set is overridden by run-mode.
    Tier("focus_p7_c7_l452", 7, 7, 452),
]


def _repo_root() -> Path:
    return _ROOT


def _git_short() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(_repo_root()), stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="replace").strip() or "nogit"
    except Exception:
        return "nogit"


def _apply_run_mode() -> None:
    global PROFILE, HEARTBEAT_SECONDS, TIERS, TEXT_OFFSETS, KEY_SEEDS
    global STAGE1_SUB_CANDIDATES, STAGE3_INITIAL_KEYS
    if PIPELINE_RUN_MODE == "full":
        return
    if PIPELINE_RUN_MODE == "smoke":
        PROFILE = "pipeline_no_wli_smoke_v1"
        HEARTBEAT_SECONDS = 300
        TEXT_OFFSETS[:] = [0]
        KEY_SEEDS[:] = [111]
        TIERS[:] = [
            Tier("smoke_p7_c5_l452", 7, 5, 452),
            Tier("smoke_p9_c7_l446", 9, 7, 446),
        ]
        return
    if PIPELINE_RUN_MODE == "focus_500_nowli":
        PROFILE = "pipeline_no_wli_focus500_v1"
        HEARTBEAT_SECONDS = 900
        TEXT_OFFSETS[:] = [0]
        KEY_SEEDS[:] = [111]
        # Curated, runic-like lengths and friendly columns (<=7) so stage2 exact tail is exercised.
        TIERS[:] = [
            Tier("focus_p7_c5_l452", 7, 5, 452),
            Tier("focus_p7_c7_l452", 7, 7, 452),
            Tier("focus_p8_c5_l505", 8, 5, 505),
            Tier("focus_p9_c5_l446", 9, 5, 446),
            Tier("focus_p9_c7_l446", 9, 7, 446),
            Tier("focus_p14_c5_l452", 14, 5, 452),
            Tier("focus_p15_c7_l415", 15, 7, 415),
            Tier("focus_p18_c7_l446", 18, 7, 446),
            Tier("focus_p21_c5_l483", 21, 5, 483),
            Tier("focus_p21_c7_l483", 21, 7, 483),
        ]
        STAGE1_SUB_CANDIDATES = 16
        STAGE3_INITIAL_KEYS = 24
        return


def _extract_top_keys(sol: Any, *, limit: int) -> List[List[int]]:
    """Best-effort extraction of top keys from Kaeding telemetry.

    Matches the behaviour in the proven pipeline script: take telemetry top_keys
    if present, then include the final key, and dedupe.
    """
    out: List[List[int]] = []
    try:
        tel = getattr(sol, "meta", {}).get("telemetry", {})
        km = tel.get("kaeding", {}) if isinstance(tel, dict) else {}
        top = km.get("top_keys", None) if isinstance(km, dict) else None
        if isinstance(top, list):
            out.extend([list(map(int, row)) for row in top])
    except Exception:
        pass
    try:
        if getattr(sol, "key", None) is not None:
            out.append(list(map(int, list(sol.key))))
    except Exception:
        pass

    seen: set[tuple[int, ...]] = set()
    dedup: List[List[int]] = []
    for k in out:
        t = tuple(int(x) for x in k)
        if t in seen:
            continue
        seen.add(t)
        dedup.append(list(k))
        if len(dedup) >= int(limit):
            break
    return dedup


def _preview_latin(pt: Sequence[int], wli: Sequence[Sequence[int]]) -> str:
    return base._safe_preview_latin(pt, wli, limit=PREVIEW_CHARS)


def _print_stage_preview(
    *,
    label: str,
    pt: Sequence[int],
    wli: Sequence[Sequence[int]],
    match_ratio: float | None = None,
) -> None:
    txt = _preview_latin(pt, wli)
    mr_txt = ""
    if match_ratio is not None and np.isfinite(float(match_ratio)):
        mr_txt = f" match_ratio={float(match_ratio):.3f}"
    print(
        f"[pipeline_no_wli] preview {label} scorer_wli=off "
        f"len={len(pt)} words={len(wli)}{mr_txt} text=\"{txt}\"",
        flush=True,
    )


def _objective_text(obj: Any) -> str:
    family = str(getattr(obj, "family", "unknown"))
    stat = str(getattr(obj, "stat", "unknown"))
    win = getattr(obj, "win", None)
    fam_txt = family.split(".")[-1].lower()
    stat_txt = stat.split(".")[-1].lower()
    return f"{fam_txt}.{stat_txt}.win{int(win) if win is not None else 'na'}"


def _weights_text(weights: Dict[int, float]) -> str:
    if not weights:
        return "{}"
    parts = [f"{int(k)}:{float(v):g}" for k, v in sorted(weights.items(), key=lambda kv: int(kv[0]))]
    return "{" + ",".join(parts) + "}"


def _select_stage3_band(gap_to_oracle: float) -> Dict[str, Any]:
    gap = float(gap_to_oracle)
    for band in STAGE3_DYNAMIC_BANDS:
        if gap <= float(band.get("max_gap", 1e9)):
            return dict(band)
    return dict(STAGE3_DYNAMIC_BANDS[-1])


def _oracle_score_for_stage(
    *,
    pt_idx: np.ndarray,
    cipher_cfg: CipherConfig,
    scorer_params: Dict[str, Any],
) -> Tuple[float, float, str]:
    s_cfg = ScoringConfig(**scorer_params)
    scorer = build_scorer(cipher_cfg, s_cfg)
    # no-WLI: always score without WLI arg.
    score, raw = scorer.score_with_raw(pt_idx, None)
    return float(score), float(raw), _objective_text(getattr(s_cfg, "objective", None))


def _write_csv_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: List[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key in seen:
                continue
            seen.add(key)
            fieldnames.append(str(key))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main() -> None:
    _apply_run_mode()
    direction = Direction.LTR
    print("[pipeline_no_wli] bootstrap: checking char LM assets...", flush=True)
    base._require_assets(direction, ns=(1, 3, 4), need_wli=False)
    pt_base, wli_base = base._encode_long_plaintext(direction)

    root = _repo_root()
    out_root = root / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"{stamp}__bench_solve_pipeline_no_wli__{_git_short()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"[pipeline_no_wli] setup: profile={PROFILE} mode={PIPELINE_RUN_MODE} "
        f"direction={direction.value} order={ORDER} A={ALPHABET_SIZE}",
        flush=True,
    )
    print(f"[pipeline_no_wli] setup: objective=pct.logp.win10 stage1=(char1,wli_off) stage2/3=(char34,wli_off)", flush=True)
    print(f"[pipeline_no_wli] setup: tiers={len(TIERS)} text_offsets={TEXT_OFFSETS} key_seeds={KEY_SEEDS}", flush=True)
    print(f"[pipeline_no_wli] reports: {run_dir.relative_to(root)}", flush=True)

    stages: List[dict] = []
    instances: List[dict] = []
    total = len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS)
    done = 0
    t0_all = time.time()
    last_hb = float(t0_all)
    best_global = {"match": float("-inf"), "tier": "", "text_id": -1, "key_seed": -1, "stage": "", "preview": ""}

    for tier in TIERS:
        for text_id, off in enumerate(TEXT_OFFSETS):
            pt_idx, wli, offset_used = base._slice_word_aligned(pt_base, wli_base, length=tier.length, offset_hint=int(off))
            for key_seed in KEY_SEEDS:
                t0_i = time.time()
                key_len = int(tier.period * ALPHABET_SIZE + tier.columns)
                rng = np.random.default_rng(int(key_seed))
                keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=tier.period, A=ALPHABET_SIZE, columns=tier.columns)
                key_true = keyops.random(rng).astype(np.int16, copy=False)

                cfg_full = CipherConfig(
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
                cfg_sub = CipherConfig(
                    name="periodic_substitution",
                    ciphertext=[],
                    period=tier.period,
                    alphabet_size=ALPHABET_SIZE,
                    key_length=tier.period * ALPHABET_SIZE,
                    encoding_dir=direction,
                    wli_data=[],
                    device=Device.CPU,
                )
                full_cipher = PeriodicColumnarCipher(cfg_full)
                sub_cipher = PeriodicSubstitutionCipher(cfg_sub)
                ct_idx = full_cipher.encrypt_single(plaintext=pt_idx, key=key_true)

                sub_len = int(tier.period * ALPHABET_SIZE)
                true_sub = key_true[:sub_len].astype(np.int16, copy=False)
                pt_stage1_oracle = np.asarray(sub_cipher.decrypt_single(ciphertext=ct_idx, key=true_sub), dtype=np.uint8).reshape(-1)

                scorer_stage1 = dict(SCORER_STAGE1, encoding_dir=direction)
                scorer_full = dict(SCORER_FULL, encoding_dir=direction)
                scorer_full_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_full))
                scorer_stage2_fast_runtime = None
                if int(tier.columns) <= int(STAGE2_EXACT_MAX_COLUMNS) and bool(STAGE2_EXACT_TWO_PASS):
                    scorer_stage2_fast = dict(
                        objective="pct.logp.win10",
                        include_char=True,
                        use_word_breaks=False,
                        char_weights=dict(STAGE2_FAST_CHAR_WEIGHTS),
                        wli_weights={},
                        encoding_dir=direction,
                    )
                    scorer_stage2_fast_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_stage2_fast))

                oracle_s1, oracle_s1_raw, s1_obj = _oracle_score_for_stage(pt_idx=pt_stage1_oracle, cipher_cfg=cfg_sub, scorer_params=scorer_stage1)
                oracle_s23, oracle_s23_raw, s23_obj = _oracle_score_for_stage(pt_idx=pt_idx, cipher_cfg=cfg_full, scorer_params=scorer_full)
                print(
                    f"[pipeline_no_wli] objective tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"stage1={scorer_stage1['objective']} stage23={scorer_full['objective']}",
                    flush=True,
                )
                print(
                    "[pipeline_no_wli] oracle-score "
                    f"stage=stage1_sub model={s1_obj} "
                    f"(char={_weights_text(dict(SCORER_STAGE1.get('char_weights', {})))},wli={{}},wb=0) "
                    f"score={oracle_s1:.6f} raw={oracle_s1_raw:.6f}",
                    flush=True,
                )
                print(
                    "[pipeline_no_wli] oracle-score "
                    f"stage=stage2_3 model={s23_obj} "
                    f"(char={_weights_text(dict(SCORER_FULL.get('char_weights', {})))},wli={{}},wb=0) "
                    f"score={oracle_s23:.6f} raw={oracle_s23_raw:.6f}",
                    flush=True,
                )

                if not np.array_equal(
                    np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=key_true), dtype=np.uint8),
                    np.asarray(pt_idx, dtype=np.uint8),
                ):
                    raise RuntimeError(f"[pipeline_no_wli] gate0 roundtrip failed tier={tier.name} text={text_id} key_seed={key_seed}")

                _print_stage_preview(label="oracle", pt=pt_idx.tolist(), wli=wli, match_ratio=1.0)

                # Stage 1: periodic substitution
                t_s1 = time.time()
                solver_stage1_cfg = dict(SOLVER_STAGE1)
                stage1_sub_limit = int(STAGE1_SUB_CANDIDATES_BY_COLUMNS.get(int(tier.columns), STAGE1_SUB_CANDIDATES))
                if STAGE1_USE_ORACLE_GUIDE_STOP:
                    s1_stop = min(0.999999, float(oracle_s1) + float(STAGE1_ORACLE_STOP_MARGIN))
                    solver_stage1_cfg["stop_score"] = float(s1_stop)

                s1_seeds = make_periodic_seed_pool(
                    ct_idx,
                    period=tier.period,
                    direction=direction.value,
                    seed=2026 + int(key_seed),
                    n_block_seeds=int(STAGE1_SEED_N_BLOCKS),
                    total_seeds=int(STAGE1_SEED_TOTAL),
                    swaps_per_block=int(STAGE1_SEED_SWAPS),
                    alphabet_size=ALPHABET_SIZE,
                )
                sol1 = run(
                    text=ct_idx.tolist(),
                    cipher=by_name.cipher("periodic_substitution", period=tier.period, alphabet_size=ALPHABET_SIZE),
                    key=KeySpec.periodic_substitution(period=tier.period, alphabet_size=ALPHABET_SIZE),
                    solver=SolverSpec.kaeding(**solver_stage1_cfg),
                    scorer_params=scorer_stage1,
                    wli_data=wli,
                    encoding_dir=direction,
                    telemetry_on=True,
                    initial_keys=s1_seeds,
                    force_no_wli=True,
                )
                dt1 = float(time.time() - t_s1)
                ev1 = int((getattr(sol1, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                sub_best = np.asarray(getattr(sol1, "key", []) or [], dtype=np.int16).reshape(-1)
                sub_key_match = base._match_ratio(sub_best.tolist(), true_sub.tolist())
                sub_candidates = _extract_top_keys(sol1, limit=stage1_sub_limit) or [sub_best.astype(int).tolist()]
                pt1 = np.asarray(getattr(sol1, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                if pt1.size > 0:
                    m1 = base._match_ratio(pt1.tolist(), pt_idx.tolist())
                    _print_stage_preview(label="stage1_sub", pt=pt1.tolist(), wli=wli, match_ratio=float(m1))
                stages.append(
                    dict(
                        tier=tier.name,
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                        stage="stage1_sub",
                        score=float(getattr(sol1, "score", float("nan"))),
                        sub_key_match=float(sub_key_match),
                        seconds=round(dt1, 3),
                        evals=ev1,
                        candidates=len(sub_candidates),
                    )
                )
                print(
                    f"[pipeline_no_wli] stage1-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"score={float(getattr(sol1, 'score', float('nan'))):.6f} sub_key_match={float(sub_key_match):.3f} "
                    f"evals={ev1} seconds={dt1:.1f} candidates={len(sub_candidates)}",
                    flush=True,
                )

                # Stage 2: exact tail (C<=7) or identity for C=1
                best2_match, best2_score, best2_key, best2_preview = float("-inf"), float("-inf"), None, ""
                stage2_evals_total = 0
                exact_sub_limit = int(STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS.get(int(tier.columns), STAGE2_EXACT_SUB_CANDIDATES))
                pass1_top_tails = int(STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS.get(int(tier.columns), STAGE2_EXACT_PASS1_TOP_TAILS))

                if int(tier.columns) <= 1:
                    for i, sub_key in enumerate(sub_candidates):
                        sub_arr = np.asarray(sub_key, dtype=np.int16)
                        full_key = np.concatenate([sub_arr, np.asarray([0], dtype=np.int16)], axis=0)
                        pt2 = np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key), dtype=np.uint8).reshape(-1)
                        m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                        sc2 = float(scorer_full_runtime.score(pt2, None))
                        stage2_evals_total += 1
                        if (m2 > best2_match) or (abs(m2 - best2_match) <= 1e-12 and sc2 > best2_score):
                            best2_match, best2_score = float(m2), float(sc2)
                            best2_key = full_key.astype(int).tolist()
                            best2_preview = _preview_latin(pt2.tolist(), wli)
                            _print_stage_preview(label=f"stage2_identity_best_{i+1}", pt=pt2.tolist(), wli=wli, match_ratio=float(m2))
                    print(
                        f"[pipeline_no_wli] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=identity best_match={float(best2_match):.3f} best_score={float(best2_score):.6f} evals={int(stage2_evals_total)}",
                        flush=True,
                    )
                elif int(tier.columns) <= int(STAGE2_EXACT_MAX_COLUMNS):
                    exact_subs = sub_candidates[: max(1, int(exact_sub_limit))]
                    exact_early_stop = False
                    for i, sub_key in enumerate(exact_subs):
                        sub_arr = np.asarray(sub_key, dtype=np.int16)
                        pass1_evals = 0
                        pass2_evals = 0
                        shortlist_tails: List[Tuple[int, ...]] = []

                        if bool(STAGE2_EXACT_TWO_PASS) and scorer_stage2_fast_runtime is not None:
                            pass1_ranked: List[Tuple[float, Tuple[int, ...]]] = []
                            for tail in permutations(range(int(tier.columns))):
                                col_key = np.asarray(tail, dtype=np.int16)
                                full_key = np.concatenate([sub_arr, col_key], axis=0)
                                pt2 = np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key), dtype=np.uint8).reshape(-1)
                                fast_sc = float(scorer_stage2_fast_runtime.score(pt2, None))
                                pass1_ranked.append((fast_sc, tuple(int(x) for x in tail)))
                                pass1_evals += 1
                                stage2_evals_total += 1
                                if bool(STAGE2_EXACT_EARLY_SOLVE_BREAK):
                                    m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                                    if float(m2) >= float(SOLVE_MATCH_THRESHOLD):
                                        sc2 = float(scorer_full_runtime.score(pt2, None))
                                        pass2_evals += 1
                                        stage2_evals_total += 1
                                        if (m2 > best2_match) or (abs(m2 - best2_match) <= 1e-12 and sc2 > best2_score):
                                            best2_match, best2_score = float(m2), float(sc2)
                                            best2_key = full_key.astype(int).tolist()
                                            best2_preview = _preview_latin(pt2.tolist(), wli)
                                            _print_stage_preview(label=f"stage2_exact_best_sub{i+1}", pt=pt2.tolist(), wli=wli, match_ratio=float(m2))
                                        exact_early_stop = True
                                        break
                            if not exact_early_stop:
                                pass1_ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
                                k_short = min(int(pass1_top_tails), len(pass1_ranked))
                                shortlist_tails = [tail for _s, tail in pass1_ranked[:k_short]]
                        else:
                            shortlist_tails = [tuple(int(x) for x in tail) for tail in permutations(range(int(tier.columns)))]

                        if not exact_early_stop:
                            for tail in shortlist_tails:
                                col_key = np.asarray(tail, dtype=np.int16)
                                full_key = np.concatenate([sub_arr, col_key], axis=0)
                                pt2 = np.asarray(full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key), dtype=np.uint8).reshape(-1)
                                m2 = base._match_ratio(pt2.tolist(), pt_idx.tolist())
                                sc2 = float(scorer_full_runtime.score(pt2, None))
                                pass2_evals += 1
                                stage2_evals_total += 1
                                if (m2 > best2_match) or (abs(m2 - best2_match) <= 1e-12 and sc2 > best2_score):
                                    best2_match, best2_score = float(m2), float(sc2)
                                    best2_key = full_key.astype(int).tolist()
                                    best2_preview = _preview_latin(pt2.tolist(), wli)
                                    _print_stage_preview(label=f"stage2_exact_best_sub{i+1}", pt=pt2.tolist(), wli=wli, match_ratio=float(m2))
                                if bool(STAGE2_EXACT_EARLY_SOLVE_BREAK) and float(m2) >= float(SOLVE_MATCH_THRESHOLD):
                                    exact_early_stop = True
                                    break

                        stages.append(
                            dict(
                                tier=tier.name,
                                text_id=int(text_id),
                                key_seed=int(key_seed),
                                stage=f"stage2_exact_attempt_{i+1}",
                                score=float(best2_score),
                                match_ratio=float(best2_match),
                                seconds=0.0,
                                evals=int(stage2_evals_total),
                                pass1_evals=int(pass1_evals),
                                pass2_evals=int(pass2_evals),
                                pass2_shortlist=int(len(shortlist_tails)),
                                pass1_top_cap=int(pass1_top_tails),
                                exact_sub_limit=int(exact_sub_limit),
                                early_stop=int(bool(exact_early_stop)),
                            )
                        )
                        if exact_early_stop:
                            break
                    print(
                        f"[pipeline_no_wli] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"mode=exact best_match={float(best2_match):.3f} best_score={float(best2_score):.6f} evals={int(stage2_evals_total)}",
                        flush=True,
                    )
                else:
                    # Columns too large for exact tail in v1 focus tiers; keep stage2 empty.
                    print(
                        f"[pipeline_no_wli] stage2-summary tier={tier.name} text={text_id} key_seed={key_seed} mode=skip_largeC",
                        flush=True,
                    )

                # Stage 3: full refine on product cipher, seeded from stage2 (or stage1).
                best3_match, best3_score, stop_reason = float("-inf"), float("-inf"), ""
                if best2_key is None:
                    # Build a small seed set from stage1 candidates.
                    init3 = []
                    init3_n = int(STAGE3_INITIAL_KEYS_BY_COLUMNS.get(int(tier.columns), STAGE3_INITIAL_KEYS))
                    for k in sub_candidates[: max(1, int(init3_n))]:
                        init3.append(np.concatenate([np.asarray(k, dtype=np.int16), np.asarray(list(range(int(tier.columns))), dtype=np.int16)], axis=0).astype(int).tolist())
                else:
                    init3 = [best2_key]
                    init3_n = 1

                t_s3 = time.time()
                solver_stage3_cfg = dict(SOLVER_STAGE3)
                stage2_gap_to_oracle = float(oracle_s23) - float(best2_score if np.isfinite(best2_score) else float(oracle_s23))
                band = _select_stage3_band(stage2_gap_to_oracle)
                stage3_band_name = str(band.get("name", ""))
                solver_stage3_cfg.update(
                    steps=int(band.get("steps", solver_stage3_cfg.get("steps", 0))),
                    restarts=int(band.get("restarts", solver_stage3_cfg.get("restarts", 0))),
                    plateau_rounds=int(band.get("plateau_rounds", solver_stage3_cfg.get("plateau_rounds", 0))),
                    col_batch=int(band.get("col_batch", solver_stage3_cfg.get("col_batch", 0))),
                    inner_batch=int(band.get("inner_batch", solver_stage3_cfg.get("inner_batch", 0))),
                )
                sol3 = run(
                    text=ct_idx.tolist(),
                    cipher=by_name.cipher("periodic_columnar", period=tier.period, columns=tier.columns, order=ORDER, alphabet_size=ALPHABET_SIZE),
                    key=KeySpec.periodic_columnar(period=tier.period, columns=tier.columns, alphabet_size=ALPHABET_SIZE),
                    solver=SolverSpec.kaeding(**solver_stage3_cfg),
                    scorer_params=scorer_full,
                    wli_data=wli,
                    encoding_dir=direction,
                    telemetry_on=True,
                    force_no_wli=True,
                    initial_keys=init3,
                )
                dt3 = float(time.time() - t_s3)
                ev3 = int((getattr(sol3, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                pt3 = np.asarray(getattr(sol3, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                if pt3.size > 0:
                    best3_match = base._match_ratio(pt3.tolist(), pt_idx.tolist())
                    best3_score = float(getattr(sol3, "score", float("nan")))
                    _print_stage_preview(label="stage3_full_refine", pt=pt3.tolist(), wli=wli, match_ratio=float(best3_match))
                stages.append(
                    dict(
                        tier=tier.name,
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                        stage="stage3_full_refine",
                        score=float(best3_score),
                        match_ratio=float(best3_match),
                        seconds=round(dt3, 3),
                        evals=ev3,
                        stage3_band=stage3_band_name,
                        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
                    )
                )
                if np.isfinite(best3_match) and best3_match >= SOLVE_MATCH_THRESHOLD:
                    stop_reason = "solved_stage3"
                elif (best3_match - best2_match) <= STALL_DELTA:
                    stop_reason = "stalled_no_improve"
                else:
                    stop_reason = "unsolved"
                print(
                    f"[pipeline_no_wli] stage3-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"band={stage3_band_name} match={float(best3_match):.3f} score={float(best3_score):.6f} evals={ev3} stop={stop_reason}",
                    flush=True,
                )

                best_match = max(float(best2_match if np.isfinite(best2_match) else 0.0), float(best3_match if np.isfinite(best3_match) else 0.0))
                best_stage = "stage3_full_refine" if np.isfinite(best3_match) and best3_match >= best2_match else "stage2_search"
                status = "solved" if best_match >= SOLVE_MATCH_THRESHOLD else ("stalled" if stop_reason == "stalled_no_improve" else "unsolved")
                dt_i = float(time.time() - t0_i)
                total_evals = int(ev1 + int(stage2_evals_total) + int(ev3))
                preview_best = best2_preview if best2_preview else (base._safe_preview_latin(pt3, wli) if pt3.size > 0 else "")
                instances.append(
                    dict(
                        tier=tier.name,
                        period=tier.period,
                        columns=tier.columns,
                        length=tier.length,
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                        offset_hint=int(off),
                        offset_used=int(offset_used),
                        status=status,
                        stop_reason=stop_reason,
                        solve_threshold=float(SOLVE_MATCH_THRESHOLD),
                        best_stage=best_stage,
                        best_match_ratio=float(best_match),
                        stage1_sub_key_match=float(sub_key_match),
                        stage2_match_ratio=float(best2_match if np.isfinite(best2_match) else np.nan),
                        stage3_match_ratio=float(best3_match if np.isfinite(best3_match) else np.nan),
                        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
                        stage3_band=str(stage3_band_name),
                        total_seconds=round(dt_i, 3),
                        total_evals=total_evals,
                        preview_best_latin=str(preview_best),
                    )
                )

                if best_match > float(best_global["match"]):
                    best_global.update(match=float(best_match), tier=str(tier.name), text_id=int(text_id), key_seed=int(key_seed), stage=str(best_stage), preview=str(preview_best))

                done += 1
                elapsed = time.time() - t0_all
                eta = (elapsed / float(done)) * float(total - done) if done else 0.0
                print(
                    f"[pipeline_no_wli] {done}/{total} tier={tier.name} status={status} best_match={best_match:.3f} "
                    f"run={base._format_seconds(dt_i)} elapsed={base._format_seconds(elapsed)} eta={base._format_seconds(eta)}",
                    flush=True,
                )
                if preview_best:
                    print(f"[pipeline_no_wli] best-instance-preview tier={tier.name} text={text_id} key_seed={key_seed} text=\"{preview_best}\"", flush=True)
                now = time.time()
                if (now - last_hb) >= float(HEARTBEAT_SECONDS):
                    print(
                        f"[pipeline_no_wli] heartbeat elapsed={base._format_seconds(now - t0_all)} done={done}/{total} "
                        f"global_best_match={float(best_global['match']):.3f} tier={best_global['tier']} "
                        f"text={best_global['text_id']} key_seed={best_global['key_seed']} stage={best_global['stage']} "
                        f"preview=\"{best_global['preview']}\"",
                        flush=True,
                    )
                    last_hb = now

    summary: Dict[str, Any] = {"tiers": {}}
    for t in TIERS:
        rs = [r for r in instances if r["tier"] == t.name]
        if not rs:
            continue
        arr = np.asarray([float(r["best_match_ratio"]) for r in rs], dtype=np.float64)
        summary["tiers"][t.name] = dict(
            n=len(rs),
            solved_rate=float(np.mean(arr >= SOLVE_MATCH_THRESHOLD)),
            best_match_p50=float(np.percentile(arr, 50)),
            best_match_p90=float(np.percentile(arr, 90)),
        )

    (run_dir / "instances.json").write_text(json.dumps(instances, indent=2), encoding="utf-8")
    (run_dir / "stages.json").write_text(json.dumps(stages, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_csv_rows(run_dir / "instances.csv", instances)
    _write_csv_rows(run_dir / "stages.csv", stages)

    hist = root / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_no_wli_log.csv"
    hist.parent.mkdir(parents=True, exist_ok=True)
    hist_rows = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for r in instances:
        hist_rows.append(
            dict(
                timestamp_utc=now_iso,
                run_id=run_dir.name,
                profile_id=PROFILE,
                fixture_id=r["tier"],
                text_id=r["text_id"],
                key_seed=r["key_seed"],
                period=r["period"],
                columns=r["columns"],
                length=r["length"],
                status=r["status"],
                solve_threshold=r["solve_threshold"],
                best_match_ratio=r["best_match_ratio"],
                best_stage=r["best_stage"],
                stage1_sub_key_match=r["stage1_sub_key_match"],
                stage2_match_ratio=r["stage2_match_ratio"],
                stage3_match_ratio=r["stage3_match_ratio"],
                total_seconds=r["total_seconds"],
                total_evals=r["total_evals"],
                notes=r["stop_reason"],
            )
        )
    if hist_rows:
        cols = list(hist_rows[0].keys())
        write_header = (not hist.exists()) or hist.stat().st_size == 0
        with hist.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if write_header:
                w.writeheader()
            w.writerows(hist_rows)

    print(f"[pipeline_no_wli] completed in {base._format_seconds(time.time() - t0_all)}", flush=True)
    print(f"[pipeline_no_wli] reports: {run_dir.relative_to(root)}", flush=True)
    print(f"[pipeline_no_wli] history: {hist.relative_to(root)} rows={len(hist_rows)}", flush=True)


if __name__ == "__main__":
    main()
