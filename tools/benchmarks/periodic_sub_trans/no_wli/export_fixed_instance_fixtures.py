from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

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
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import (
    PeriodicStructuredMatrixKeyOps,
)
from tools.benchmarks.periodic_sub_trans.common import (
    bench_solve_periodic_columnar_kaeding as base,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_io import (
    load_fixed_instance_spec,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_models import (
    FixedCipherInstanceSpec,
)


SOURCE_ARTIFACT_REL_PATHS: tuple[str, ...] = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/20260405T020334839969Z__bench_solve_pipeline_no_wli__37dc435/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed611.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/20260406T161236795849Z__bench_solve_pipeline_no_wli__37dc435/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed1111.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/20260407T083149740840Z__bench_solve_pipeline_no_wli__37dc435/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed1411.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/20260407T150201170377Z__bench_solve_pipeline_no_wli__37dc435/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed1511.json",
)
OUTPUT_DIR = "tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances"

_SOURCE_ARTIFACT_NAME_RE = re.compile(
    r"^fixture_(?P<fixture_id>fixture_\d+)_p(?P<period>\d+)_c(?P<columns>\d+)_l(?P<length>\d+)__text(?P<text_id>\d+)__seed(?P<seed>\d+)\.json$"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_repo_rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _build_cipher(*, period: int, columns: int, alphabet_size: int, direction: str, order: str) -> PeriodicColumnarCipher:
    cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=int(period),
        columns=int(columns),
        alphabet_size=int(alphabet_size),
        key_length=int(period) * int(alphabet_size) + int(columns),
        order=str(order),
        encoding_dir=Direction(str(direction)),
        wli_data=[],
        device=Device.CPU,
    )
    return PeriodicColumnarCipher(cfg)


def _parse_source_fixture_metadata(artifact_path: Path, artifact: Mapping[str, Any]) -> dict[str, Any]:
    match = _SOURCE_ARTIFACT_NAME_RE.match(artifact_path.name)
    if match is None:
        raise ValueError(f"Unexpected artifact filename: {artifact_path.name}")
    source_run_id = str(artifact.get("run_id") or artifact_path.parents[1].name)
    source_fixture_id = str(artifact.get("fixture_id") or match.group("fixture_id"))
    text_id = int(artifact.get("text_id", int(match.group("text_id"))))
    source_key_seed = int(artifact.get("key_seed", int(match.group("seed"))))
    return {
        "source_run_id": source_run_id,
        "source_fixture_id": source_fixture_id,
        "text_id": text_id,
        "source_key_seed": source_key_seed,
    }


def _build_instance_fixture_id(
    *,
    source_fixture_id: str,
    period: int,
    columns: int,
    length: int,
    text_id: int,
    source_key_seed: int,
) -> str:
    return (
        f"{source_fixture_id}__p{int(period)}_c{int(columns)}_l{int(length)}"
        f"__text{int(text_id)}__seed{int(source_key_seed)}"
    )


def _build_true_key_idx(
    source_key_seed: int,
    period: int,
    columns: int,
    alphabet_size: int,
) -> tuple[int, ...]:
    key_len = int(period) * int(alphabet_size) + int(columns)
    rng = np.random.default_rng(int(source_key_seed))
    keyops = PeriodicStructuredMatrixKeyOps(
        K=int(key_len),
        period=int(period),
        A=int(alphabet_size),
        columns=int(columns),
    )
    key_true = keyops.random(rng).astype(np.int16, copy=False)
    return tuple(int(x) for x in key_true.tolist())


def _recover_target_slice(
    artifact: Mapping[str, Any],
    *,
    encode_long_plaintext_fn: Callable[[Direction], tuple[np.ndarray, np.ndarray]],
    slice_word_aligned_fn: Callable[..., tuple[np.ndarray, list[list[int]], int]],
) -> tuple[tuple[int, ...], tuple[tuple[int, int], ...], int]:
    direction = Direction(str(artifact["direction"]))
    pt_base, wli_base = encode_long_plaintext_fn(direction)
    recovered_pt, recovered_wli, recovered_offset = slice_word_aligned_fn(
        pt_base,
        wli_base,
        length=int(artifact["length"]),
        offset_hint=int(artifact["offset_used"]),
    )
    saved_pt = tuple(int(x) for x in list(artifact["target_plaintext_idx"]))
    recovered_pt_tuple = tuple(int(x) for x in recovered_pt.astype(int).tolist())
    if recovered_pt_tuple != saved_pt:
        raise ValueError("Recovered target_plaintext_idx does not match stored artifact")
    if int(recovered_offset) != int(artifact["offset_used"]):
        raise ValueError("Recovered offset_used does not match stored artifact")
    recovered_wli_tuple = tuple((int(a), int(b)) for a, b in recovered_wli)
    return recovered_pt_tuple, recovered_wli_tuple, int(recovered_offset)


def build_fixed_instance_spec_from_artifact(
    source_artifact_path: Path | str,
    *,
    encode_long_plaintext_fn: Callable[[Direction], tuple[np.ndarray, np.ndarray]] = base._encode_long_plaintext,
    slice_word_aligned_fn: Callable[..., tuple[np.ndarray, list[list[int]], int]] = base._slice_word_aligned,
) -> FixedCipherInstanceSpec:
    artifact_path = Path(source_artifact_path)
    artifact = _load_json(artifact_path)
    meta = _parse_source_fixture_metadata(artifact_path, artifact)
    source_artifact_rel_path = _to_repo_rel(artifact_path)
    target_plaintext_idx, target_wli, recovered_offset = _recover_target_slice(
        artifact,
        encode_long_plaintext_fn=encode_long_plaintext_fn,
        slice_word_aligned_fn=slice_word_aligned_fn,
    )
    true_key_idx = _build_true_key_idx(
        meta["source_key_seed"],
        int(artifact["period"]),
        int(artifact["columns"]),
        int(artifact["alphabet_size"]),
    )
    cipher = _build_cipher(
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        alphabet_size=int(artifact["alphabet_size"]),
        direction=str(artifact["direction"]),
        order=str(artifact["order"]),
    )
    ciphertext_idx = tuple(int(x) for x in list(artifact["ciphertext_idx"]))
    calc_ciphertext = tuple(
        int(x)
        for x in np.asarray(
            cipher.encrypt_single(
                plaintext=np.asarray(target_plaintext_idx, dtype=np.uint8),
                key=np.asarray(true_key_idx, dtype=np.int16),
            ),
            dtype=np.uint8,
        ).reshape(-1).astype(int).tolist()
    )
    if calc_ciphertext != ciphertext_idx:
        raise ValueError("Re-encryption from recomputed true_key_idx does not match stored ciphertext_idx")
    instance_fixture_id = _build_instance_fixture_id(
        source_fixture_id=meta["source_fixture_id"],
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        length=int(artifact["length"]),
        text_id=meta["text_id"],
        source_key_seed=meta["source_key_seed"],
    )
    return FixedCipherInstanceSpec(
        instance_fixture_id=instance_fixture_id,
        source_artifact_rel_path=source_artifact_rel_path,
        source_run_id=meta["source_run_id"],
        source_fixture_id=meta["source_fixture_id"],
        text_id=int(meta["text_id"]),
        source_key_seed=int(meta["source_key_seed"]),
        offset_used=int(recovered_offset),
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        length=int(artifact["length"]),
        alphabet_size=int(artifact["alphabet_size"]),
        direction=str(artifact["direction"]),
        order=str(artifact["order"]),
        ciphertext_idx=ciphertext_idx,
        target_plaintext_idx=target_plaintext_idx,
        target_wli=target_wli,
        true_key_idx=true_key_idx,
        notes=(
            "exported_from_final_artifact",
            "ciphertext_and_true_key_verified",
            "target_wli_reconstructed_from_long_plaintext",
        ),
    )


def export_fixed_instance_fixture(
    source_artifact_rel_path: str,
    *,
    output_dir: str = OUTPUT_DIR,
) -> Path:
    artifact_path = (REPO_ROOT / source_artifact_rel_path).resolve()
    output_root = (REPO_ROOT / output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    spec = build_fixed_instance_spec_from_artifact(artifact_path)
    output_path = output_root / f"{spec.instance_fixture_id}.json"
    output_path.write_text(json.dumps(spec.as_dict(), indent=2), encoding="utf-8")
    load_fixed_instance_spec(output_path)
    return output_path


def export_fixed_instance_fixtures(
    *,
    source_artifact_rel_paths: Sequence[str] = SOURCE_ARTIFACT_REL_PATHS,
    output_dir: str = OUTPUT_DIR,
) -> list[Path]:
    return [
        export_fixed_instance_fixture(source_artifact_rel_path, output_dir=output_dir)
        for source_artifact_rel_path in source_artifact_rel_paths
    ]


def main() -> int:
    written = export_fixed_instance_fixtures()
    repo_rel_written = [_to_repo_rel(path) for path in written]
    print(
        "[export_fixed_instance_fixtures] "
        f"exported={len(repo_rel_written)} output_dir={OUTPUT_DIR}"
    )
    for rel_path in repo_rel_written:
        print(f"  - {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
