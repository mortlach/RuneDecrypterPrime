from __future__ import annotations

from typing import Any, Dict, Mapping


STAGE3_RUNTIME_CONFIG_STATE_KEYS = (
    "STAGE3_PHASEC_START_POLICY",
    "STAGE35_BASELINE_SELECTOR",
)


def extract_stage3_runtime_config_state(
    *,
    state: Mapping[str, Any],
) -> Dict[str, Any]:
    return {key: state[key] for key in STAGE3_RUNTIME_CONFIG_STATE_KEYS}


def build_stage3_runtime_config_state(
    *,
    stage3_phasec_start_policy: str,
    stage35_baseline_selector: str,
) -> Dict[str, Any]:
    return {
        "STAGE3_PHASEC_START_POLICY": str(stage3_phasec_start_policy),
        "STAGE35_BASELINE_SELECTOR": str(stage35_baseline_selector),
    }
