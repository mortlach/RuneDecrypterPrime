from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in [cur.parent, *cur.parents]:
        if (parent / "src" / "rune_decrypter_prime").exists():
            return parent
    return cur.parents[0]


REPO_ROOT = _find_repo_root(Path(__file__).resolve())

if __package__ in (None, ""):
    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "src"))

from rune_decrypter_prime.api import Direction
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.types import Device


OUTPUT_ROOT = REPO_ROOT / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _match_ratio(a: List[int], b: List[int]) -> float:
    if not a or not b or len(a) != len(b):
        return float("nan")
    arr_a = np.asarray(a, dtype=np.int64)
    arr_b = np.asarray(b, dtype=np.int64)
    return float(np.mean(arr_a == arr_b))


def _latest_no_wli_run_dir() -> Path:
    if not OUTPUT_ROOT.exists():
        raise FileNotFoundError(f"Output root missing: {OUTPUT_ROOT}")
    cands = [p for p in OUTPUT_ROOT.iterdir() if p.is_dir()]
    if not cands:
        raise FileNotFoundError(f"No no-WLI run directories found under: {OUTPUT_ROOT}")
    cands.sort(key=lambda p: p.name, reverse=True)
    return cands[0]


def _build_cipher(artifact: Dict[str, Any]) -> PeriodicColumnarCipher:
    direction = Direction(str(artifact.get("direction", "ltr")))
    cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        alphabet_size=int(artifact["alphabet_size"]),
        key_length=int(artifact["period"]) * int(artifact["alphabet_size"]) + int(artifact["columns"]),
        order=str(artifact["order"]),
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    return PeriodicColumnarCipher(cfg)


def _verify_topk_rows(
    *,
    rows: List[Dict[str, Any]],
    cipher: PeriodicColumnarCipher,
    ciphertext: np.ndarray,
    expected_target: List[int],
    label: str,
) -> Tuple[int, int, List[str]]:
    ok = 0
    fail = 0
    errors: List[str] = []
    for row in rows:
        rank = int(row.get("rank", -1))
        key_idx = list(map(int, row.get("key_idx", [])))
        pt_idx_saved = list(map(int, row.get("plaintext_idx", [])))
        if not key_idx or not pt_idx_saved:
            fail += 1
            errors.append(f"{label} rank={rank}: missing key_idx/plaintext_idx")
            continue
        dec = np.asarray(
            cipher.decrypt_single(ciphertext=ciphertext, key=np.asarray(key_idx, dtype=np.int16)),
            dtype=np.uint8,
        ).reshape(-1)
        dec_list = dec.astype(int).tolist()
        if dec_list != pt_idx_saved:
            fail += 1
            errors.append(f"{label} rank={rank}: plaintext_idx mismatch")
            continue
        saved_match = float(row.get("match_ratio", float("nan")))
        calc_match = _match_ratio(dec_list, expected_target)
        if np.isfinite(saved_match) and np.isfinite(calc_match) and abs(saved_match - calc_match) > 1e-9:
            fail += 1
            errors.append(
                f"{label} rank={rank}: match_ratio mismatch saved={saved_match:.12f} calc={calc_match:.12f}"
            )
            continue
        ok += 1
    return ok, fail, errors


def verify_final_artifacts(
    *,
    run_dir: Path,
    verify_stage2_topk: bool = True,
    verify_stage3_topk: bool = True,
    strict_missing_best: bool = False,
) -> Dict[str, Any]:
    run_dir = run_dir.resolve()
    final_dir = run_dir / "final_instances"
    if not final_dir.exists() or not final_dir.is_dir():
        return {
            "ok": False,
            "run_dir": str(run_dir),
            "errors": [f"missing final_instances directory: {final_dir}"],
            "warnings": [],
        }

    files = sorted(final_dir.glob("*.json"))
    if not files:
        return {
            "ok": False,
            "run_dir": str(run_dir),
            "errors": [f"no artifact json files in: {final_dir}"],
            "warnings": [],
        }

    errors: List[str] = []
    warnings: List[str] = []
    verified_instances = 0
    skipped_instances = 0
    stage2_rows_ok = 0
    stage2_rows_fail = 0
    stage3_rows_ok = 0
    stage3_rows_fail = 0

    for fp in files:
        artifact = _load_json(fp)
        key_idx = list(map(int, artifact.get("final_best_key_idx", [])))
        pt_idx_saved = list(map(int, artifact.get("final_best_plaintext_idx", [])))
        ct_idx = list(map(int, artifact.get("ciphertext_idx", [])))
        target_idx = list(map(int, artifact.get("target_plaintext_idx", [])))
        instance_id = f"{fp.name}"

        if not key_idx or not pt_idx_saved:
            skipped_instances += 1
            msg = f"{instance_id}: missing final_best_key_idx/final_best_plaintext_idx"
            if strict_missing_best:
                errors.append(msg)
            else:
                warnings.append(msg)
            continue

        cipher = _build_cipher(artifact)
        ct_arr = np.asarray(ct_idx, dtype=np.uint8).reshape(-1)
        dec = np.asarray(
            cipher.decrypt_single(ciphertext=ct_arr, key=np.asarray(key_idx, dtype=np.int16)),
            dtype=np.uint8,
        ).reshape(-1)
        dec_list = dec.astype(int).tolist()
        if dec_list != pt_idx_saved:
            errors.append(f"{instance_id}: final_best_plaintext_idx mismatch")
            continue

        saved_match = float(artifact.get("best_match_ratio", float("nan")))
        calc_match = _match_ratio(dec_list, target_idx)
        if np.isfinite(saved_match) and np.isfinite(calc_match) and abs(saved_match - calc_match) > 1e-9:
            errors.append(
                f"{instance_id}: best_match_ratio mismatch saved={saved_match:.12f} calc={calc_match:.12f}"
            )
            continue

        if verify_stage2_topk:
            rows = artifact.get("stage2_topk", [])
            if isinstance(rows, list):
                ok_n, fail_n, errs = _verify_topk_rows(
                    rows=rows,
                    cipher=cipher,
                    ciphertext=ct_arr,
                    expected_target=target_idx,
                    label=f"{instance_id}:stage2_topk",
                )
                stage2_rows_ok += int(ok_n)
                stage2_rows_fail += int(fail_n)
                errors.extend(errs)

        if verify_stage3_topk:
            rows = artifact.get("stage3_topk", [])
            if isinstance(rows, list):
                ok_n, fail_n, errs = _verify_topk_rows(
                    rows=rows,
                    cipher=cipher,
                    ciphertext=ct_arr,
                    expected_target=target_idx,
                    label=f"{instance_id}:stage3_topk",
                )
                stage3_rows_ok += int(ok_n)
                stage3_rows_fail += int(fail_n)
                errors.extend(errs)

        verified_instances += 1

    return {
        "ok": len(errors) == 0,
        "run_dir": str(run_dir),
        "artifacts_dir": str(final_dir),
        "artifact_files": len(files),
        "verified_instances": int(verified_instances),
        "skipped_instances": int(skipped_instances),
        "stage2_rows_ok": int(stage2_rows_ok),
        "stage2_rows_fail": int(stage2_rows_fail),
        "stage3_rows_ok": int(stage3_rows_ok),
        "stage3_rows_fail": int(stage3_rows_fail),
        "errors": errors,
        "warnings": warnings,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify no-WLI final artifact reproducibility (no re-solve needed)."
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Path to a no-WLI benchmark run directory; defaults to latest.",
    )
    parser.add_argument(
        "--skip-stage2-topk",
        action="store_true",
        help="Skip verifying stage2_topk rows.",
    )
    parser.add_argument(
        "--skip-stage3-topk",
        action="store_true",
        help="Skip verifying stage3_topk rows.",
    )
    parser.add_argument(
        "--strict-missing-best",
        action="store_true",
        help="Fail if an instance has no final_best key/plaintext stored.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional output path for verification report JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    run_dir = args.run_dir if args.run_dir is not None else _latest_no_wli_run_dir()
    report = verify_final_artifacts(
        run_dir=run_dir,
        verify_stage2_topk=not bool(args.skip_stage2_topk),
        verify_stage3_topk=not bool(args.skip_stage3_topk),
        strict_missing_best=bool(args.strict_missing_best),
    )
    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if report["ok"]:
        print(
            "[verify_no_wli] ok "
            f"run={report['run_dir']} files={report['artifact_files']} "
            f"verified={report['verified_instances']} skipped={report['skipped_instances']} "
            f"stage2_ok={report['stage2_rows_ok']} stage3_ok={report['stage3_rows_ok']}"
        )
        for msg in report["warnings"]:
            print(f"  * warning: {msg}")
        return 0

    print(
        "[verify_no_wli] failed "
        f"run={report['run_dir']} errors={len(report['errors'])}"
    )
    for msg in report["errors"]:
        print(f"  - {msg}")
    for msg in report["warnings"]:
        print(f"  * warning: {msg}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
