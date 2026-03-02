from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
RUN_ROOT = REPO_ROOT / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli"
RUN_DIR_OVERRIDE: Path | None = None
AUDIT_JSONL_NAME = "iteration_audit_chain.jsonl"
MANIFEST_NAME = "run_manifest.json"


def _resolve_run_dir() -> Path:
    if RUN_DIR_OVERRIDE is not None:
        p = Path(RUN_DIR_OVERRIDE).expanduser()
        return (p if p.is_absolute() else (REPO_ROOT / p)).resolve()
    if not RUN_ROOT.exists():
        raise FileNotFoundError(f"run root not found: {RUN_ROOT}")
    candidates = [p for p in RUN_ROOT.iterdir() if p.is_dir() and "__bench_solve_pipeline_no_wli__" in p.name]
    if not candidates:
        raise FileNotFoundError(f"no no_wli run dirs found under: {RUN_ROOT}")
    # Prefer latest completed run with audit file present; interrupted runs are valid
    # artifacts but should not block routine verifier usage.
    for cand in sorted(candidates, key=lambda p: p.name, reverse=True):
        manifest_fp = cand / MANIFEST_NAME
        audit_fp = cand / AUDIT_JSONL_NAME
        if not manifest_fp.exists() or not audit_fp.exists():
            continue
        try:
            manifest = json.loads(manifest_fp.read_text(encoding="utf-8"))
            status = str(manifest.get("run_status", "")).strip().lower()
        except Exception:
            continue
        if status in {"completed", "complete", "finished", "done"}:
            return cand.resolve()

    # Fallback: latest run that has both manifest and audit files.
    for cand in sorted(candidates, key=lambda p: p.name, reverse=True):
        if (cand / MANIFEST_NAME).exists() and (cand / AUDIT_JSONL_NAME).exists():
            return cand.resolve()

    # Last-resort legacy behavior.
    return sorted(candidates, key=lambda p: p.name)[-1].resolve()


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float):
        return value if value == value else None
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(_sanitize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    run_dir = _resolve_run_dir()
    audit_jsonl = run_dir / AUDIT_JSONL_NAME
    manifest_fp = run_dir / MANIFEST_NAME
    if not audit_jsonl.exists():
        raise FileNotFoundError(f"missing audit jsonl: {audit_jsonl}")
    if not manifest_fp.exists():
        raise FileNotFoundError(f"missing run manifest: {manifest_fp}")

    manifest = json.loads(manifest_fp.read_text(encoding="utf-8"))
    expected_last = str(manifest.get("progress", {}).get("audit_last_chain_hash", ""))
    seed = str(manifest.get("progress", {}).get("audit_last_chain_hash", ""))  # fallback if empty file
    # Prefer explicit configured seed if present.
    cfg_seed = str(manifest.get("audit", {}).get("chain_seed", "")).strip()
    if cfg_seed:
        seed = cfg_seed
    if not seed:
        seed = "0" * 64

    prev_chain = seed
    rows = 0
    with audit_jsonl.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            txt = line.strip()
            if not txt:
                continue
            row = json.loads(txt)
            row_hash = str(row.get("row_hash", ""))
            row_prev = str(row.get("prev_chain_hash", ""))
            row_chain = str(row.get("chain_hash", ""))
            payload = {k: v for k, v in row.items() if k not in {"row_hash", "prev_chain_hash", "chain_hash"}}
            calc_row_hash = _sha256_text(_canonical_json(payload))
            if row_hash != calc_row_hash:
                raise RuntimeError(
                    f"row hash mismatch line={line_no} expected={row_hash} calculated={calc_row_hash}"
                )
            if row_prev != prev_chain:
                raise RuntimeError(
                    f"prev chain mismatch line={line_no} expected={prev_chain} found={row_prev}"
                )
            calc_chain = _sha256_text(f"{row_prev}|{row_hash}")
            if row_chain != calc_chain:
                raise RuntimeError(
                    f"chain hash mismatch line={line_no} expected={row_chain} calculated={calc_chain}"
                )
            prev_chain = row_chain
            rows += 1

    if rows > 0 and expected_last and expected_last != prev_chain:
        raise RuntimeError(
            f"manifest last chain mismatch expected={expected_last} calculated={prev_chain}"
        )

    rel = run_dir.relative_to(REPO_ROOT)
    print(
        f"[verify_audit] ok run={rel} rows={rows} last_chain={prev_chain}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
