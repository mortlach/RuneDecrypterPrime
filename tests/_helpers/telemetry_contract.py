from __future__ import annotations
import re
from typing import Any, Iterable


def assert_min_telemetry(tel: dict, device: str) -> None:
    """
    Minimal telemetry contract asserted in Tier-A.
    """
    assert isinstance(tel, dict), "telemetry must be a dict"
    for k in (
        "optimizer",
        "scorer",
        "tokens_processed",
        "decrypt_time_s",
        "score_time_s",
        "seed",
        "device",
    ):
        assert k in tel, f"missing telemetry key: {k}"
    sc = tel.get("scorer", {})
    assert isinstance(sc, dict), "scorer block must be a dict"
    assert (
        "impl" in sc and "device" in sc and ("dtype" in sc)
    ), "scorer must expose impl/device/dtype"
    if device == "cpu":
        assert sc.get("device") == "cpu"
    elif device == "cuda":
        assert str(sc.get("device", "")).startswith("cuda")
        assert sc.get("impl") in ("torch", "cuda", "torch_cuda")


check_telemetry_min_schema = assert_min_telemetry
_BANNED_TOKENS = {"fwd", "rev", "reverse", "text_transposition", "perm"}
_HEX_RE = re.compile("^[0-9a-f]+$")


def _walk_json_like(obj: Any) -> Iterable[str]:
    """Yield all string-like leaves and mapping keys for 'magic string' sweeps."""
    if obj is None:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                yield k
            yield from _walk_json_like(v)
    elif isinstance(obj, (list, tuple)):
        for it in obj:
            yield from _walk_json_like(it)
    elif isinstance(obj, str):
        yield obj


def assert_no_magic_strings(telemetry: dict) -> None:
    """Nothing in telemetry should contain legacy aliases or magic tokens (case-insensitive)."""
    lower_tokens = {s.lower() for s in _walk_json_like(telemetry)}
    banned_present = _BANNED_TOKENS.intersection(lower_tokens)
    assert not banned_present, f"Banned tokens present in telemetry: {banned_present}"


def assert_basic_timing_fields(telemetry: dict) -> None:
    """Timing fields must use *_time_s names and be non-negative numbers."""
    for k in ("decrypt_time_s", "score_time_s", "wall_time_s"):
        assert k in telemetry, f"missing telemetry field: {k}"
        v = telemetry[k]
        assert isinstance(v, (int, float)), f"{k} must be numeric, got {type(v)}"
        assert v >= 0, f"{k} must be >= 0, got {v}"


def assert_pipeline_contract(
    telemetry: dict,
    *,
    expected_direction: str | None = None,
    expected_perm_kind: str | None = None,
    expected_length: int | None = None,
) -> None:
    """Validate the pipeline block shape and canonical value set."""
    assert "pipeline" in telemetry and isinstance(
        telemetry["pipeline"], dict
    ), "missing 'pipeline' block"
    pipe = telemetry["pipeline"]
    assert (
        "text_encoding_direction" in pipe
    ), "pipeline.text_encoding_direction is required"
    dir_val = pipe["text_encoding_direction"]
    assert dir_val in {
        "ltr",
        "rtl",
    }, f"direction must be 'ltr' or 'rtl', got {dir_val!r}"
    if expected_direction is not None:
        assert (
            dir_val == expected_direction
        ), f"direction mismatch: {dir_val!r} != {expected_direction!r}"
    assert "input_permutation" in pipe and isinstance(
        pipe["input_permutation"], dict
    ), "pipeline.input_permutation must be an object"
    ip = pipe["input_permutation"]
    for key in ("kind", "length", "hash"):
        assert key in ip, f"pipeline.input_permutation.{key} missing"
    assert ip["kind"] in {
        "none",
        "custom",
    }, f"perm.kind must be 'none' or 'custom', got {ip['kind']!r}"
    if expected_perm_kind is not None:
        assert (
            ip["kind"] == expected_perm_kind
        ), f"perm.kind mismatch: {ip['kind']!r} != {expected_perm_kind!r}"
    assert (
        isinstance(ip["length"], int) and ip["length"] >= 1
    ), f"perm.length must be int >=1, got {ip['length']!r}"
    if expected_length is not None:
        assert (
            ip["length"] == expected_length
        ), f"perm.length mismatch: {ip['length']} != {expected_length}"
    h = ip["hash"]
    assert isinstance(h, str) and _HEX_RE.match(
        h
    ), f"perm.hash must be lowercase hex string, got {h!r}"
    assert len(h) in (
        16,
        32,
        40,
        64,
    ), f"perm.hash length must be 32/40/64, got {len(h)}"


def assert_pipeline_stable(t1: dict, t2: dict) -> None:
    """The entire pipeline subtree must be identical across identical runs."""
    p1 = t1.get("pipeline")
    p2 = t2.get("pipeline")
    assert p1 == p2, f"pipeline not stable across identical runs:\n{p1}\n!=\n{p2}"
