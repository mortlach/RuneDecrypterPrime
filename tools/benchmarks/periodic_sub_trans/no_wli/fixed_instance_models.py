from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


FIXED_CIPHER_INSTANCE_SCHEMA_VERSION = "no_wli_fixed_instance_v1"
FIXED_CIPHER_PANEL_SCHEMA_VERSION = "no_wli_fixed_instance_panel_v1"


@dataclass(frozen=True)
class FixedCipherInstanceSpec:
    fixture_schema_version: str = FIXED_CIPHER_INSTANCE_SCHEMA_VERSION
    instance_fixture_id: str = ""
    source_artifact_rel_path: str = ""
    source_run_id: str = ""
    source_fixture_id: str = ""
    text_id: int = 0
    source_key_seed: int = 0
    offset_used: int = 0
    period: int = 0
    columns: int = 0
    length: int = 0
    alphabet_size: int = 0
    direction: str = ""
    order: str = ""
    ciphertext_idx: tuple[int, ...] = field(default_factory=tuple)
    target_plaintext_idx: tuple[int, ...] = field(default_factory=tuple)
    target_wli: tuple[tuple[int, int], ...] = field(default_factory=tuple)
    true_key_idx: tuple[int, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "fixture_schema_version": str(self.fixture_schema_version),
            "instance_fixture_id": str(self.instance_fixture_id),
            "source_artifact_rel_path": str(self.source_artifact_rel_path),
            "source_run_id": str(self.source_run_id),
            "source_fixture_id": str(self.source_fixture_id),
            "text_id": int(self.text_id),
            "source_key_seed": int(self.source_key_seed),
            "offset_used": int(self.offset_used),
            "period": int(self.period),
            "columns": int(self.columns),
            "length": int(self.length),
            "alphabet_size": int(self.alphabet_size),
            "direction": str(self.direction),
            "order": str(self.order),
            "ciphertext_idx": [int(x) for x in self.ciphertext_idx],
            "target_plaintext_idx": [int(x) for x in self.target_plaintext_idx],
            "target_wli": [[int(a), int(b)] for a, b in self.target_wli],
            "true_key_idx": [int(x) for x in self.true_key_idx],
            "notes": [str(x) for x in self.notes],
        }


@dataclass(frozen=True)
class FixedCipherPanelSpec:
    panel_schema_version: str = FIXED_CIPHER_PANEL_SCHEMA_VERSION
    panel_id: str = ""
    instance_fixture_ids: tuple[str, ...] = field(default_factory=tuple)
    search_seeds: tuple[int, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "panel_schema_version": str(self.panel_schema_version),
            "panel_id": str(self.panel_id),
            "instance_fixture_ids": [str(x) for x in self.instance_fixture_ids],
            "search_seeds": [int(x) for x in self.search_seeds],
            "notes": [str(x) for x in self.notes],
        }
