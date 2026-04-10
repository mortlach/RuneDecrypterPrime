from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_models import (
    FIXED_CIPHER_INSTANCE_SCHEMA_VERSION,
    FIXED_CIPHER_PANEL_SCHEMA_VERSION,
    FixedCipherInstanceSpec,
    FixedCipherPanelSpec,
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_sequence_like(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return str(value)


def _require_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key, None)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return int(value)


def _require_int_list(payload: Mapping[str, Any], key: str) -> tuple[int, ...]:
    value = payload.get(key, None)
    if not _is_sequence_like(value):
        raise ValueError(f"{key} must be a sequence of integers")
    out: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError(f"{key} must contain integers only")
        out.append(int(item))
    return tuple(out)


def _require_wli_list(payload: Mapping[str, Any], key: str) -> tuple[tuple[int, int], ...]:
    value = payload.get(key, None)
    if not _is_sequence_like(value):
        raise ValueError(f"{key} must be a sequence of [pos, len] pairs")
    out: list[tuple[int, int]] = []
    for item in value:
        if not _is_sequence_like(item) or len(item) != 2:
            raise ValueError(f"{key} must contain [pos, len] pairs")
        pos, ln = item
        if isinstance(pos, bool) or not isinstance(pos, int):
            raise ValueError(f"{key} pos must be an integer")
        if isinstance(ln, bool) or not isinstance(ln, int):
            raise ValueError(f"{key} len must be an integer")
        out.append((int(pos), int(ln)))
    return tuple(out)


def _require_str_list(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key, None)
    if not _is_sequence_like(value):
        raise ValueError(f"{key} must be a sequence of strings")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{key} must contain strings only")
        out.append(str(item))
    return tuple(out)


def _validate_instance_lengths(spec: FixedCipherInstanceSpec) -> None:
    expected_key_len = int(spec.period) * int(spec.alphabet_size) + int(spec.columns)
    if len(spec.ciphertext_idx) != int(spec.length):
        raise ValueError("ciphertext_idx length must match length")
    if len(spec.target_plaintext_idx) != int(spec.length):
        raise ValueError("target_plaintext_idx length must match length")
    if len(spec.target_wli) != int(spec.length):
        raise ValueError("target_wli length must match length")
    if len(spec.true_key_idx) != expected_key_len:
        raise ValueError(
            f"true_key_idx length must be period*alphabet_size+columns ({expected_key_len})"
        )
    for pos, ln in spec.target_wli:
        if pos < 0 or ln <= 0 or pos >= ln:
            raise ValueError("target_wli entries must be valid [pos, len] pairs")


def validate_fixed_instance_payload(
    payload: Mapping[str, Any],
    *,
    source: str,
) -> FixedCipherInstanceSpec:
    schema_version = _require_str(payload, "fixture_schema_version")
    if schema_version != FIXED_CIPHER_INSTANCE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported fixed-instance schema version in {source}: {schema_version!r}"
        )
    spec = FixedCipherInstanceSpec(
        fixture_schema_version=schema_version,
        instance_fixture_id=_require_str(payload, "instance_fixture_id"),
        source_artifact_rel_path=_require_str(payload, "source_artifact_rel_path"),
        source_run_id=_require_str(payload, "source_run_id"),
        source_fixture_id=_require_str(payload, "source_fixture_id"),
        text_id=_require_int(payload, "text_id"),
        source_key_seed=_require_int(payload, "source_key_seed"),
        offset_used=_require_int(payload, "offset_used"),
        period=_require_int(payload, "period"),
        columns=_require_int(payload, "columns"),
        length=_require_int(payload, "length"),
        alphabet_size=_require_int(payload, "alphabet_size"),
        direction=_require_str(payload, "direction"),
        order=_require_str(payload, "order"),
        ciphertext_idx=_require_int_list(payload, "ciphertext_idx"),
        target_plaintext_idx=_require_int_list(payload, "target_plaintext_idx"),
        target_wli=_require_wli_list(payload, "target_wli"),
        true_key_idx=_require_int_list(payload, "true_key_idx"),
        notes=_require_str_list(payload, "notes"),
    )
    _validate_instance_lengths(spec)
    return spec


def load_fixed_instance_spec(path: Path | str) -> FixedCipherInstanceSpec:
    fixture_path = Path(path)
    payload = _load_json(fixture_path)
    return validate_fixed_instance_payload(payload, source=str(fixture_path))


def load_fixed_instance_specs(
    *,
    fixture_dir: Path | str | None = None,
    fixture_paths: Sequence[Path | str] | None = None,
) -> list[FixedCipherInstanceSpec]:
    if fixture_dir is None and fixture_paths is None:
        raise ValueError("Provide fixture_dir or fixture_paths")
    paths: list[Path] = []
    if fixture_dir is not None:
        paths.extend(sorted(Path(fixture_dir).glob("*.json")))
    if fixture_paths is not None:
        paths.extend(Path(path) for path in fixture_paths)
    unique_paths: list[Path] = []
    seen_paths: set[Path] = set()
    for path in paths:
        resolved = Path(path).resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        unique_paths.append(Path(path))
    return [load_fixed_instance_spec(path) for path in unique_paths]


def load_fixed_instance_spec_map(
    *,
    fixture_dir: Path | str | None = None,
    fixture_paths: Sequence[Path | str] | None = None,
) -> dict[str, FixedCipherInstanceSpec]:
    specs = load_fixed_instance_specs(fixture_dir=fixture_dir, fixture_paths=fixture_paths)
    out: dict[str, FixedCipherInstanceSpec] = {}
    for spec in specs:
        if spec.instance_fixture_id in out:
            raise ValueError(f"Duplicate instance_fixture_id: {spec.instance_fixture_id}")
        out[spec.instance_fixture_id] = spec
    return out


def validate_fixed_cipher_panel_payload(
    payload: Mapping[str, Any],
    *,
    source: str,
) -> FixedCipherPanelSpec:
    schema_version = _require_str(payload, "panel_schema_version")
    if schema_version != FIXED_CIPHER_PANEL_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported fixed-panel schema version in {source}: {schema_version!r}"
        )
    spec = FixedCipherPanelSpec(
        panel_schema_version=schema_version,
        panel_id=_require_str(payload, "panel_id"),
        instance_fixture_ids=_require_str_list(payload, "instance_fixture_ids"),
        search_seeds=_require_int_list(payload, "search_seeds"),
        notes=_require_str_list(payload, "notes"),
    )
    if not spec.instance_fixture_ids:
        raise ValueError("instance_fixture_ids must be non-empty")
    if not spec.search_seeds:
        raise ValueError("search_seeds must be non-empty")
    return spec


def load_fixed_cipher_panel_spec(path: Path | str) -> FixedCipherPanelSpec:
    panel_path = Path(path)
    payload = _load_json(panel_path)
    return validate_fixed_cipher_panel_payload(payload, source=str(panel_path))
