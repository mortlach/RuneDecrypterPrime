from __future__ import annotations

import ast
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SRC_ROOT = Path("src/rune_decrypter_prime")
LEDGER = Path("docs/v1_traceability/v1_enum_domain_ledger.json")


@dataclass(frozen=True)
class EnumMember:
    path: str
    enum_class: str
    member_name: str
    value: str

    @property
    def qualified_name(self) -> str:
        return f"{self.enum_class}.{self.member_name}"

    @property
    def location(self) -> str:
        return f"{self.path}:{self.qualified_name}"


def _load_ledger() -> dict:
    assert LEDGER.is_file(), f"missing enum-domain ledger: {LEDGER}"
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert data["schema"] == "rdp_v1_enum_domain_ledger.v1"
    assert data["policy"] == "enum_wire_values_have_explicit_domain_ownership"
    assert isinstance(data.get("allowed_shared_wire_values"), list)
    assert isinstance(data.get("forbidden_enum_usages"), list)
    return data


def _py_files() -> Iterable[Path]:
    assert SRC_ROOT.is_dir(), f"missing source root: {SRC_ROOT}"
    for path in sorted(SRC_ROOT.rglob("*.py")):
        parts = set(path.parts)
        if "__pycache__" in parts:
            continue
        yield path


def _base_name(base: ast.expr) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    if isinstance(base, ast.Subscript):
        return _base_name(base.value)
    return None


def _is_enum_class(node: ast.ClassDef) -> bool:
    return any(_base_name(base) in {"Enum", "StrEnum", "IntEnum"} for base in node.bases)


def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _iter_string_enum_members() -> Iterable[EnumMember]:
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        relpath = path.as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or not _is_enum_class(node):
                continue
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                value = _string_literal(stmt.value)
                if value is None:
                    continue
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        yield EnumMember(
                            path=relpath,
                            enum_class=node.name,
                            member_name=target.id,
                            value=value,
                        )


def _allowed_shared_value_map(data: dict) -> dict[str, set[str]]:
    allowed: dict[str, set[str]] = {}
    for row in data["allowed_shared_wire_values"]:
        value = row["value"]
        members = set(row["enum_members"])
        assert value, row
        assert members, row
        assert str(row.get("reason", "")).strip(), row
        allowed[value] = members
    return allowed


def test_enum_domain_ledger_schema_is_valid() -> None:
    _load_ledger()


def test_cross_enum_string_wire_value_reuse_is_explicitly_ledgered() -> None:
    data = _load_ledger()
    allowed = _allowed_shared_value_map(data)

    by_value: dict[str, list[EnumMember]] = defaultdict(list)
    for member in _iter_string_enum_members():
        by_value[member.value].append(member)

    unledgered: list[str] = []
    for value, members in sorted(by_value.items()):
        classes = {member.enum_class for member in members}
        if len(classes) < 2:
            continue
        qualified = {member.qualified_name for member in members}
        if value in allowed and qualified <= allowed[value]:
            continue
        locations = ", ".join(member.location for member in members)
        unledgered.append(f"{value!r} -> {locations}")

    assert not unledgered, (
        "String enum wire values are reused across enum classes without a ledger entry. "
        "Either split the domains or add a justified entry to "
        f"{LEDGER}:\n" + "\n".join(unledgered)
    )


def test_known_wrong_domain_enum_borrowing_patterns_are_absent() -> None:
    data = _load_ledger()
    failures: list[str] = []

    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        for rule in data["forbidden_enum_usages"]:
            expression = rule["enum_expression"]
            contexts = rule.get("forbidden_when_file_contains_any", [])
            if expression not in text:
                continue
            if contexts and not any(context in text for context in contexts):
                continue
            failures.append(
                f"{path.as_posix()}: {rule['id']} uses {expression}; "
                f"use {rule['replacement']} instead. Reason: {rule['reason']}"
            )

    assert not failures, "\n".join(failures)
