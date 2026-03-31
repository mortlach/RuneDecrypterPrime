from __future__ import annotations

from typing import Any, Dict, Mapping


COMMIT_BRIDGE_STATE_KEYS = frozenset(
    {
        "stage2_resume_live",
        "stage3_prep_live",
    }
)

REQUIRED_COMMIT_RUNNER_SERVICE_KEYS = frozenset(
    {
        "write_json",
        "_build_summary",
        "write_pipeline_snapshot_files",
        "_append_csv_row",
        "_append_iteration_audit_row",
        "_hash_payload",
        "_sha256_file",
        "_format_seconds",
    }
)

REQUIRED_COMMIT_RUNNER_VALUE_KEYS = frozenset(
    {
        "SAVE_RESUME_HANDOFFS",
    }
)


def extract_commit_bridge_state(
    *,
    iteration_state: Mapping[str, Any],
) -> Dict[str, Any]:
    bridge_state: Dict[str, Any] = {}
    for key in COMMIT_BRIDGE_STATE_KEYS:
        value = iteration_state.get(key)
        if isinstance(value, Mapping) and value:
            bridge_state[key] = dict(value)
    return bridge_state


def validate_commit_runner_state(
    *,
    state: Mapping[str, Any],
) -> None:
    missing_keys = sorted(
        str(key) for key in REQUIRED_COMMIT_RUNNER_SERVICE_KEYS if key not in state
    )
    if missing_keys:
        raise KeyError(
            "missing commit runner services: " + ", ".join(missing_keys)
        )

    missing_value_keys = sorted(
        str(key) for key in REQUIRED_COMMIT_RUNNER_VALUE_KEYS if key not in state
    )
    if missing_value_keys:
        raise KeyError(
            "missing commit runner values: " + ", ".join(missing_value_keys)
        )

    non_callable_keys = sorted(
        str(key)
        for key in REQUIRED_COMMIT_RUNNER_SERVICE_KEYS
        if not callable(state[key])
    )
    if non_callable_keys:
        raise TypeError(
            "non-callable commit runner services: " + ", ".join(non_callable_keys)
        )


def resolve_commit_bridge_state(
    *,
    runner_state: Mapping[str, Any],
    bridge_state: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if bridge_state is None:
        validate_commit_runner_state(state=runner_state)
        return runner_state
    if bridge_state is runner_state:
        validate_commit_runner_state(state=runner_state)
        return runner_state

    bridge_state_dict = dict(bridge_state)
    unexpected_keys = sorted(
        str(key) for key in set(bridge_state_dict) - set(COMMIT_BRIDGE_STATE_KEYS)
    )
    if unexpected_keys:
        raise KeyError(
            "unexpected commit bridge_state keys: "
            + ", ".join(unexpected_keys)
        )
    if not bridge_state_dict:
        return runner_state

    merged_state = dict(runner_state)
    merged_state.update(bridge_state_dict)
    validate_commit_runner_state(state=merged_state)
    return merged_state
