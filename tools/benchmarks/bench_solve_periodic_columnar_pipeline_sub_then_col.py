from __future__ import annotations

"""
Benchmark pipeline for periodic-columnar with order="sub_then_col".

This pipeline is intentionally separate from the col_then_sub benchmark because
the search shape is different:

1) probe/rank column permutations first
2) solve periodic substitution on top column candidates
3) optional full integrated refine

It writes per-instance checkpoints and append-only history, plus a solved-only
JSONL with config+instance payload for reproducibility.

Stage A/B scorer profile is selected via:
- RDP_SUBCOL_STAGEAB_PROFILE=A_char1|A_char34|A_char34_wli34
"""

import csv
import json
import os
import re
import subprocess
import sys
import time
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
from rune_decrypter_prime.utils.seed_utils_periodic_columnar_sub_then_col import (
    enumerate_column_permutations,
    undo_columnar_with_perm,
)

from tools.benchmarks import bench_solve_periodic_columnar_kaeding as base

ALPHABET_SIZE = 29
ORDER = "sub_then_col"
PROFILE = "pipeline_sub_then_col_v1"
PIPELINE_RUN_MODE = str(os.environ.get("RDP_SUBCOL_MODE", "focus_sub_then_col")).strip()  # "focus_sub_then_col" | "smoke"

SOLVE_MATCH_THRESHOLD = 0.90
STALL_DELTA = 0.002
PREVIEW_CHARS = 240
HEARTBEAT_SECONDS = 1200

AUTOSKIP_PROVEN = True
AUTOSKIP_PROVEN_MIN_MATCH = SOLVE_MATCH_THRESHOLD
FORCE_RERUN_PROVEN = str(os.environ.get("RDP_SUBCOL_FORCE_RERUN_PROVEN", "0")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

TEXT_OFFSETS = [0]
KEY_SEEDS = [111]
KEY_SEEDS_OVERRIDE = str(os.environ.get("RDP_SUBCOL_KEY_SEEDS", "")).strip()
TIERS_REGEX_OVERRIDE = str(os.environ.get("RDP_SUBCOL_TIERS_REGEX", "")).strip()

STAGEAB_SCORER_PROFILE = str(
    os.environ.get("RDP_SUBCOL_STAGEAB_PROFILE", "A_char34_wli34")
).strip()
STAGEAB_SCORER_PROFILES: Dict[str, Dict[str, Any]] = {
    "A_char1": dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,
        char_weights={1: 1.0},
        wli_weights={},
    ),
    "A_char34": dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,
        char_weights={3: 0.3, 4: 0.7},
        wli_weights={},
    ),
    "A_char34_wli34": dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={3: 0.3, 4: 0.7},
        wli_weights={3: 0.4, 4: 0.6},
    ),
}
SCORER_SUB: Dict[str, Any] = dict(STAGEAB_SCORER_PROFILES["A_char34_wli34"])
SCORER_FULL = dict(
    objective="pct.logp.win10",
    include_char=True,
    use_word_breaks=True,
    char_weights={3: 0.3, 4: 0.7},
    wli_weights={3: 0.4, 4: 0.6},
)

SOLVER_SUB = dict(
    steps=2200,
    restarts=2,
    inner_batch=128,
    slip_every=60,
    slip_blocks=1,
    slip_policy="stall",
    stall_rounds=220,
    stall_slip_limit=3,
    slip_swaps=36,
    stall_stop_on_limit=True,
    block_schedule="round_robin",
    col_every=0,
    col_batch=0,
    use_raw_score=False,
    raw_accept_min_delta=1e-6,
    pct_plateau_min_delta=1e-4,
    plateau_rounds=360,
    plateau_min_delta=3e-4,
    delta_window=200,
    top_k=32,
    progress_pct=10,
    print_progress=True,
    seed=2026,
    seed_restarts=96,
)

SOLVER_FULL = dict(
    steps=3600,
    restarts=2,
    inner_batch=128,
    col_every=1,
    col_batch=112,
    slip_every=80,
    slip_blocks=1,
    slip_policy="stall",
    stall_rounds=220,
    stall_slip_limit=4,
    slip_swaps=50,
    use_raw_score=False,
    raw_accept_min_delta=1e-6,
    pct_plateau_min_delta=1e-4,
    plateau_rounds=360,
    plateau_min_delta=4e-4,
    delta_window=200,
    top_k=24,
    progress_pct=2,
    print_progress=True,
    seed=2026,
)

STAGE3_USE_ORACLE_GUIDE_STOP = True
STAGE3_ORACLE_STOP_MARGIN = 0.0
STAGE3_ORACLE_STOP_RELAX_FRACTION = 0.10

COL_EXACT_MAX_COLUMNS = 7
COL_SAMPLE_SIZE = 6000
COL_SAMPLE_SIZE_BY_COLUMNS = {10: 9000, 13: 12000}
COL_KEEP = 18
COL_KEEP_BY_COLUMNS = {3: 24, 5: 24, 7: 20, 10: 24, 13: 32}

SUB_PROBE_N_BLOCKS = 10
SUB_PROBE_TOTAL_SEEDS = 72
SUB_PROBE_SWAPS = 3
SUB_PROBE_EVAL_KEYS = 8

SUB_REFINE_N_BLOCKS = 18
SUB_REFINE_TOTAL_SEEDS = 256
SUB_REFINE_SWAPS = 3
SUB_REFINE_TOP_KEYS_PER_PERM = 3
STAGE3_INITIAL_KEYS = 20
STAGE3_INITIAL_KEYS_BY_COLUMNS = {3: 24, 5: 24, 7: 20, 10: 28, 13: 32}

STAGE3_FULL_ENTRY_SCORE = 0.10
STAGE3_PROBE_ENTRY_SCORE = 0.06


@dataclass(frozen=True)
class Tier:
    name: str
    period: int
    columns: int
    length: int


TIERS = [
    Tier("subcol_p7_c1_l2376", 7, 1, 2376),
    Tier("subcol_p7_c3_l2376", 7, 3, 2376),
    Tier("subcol_p7_c5_l2376", 7, 5, 2376),
    Tier("subcol_p7_c7_l2376", 7, 7, 2376),
    Tier("subcol_p10_c1_l2376", 10, 1, 2376),
    Tier("subcol_p10_c3_l2376", 10, 3, 2376),
    Tier("subcol_p10_c5_l2376", 10, 5, 2376),
    Tier("subcol_p10_c7_l2376", 10, 7, 2376),
    Tier("subcol_p10_c10_l2376", 10, 10, 2376),
    Tier("subcol_p13_c1_l2376", 13, 1, 2376),
    Tier("subcol_p13_c3_l2376", 13, 3, 2376),
    Tier("subcol_p13_c5_l2376", 13, 5, 2376),
    Tier("subcol_p13_c7_l2376", 13, 7, 2376),
    Tier("subcol_p13_c10_l2376", 13, 10, 2376),
    Tier("subcol_p13_c13_l2376", 13, 13, 2376),
]


def _apply_run_mode() -> None:
    global PROFILE, HEARTBEAT_SECONDS, TIERS
    global COL_SAMPLE_SIZE, STAGE3_INITIAL_KEYS, STAGE3_FULL_ENTRY_SCORE, STAGE3_PROBE_ENTRY_SCORE
    global COL_KEEP, SUB_PROBE_N_BLOCKS, SUB_PROBE_TOTAL_SEEDS, SUB_PROBE_SWAPS, SUB_PROBE_EVAL_KEYS
    global SUB_REFINE_N_BLOCKS, SUB_REFINE_TOTAL_SEEDS, SUB_REFINE_SWAPS, SUB_REFINE_TOP_KEYS_PER_PERM
    if PIPELINE_RUN_MODE == "focus_sub_then_col":
        PROFILE = "pipeline_sub_then_col_focus_v1"
        HEARTBEAT_SECONDS = 1200
        return
    if PIPELINE_RUN_MODE == "smoke":
        PROFILE = "pipeline_sub_then_col_smoke_v1"
        HEARTBEAT_SECONDS = 120
        TIERS = [
            Tier("subcol_smoke_p5_c3_l200", 5, 3, 200),
        ]
        COL_SAMPLE_SIZE = 96
        COL_KEEP = 4
        SUB_PROBE_N_BLOCKS = 4
        SUB_PROBE_TOTAL_SEEDS = 16
        SUB_PROBE_SWAPS = 2
        SUB_PROBE_EVAL_KEYS = 3
        SUB_REFINE_N_BLOCKS = 6
        SUB_REFINE_TOTAL_SEEDS = 24
        SUB_REFINE_SWAPS = 2
        SUB_REFINE_TOP_KEYS_PER_PERM = 1
        STAGE3_INITIAL_KEYS = 4
        STAGE3_FULL_ENTRY_SCORE = None
        STAGE3_PROBE_ENTRY_SCORE = None
        SOLVER_SUB.update(
            steps=24,
            restarts=1,
            inner_batch=32,
            top_k=6,
            progress_pct=50,
            plateau_rounds=16,
            seed_restarts=8,
        )
        SOLVER_FULL.update(
            steps=48,
            restarts=1,
            inner_batch=32,
            top_k=6,
            progress_pct=50,
            plateau_rounds=24,
            col_batch=24,
        )
        return
    raise ValueError(
        f"Unknown PIPELINE_RUN_MODE={PIPELINE_RUN_MODE!r}; expected 'focus_sub_then_col' or 'smoke'"
    )


def _resolve_stageab_scorer_profile() -> None:
    global SCORER_SUB
    k = str(STAGEAB_SCORER_PROFILE).strip()
    if k not in STAGEAB_SCORER_PROFILES:
        allowed = ", ".join(sorted(STAGEAB_SCORER_PROFILES.keys()))
        raise ValueError(
            f"Unknown RDP_SUBCOL_STAGEAB_PROFILE={k!r}; expected one of: {allowed}"
        )
    SCORER_SUB = dict(STAGEAB_SCORER_PROFILES[k])


def _apply_runtime_overrides() -> None:
    global KEY_SEEDS, TIERS
    if KEY_SEEDS_OVERRIDE:
        vals = []
        for token in KEY_SEEDS_OVERRIDE.split(","):
            t = token.strip()
            if not t:
                continue
            vals.append(int(t))
        if vals:
            seen: set[int] = set()
            KEY_SEEDS = [int(x) for x in vals if not (int(x) in seen or seen.add(int(x)))]
    if TIERS_REGEX_OVERRIDE:
        rx = re.compile(TIERS_REGEX_OVERRIDE)
        TIERS = [t for t in TIERS if rx.search(str(t.name))]
        if not TIERS:
            raise ValueError(
                f"RDP_SUBCOL_TIERS_REGEX={TIERS_REGEX_OVERRIDE!r} matched zero tiers"
            )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_short() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=_repo_root())
            .decode()
            .strip()
            or "nogit"
        )
    except Exception:
        return "nogit"


def _extract_top_keys(sol: Any, limit: int) -> List[List[int]]:
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


def _mutate_full_key(base_key: Sequence[int], *, period: int, columns: int, seed: int, n: int) -> List[List[int]]:
    rng = np.random.default_rng(int(seed))
    base = np.asarray(base_key, dtype=np.int16).copy()
    out = [base.astype(int).tolist()]
    sub_len = int(period) * ALPHABET_SIZE
    while len(out) < int(n):
        k = base.copy()
        ph = int(rng.integers(0, int(period)))
        a = int(rng.integers(0, ALPHABET_SIZE))
        b = int(rng.integers(0, ALPHABET_SIZE - 1))
        if b >= a:
            b += 1
        i1, i2 = int(ph * ALPHABET_SIZE + a), int(ph * ALPHABET_SIZE + b)
        k[i1], k[i2] = k[i2], k[i1]
        if int(columns) > 1:
            a = int(rng.integers(0, int(columns)))
            b = int(rng.integers(0, int(columns - 1)))
            if b >= a:
                b += 1
            t1, t2 = int(sub_len + a), int(sub_len + b)
            k[t1], k[t2] = k[t2], k[t1]
        out.append(k.astype(int).tolist())
    return out[: int(n)]


def _preview_latin(pt: Sequence[int], wli: Sequence[Sequence[int]]) -> str:
    return base._safe_preview_latin(pt, wli, limit=PREVIEW_CHARS)


def _print_stage_preview(
    *,
    label: str,
    pt: Sequence[int],
    wli: Sequence[Sequence[int]],
    scorer_wli: bool,
    match_ratio: float | None = None,
) -> None:
    txt = _preview_latin(pt, wli)
    mr_txt = ""
    if match_ratio is not None and np.isfinite(float(match_ratio)):
        mr_txt = f" match_ratio={float(match_ratio):.3f}"
    print(
        f"[subcol] preview {label} scorer_wli={'on' if scorer_wli else 'off'} "
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


def _oracle_score_for_stage(
    *,
    pt_idx: np.ndarray,
    wli: Sequence[Sequence[int]],
    cipher_cfg: CipherConfig,
    scorer_params: Dict[str, Any],
) -> Tuple[float, float, str]:
    s_cfg = ScoringConfig(**scorer_params)
    scorer = build_scorer(cipher_cfg, s_cfg)
    use_wli = bool(getattr(s_cfg, "use_word_breaks", False))
    wli_arg = wli if use_wli else None
    score, raw = scorer.score_with_raw(pt_idx, wli_arg)
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


def _append_csv_row(path: Path, row: Dict[str, Any]) -> None:
    if not row:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    new_fields = [str(k) for k in row.keys()]
    if (not path.exists()) or path.stat().st_size == 0:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=new_fields, extrasaction="ignore")
            w.writeheader()
            w.writerow(row)
        return

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        old_fields = [str(k) for k in (reader.fieldnames or [])]
        old_rows = []
        for r in reader:
            clean = {str(k): v for k, v in r.items() if k is not None}
            old_rows.append(clean)

    merged_fields = list(old_fields)
    for k in new_fields:
        if k not in merged_fields:
            merged_fields.append(k)

    if merged_fields == old_fields:
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=merged_fields, extrasaction="ignore")
            w.writerow(row)
        return

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=merged_fields, extrasaction="ignore")
        w.writeheader()
        for r in old_rows:
            w.writerow(r)
        w.writerow(row)


def _build_summary(tiers: Sequence[Tier], instances: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"tiers": {}}
    for t in tiers:
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
    return summary


def _load_proven_solved_index(path: Path, *, min_match: float) -> Dict[Tuple[str, int, int], Dict[str, Any]]:
    out: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
    if not path.exists():
        return out
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get("status", "")).strip().lower() not in {"solved", "skipped_proven"}:
                    continue
                try:
                    mr = float(row.get("best_match_ratio", "nan"))
                except Exception:
                    continue
                if (not np.isfinite(mr)) or (mr < float(min_match)):
                    continue
                key = (
                    str(row.get("fixture_id", "")).strip(),
                    int(row.get("text_id", -1)),
                    int(row.get("key_seed", -1)),
                )
                prev = out.get(key)
                if prev is None or mr > float(prev.get("best_match_ratio", float("-inf"))):
                    out[key] = dict(
                        run_id=str(row.get("run_id", "")).strip(),
                        timestamp_utc=str(row.get("timestamp_utc", "")).strip(),
                        best_match_ratio=float(mr),
                        best_stage=str(row.get("best_stage", "")).strip(),
                    )
    except Exception:
        return {}
    return out


def _stable_top_by_score(rows: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    if k <= 0 or not rows:
        return []
    return sorted(
        rows,
        key=lambda r: (float(r.get("score", float("-inf"))), float(r.get("match", float("-inf")))),
        reverse=True,
    )[: int(k)]


def _fmt_secs(seconds: float) -> str:
    s = max(0.0, float(seconds))
    h = int(s // 3600.0)
    m = int((s % 3600.0) // 60.0)
    sec = s - (h * 3600.0 + m * 60.0)
    if h > 0:
        return f"{h}h{m:02d}m"
    if m > 0:
        return f"{m}m{sec:04.1f}s"
    return f"{sec:.1f}s"


def main() -> None:
    _apply_run_mode()
    _resolve_stageab_scorer_profile()
    _apply_runtime_overrides()
    direction = Direction.LTR
    root = _repo_root()

    print("[subcol] bootstrap: checking LM assets...", flush=True)
    base._require_assets(direction, ns=(3, 4), need_wli=True)

    pt_base, wli_base = base._encode_long_plaintext(direction)
    pt_base = np.asarray(pt_base, dtype=np.uint8)
    wli_base = np.asarray(wli_base, dtype=np.uint8)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = (
        root
        / "output"
        / "tools"
        / "benchmarks"
        / f"{stamp}__bench_solve_sub_then_col_pipeline__{_git_short()}"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    solved_dir = run_dir / "proven_instances"
    solved_dir.mkdir(parents=True, exist_ok=True)

    hist = root / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_sub_then_col_log.csv"
    solved_jsonl = root / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_sub_then_col_solved.jsonl"
    hist.parent.mkdir(parents=True, exist_ok=True)
    solved_jsonl.parent.mkdir(parents=True, exist_ok=True)

    autoskip_effective = bool(AUTOSKIP_PROVEN) and (not bool(FORCE_RERUN_PROVEN))
    proven_index = (
        _load_proven_solved_index(hist, min_match=float(AUTOSKIP_PROVEN_MIN_MATCH))
        if autoskip_effective
        else {}
    )

    print(
        f"[subcol] setup: profile={PROFILE} mode={PIPELINE_RUN_MODE} direction={direction.value} order={ORDER} A={ALPHABET_SIZE}",
        flush=True,
    )
    print(
        f"[subcol] setup: stageAB_scorer_profile={STAGEAB_SCORER_PROFILE} "
        f"stageAB=(char={_weights_text(dict(SCORER_SUB.get('char_weights', {})))}"
        f",wli={_weights_text(dict(SCORER_SUB.get('wli_weights', {})))},"
        f"wb={1 if bool(SCORER_SUB.get('use_word_breaks', False)) else 0})",
        flush=True,
    )
    print(
        f"[subcol] setup: threshold={float(SOLVE_MATCH_THRESHOLD):.3f} stall_delta={float(STALL_DELTA):.4f}",
        flush=True,
    )
    print(
        f"[subcol] setup: autoskip_proven={'on' if autoskip_effective else 'off'} "
        f"(requested={'on' if AUTOSKIP_PROVEN else 'off'}, force_rerun={'on' if FORCE_RERUN_PROVEN else 'off'}) "
        f"min_match={float(AUTOSKIP_PROVEN_MIN_MATCH):.3f} loaded={len(proven_index)}",
        flush=True,
    )
    print(
        f"[subcol] setup: col_probe exact_max={COL_EXACT_MAX_COLUMNS} sample={COL_SAMPLE_SIZE} "
        f"keep={COL_KEEP} keep_by_c={json.dumps(COL_KEEP_BY_COLUMNS, separators=(',', ':'))}",
        flush=True,
    )
    print(
        f"[subcol] setup: tiers={len(TIERS)} text_offsets={TEXT_OFFSETS} key_seeds={KEY_SEEDS} "
        f"tiers_regex={TIERS_REGEX_OVERRIDE if TIERS_REGEX_OVERRIDE else 'none'}",
        flush=True,
    )
    print(f"[subcol] reports: {run_dir.relative_to(root)}", flush=True)

    instances: List[Dict[str, Any]] = []
    stages: List[Dict[str, Any]] = []
    history_rows_written = 0

    total = len(TIERS) * len(TEXT_OFFSETS) * len(KEY_SEEDS)
    done = 0
    t0_all = time.time()
    last_hb = t0_all

    best_global = {
        "match": float("-inf"),
        "tier": "",
        "text_id": -1,
        "key_seed": -1,
        "stage": "",
        "preview": "",
    }

    run_manifest = dict(
        profile=PROFILE,
        mode=PIPELINE_RUN_MODE,
        direction=str(direction.value),
        order=str(ORDER),
        alphabet_size=int(ALPHABET_SIZE),
        solve_threshold=float(SOLVE_MATCH_THRESHOLD),
        autoskip_proven=bool(autoskip_effective),
        autoskip_proven_requested=bool(AUTOSKIP_PROVEN),
        force_rerun_proven=bool(FORCE_RERUN_PROVEN),
        autoskip_proven_min_match=float(AUTOSKIP_PROVEN_MIN_MATCH),
        stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
        stageab_scorer_profiles=dict(STAGEAB_SCORER_PROFILES),
        scorer_sub=dict(SCORER_SUB),
        scorer_full=dict(SCORER_FULL),
        solver_sub=dict(SOLVER_SUB),
        solver_full=dict(SOLVER_FULL),
        col_probe=dict(
            exact_max_columns=int(COL_EXACT_MAX_COLUMNS),
            sample_size=int(COL_SAMPLE_SIZE),
            sample_size_by_c=dict(COL_SAMPLE_SIZE_BY_COLUMNS),
            keep=int(COL_KEEP),
            keep_by_c=dict(COL_KEEP_BY_COLUMNS),
            seed_blocks=int(SUB_PROBE_N_BLOCKS),
            seed_total=int(SUB_PROBE_TOTAL_SEEDS),
            seed_swaps=int(SUB_PROBE_SWAPS),
            eval_keys=int(SUB_PROBE_EVAL_KEYS),
        ),
        sub_refine=dict(
            seed_blocks=int(SUB_REFINE_N_BLOCKS),
            seed_total=int(SUB_REFINE_TOTAL_SEEDS),
            seed_swaps=int(SUB_REFINE_SWAPS),
            top_keys_per_perm=int(SUB_REFINE_TOP_KEYS_PER_PERM),
        ),
        stage3=dict(
            initial_keys=int(STAGE3_INITIAL_KEYS),
            initial_keys_by_c=dict(STAGE3_INITIAL_KEYS_BY_COLUMNS),
            full_entry_score=(None if STAGE3_FULL_ENTRY_SCORE is None else float(STAGE3_FULL_ENTRY_SCORE)),
            probe_entry_score=(None if STAGE3_PROBE_ENTRY_SCORE is None else float(STAGE3_PROBE_ENTRY_SCORE)),
            use_oracle_stop=bool(STAGE3_USE_ORACLE_GUIDE_STOP),
            oracle_stop_margin=float(STAGE3_ORACLE_STOP_MARGIN),
            oracle_relax=float(STAGE3_ORACLE_STOP_RELAX_FRACTION),
        ),
        tiers=[dict(name=t.name, period=t.period, columns=t.columns, length=t.length) for t in TIERS],
        text_offsets=[int(x) for x in TEXT_OFFSETS],
        key_seeds=[int(x) for x in KEY_SEEDS],
        runtime_overrides=dict(
            key_seeds_override=str(KEY_SEEDS_OVERRIDE),
            tiers_regex_override=str(TIERS_REGEX_OVERRIDE),
        ),
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        git_short=_git_short(),
    )
    (run_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")

    for tier in TIERS:
        for text_id, off in enumerate(TEXT_OFFSETS):
            pt_idx, wli, offset_used = base._slice_word_aligned(
                pt_base,
                wli_base,
                length=tier.length,
                offset_hint=int(off),
            )
            for key_seed in KEY_SEEDS:
                t0_i = time.time()
                proven_key = (str(tier.name), int(text_id), int(key_seed))
                if bool(autoskip_effective) and (proven_key in proven_index):
                    src = dict(proven_index.get(proven_key, {}))
                    src_run = str(src.get("run_id", "") or "")
                    src_match = float(src.get("best_match_ratio", float("nan")))
                    src_stage = str(src.get("best_stage", "") or "proven_history")
                    preview_txt = f"[autoskip] source_run={src_run}" if src_run else "[autoskip] proven history"
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
                            status="skipped_proven",
                            stop_reason="autoskip_proven",
                            solve_threshold=float(SOLVE_MATCH_THRESHOLD),
                            best_stage=src_stage,
                            best_match_ratio=float(src_match if np.isfinite(src_match) else np.nan),
                            best_objective_score=np.nan,
                            stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
                            stage_probe_match=np.nan,
                            stage_sub_match=np.nan,
                            stage_full_match=np.nan,
                            n_tails_considered=0,
                            n_tails_kept_after_rank=0,
                            n_unique_tails_kept=0,
                            n_unique_tails_promoted_to_B=0,
                            n_unique_tails_promoted_to_C=0,
                            best_score_per_tail_top5="[]",
                            total_seconds=0.0,
                            total_evals=0,
                            preview_best_latin=preview_txt,
                        )
                    )
                    stages.append(
                        dict(
                            tier=tier.name,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            stage="skip_proven",
                            score=np.nan,
                            match_ratio=float(src_match if np.isfinite(src_match) else np.nan),
                            stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
                            n_tails_considered=0,
                            n_tails_kept_after_rank=0,
                            n_unique_tails_kept=0,
                            n_unique_tails_promoted_to_B=0,
                            n_unique_tails_promoted_to_C=0,
                            best_score_per_tail_top5="[]",
                            seconds=0.0,
                            evals=0,
                        )
                    )
                    _append_csv_row(
                        hist,
                        dict(
                            timestamp_utc=datetime.now(timezone.utc).isoformat(),
                            run_id=run_dir.name,
                            profile_id=PROFILE,
                            fixture_id=tier.name,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            period=tier.period,
                            columns=tier.columns,
                            length=tier.length,
                            status="skipped_proven",
                            solve_threshold=float(SOLVE_MATCH_THRESHOLD),
                            stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
                            best_match_ratio=float(src_match if np.isfinite(src_match) else np.nan),
                            best_stage=src_stage,
                            stage_probe_match=np.nan,
                            stage_sub_match=np.nan,
                            stage_full_match=np.nan,
                            n_tails_considered=0,
                            n_tails_kept_after_rank=0,
                            n_unique_tails_kept=0,
                            n_unique_tails_promoted_to_B=0,
                            n_unique_tails_promoted_to_C=0,
                            best_score_per_tail_top5="[]",
                            total_seconds=0.0,
                            total_evals=0,
                            notes="autoskip_proven",
                        ),
                    )
                    history_rows_written += 1
                    done += 1
                    elapsed = time.time() - t0_all
                    eta = (elapsed / float(done)) * float(total - done) if done else 0.0
                    print(
                        f"[subcol] skip-proven tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"source_run={src_run if src_run else 'unknown'} best_match={float(src_match):.3f}",
                        flush=True,
                    )
                    print(
                        f"[subcol] {done}/{total} tier={tier.name} status=skipped_proven "
                        f"elapsed={_fmt_secs(elapsed)} eta={_fmt_secs(eta)}",
                        flush=True,
                    )
                    continue

                rng = np.random.default_rng(int(key_seed))
                key_len = int(tier.period * ALPHABET_SIZE + tier.columns)
                keyops = PeriodicStructuredMatrixKeyOps(
                    K=key_len,
                    period=tier.period,
                    A=ALPHABET_SIZE,
                    columns=tier.columns,
                )
                key_true = keyops.random(rng).astype(np.int16, copy=False)
                sub_len = int(tier.period * ALPHABET_SIZE)
                true_sub = key_true[:sub_len].astype(np.int16, copy=False)
                true_col = key_true[sub_len:].astype(np.int16, copy=False)

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
                    key_length=sub_len,
                    encoding_dir=direction,
                    wli_data=[],
                    device=Device.CPU,
                )
                full_cipher = PeriodicColumnarCipher(cfg_full)
                sub_cipher = PeriodicSubstitutionCipher(cfg_sub)

                ct_idx = full_cipher.encrypt_single(plaintext=pt_idx, key=key_true)
                ct_sub_oracle = undo_columnar_with_perm(ct_idx, perm=true_col.tolist())
                pt_oracle_stage = np.asarray(
                    sub_cipher.decrypt_single(ciphertext=ct_sub_oracle, key=true_sub),
                    dtype=np.uint8,
                ).reshape(-1)
                if not np.array_equal(pt_oracle_stage, np.asarray(pt_idx, dtype=np.uint8)):
                    raise RuntimeError(
                        f"[subcol] gate0 stage-order mismatch tier={tier.name} text={text_id} key_seed={key_seed}"
                    )

                scorer_sub = dict(SCORER_SUB, encoding_dir=direction)
                scorer_full = dict(SCORER_FULL, encoding_dir=direction)
                scorer_sub_runtime = build_scorer(cfg_sub, ScoringConfig(**scorer_sub))
                scorer_full_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_full))
                oracle_sub, oracle_sub_raw, obj_sub = _oracle_score_for_stage(
                    pt_idx=np.asarray(pt_idx, dtype=np.uint8),
                    wli=wli,
                    cipher_cfg=cfg_sub,
                    scorer_params=scorer_sub,
                )
                oracle_full, oracle_full_raw, obj_full = _oracle_score_for_stage(
                    pt_idx=np.asarray(pt_idx, dtype=np.uint8),
                    wli=wli,
                    cipher_cfg=cfg_full,
                    scorer_params=scorer_full,
                )
                print(
                    f"[subcol] objective tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"stage_sub={scorer_sub['objective']} stage_full={scorer_full['objective']}",
                    flush=True,
                )
                print(
                    "[subcol] oracle-score "
                    f"stage=sub model={obj_sub} "
                    f"(char={_weights_text(dict(SCORER_SUB.get('char_weights', {})))}"
                    f",wli={_weights_text(dict(SCORER_SUB.get('wli_weights', {})))},wb=1) "
                    f"score={oracle_sub:.6f} raw={oracle_sub_raw:.6f}",
                    flush=True,
                )
                print(
                    "[subcol] oracle-score "
                    f"stage=full model={obj_full} "
                    f"(char={_weights_text(dict(SCORER_FULL.get('char_weights', {})))}"
                    f",wli={_weights_text(dict(SCORER_FULL.get('wli_weights', {})))},wb=1) "
                    f"score={oracle_full:.6f} raw={oracle_full_raw:.6f}",
                    flush=True,
                )
                _print_stage_preview(
                    label="oracle",
                    pt=pt_idx.tolist(),
                    wli=wli,
                    scorer_wli=True,
                    match_ratio=1.0,
                )

                # Stage A: column probe
                t_probe = time.time()
                probe_rows: List[Dict[str, Any]] = []
                probe_evals = 0
                tails_promoted_to_B: set[Tuple[int, ...]] = set()
                tails_promoted_to_C: set[Tuple[int, ...]] = set()
                best_score_per_tail_top5 = "[]"
                perm_pool = enumerate_column_permutations(
                    int(tier.columns),
                    max_exact_columns=int(COL_EXACT_MAX_COLUMNS),
                    sample_size=int(COL_SAMPLE_SIZE_BY_COLUMNS.get(int(tier.columns), COL_SAMPLE_SIZE)),
                    seed=4000 + int(key_seed) + 101 * int(tier.period) + 7 * int(tier.columns),
                )
                keep_n = int(COL_KEEP_BY_COLUMNS.get(int(tier.columns), COL_KEEP))
                total_perm = len(perm_pool)
                mark_step = max(1, total_perm // 10)
                best_probe_match = float("-inf")
                best_probe_score = float("-inf")
                best_probe_preview = ""
                for i, perm in enumerate(perm_pool, start=1):
                    ct_sub = undo_columnar_with_perm(ct_idx, perm=perm)
                    seed_pool = make_periodic_seed_pool(
                        ct_sub.tolist(),
                        period=tier.period,
                        direction=direction.value,
                        seed=5200 + int(key_seed) + int(i),
                        n_block_seeds=int(SUB_PROBE_N_BLOCKS),
                        total_seeds=int(SUB_PROBE_TOTAL_SEEDS),
                        swaps_per_block=int(SUB_PROBE_SWAPS),
                        alphabet_size=ALPHABET_SIZE,
                    )
                    best_score_here = float("-inf")
                    best_match_here = float("-inf")
                    best_sub_here: List[int] | None = None
                    best_pt_here: List[int] | None = None
                    for sub_key in seed_pool[: int(SUB_PROBE_EVAL_KEYS)]:
                        sub_arr = np.asarray(sub_key, dtype=np.int16).reshape(-1)
                        if sub_arr.size != int(sub_len):
                            continue
                        pt_guess = np.asarray(
                            sub_cipher.decrypt_single(ciphertext=ct_sub, key=sub_arr),
                            dtype=np.uint8,
                        ).reshape(-1)
                        sc = float(scorer_sub_runtime.score(pt_guess, wli))
                        mr = float(base._match_ratio(pt_guess.tolist(), pt_idx.tolist()))
                        probe_evals += 1
                        if (sc > best_score_here) or (sc == best_score_here and mr > best_match_here):
                            best_score_here = sc
                            best_match_here = mr
                            best_sub_here = sub_arr.astype(int).tolist()
                            best_pt_here = pt_guess.astype(int).tolist()

                    if best_sub_here is None:
                        continue
                    probe_rows.append(
                        dict(
                            perm=tuple(int(x) for x in perm),
                            score=float(best_score_here),
                            match=float(best_match_here),
                            sub_key=list(best_sub_here),
                            plaintext=list(best_pt_here),
                        )
                    )
                    if best_match_here > best_probe_match:
                        best_probe_match = float(best_match_here)
                    if best_score_here > best_probe_score:
                        best_probe_score = float(best_score_here)
                        best_probe_preview = _preview_latin(best_pt_here, wli)
                    if (i % mark_step == 0) or (i == total_perm):
                        pct = int(round(100.0 * float(i) / float(max(1, total_perm))))
                        print(
                            f"[subcol colprobe {pct:3d}%] perms={i}/{total_perm} "
                            f"best_score={best_probe_score:.6f} best_match={best_probe_match:.3f} "
                            f"evals={probe_evals}",
                            flush=True,
                        )

                probe_rows = _stable_top_by_score(probe_rows, keep_n)
                n_tails_considered = int(total_perm)
                n_tails_kept_after_rank = int(len(probe_rows))
                n_unique_tails_kept = int(len({tuple(int(x) for x in r.get("perm", [])) for r in probe_rows}))
                top5_payload = [
                    dict(
                        tail=[int(x) for x in r.get("perm", [])],
                        score=round(float(r.get("score", float("nan"))), 6),
                        match=round(float(r.get("match", float("nan"))), 6),
                    )
                    for r in probe_rows[:5]
                ]
                best_score_per_tail_top5 = json.dumps(top5_payload, separators=(",", ":"))
                dt_probe = float(time.time() - t_probe)
                stage_probe_match = float(probe_rows[0]["match"]) if probe_rows else float("nan")
                stage_probe_score = float(probe_rows[0]["score"]) if probe_rows else float("nan")
                if probe_rows:
                    _print_stage_preview(
                        label="stageA_col_probe_best",
                        pt=probe_rows[0]["plaintext"],
                        wli=wli,
                        scorer_wli=True,
                        match_ratio=stage_probe_match,
                    )
                stages.append(
                    dict(
                        tier=tier.name,
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                        stage="stageA_col_probe",
                        score=stage_probe_score,
                        match_ratio=stage_probe_match,
                        stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
                        n_tails_considered=int(n_tails_considered),
                        n_tails_kept_after_rank=int(n_tails_kept_after_rank),
                        n_unique_tails_kept=int(n_unique_tails_kept),
                        n_unique_tails_promoted_to_B=0,
                        n_unique_tails_promoted_to_C=0,
                        best_score_per_tail_top5=str(best_score_per_tail_top5),
                        seconds=round(dt_probe, 3),
                        evals=int(probe_evals),
                        perms_tested=int(total_perm),
                        perms_kept=int(len(probe_rows)),
                        probe_preview=str(best_probe_preview),
                    )
                )
                print(
                    f"[subcol] stageA-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"perms={total_perm} kept={len(probe_rows)} score={stage_probe_score:.6f} "
                    f"match={stage_probe_match:.3f} evals={probe_evals} "
                    f"unique_kept={n_unique_tails_kept}",
                    flush=True,
                )

                # Stage B: substitution solve on top column candidates
                t_sub = time.time()
                stageB_rows: Dict[Tuple[int, ...], Dict[str, Any]] = {}
                stageB_evals = 0
                for j, cand in enumerate(probe_rows, start=1):
                    perm = tuple(int(x) for x in cand["perm"])
                    tails_promoted_to_B.add(perm)
                    ct_sub = undo_columnar_with_perm(ct_idx, perm=perm)
                    sub_seeds = make_periodic_seed_pool(
                        ct_sub.tolist(),
                        period=tier.period,
                        direction=direction.value,
                        seed=6100 + int(key_seed) + int(j),
                        n_block_seeds=int(SUB_REFINE_N_BLOCKS),
                        total_seeds=int(SUB_REFINE_TOTAL_SEEDS),
                        swaps_per_block=int(SUB_REFINE_SWAPS),
                        alphabet_size=ALPHABET_SIZE,
                    )
                    sol_sub = run(
                        text=ct_sub.tolist(),
                        cipher=by_name.cipher(
                            "periodic_substitution",
                            period=tier.period,
                            alphabet_size=ALPHABET_SIZE,
                        ),
                        key=KeySpec.periodic_substitution(period=tier.period, alphabet_size=ALPHABET_SIZE),
                        solver=SolverSpec.kaeding(**dict(SOLVER_SUB)),
                        scorer_params=scorer_sub,
                        wli_data=wli,
                        encoding_dir=direction,
                        telemetry_on=True,
                        force_no_wli=False,
                        initial_keys=sub_seeds,
                    )
                    ev_sub = int((getattr(sol_sub, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                    stageB_evals += ev_sub
                    top_subs = _extract_top_keys(sol_sub, limit=int(SUB_REFINE_TOP_KEYS_PER_PERM))
                    if not top_subs and getattr(sol_sub, "key", None) is not None:
                        top_subs = [list(map(int, list(sol_sub.key)))]
                    for sub_key in top_subs:
                        sub_arr = np.asarray(sub_key, dtype=np.int16).reshape(-1)
                        if sub_arr.size != int(sub_len):
                            continue
                        full_key = np.concatenate(
                            [sub_arr, np.asarray(perm, dtype=np.int16)],
                            axis=0,
                        ).astype(np.int16, copy=False)
                        pt_guess = np.asarray(
                            full_cipher.decrypt_single(ciphertext=ct_idx, key=full_key),
                            dtype=np.uint8,
                        ).reshape(-1)
                        sc = float(scorer_full_runtime.score(pt_guess, wli))
                        mr = float(base._match_ratio(pt_guess.tolist(), pt_idx.tolist()))
                        kt = tuple(int(x) for x in full_key.tolist())
                        prev = stageB_rows.get(kt)
                        if (prev is None) or (sc > float(prev.get("score", float("-inf")))):
                            stageB_rows[kt] = dict(
                                key=full_key.astype(int).tolist(),
                                score=float(sc),
                                match=float(mr),
                                plaintext=pt_guess.astype(int).tolist(),
                                perm=list(perm),
                            )
                stageB_ranked = _stable_top_by_score(
                    list(stageB_rows.values()),
                    int(STAGE3_INITIAL_KEYS_BY_COLUMNS.get(int(tier.columns), STAGE3_INITIAL_KEYS)),
                )
                dt_sub = float(time.time() - t_sub)
                stage_sub_match = float(stageB_ranked[0]["match"]) if stageB_ranked else float("nan")
                stage_sub_score = float(stageB_ranked[0]["score"]) if stageB_ranked else float("nan")
                if stageB_ranked:
                    _print_stage_preview(
                        label="stageB_sub_refine_best",
                        pt=stageB_ranked[0]["plaintext"],
                        wli=wli,
                        scorer_wli=True,
                        match_ratio=stage_sub_match,
                    )
                stages.append(
                    dict(
                        tier=tier.name,
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                        stage="stageB_sub_refine",
                        score=stage_sub_score,
                        match_ratio=stage_sub_match,
                        stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
                        n_tails_considered=int(n_tails_considered),
                        n_tails_kept_after_rank=int(n_tails_kept_after_rank),
                        n_unique_tails_kept=int(n_unique_tails_kept),
                        n_unique_tails_promoted_to_B=int(len(tails_promoted_to_B)),
                        n_unique_tails_promoted_to_C=0,
                        best_score_per_tail_top5=str(best_score_per_tail_top5),
                        seconds=round(dt_sub, 3),
                        evals=int(stageB_evals),
                        candidates=int(len(stageB_ranked)),
                    )
                )
                print(
                    f"[subcol] stageB-summary tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"candidates={len(stageB_ranked)} score={stage_sub_score:.6f} "
                    f"match={stage_sub_match:.3f} evals={stageB_evals} "
                    f"tails_promoted_B={len(tails_promoted_to_B)}",
                    flush=True,
                )

                # Stage C: full refine (optional if not solved in stage B)
                best_full_match = float(stage_sub_match if np.isfinite(stage_sub_match) else float("-inf"))
                best_full_score = float(stage_sub_score if np.isfinite(stage_sub_score) else float("-inf"))
                best_stage = "stageB_sub_refine"
                best_preview = _preview_latin(stageB_ranked[0]["plaintext"], wli) if stageB_ranked else ""
                stop_reason = "unsolved"
                full_evals = 0
                stage3_entry_mode = "none"
                stage3_band = "none"
                if np.isfinite(best_full_match) and best_full_match >= float(SOLVE_MATCH_THRESHOLD):
                    stop_reason = "solved_stageB"
                elif stageB_ranked:
                    entry_score = float(stageB_ranked[0]["score"])
                    full_gate = (
                        float(STAGE3_FULL_ENTRY_SCORE)
                        if STAGE3_FULL_ENTRY_SCORE is not None
                        else float("-inf")
                    )
                    probe_gate = (
                        float(STAGE3_PROBE_ENTRY_SCORE)
                        if STAGE3_PROBE_ENTRY_SCORE is not None
                        else float("-inf")
                    )
                    solver_full_cfg = dict(SOLVER_FULL)
                    if STAGE3_FULL_ENTRY_SCORE is None and STAGE3_PROBE_ENTRY_SCORE is None:
                        stage3_entry_mode = "full"
                    elif entry_score >= full_gate:
                        stage3_entry_mode = "full"
                    elif entry_score >= probe_gate:
                        stage3_entry_mode = "medium"
                    else:
                        stage3_entry_mode = "probe"

                    if stage3_entry_mode == "medium":
                        solver_full_cfg.update(
                            steps=max(1400, min(int(solver_full_cfg.get("steps", 0)), 2000)),
                            restarts=1,
                            plateau_rounds=min(int(solver_full_cfg.get("plateau_rounds", 0)), 220),
                            col_batch=min(int(solver_full_cfg.get("col_batch", 0)), 96),
                            inner_batch=min(int(solver_full_cfg.get("inner_batch", 0)), 128),
                        )
                    elif stage3_entry_mode == "probe":
                        solver_full_cfg.update(
                            steps=max(900, min(int(solver_full_cfg.get("steps", 0)), 1200)),
                            restarts=1,
                            plateau_rounds=min(int(solver_full_cfg.get("plateau_rounds", 0)), 160),
                            col_batch=min(int(solver_full_cfg.get("col_batch", 0)), 96),
                            inner_batch=min(int(solver_full_cfg.get("inner_batch", 0)), 128),
                        )

                    if STAGE3_USE_ORACLE_GUIDE_STOP:
                        relax = max(0.0, min(0.95, float(STAGE3_ORACLE_STOP_RELAX_FRACTION)))
                        s3_stop = float(oracle_full) - (abs(float(oracle_full)) * relax) + float(
                            STAGE3_ORACLE_STOP_MARGIN
                        )
                        s3_stop = min(0.999999, float(s3_stop))
                        solver_full_cfg["stop_score"] = float(s3_stop)

                    init_n = int(STAGE3_INITIAL_KEYS_BY_COLUMNS.get(int(tier.columns), STAGE3_INITIAL_KEYS))
                    promoted = [list(map(int, r["key"])) for r in stageB_ranked[: max(1, init_n // 2)]]
                    tails_promoted_to_C = {
                        tuple(int(x) for x in r.get("perm", []))
                        for r in stageB_ranked[: max(1, init_n // 2)]
                        if r.get("perm") is not None
                    }
                    init_all: List[List[int]] = []
                    for j, key_seed_init in enumerate(promoted):
                        init_all.extend(
                            _mutate_full_key(
                                key_seed_init,
                                period=tier.period,
                                columns=tier.columns,
                                seed=7300 + int(key_seed) + 97 * int(j),
                                n=max(1, int(np.ceil(float(init_n) / float(max(1, len(promoted)))))),
                            )
                        )
                    init3: List[List[int]] = []
                    seen3: set[Tuple[int, ...]] = set()
                    for k in init_all:
                        t = tuple(int(x) for x in k)
                        if t in seen3:
                            continue
                        seen3.add(t)
                        init3.append(list(map(int, k)))
                        if len(init3) >= init_n:
                            break
                    stage3_band = (
                        "full_budget"
                        if stage3_entry_mode == "full"
                        else ("medium_budget" if stage3_entry_mode == "medium" else "probe_budget")
                    )
                    print(
                        f"[subcol] stageC-stop tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"entry_mode={stage3_entry_mode} entry_score={entry_score:.6f} "
                        f"init_keys={len(init3)} steps={solver_full_cfg.get('steps')} "
                        f"restarts={solver_full_cfg.get('restarts')} stop_score={solver_full_cfg.get('stop_score', 'none')} "
                        f"plateau_rounds={solver_full_cfg.get('plateau_rounds')}",
                        flush=True,
                    )
                    t_full = time.time()
                    sol_full = run(
                        text=ct_idx.tolist(),
                        cipher=by_name.cipher(
                            "periodic_columnar",
                            period=tier.period,
                            columns=tier.columns,
                            order=ORDER,
                            alphabet_size=ALPHABET_SIZE,
                        ),
                        key=KeySpec.periodic_columnar(
                            period=tier.period,
                            columns=tier.columns,
                            alphabet_size=ALPHABET_SIZE,
                        ),
                        solver=SolverSpec.kaeding(**solver_full_cfg),
                        scorer_params=scorer_full,
                        wli_data=wli,
                        encoding_dir=direction,
                        telemetry_on=True,
                        force_no_wli=False,
                        initial_keys=init3,
                    )
                    dt_full = float(time.time() - t_full)
                    full_evals = int((getattr(sol_full, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                    pt_full = np.asarray(getattr(sol_full, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                    m_full = float(base._match_ratio(pt_full.tolist(), pt_idx.tolist()))
                    s_full = float(getattr(sol_full, "score", float("nan")))
                    if pt_full.size > 0:
                        _print_stage_preview(
                            label="stageC_full_refine",
                            pt=pt_full.tolist(),
                            wli=wli,
                            scorer_wli=True,
                            match_ratio=float(m_full),
                        )
                    stages.append(
                        dict(
                            tier=tier.name,
                            text_id=int(text_id),
                            key_seed=int(key_seed),
                            stage="stageC_full_refine",
                            score=float(s_full),
                            match_ratio=float(m_full),
                            stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
                            n_tails_considered=int(n_tails_considered),
                            n_tails_kept_after_rank=int(n_tails_kept_after_rank),
                            n_unique_tails_kept=int(n_unique_tails_kept),
                            n_unique_tails_promoted_to_B=int(len(tails_promoted_to_B)),
                            n_unique_tails_promoted_to_C=int(len(tails_promoted_to_C)),
                            best_score_per_tail_top5=str(best_score_per_tail_top5),
                            seconds=round(dt_full, 3),
                            evals=int(full_evals),
                            stage3_entry_mode=str(stage3_entry_mode),
                            stage3_band=str(stage3_band),
                        )
                    )
                    if (m_full > best_full_match) or (
                        abs(m_full - best_full_match) <= 1e-12 and s_full > best_full_score
                    ):
                        best_full_match = float(m_full)
                        best_full_score = float(s_full)
                        best_stage = "stageC_full_refine"
                        best_preview = _preview_latin(pt_full.tolist(), wli) if pt_full.size > 0 else best_preview
                    if np.isfinite(m_full) and m_full >= float(SOLVE_MATCH_THRESHOLD):
                        stop_reason = "solved_stageC"
                    elif (m_full - (stage_sub_match if np.isfinite(stage_sub_match) else 0.0)) <= float(STALL_DELTA):
                        stop_reason = "stalled_no_improve"
                    else:
                        stop_reason = "completed_pipeline"

                status = "solved" if best_full_match >= float(SOLVE_MATCH_THRESHOLD) else (
                    "stalled" if stop_reason == "stalled_no_improve" else "unsolved"
                )
                dt_i = float(time.time() - t0_i)
                total_evals = int(probe_evals + stageB_evals + full_evals)
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
                        stop_reason=str(stop_reason),
                        solve_threshold=float(SOLVE_MATCH_THRESHOLD),
                        best_stage=str(best_stage),
                        best_match_ratio=float(best_full_match),
                        best_objective_score=float(best_full_score),
                        stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
                        stage_probe_match=float(stage_probe_match if np.isfinite(stage_probe_match) else np.nan),
                        stage_sub_match=float(stage_sub_match if np.isfinite(stage_sub_match) else np.nan),
                        stage_full_match=float(best_full_match if best_stage == "stageC_full_refine" else np.nan),
                        n_tails_considered=int(n_tails_considered),
                        n_tails_kept_after_rank=int(n_tails_kept_after_rank),
                        n_unique_tails_kept=int(n_unique_tails_kept),
                        n_unique_tails_promoted_to_B=int(len(tails_promoted_to_B)),
                        n_unique_tails_promoted_to_C=int(len(tails_promoted_to_C)),
                        best_score_per_tail_top5=str(best_score_per_tail_top5),
                        stage3_entry_mode=str(stage3_entry_mode),
                        stage3_band=str(stage3_band),
                        total_seconds=round(dt_i, 3),
                        total_evals=int(total_evals),
                        preview_best_latin=str(best_preview),
                    )
                )

                if best_full_match > float(best_global["match"]):
                    best_global["match"] = float(best_full_match)
                    best_global["tier"] = str(tier.name)
                    best_global["text_id"] = int(text_id)
                    best_global["key_seed"] = int(key_seed)
                    best_global["stage"] = str(best_stage)
                    best_global["preview"] = str(best_preview)

                summary_ckpt = _build_summary(TIERS, instances)
                (run_dir / "instances.json").write_text(json.dumps(instances, indent=2), encoding="utf-8")
                (run_dir / "stages.json").write_text(json.dumps(stages, indent=2), encoding="utf-8")
                (run_dir / "summary.json").write_text(json.dumps(summary_ckpt, indent=2), encoding="utf-8")
                _write_csv_rows(run_dir / "instances.csv", instances)
                _write_csv_rows(run_dir / "stages.csv", stages)

                hist_row = dict(
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    run_id=run_dir.name,
                    profile_id=PROFILE,
                    fixture_id=tier.name,
                    text_id=int(text_id),
                    key_seed=int(key_seed),
                    period=tier.period,
                    columns=tier.columns,
                    length=tier.length,
                    status=status,
                    solve_threshold=float(SOLVE_MATCH_THRESHOLD),
                    stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
                    best_match_ratio=float(best_full_match),
                    best_stage=str(best_stage),
                    stage_probe_match=float(stage_probe_match if np.isfinite(stage_probe_match) else np.nan),
                    stage_sub_match=float(stage_sub_match if np.isfinite(stage_sub_match) else np.nan),
                    stage_full_match=float(best_full_match if best_stage == "stageC_full_refine" else np.nan),
                    n_tails_considered=int(n_tails_considered),
                    n_tails_kept_after_rank=int(n_tails_kept_after_rank),
                    n_unique_tails_kept=int(n_unique_tails_kept),
                    n_unique_tails_promoted_to_B=int(len(tails_promoted_to_B)),
                    n_unique_tails_promoted_to_C=int(len(tails_promoted_to_C)),
                    best_score_per_tail_top5=str(best_score_per_tail_top5),
                    total_seconds=round(dt_i, 3),
                    total_evals=int(total_evals),
                    notes=str(stop_reason),
                )
                _append_csv_row(hist, hist_row)
                history_rows_written += 1

                if status == "solved":
                    stage_rows_instance = [
                        dict(s)
                        for s in stages
                        if s.get("tier") == tier.name
                        and int(s.get("text_id", -1)) == int(text_id)
                        and int(s.get("key_seed", -1)) == int(key_seed)
                    ]
                    solved_payload = dict(
                        timestamp_utc=datetime.now(timezone.utc).isoformat(),
                        run_id=run_dir.name,
                        profile=PROFILE,
                        mode=PIPELINE_RUN_MODE,
                        stageab_scorer_profile=str(STAGEAB_SCORER_PROFILE),
                        config=run_manifest,
                        instance=dict(instances[-1]),
                        stages=stage_rows_instance,
                        io=dict(
                            ciphertext_idx=[int(x) for x in np.asarray(ct_idx, dtype=np.int64).reshape(-1).tolist()],
                            oracle_plaintext_idx=[int(x) for x in np.asarray(pt_idx, dtype=np.int64).reshape(-1).tolist()],
                            wli_data=[[int(a), int(b)] for a, b in wli],
                        ),
                    )
                    with solved_jsonl.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(solved_payload, ensure_ascii=False) + "\n")
                    solved_path = solved_dir / f"{tier.name}__text{text_id}__seed{key_seed}.json"
                    solved_path.write_text(json.dumps(solved_payload, indent=2), encoding="utf-8")
                    print(
                        f"[subcol] proven-solved-write tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"jsonl={solved_jsonl.relative_to(root)} file={solved_path.relative_to(root)}",
                        flush=True,
                    )

                done += 1
                elapsed = time.time() - t0_all
                eta = (elapsed / float(done)) * float(total - done) if done else 0.0
                print(
                    f"[subcol] {done}/{total} tier={tier.name} status={status} best_match={float(best_full_match):.3f} "
                    f"run={_fmt_secs(dt_i)} elapsed={_fmt_secs(elapsed)} eta={_fmt_secs(eta)}",
                    flush=True,
                )
                if best_preview:
                    print(
                        f"[subcol] best-instance-preview tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"text=\"{best_preview}\"",
                        flush=True,
                    )

                now = time.time()
                if (now - last_hb) >= HEARTBEAT_SECONDS:
                    print(
                        f"[subcol] heartbeat elapsed={_fmt_secs(now - t0_all)} done={done}/{total} "
                        f"global_best_match={float(best_global['match']):.3f} "
                        f"tier={best_global['tier']} text={best_global['text_id']} key_seed={best_global['key_seed']} "
                        f"stage={best_global['stage']} preview=\"{best_global['preview']}\"",
                        flush=True,
                    )
                    last_hb = now

    elapsed_total = time.time() - t0_all
    summary = _build_summary(TIERS, instances)
    (run_dir / "instances.json").write_text(json.dumps(instances, indent=2), encoding="utf-8")
    (run_dir / "stages.json").write_text(json.dumps(stages, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_csv_rows(run_dir / "instances.csv", instances)
    _write_csv_rows(run_dir / "stages.csv", stages)
    print(f"[subcol] completed in {_fmt_secs(elapsed_total)}", flush=True)
    print(f"[subcol] reports: {run_dir.relative_to(root)}", flush=True)
    print(
        f"[subcol] history: {hist.relative_to(root)} rows_written={history_rows_written}",
        flush=True,
    )


if __name__ == "__main__":
    main()
