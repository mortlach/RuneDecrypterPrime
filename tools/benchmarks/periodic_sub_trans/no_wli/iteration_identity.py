from __future__ import annotations

from typing import Any, Mapping


def normalize_instance_input_mode(mode: str | None) -> str:
    normalized = str(mode or "generated").strip().lower()
    if normalized not in {"generated", "fixed_ciphertext"}:
        raise ValueError(
            f"Unsupported INSTANCE_INPUT_MODE={mode!r}; "
            "expected generated|fixed_ciphertext"
        )
    return normalized


def build_iteration_identity_fields(
    *,
    tier_name: str,
    text_id: int,
    key_seed: int,
    instance_input_mode: str = "generated",
    instance_fixture_id: str = "",
    instance_source_key_seed: int | None = None,
    search_seed: int | None = None,
) -> dict[str, Any]:
    mode = normalize_instance_input_mode(instance_input_mode)
    search_seed_value = int(search_seed if search_seed is not None else key_seed)
    if mode == "fixed_ciphertext":
        fixture_id = str(instance_fixture_id or "").strip()
        if not fixture_id:
            raise ValueError(
                "instance_fixture_id is required for fixed_ciphertext identity"
            )
        source_key_seed = int(
            instance_source_key_seed
            if instance_source_key_seed is not None
            else key_seed
        )
        artifact_basename = f"{fixture_id}__search{search_seed_value}.json"
        history_fixture_id = fixture_id
    else:
        fixture_id = ""
        source_key_seed = int(
            instance_source_key_seed
            if instance_source_key_seed is not None
            else key_seed
        )
        artifact_basename = (
            f"{str(tier_name)}__text{int(text_id)}__seed{int(key_seed)}.json"
        )
        history_fixture_id = str(tier_name)
    return dict(
        instance_input_mode=str(mode),
        instance_fixture_id=str(fixture_id),
        instance_source_key_seed=int(source_key_seed),
        search_seed=int(search_seed_value),
        history_fixture_id=str(history_fixture_id),
        artifact_basename=str(artifact_basename),
    )


def build_iteration_identity_fields_from_row(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    return build_iteration_identity_fields(
        tier_name=str(row.get("tier", "") or ""),
        text_id=int(row.get("text_id", 0) or 0),
        key_seed=int(row.get("key_seed", 0) or 0),
        instance_input_mode=str(row.get("instance_input_mode", "generated") or "generated"),
        instance_fixture_id=str(row.get("instance_fixture_id", "") or ""),
        instance_source_key_seed=(
            int(row.get("instance_source_key_seed"))
            if row.get("instance_source_key_seed", None) is not None
            else None
        ),
        search_seed=(
            int(row.get("search_seed"))
            if row.get("search_seed", None) is not None
            else None
        ),
    )


def build_proven_solved_key(
    *,
    tier_name: str,
    text_id: int,
    key_seed: int,
    instance_input_mode: str = "generated",
    instance_fixture_id: str = "",
    search_seed: int | None = None,
) -> tuple[Any, ...]:
    mode = normalize_instance_input_mode(instance_input_mode)
    if mode == "fixed_ciphertext":
        fixture_id = str(instance_fixture_id or "").strip()
        if not fixture_id:
            raise ValueError(
                "instance_fixture_id is required for fixed_ciphertext proven key"
            )
        return (str(mode), fixture_id, int(search_seed if search_seed is not None else key_seed))
    return (str(mode), str(tier_name), int(text_id), int(key_seed))


def build_proven_solved_key_from_row(
    row: Mapping[str, Any],
) -> tuple[Any, ...]:
    mode = str(row.get("instance_input_mode", "generated") or "generated")
    if str(mode).strip().lower() == "fixed_ciphertext":
        fixture_id = str(
            row.get("instance_fixture_id", row.get("fixture_id", "")) or ""
        ).strip()
        search_seed_raw = row.get("search_seed", row.get("key_seed", None))
        if not fixture_id or search_seed_raw is None:
            raise ValueError(
                "fixed_ciphertext history row missing instance_fixture_id/search_seed"
            )
        return build_proven_solved_key(
            tier_name=str(row.get("tier", "") or ""),
            text_id=int(row.get("text_id", 0) or 0),
            key_seed=int(row.get("key_seed", 0) or 0),
            instance_input_mode="fixed_ciphertext",
            instance_fixture_id=fixture_id,
            search_seed=int(search_seed_raw),
        )
    fixture_id = str(row.get("fixture_id", "") or "").strip()
    text_id_raw = row.get("text_id", None)
    key_seed_raw = row.get("key_seed", None)
    if not fixture_id or text_id_raw is None or key_seed_raw is None:
        raise ValueError("generated history row missing fixture_id/text_id/key_seed")
    return build_proven_solved_key(
        tier_name=fixture_id,
        text_id=int(text_id_raw),
        key_seed=int(key_seed_raw),
        instance_input_mode="generated",
    )
