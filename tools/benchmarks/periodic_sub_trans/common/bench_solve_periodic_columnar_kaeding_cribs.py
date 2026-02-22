"""
Focused benchmark: Kaeding + hard-crib profiles for periodic-columnar.

Why this exists
---------------
- We need an auditable crib benchmark that starts with easier tiers (period=7)
  and includes period=13.
- We want to measure both help and overhead from hard-reject cribs.
- We keep this separate from the main solve benchmark to avoid mode drift.
"""

from __future__ import annotations

import csv
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, run
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.hard_crib import normalize_hard_crib_config
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, ObjectiveFamily, ObjectiveSpec, ScorerImpl, SeMode, Stat
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
from rune_decrypter_prime.data.wordlists.loaders import load_short_word_csv
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils_periodic_columnar import SeedPlan, generate_seed_keys_periodic_columnar


ALPHABET_SIZE = 29
ORDER = "col_then_sub"
RANDOM_KEYS_SANITY = 24

# New focused matrix (no CLI)
BENCH_PROFILE = "cribs_overnight_8h"
# Optional resume path (hardcoded, no CLI). Set to a previous run folder path.
RESUME_FROM_RUN_DIR: str | None = None

LONG14_DISAPPOINTMENT = [23, 10, 15, 24, 13, 13, 3, 10, 9, 16, 19, 18, 9, 16]
SHORT_WORD_LENGTHS = (1, 2, 3)


@dataclass(frozen=True)
class Tier:
    name: str
    period: int
    columns: int
    length: int


@dataclass(frozen=True)
class Mode:
    name: str
    enforce_long14_word: bool = False
    fixed_from_long14_offsets: Tuple[int, ...] = ()
    short_global_lengths: Tuple[int, ...] = ()
    short_per_word_budget: Tuple[Tuple[int, int], ...] = ()
    # If >0, run a cheap random-key precheck and skip this mode when pass-rate is below threshold.
    min_random_pass_rate: float = 0.0
    use_seed_pool: bool = False
    seed_filter_by_crib: bool = False
    seed_filter_min_keep: int = 0
    seed_filter_backfill: int = 0


# Cheap mode viability gate (to avoid spending minutes on known over-pruned modes).
PRECHECK_RANDOM_KEYS = 256
SEED_POOL_N = 64
SEED_POOL_PLAN = SeedPlan(
    n_block_seeds=6,
    n_tail_seeds=6,
    n_starts=24,
    refine_steps=220,
    tail_move_prob=0.45,
    temp_start=0.06,
    temp_end=0.008,
)


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in [cur.parent, *cur.parents]:
        if (parent / "src" / "rune_decrypter_prime").exists():
            return parent
    return cur.parents[0]


def _git_short_hash() -> str:
    try:
        value = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=_repo_root()).decode().strip()
        return value or "nogit"
    except Exception:
        return "nogit"


def _format_seconds(total_s: float) -> str:
    s = float(max(0.0, total_s))
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60.0
    if h > 0:
        return f"{h}h{m:02d}m"
    if m > 0:
        return f"{m}m{sec:04.1f}s"
    return f"{sec:.1f}s"


def _write_csv(path: Path, rows: List[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in keys})


def _percentiles(values: Iterable[float], pcts: Tuple[int, ...] = (10, 25, 50, 75, 90)) -> Dict[str, float]:
    arr = np.asarray(list(values), dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {f"p{p}": float("nan") for p in pcts}
    out: Dict[str, float] = {f"p{p}": float(np.percentile(arr, p)) for p in pcts}
    out["mean"] = float(np.mean(arr))
    out["std"] = float(np.std(arr))
    return out


def _compute_summary(rows: List[dict]) -> dict:
    out: dict[str, list[dict]] = {}
    groups: Dict[Tuple[str, str], List[dict]] = {}
    for r in rows:
        groups.setdefault((str(r["tier"]), str(r["mode"])), []).append(r)
    for (tier, mode), items in groups.items():
        out.setdefault(tier, []).append(
            {
                "tier": tier,
                "mode": mode,
                "n": len(items),
                "match_ratio": _percentiles(float(x["match_ratio"]) for x in items),
                "score": _percentiles(float(x["sol_score"]) for x in items),
                "seconds": _percentiles(float(x["seconds"]) for x in items),
                "evals": _percentiles(float(x.get("evals", 0.0)) for x in items),
                "evals_per_second": _percentiles(float(x.get("evals_per_second", float("nan"))) for x in items),
                "crib_reject_total": _percentiles(float(x.get("crib_reject_total", 0.0)) for x in items),
                "crib_all_rejected_batches": _percentiles(float(x.get("crib_all_rejected_batches", 0.0)) for x in items),
                "crib_reject_rate": _percentiles(float(x.get("crib_reject_rate", float("nan"))) for x in items),
                "precheck_pass_rate": _percentiles(float(x.get("precheck_pass_rate", float("nan"))) for x in items),
                "seed_candidates_total": _percentiles(float(x.get("seed_candidates_total", 0.0)) for x in items),
                "seed_candidates_pass": _percentiles(float(x.get("seed_candidates_pass", 0.0)) for x in items),
                "seed_candidates_used": _percentiles(float(x.get("seed_candidates_used", 0.0)) for x in items),
                "rate_all_rejected": float(
                    np.mean(np.asarray([int(x.get("hard_crib_all_rejected", 0)) for x in items], dtype=np.float64))
                ),
                "rate_crib_enabled": float(
                    np.mean(np.asarray([int(x.get("crib_enabled_runtime", 0)) for x in items], dtype=np.float64))
                ),
                "rate_skipped_overprune": float(
                    np.mean(np.asarray([int(x.get("skipped_overprune", 0)) for x in items], dtype=np.float64))
                ),
                "rate_seed_filter_fallback": float(
                    np.mean(np.asarray([int(x.get("seed_filter_fallback_used", 0)) for x in items], dtype=np.float64))
                ),
            }
        )
    return {"tiers": out}


def _write_reports(rows: List[dict], summary: dict, *, manifest: dict) -> Path:
    root = _repo_root()
    out_root = root / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"{stamp}__bench_solve_cribs__{_git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "instances.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_csv(run_dir / "instances.csv", rows)
    return run_dir


def _create_run_dir() -> Path:
    root = _repo_root()
    out_root = root / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"{stamp}__bench_solve_cribs__{_git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _checkpoint(run_dir: Path, *, rows: List[dict], manifest: dict) -> dict:
    summary = _compute_summary(rows)
    _atomic_write_text(run_dir / "instances.json", json.dumps(rows, indent=2))
    _atomic_write_text(run_dir / "summary.json", json.dumps(summary, indent=2))
    _atomic_write_text(run_dir / "run_manifest.json", json.dumps(manifest, indent=2))
    _write_csv(run_dir / "instances.csv", rows)
    return summary


def _row_id(row: dict) -> tuple[str, str, int, int]:
    return (
        str(row["tier"]),
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
        raise RuntimeError(f"[bench_cribs] resume file is not a row list: {p}")
    out: List[dict] = []
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            raise RuntimeError(f"[bench_cribs] resume row {i} is not an object")
        out.append(row)
    return out


def _require_assets(direction: Direction, *, ns: Tuple[int, ...]) -> Path:
    from tests.scoring._helpers.lm_test_guard import require_full_lm_assets

    root, _ = require_full_lm_assets(
        models=("char",),
        modes=(direction.value,),
        poses=("nose",),
        ns=ns,
        ecdf_stats=("logp",),
    )
    return root


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


def _encode_long_plaintext(direction: Direction) -> tuple[np.ndarray, np.ndarray]:
    pt_idx, wli, _runes = Runeglish.encode_english_to_runes(long_plaintext_string.strip(), direction=direction.value)
    pt_u8 = np.asarray(pt_idx, dtype=np.uint8)
    wli_u8 = np.asarray(wli, dtype=np.uint8)
    if wli_u8.ndim != 2 or wli_u8.shape[1] != 2 or wli_u8.shape[0] != pt_u8.size:
        raise RuntimeError("[bench_cribs] encoded WLI malformed")
    return pt_u8, wli_u8


def _tile_stream(pt_base: np.ndarray, wli_base: np.ndarray, needed: int) -> tuple[np.ndarray, np.ndarray]:
    if needed <= pt_base.size:
        return pt_base, wli_base
    reps = int(np.ceil(float(needed) / float(pt_base.size)))
    pt_t = np.tile(pt_base, reps)
    wli_t = np.tile(wli_base, (reps, 1))
    return np.ascontiguousarray(pt_t, dtype=np.uint8), np.ascontiguousarray(wli_t, dtype=np.uint8)


def _slice_word_aligned(
    pt_base: np.ndarray,
    wli_base: np.ndarray,
    *,
    length: int,
    offset_hint: int,
) -> tuple[np.ndarray, List[List[int]], int]:
    if length <= 0:
        raise ValueError("length must be > 0")
    max_scan = int(pt_base.size * 2)
    pt_t, wli_t = _tile_stream(pt_base, wli_base, needed=offset_hint + length + max_scan + 4)
    start = int(offset_hint)
    end_limit = int(min(start + max_scan, pt_t.size - length))
    for s in range(start, end_limit + 1):
        if int(wli_t[s, 0]) != 0:
            continue
        e = s + length - 1
        pos_e = int(wli_t[e, 0])
        len_e = int(wli_t[e, 1])
        if pos_e != len_e - 1:
            continue
        pt = np.ascontiguousarray(pt_t[s : s + length], dtype=np.uint8)
        wli = [[int(a), int(b)] for a, b in wli_t[s : s + length].tolist()]
        return pt, wli, int(s)
    raise RuntimeError(f"Unable to find word-aligned slice length={length} near offset={offset_hint}")


def _word_spans_from_wli(wli: Sequence[Sequence[int]]) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    i = 0
    n = int(len(wli))
    while i < n:
        pos, ln = int(wli[i][0]), int(wli[i][1])
        if pos != 0 or ln <= 0:
            raise ValueError("malformed WLI")
        end = i + ln
        if end > n:
            raise ValueError("malformed WLI (length overflow)")
        spans.append((i, end))
        i = end
    return spans


def _match_ratio(a: Sequence[int], b: Sequence[int]) -> float:
    aa = np.asarray(a, dtype=np.int64).reshape(-1)
    bb = np.asarray(b, dtype=np.int64).reshape(-1)
    n = min(int(aa.size), int(bb.size))
    if n <= 0:
        return 0.0
    return float(np.mean(aa[:n] == bb[:n]))


def _load_short_allowed_by_len(direction: Direction, lengths: Sequence[int] = SHORT_WORD_LENGTHS) -> Dict[int, List[List[int]]]:
    out: Dict[int, List[List[int]]] = {}
    for L in lengths:
        tbl = load_short_word_csv(length=int(L), direction=direction)
        words: List[List[int]] = []
        seen: set[tuple[int, ...]] = set()
        for latin in tbl.keys():
            idx, _wli, _runes = Runeglish.encode_english_to_runes(latin, direction=direction.value)
            seq = tuple(int(v) for v in idx)
            if len(seq) != int(L):
                continue
            if seq in seen:
                continue
            seen.add(seq)
            words.append([int(v) for v in seq])
        if not words:
            raise RuntimeError(f"[bench_cribs] no words loaded for length {L}")
        out[int(L)] = words
    return out


def _find_unique_word_index(
    *,
    pt_idx: np.ndarray,
    wli: Sequence[Sequence[int]],
    target: Sequence[int],
) -> Tuple[int, int, int]:
    spans = _word_spans_from_wli(wli)
    tgt = tuple(int(v) for v in target)
    hits: List[Tuple[int, int, int]] = []
    for wi, (s, e) in enumerate(spans):
        seq = tuple(int(v) for v in pt_idx[s:e].tolist())
        if seq == tgt:
            hits.append((wi, s, e))
    if len(hits) != 1:
        raise ValueError(f"[bench_cribs] expected exactly one long14 hit, found {len(hits)}")
    return hits[0]


def _pick_short_word_indices(
    *,
    wli: Sequence[Sequence[int]],
    budget_by_len: Dict[int, int],
) -> Dict[int, List[int]]:
    spans = _word_spans_from_wli(wli)
    by_len: Dict[int, List[int]] = {}
    for wi, (s, e) in enumerate(spans):
        by_len.setdefault(int(e - s), []).append(int(wi))

    picked: Dict[int, List[int]] = {}
    for L, budget in sorted((int(k), int(v)) for k, v in budget_by_len.items()):
        candidates = by_len.get(L, [])
        if budget <= 0 or not candidates:
            continue
        k = min(int(budget), len(candidates))
        if k == len(candidates):
            picked[L] = list(candidates)
            continue
        # Deterministic spread across the slice.
        idxs = np.linspace(0, len(candidates) - 1, num=k, dtype=np.int64)
        chosen = [int(candidates[int(i)]) for i in idxs.tolist()]
        # Preserve order and drop accidental duplicates from linspace rounding.
        uniq: List[int] = []
        seen: set[int] = set()
        for wi in chosen:
            if wi in seen:
                continue
            seen.add(wi)
            uniq.append(wi)
        picked[L] = uniq
    return picked


def build_hard_crib_payload(
    *,
    mode: Mode,
    direction: Direction,
    pt_idx: np.ndarray,
    wli: Sequence[Sequence[int]],
    short_allowed_by_len: Dict[int, List[List[int]]],
) -> tuple[dict | None, dict]:
    meta = {
        "hard_crib_enabled_requested": 0,
        "hard_crib_rule_fixed_chars": 0,
        "hard_crib_rule_per_word": 0,
        "hard_crib_rule_global_len": 0,
        "hard_crib_long14_word_index": -1,
        "hard_crib_short_per_word_count": 0,
        "hard_crib_mode_random_gate": float(mode.min_random_pass_rate),
    }
    if mode.name == "none":
        return None, meta

    cfg: Dict[str, Any] = {
        "enabled": True,
        "mode": "hard",
        "require_wli_for_word_rules": True,
        "fixed_chars": {},
        "per_word_allowed": {},
        "global_allowed_by_len": {},
    }

    if mode.short_global_lengths:
        for L in mode.short_global_lengths:
            cfg["global_allowed_by_len"][int(L)] = short_allowed_by_len[int(L)]

    if mode.short_per_word_budget:
        budget_by_len = {int(k): int(v) for k, v in mode.short_per_word_budget}
        picked = _pick_short_word_indices(wli=wli, budget_by_len=budget_by_len)
        for L, indices in picked.items():
            allowed = short_allowed_by_len.get(int(L))
            if not allowed:
                continue
            for wi in indices:
                cfg["per_word_allowed"][int(wi)] = allowed
                meta["hard_crib_short_per_word_count"] = int(meta["hard_crib_short_per_word_count"]) + 1

    need_long14_lookup = bool(mode.enforce_long14_word) or bool(mode.fixed_from_long14_offsets)
    if need_long14_lookup:
        wi, s, e = _find_unique_word_index(pt_idx=pt_idx, wli=wli, target=LONG14_DISAPPOINTMENT)
        meta["hard_crib_long14_word_index"] = int(wi)
        if mode.enforce_long14_word:
            cfg["per_word_allowed"][int(wi)] = [list(LONG14_DISAPPOINTMENT)]
        for off in mode.fixed_from_long14_offsets:
            pos = int(s + int(off))
            if pos < 0 or pos >= int(pt_idx.size):
                raise ValueError(f"[bench_cribs] fixed offset outside plaintext: off={off}")
            cfg["fixed_chars"][pos] = [int(pt_idx[pos])]

    norm = normalize_hard_crib_config(cfg)
    if norm is None or not norm.enabled or not norm.has_any_rules:
        raise RuntimeError("[bench_cribs] crib mode produced no effective rules")
    payload = norm.asdict()
    meta["hard_crib_enabled_requested"] = 1
    meta["hard_crib_rule_fixed_chars"] = len(payload.get("fixed_chars", {}) or {})
    meta["hard_crib_rule_per_word"] = len(payload.get("per_word_allowed", {}) or {})
    meta["hard_crib_rule_global_len"] = len(payload.get("global_allowed_by_len", {}) or {})
    return payload, meta


def _candidate_passes_hard_crib(
    *,
    pt: np.ndarray,
    wli: Sequence[Sequence[int]],
    hard_crib: dict,
) -> bool:
    cfg = normalize_hard_crib_config(hard_crib)
    if cfg is None or not cfg.enabled or not cfg.has_any_rules:
        return True
    arr = np.asarray(pt, dtype=np.uint8).reshape(-1)
    for pos, allowed in (cfg.fixed_chars or {}).items():
        p = int(pos)
        if p < 0 or p >= arr.size:
            return False
        if int(arr[p]) not in {int(v) for v in allowed}:
            return False

    spans = _word_spans_from_wli(wli)
    for idx, allowed_words in (cfg.per_word_allowed or {}).items():
        i = int(idx)
        if i < 0 or i >= len(spans):
            return False
        s, e = spans[i]
        cand = tuple(int(v) for v in arr[s:e].tolist())
        allowed = {tuple(int(x) for x in row) for row in allowed_words}
        if cand not in allowed:
            return False
    for s, e in spans:
        L = int(e - s)
        allowed_words = (cfg.global_allowed_by_len or {}).get(L)
        if not allowed_words:
            continue
        cand = tuple(int(v) for v in arr[s:e].tolist())
        allowed = {tuple(int(x) for x in row) for row in allowed_words}
        if cand not in allowed:
            return False
    return True


def _estimate_random_pass_rate(
    *,
    cipher: PeriodicColumnarCipher,
    ciphertext: np.ndarray,
    keyops: PeriodicStructuredMatrixKeyOps,
    rng: np.random.Generator,
    wli: Sequence[Sequence[int]],
    hard_crib: dict,
    n_samples: int = PRECHECK_RANDOM_KEYS,
) -> float:
    if n_samples <= 0:
        return float("nan")
    passed = 0
    for _ in range(int(n_samples)):
        k = keyops.random(rng).astype(np.int16, copy=False)
        pt = cipher.decrypt_single(ciphertext=ciphertext, key=k)
        if _candidate_passes_hard_crib(pt=np.asarray(pt, dtype=np.uint8), wli=wli, hard_crib=hard_crib):
            passed += 1
    return float(passed) / float(max(1, int(n_samples)))


def _build_seed_pool_cfg(*, direction: Direction, model_root: Path) -> ScoringConfig:
    return ScoringConfig(
        model_root=model_root,
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        se_mode=SeMode.NOSE,
        encoding_dir=direction,
        include_char=True,
        use_word_breaks=False,
        char_weights={3: 0.5, 4: 0.5},
        wli_weights={},
        impl=ScorerImpl.NUMPY,
    )


def _make_seed_keys(
    *,
    ciphertext: np.ndarray,
    period: int,
    columns: int,
    direction: Direction,
    seed: int,
    scoring_cfg: ScoringConfig,
    n_keys: int = SEED_POOL_N,
) -> List[List[int]]:
    return generate_seed_keys_periodic_columnar(
        ciphertext,
        period=int(period),
        columns=int(columns),
        order=ORDER,
        direction=direction,
        seed=int(seed),
        scoring_cfg=scoring_cfg,
        n_keys=int(n_keys),
        plan=SEED_POOL_PLAN,
        refine=True,
    )


def _filter_seed_keys_by_crib(
    *,
    seed_keys: Sequence[Sequence[int]],
    cipher: PeriodicColumnarCipher,
    ciphertext: np.ndarray,
    wli: Sequence[Sequence[int]],
    hard_crib: dict,
    min_keep: int,
    backfill: int,
) -> tuple[List[List[int]], int]:
    passed: List[List[int]] = []
    failed: List[List[int]] = []
    for k in seed_keys:
        key = np.asarray(k, dtype=np.int16)
        pt = cipher.decrypt_single(ciphertext=ciphertext, key=key)
        if _candidate_passes_hard_crib(pt=np.asarray(pt, dtype=np.uint8), wli=wli, hard_crib=hard_crib):
            passed.append([int(v) for v in key.tolist()])
        else:
            failed.append([int(v) for v in key.tolist()])
    selected = list(passed)
    if len(selected) < int(min_keep) and int(backfill) > 0:
        need = min(int(backfill), max(0, int(min_keep) - len(selected)), len(failed))
        selected.extend(failed[:need])
    if not selected:
        selected = failed[: min(8, len(failed))]
    return selected, int(len(passed))


def _preflight_oracle_crib(
    *,
    hard_crib: dict | None,
    pt_true: np.ndarray,
    wli: Sequence[Sequence[int]],
) -> None:
    if not hard_crib:
        return
    cfg = normalize_hard_crib_config(hard_crib)
    if cfg is None or not cfg.enabled or not cfg.has_any_rules:
        return
    pt = np.asarray(pt_true, dtype=np.uint8).reshape(-1)
    for pos, allowed in (cfg.fixed_chars or {}).items():
        p = int(pos)
        if p < 0 or p >= pt.size or int(pt[p]) not in {int(v) for v in allowed}:
            raise RuntimeError(f"[bench_cribs] oracle violates fixed_chars at pos={p}")
    spans = _word_spans_from_wli(wli)
    for idx, allowed_words in (cfg.per_word_allowed or {}).items():
        i = int(idx)
        if i < 0 or i >= len(spans):
            raise RuntimeError(f"[bench_cribs] per_word index out of range: {i}")
        s, e = spans[i]
        cand = tuple(int(v) for v in pt[s:e].tolist())
        allowed = {tuple(int(x) for x in row) for row in allowed_words}
        if cand not in allowed:
            raise RuntimeError(f"[bench_cribs] oracle violates per_word_allowed idx={i}")
    for s, e in spans:
        L = int(e - s)
        allowed_words = (cfg.global_allowed_by_len or {}).get(L)
        if not allowed_words:
            continue
        cand = tuple(int(v) for v in pt[s:e].tolist())
        allowed = {tuple(int(x) for x in row) for row in allowed_words}
        if cand not in allowed:
            raise RuntimeError(f"[bench_cribs] oracle violates global_allowed_by_len[{L}]")


def _solver_small() -> SolverSpec:
    return SolverSpec.kaeding(
        steps=220,
        restarts=2,
        inner_batch=128,
        col_every=8,
        col_batch=48,
        slip_every=60,
        slip_blocks=1,
        slip_policy="stall",
        stall_rounds=220,
        stall_slip_limit=3,
        slip_swaps=36,
        use_raw_score=True,
        top_k=32,
        progress_pct=10,
        print_progress=True,
        seed=2026,
    )


def _solver_overnight() -> SolverSpec:
    return SolverSpec.kaeding(
        steps=320,
        restarts=3,
        inner_batch=128,
        col_every=8,
        col_batch=48,
        slip_every=60,
        slip_blocks=1,
        slip_policy="stall",
        stall_rounds=240,
        stall_slip_limit=3,
        slip_swaps=40,
        use_raw_score=True,
        top_k=32,
        progress_pct=10,
        print_progress=True,
        seed=2026,
    )


def _profile() -> tuple[List[Tier], List[Mode], List[int], List[int], SolverSpec]:
    p = str(BENCH_PROFILE).strip().lower()
    tiers = [
        Tier(name="calib_p7_c5_l400", period=7, columns=5, length=400),
        Tier(name="goal_p13_c13_l300", period=13, columns=13, length=300),
    ]
    if p == "cribs_p7_p13_small":
        modes = [
            Mode(name="none"),
            Mode(name="crib_anchor1", fixed_from_long14_offsets=(0,)),
            Mode(
                name="crib_anchor1_seedpool",
                fixed_from_long14_offsets=(0,),
                use_seed_pool=True,
            ),
            Mode(
                name="crib_anchor1_seedfilter",
                fixed_from_long14_offsets=(0,),
                use_seed_pool=True,
                seed_filter_by_crib=True,
                seed_filter_min_keep=8,
                seed_filter_backfill=8,
            ),
        ]
        return tiers, modes, [211], [111, 222], _solver_small()
    if p == "cribs_quick_30m":
        modes = [
            Mode(name="none"),
            Mode(name="crib_anchor1", fixed_from_long14_offsets=(0,)),
            Mode(
                name="crib_anchor1_seedpool",
                fixed_from_long14_offsets=(0,),
                use_seed_pool=True,
            ),
            Mode(
                name="crib_anchor1_seedfilter",
                fixed_from_long14_offsets=(0,),
                use_seed_pool=True,
                seed_filter_by_crib=True,
                seed_filter_min_keep=8,
                seed_filter_backfill=8,
            ),
        ]
        return tiers, modes, [211], [111], _solver_small()
    if p == "cribs_overnight_8h":
        modes = [
            Mode(name="none"),
            Mode(name="crib_anchor1", fixed_from_long14_offsets=(0,)),
            Mode(
                name="crib_anchor1_seedpool",
                fixed_from_long14_offsets=(0,),
                use_seed_pool=True,
            ),
            Mode(
                name="crib_anchor1_seedfilter",
                fixed_from_long14_offsets=(0,),
                use_seed_pool=True,
                seed_filter_by_crib=True,
                seed_filter_min_keep=8,
                seed_filter_backfill=8,
            ),
            Mode(
                name="crib_anchor1_seedfilter_len1x2",
                fixed_from_long14_offsets=(0,),
                short_per_word_budget=((1, 2),),
                min_random_pass_rate=0.001,
                use_seed_pool=True,
                seed_filter_by_crib=True,
                seed_filter_min_keep=8,
                seed_filter_backfill=8,
            ),
        ]
        return tiers, modes, [211], [111, 222, 333, 444], _solver_overnight()
    raise ValueError(f"Unknown BENCH_PROFILE={BENCH_PROFILE!r}")


def _print_setup_snapshot(
    *,
    direction: Direction,
    tiers: Sequence[Tier],
    modes: Sequence[Mode],
    text_offsets: Sequence[int],
    key_seeds: Sequence[int],
    solver: SolverSpec,
) -> None:
    print(
        f"[bench_cribs] setup: profile={BENCH_PROFILE} direction={direction.value} "
        f"order={ORDER} A={ALPHABET_SIZE} random_sanity={RANDOM_KEYS_SANITY}",
        flush=True,
    )
    tier_str = ", ".join([f"{t.name}(p{t.period},c{t.columns},L{t.length})" for t in tiers])
    print(f"[bench_cribs] setup: tiers={tier_str}", flush=True)
    print(
        f"[bench_cribs] setup: text_offsets={list(text_offsets)} key_seeds={list(key_seeds)} "
        f"modes={[m.name for m in modes]}",
        flush=True,
    )
    for m in modes:
        if m.name == "none":
            continue
        print(
            "[bench_cribs] setup: mode="
            f"{m.name} long14_word={int(bool(m.enforce_long14_word))} "
            f"fixed_offsets={list(m.fixed_from_long14_offsets)} "
            f"short_global={list(m.short_global_lengths)} "
            f"short_budget={dict(m.short_per_word_budget)} "
            f"min_pass_rate={m.min_random_pass_rate} "
            f"seed_pool={int(bool(m.use_seed_pool))} "
            f"seed_filter={int(bool(m.seed_filter_by_crib))} "
            f"seed_min_keep={int(m.seed_filter_min_keep)} "
            f"seed_backfill={int(m.seed_filter_backfill)}",
            flush=True,
        )
    print(
        f"[bench_cribs] setup: solver={solver.name} params={json.dumps(dict(solver.params), sort_keys=True)}",
        flush=True,
    )
    print(
        "[bench_cribs] setup: seed_pool="
        f"n={SEED_POOL_N} plan="
        f"(blocks={SEED_POOL_PLAN.n_block_seeds}, tails={SEED_POOL_PLAN.n_tail_seeds}, "
        f"starts={SEED_POOL_PLAN.n_starts}, refine={SEED_POOL_PLAN.refine_steps})",
        flush=True,
    )


def _print_run_warnings(rows: List[dict]) -> None:
    if not rows:
        return
    warned = False
    skipped = 0
    for r in rows:
        if int(r.get("skipped_overprune", 0) or 0) == 1:
            skipped += 1
            continue
        rej = float(r.get("crib_reject_total", 0.0))
        pas = float(r.get("crib_pass_total", 0.0))
        den = max(1.0, rej + pas)
        rr = rej / den
        if rr >= 0.98:
            warned = True
            print(
                "[bench_cribs][warn] high reject pressure "
                f"tier={r.get('tier')} mode={r.get('mode')} text={r.get('text_id')} seed={r.get('key_seed')} "
                f"reject_rate={rr:.3f}",
                flush=True,
            )
    if skipped > 0:
        warned = True
        print(f"[bench_cribs][warn] skipped_overprune rows={skipped}", flush=True)
    if not warned:
        print("[bench_cribs] reject-pressure check: no >=98% reject-rate cases.", flush=True)


def main() -> None:
    direction = Direction.LTR
    tiers, modes, text_offsets, key_seeds, solver = _profile()
    lm_root = _require_assets(direction, ns=(3, 4))
    pct_scorer = _pct_scorer(direction, model_root=lm_root, char_weights={3: 0.5, 4: 0.5})
    seed_pool_cfg = _build_seed_pool_cfg(direction=direction, model_root=lm_root)
    short_allowed = _load_short_allowed_by_len(direction, SHORT_WORD_LENGTHS)
    _print_setup_snapshot(
        direction=direction,
        tiers=tiers,
        modes=modes,
        text_offsets=text_offsets,
        key_seeds=key_seeds,
        solver=solver,
    )

    pt_base, wli_base = _encode_long_plaintext(direction)
    total = len(tiers) * len(text_offsets) * len(key_seeds) * len(modes)
    manifest = {
        "kind": "bench_solve_periodic_columnar_kaeding_cribs",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_short": _git_short_hash(),
        "profile": BENCH_PROFILE,
        "direction": direction.value,
        "order": ORDER,
        "alphabet_size": ALPHABET_SIZE,
        "random_keys_sanity": int(RANDOM_KEYS_SANITY),
        "precheck_random_keys": int(PRECHECK_RANDOM_KEYS),
        "seed_pool": {
            "n_keys": int(SEED_POOL_N),
            "plan": {
                "n_block_seeds": int(SEED_POOL_PLAN.n_block_seeds),
                "n_tail_seeds": int(SEED_POOL_PLAN.n_tail_seeds),
                "n_starts": int(SEED_POOL_PLAN.n_starts),
                "refine_steps": int(SEED_POOL_PLAN.refine_steps),
                "tail_move_prob": float(SEED_POOL_PLAN.tail_move_prob),
                "temp_start": float(SEED_POOL_PLAN.temp_start),
                "temp_end": float(SEED_POOL_PLAN.temp_end),
            },
        },
        "long14_disappointment": list(LONG14_DISAPPOINTMENT),
        "short_lengths": list(SHORT_WORD_LENGTHS),
        "tiers": [dict(name=t.name, period=t.period, columns=t.columns, length=t.length) for t in tiers],
        "text_offsets": list(text_offsets),
        "key_seeds": list(key_seeds),
        "modes": [m.__dict__ for m in modes],
        "solver": dict(name=solver.name, params=dict(solver.params)),
        "scoring": {
            "objective": "pct.logp.win10",
            "se_mode": "nose",
            "char_weights": {3: 0.5, 4: 0.5},
            "use_word_breaks": False,
            "impl": "numpy",
            "model_root": str(lm_root),
        },
        "expected": {"instances": int(len(tiers) * len(text_offsets) * len(key_seeds)), "solves": int(total)},
        "script": str(Path(__file__).resolve().as_posix()),
        "repo_root": str(_repo_root().as_posix()),
        "resume": {"enabled": bool(RESUME_FROM_RUN_DIR), "source": str(RESUME_FROM_RUN_DIR or "")},
    }

    if RESUME_FROM_RUN_DIR:
        run_dir = Path(RESUME_FROM_RUN_DIR)
        if not run_dir.is_absolute():
            run_dir = (_repo_root() / run_dir).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
        rows = _load_resume_rows(run_dir)
        completed = {_row_id(r) for r in rows}
        done = len(completed)
        _checkpoint(run_dir, rows=rows, manifest=manifest)
        print(
            f"[bench_cribs] Resuming from {run_dir.relative_to(_repo_root())} with {done}/{total} completed",
            flush=True,
        )
    else:
        run_dir = _create_run_dir()
        rows = []
        completed: set[tuple[str, str, int, int]] = set()
        done = 0
        _checkpoint(run_dir, rows=rows, manifest=manifest)
    print(f"[bench_cribs] Reports will be written to {run_dir.relative_to(_repo_root())}", flush=True)

    t0_all = time.time()

    for tier in tiers:
        for text_id, off in enumerate(text_offsets):
            pt_idx, wli, off_used = _slice_word_aligned(pt_base, wli_base, length=tier.length, offset_hint=off)
            for key_seed in key_seeds:
                key_len = int(tier.period * ALPHABET_SIZE + tier.columns)
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
                pt_check = cipher.decrypt_single(ciphertext=ct_idx, key=key_true)
                if not np.array_equal(np.asarray(pt_check, dtype=np.uint8), np.asarray(pt_idx, dtype=np.uint8)):
                    raise RuntimeError("[bench_cribs] known-key roundtrip failed")

                # Random-sanity gate (same philosophy as main benchmark).
                oracle_pct = float(pct_scorer.score(pt_idx, None))
                random_pct: List[float] = []
                for _ in range(RANDOM_KEYS_SANITY):
                    rk = keyops.random(rng).astype(np.int16, copy=False)
                    rpt = cipher.decrypt_single(ciphertext=ct_idx, key=rk)
                    random_pct.append(float(pct_scorer.score(rpt, None)))
                if not (oracle_pct > float(np.max(random_pct))):
                    raise RuntimeError("[bench_cribs] sanity failure: oracle_pct <= best_random_pct")
                print(
                    f"[bench_cribs] gate0 ok tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"oracle_pct={oracle_pct:.4f} best_random_pct={float(np.max(random_pct)):.4f}",
                    flush=True,
                )

                for mode in modes:
                    rowid = (str(tier.name), str(mode.name), int(text_id), int(key_seed))
                    if rowid in completed:
                        continue
                    t0 = time.time()
                    crib_payload, crib_meta = build_hard_crib_payload(
                        mode=mode,
                        direction=direction,
                        pt_idx=pt_idx,
                        wli=wli,
                        short_allowed_by_len=short_allowed,
                    )
                    _preflight_oracle_crib(hard_crib=crib_payload, pt_true=pt_idx, wli=wli)

                    precheck_pass_rate = float("nan")
                    skipped_overprune = 0
                    skip_reason = ""
                    seed_candidates_total = 0
                    seed_candidates_pass = 0
                    seed_candidates_used = 0
                    seed_filter_fallback_used = 0
                    if crib_payload is not None and float(mode.min_random_pass_rate) > 0.0:
                        precheck_pass_rate = _estimate_random_pass_rate(
                            cipher=cipher,
                            ciphertext=ct_idx,
                            keyops=keyops,
                            rng=rng,
                            wli=wli,
                            hard_crib=crib_payload,
                            n_samples=PRECHECK_RANDOM_KEYS,
                        )
                        if precheck_pass_rate < float(mode.min_random_pass_rate):
                            skipped_overprune = 1
                            skip_reason = (
                                f"precheck_pass_rate={precheck_pass_rate:.6f} < "
                                f"min={float(mode.min_random_pass_rate):.6f}"
                            )
                            dt = float(time.time() - t0)
                            rows.append(
                                {
                                    "tier": tier.name,
                                    "mode": mode.name,
                                    "period": tier.period,
                                    "columns": tier.columns,
                                    "length": tier.length,
                                    "text_id": int(text_id),
                                    "offset_hint": int(off),
                                    "offset_used": int(off_used),
                                    "key_seed": int(key_seed),
                                    "oracle_pct": float(oracle_pct),
                                    "best_random_pct": float(np.max(random_pct)),
                                    "sol_score": float("nan"),
                                    "match_ratio": float("nan"),
                                    "evals": 0,
                                    "seconds": round(dt, 3),
                                    "evals_per_second": float("nan"),
                                    "hard_crib_enabled_requested": int(crib_meta.get("hard_crib_enabled_requested", 0)),
                                    "hard_crib_rule_fixed_chars": int(crib_meta.get("hard_crib_rule_fixed_chars", 0)),
                                    "hard_crib_rule_per_word": int(crib_meta.get("hard_crib_rule_per_word", 0)),
                                    "hard_crib_rule_global_len": int(crib_meta.get("hard_crib_rule_global_len", 0)),
                                    "hard_crib_long14_word_index": int(crib_meta.get("hard_crib_long14_word_index", -1)),
                                    "hard_crib_short_per_word_count": int(
                                        crib_meta.get("hard_crib_short_per_word_count", 0)
                                    ),
                                    "hard_crib_mode_random_gate": float(
                                        crib_meta.get("hard_crib_mode_random_gate", 0.0)
                                    ),
                                    "mode_fixed_offsets": ",".join(str(int(v)) for v in mode.fixed_from_long14_offsets),
                                    "mode_short_global_lengths": ",".join(
                                        str(int(v)) for v in mode.short_global_lengths
                                    ),
                                    "mode_short_budget": json.dumps(
                                        {int(k): int(v) for k, v in mode.short_per_word_budget}, sort_keys=True
                                    ),
                                    "precheck_pass_rate": float(precheck_pass_rate),
                                    "precheck_random_keys": int(PRECHECK_RANDOM_KEYS),
                                    "seed_candidates_total": int(seed_candidates_total),
                                    "seed_candidates_pass": int(seed_candidates_pass),
                                    "seed_candidates_used": int(seed_candidates_used),
                                    "seed_filter_fallback_used": int(seed_filter_fallback_used),
                                    "crib_enabled_runtime": 0,
                                    "crib_pass_total": 0,
                                    "crib_reject_total": 0,
                                    "crib_reject_rate": float("nan"),
                                    "crib_reject_fixed_char": 0,
                                    "crib_reject_word_index": 0,
                                    "crib_reject_global_len": 0,
                                    "crib_all_rejected_batches": 0,
                                    "hard_crib_all_rejected": 0,
                                    "skipped_overprune": int(skipped_overprune),
                                    "skip_reason": skip_reason,
                                    "stop_reason": "skipped_overprune",
                                }
                            )
                            completed.add(rowid)
                            done += 1
                            elapsed = float(time.time() - t0_all)
                            eta = (elapsed / float(done)) * float(total - done) if done > 0 else 0.0
                            _checkpoint(run_dir, rows=rows, manifest=manifest)
                            print(
                                f"[bench_cribs] {done}/{total} tier={tier.name} mode={mode.name} text={text_id} "
                                f"key_seed={key_seed} skipped_overprune pass_rate={precheck_pass_rate:.6f} "
                                f"min={float(mode.min_random_pass_rate):.6f} elapsed={_format_seconds(elapsed)} "
                                f"eta={_format_seconds(eta)}",
                                flush=True,
                            )
                            continue

                    initial_keys = None
                    if bool(mode.use_seed_pool):
                        seed_keys = _make_seed_keys(
                            ciphertext=ct_idx,
                            period=tier.period,
                            columns=tier.columns,
                            direction=direction,
                            seed=int(key_seed) + 7001,
                            scoring_cfg=seed_pool_cfg,
                            n_keys=SEED_POOL_N,
                        )
                        seed_candidates_total = int(len(seed_keys))
                        selected_seed_keys = list(seed_keys)
                        seed_candidates_pass = int(seed_candidates_total)
                        if bool(mode.seed_filter_by_crib) and crib_payload is not None:
                            selected_seed_keys, seed_candidates_pass = _filter_seed_keys_by_crib(
                                seed_keys=seed_keys,
                                cipher=cipher,
                                ciphertext=ct_idx,
                                wli=wli,
                                hard_crib=crib_payload,
                                min_keep=int(mode.seed_filter_min_keep),
                                backfill=int(mode.seed_filter_backfill),
                            )
                            if seed_candidates_pass < max(1, int(mode.seed_filter_min_keep)):
                                seed_filter_fallback_used = 1
                        seed_candidates_used = int(len(selected_seed_keys))
                        if selected_seed_keys:
                            initial_keys = selected_seed_keys

                    scorer_params = dict(
                        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
                        se_mode=SeMode.NOSE,
                        include_char=True,
                        use_word_breaks=False,
                        char_weights={3: 0.5, 4: 0.5},
                        wli_weights={},
                        encoding_dir=direction,
                        impl=ScorerImpl.NUMPY,
                    )
                    if crib_payload is not None:
                        scorer_params["hard_crib"] = crib_payload

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
                        wli_data=wli,
                        cipher=cipher_spec,
                        key=key_spec,
                        solver=solver,
                        device=Device.CPU,
                        scorer_params=scorer_params,
                        telemetry_on=True,
                        encoding_dir=direction,
                        force_no_wli=False,
                        initial_keys=initial_keys,
                    )
                    pt_sol = np.asarray(getattr(sol, "plaintext_idx", []) or [], dtype=np.uint8).reshape(-1)
                    tel = getattr(sol, "meta", {}).get("telemetry", {}) if hasattr(sol, "meta") else {}
                    hc_meta = getattr(sol, "meta", {}).get("hard_crib", {}) if hasattr(sol, "meta") else {}
                    dt = float(time.time() - t0)
                    evals = int((getattr(sol, "meta", {}) or {}).get("work", {}).get("evals", 0) or 0)
                    crib_pass = int(tel.get("crib_pass_total", 0) or 0) if isinstance(tel, dict) else 0
                    crib_rej = int(tel.get("crib_reject_total", 0) or 0) if isinstance(tel, dict) else 0
                    crib_den = max(1, crib_pass + crib_rej)
                    crib_reject_rate = float(crib_rej) / float(crib_den)
                    evals_per_second = float(evals) / float(max(1e-9, dt))

                    rows.append(
                        {
                            "tier": tier.name,
                            "mode": mode.name,
                            "period": tier.period,
                            "columns": tier.columns,
                            "length": tier.length,
                            "text_id": int(text_id),
                            "offset_hint": int(off),
                            "offset_used": int(off_used),
                            "key_seed": int(key_seed),
                            "oracle_pct": float(oracle_pct),
                            "best_random_pct": float(np.max(random_pct)),
                            "sol_score": float(getattr(sol, "score", float("nan"))),
                            "match_ratio": float(_match_ratio(pt_sol.tolist(), pt_idx.tolist())),
                            "evals": evals,
                            "seconds": round(dt, 3),
                            "evals_per_second": float(evals_per_second),
                            "hard_crib_enabled_requested": int(crib_meta.get("hard_crib_enabled_requested", 0)),
                            "hard_crib_rule_fixed_chars": int(crib_meta.get("hard_crib_rule_fixed_chars", 0)),
                            "hard_crib_rule_per_word": int(crib_meta.get("hard_crib_rule_per_word", 0)),
                            "hard_crib_rule_global_len": int(crib_meta.get("hard_crib_rule_global_len", 0)),
                            "hard_crib_long14_word_index": int(crib_meta.get("hard_crib_long14_word_index", -1)),
                            "hard_crib_short_per_word_count": int(crib_meta.get("hard_crib_short_per_word_count", 0)),
                            "hard_crib_mode_random_gate": float(crib_meta.get("hard_crib_mode_random_gate", 0.0)),
                            "mode_fixed_offsets": ",".join(str(int(v)) for v in mode.fixed_from_long14_offsets),
                            "mode_short_global_lengths": ",".join(str(int(v)) for v in mode.short_global_lengths),
                            "mode_short_budget": json.dumps(
                                {int(k): int(v) for k, v in mode.short_per_word_budget}, sort_keys=True
                            ),
                            "precheck_pass_rate": float(precheck_pass_rate),
                            "precheck_random_keys": int(PRECHECK_RANDOM_KEYS),
                            "seed_candidates_total": int(seed_candidates_total),
                            "seed_candidates_pass": int(seed_candidates_pass),
                            "seed_candidates_used": int(seed_candidates_used),
                            "seed_filter_fallback_used": int(seed_filter_fallback_used),
                            "crib_enabled_runtime": int(bool(tel.get("crib_enabled", False))) if isinstance(tel, dict) else 0,
                            "crib_pass_total": crib_pass,
                            "crib_reject_total": crib_rej,
                            "crib_reject_rate": float(crib_reject_rate),
                            "crib_reject_fixed_char": int(tel.get("crib_reject_fixed_char", 0) or 0)
                            if isinstance(tel, dict)
                            else 0,
                            "crib_reject_word_index": int(tel.get("crib_reject_word_index", 0) or 0)
                            if isinstance(tel, dict)
                            else 0,
                            "crib_reject_global_len": int(tel.get("crib_reject_global_len", 0) or 0)
                            if isinstance(tel, dict)
                            else 0,
                            "crib_all_rejected_batches": int(tel.get("crib_all_rejected_batches", 0) or 0)
                            if isinstance(tel, dict)
                            else 0,
                            "hard_crib_all_rejected": int(bool(hc_meta.get("all_rejected", False)))
                            if isinstance(hc_meta, dict)
                            else 0,
                            "skipped_overprune": int(skipped_overprune),
                            "skip_reason": skip_reason,
                            "stop_reason": str(getattr(sol, "stop_reason", "")),
                        }
                    )

                    completed.add(rowid)
                    done += 1
                    elapsed = float(time.time() - t0_all)
                    eta = (elapsed / float(done)) * float(total - done) if done > 0 else 0.0
                    _checkpoint(run_dir, rows=rows, manifest=manifest)
                    print(
                        f"[bench_cribs] {done}/{total} tier={tier.name} mode={mode.name} text={text_id} key_seed={key_seed} "
                        f"run={_format_seconds(dt)} elapsed={_format_seconds(elapsed)} eta={_format_seconds(eta)} "
                        f"reject_rate={crib_reject_rate:.3f} evals_per_s={evals_per_second:.1f}",
                        flush=True,
                    )

    summary = _checkpoint(run_dir, rows=rows, manifest=manifest)
    total_s = float(time.time() - t0_all)
    print(f"[bench_cribs] Completed in {total_s:.1f}s. Reports: {run_dir.relative_to(_repo_root())}", flush=True)
    print("\n[bench_cribs] Summary (p50) by tier/mode")
    for tier, entries in summary.get("tiers", {}).items():
        print(f"\nTier: {tier}")
        for e in entries:
            print(
                f"  Mode={e['mode']} N={e['n']} "
                f"match_p50={e['match_ratio']['p50']:.3f} "
                f"score_p50={e['score']['p50']:.4f} "
                f"sec_p50={e['seconds']['p50']:.1f} "
                f"eps_p50={e['evals_per_second']['p50']:.1f} "
                f"crib_rej_p50={e['crib_reject_total']['p50']:.0f} "
                f"crib_rej_rate_p50={e['crib_reject_rate']['p50']:.3f} "
                f"precheck_p50={e['precheck_pass_rate']['p50']:.4f} "
                f"seed_pass_p50={e['seed_candidates_pass']['p50']:.0f}/{e['seed_candidates_total']['p50']:.0f} "
                f"seed_used_p50={e['seed_candidates_used']['p50']:.0f} "
                f"all_rej_rate={e['rate_all_rejected']:.2f} "
                f"skip_rate={e['rate_skipped_overprune']:.2f} "
                f"seed_fb_rate={e['rate_seed_filter_fallback']:.2f}"
            )
    _print_run_warnings(rows)


if __name__ == "__main__":
    main()
