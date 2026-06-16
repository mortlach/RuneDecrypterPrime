from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Runner config (edit these in your IDE; no CLI args required)
# -----------------------------------------------------------------------------
#
# Gate choices:
#   smoke       -> v1_smoke only
#   release     -> v1_smoke + v1_release
#   extended    -> v1_extended only
#   showcase    -> v1_showcase_near_solve only
#   full_v1     -> v1_smoke + v1_release + v1_extended + v1_showcase_near_solve
#   slow_demo   -> v1_slow_demo only
#   optional_lm3 -> optional_lm3 only; requires lm3_extended assets
#   all_manifest -> all manifest entries, but known-broken/remove entries are still skipped
#
# CI/review runs may override the IDE defaults with environment variables:
#   GATE_PROFILE=full_v1 python tutorials/v1/run_all.py
#   ASSET_PROFILE=lm3_extended python tutorials/v1/run_all.py
GATE_PROFILE = "full_v1"

# Asset choices:
#   lm2_baseline  -> default minimal V1 asset profile
#   lm3_extended  -> includes 3-gram assets for optional periodic tutorials
ASSET_PROFILE = "lm2_baseline"

LIST_ONLY = False
STOP_ON_FIRST_FAILURE = False

# Keep normal runs compact. Flip to True when you want full tutorial output.
ECHO_OUTPUT = False

# Print the tail of failed/near-solve output for context.
PRINT_FAILURE_TAIL = True
TAIL_LINES = 80

# Known-broken entries are skipped unless this is explicitly flipped.
RUN_KNOWN_BROKEN = False

MANIFEST_NAME = "tutorial_manifest_v1.json"

GATE_PRESETS: dict[str, tuple[str, ...]] = {
    "smoke": ("v1_smoke",),
    "release": ("v1_smoke", "v1_release"),
    "extended": ("v1_extended",),
    "showcase": ("v1_showcase_near_solve",),
    "full_v1": ("v1_smoke", "v1_release", "v1_extended", "v1_showcase_near_solve"),
    "slow_demo": ("v1_slow_demo",),
    "optional_lm3": ("optional_lm3",),
    "all_manifest": (
        "v1_smoke",
        "v1_release",
        "v1_extended",
        "v1_showcase_near_solve",
        "v1_slow_demo",
        "optional_lm3",
        "broken_contract_fix_needed",
        "wrapper_script_fix_needed",
        "remove_from_pure_release",
    ),
}

KNOWN_BLOCKED_GATES = {
    "broken_contract_fix_needed",
    "wrapper_script_fix_needed",
    "remove_from_pure_release",
}

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class RunResult:
    name: str
    gate: str
    returncode: int
    accepted: bool
    status: str
    match_ratio: float | None
    score_time_s: float | None
    tokens: int | None
    reason: str


def _env_text(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return bool(default)
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    valid = ", ".join(sorted(_TRUE_VALUES | _FALSE_VALUES))
    raise ValueError(f"Invalid boolean override {name}={value!r}; expected one of: {valid}")


def _gate_profile() -> str:
    return _env_text("GATE_PROFILE", GATE_PROFILE)


def _asset_profile() -> str:
    return _env_text("ASSET_PROFILE", ASSET_PROFILE)


def _run_known_broken() -> bool:
    return _env_bool("RUN_KNOWN_BROKEN", RUN_KNOWN_BROKEN)


def _load_manifest(base: Path) -> dict[str, Any]:
    manifest_path = base / MANIFEST_NAME
    with manifest_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("schema") != "rdp_tutorial_manifest.v1":
        raise ValueError(f"Unexpected tutorial manifest schema in {manifest_path}: {data.get('schema')!r}")
    if "tutorials" not in data or not isinstance(data["tutorials"], list):
        raise ValueError(f"Tutorial manifest missing list field 'tutorials': {manifest_path}")
    return data


def _selected_gates() -> tuple[str, ...]:
    profile = _gate_profile()
    try:
        return GATE_PRESETS[profile]
    except KeyError as exc:
        valid = ", ".join(sorted(GATE_PRESETS))
        raise ValueError(f"Unknown GATE_PROFILE={profile!r}; expected one of: {valid}") from exc


def _parse_last_float(pattern: str, text: str) -> float | None:
    vals = re.findall(pattern, text, flags=re.IGNORECASE)
    if not vals:
        return None
    try:
        return float(vals[-1])
    except ValueError:
        return None


def _parse_match_ratio(text: str) -> float | None:
    return _parse_last_float(r"(?:Match ratio(?:\s*\([^)]*\))?|match_ratio)\s*:?\s*([0-9]+(?:\.[0-9]+)?)", text)


def _parse_score_time_s(text: str) -> float | None:
    # Matches report dictionaries such as: 'score_time_s': 53.67828460004239
    return _parse_last_float(r"score_time_s['\"]?\s*:\s*([0-9]+(?:\.[0-9]+)?)", text)


def _parse_tokens(text: str) -> int | None:
    vals = re.findall(r"tokens['\"]?\s*[:=]\s*([0-9][0-9,]*)", text, flags=re.IGNORECASE)
    if not vals:
        return None
    try:
        return int(vals[-1].replace(",", ""))
    except ValueError:
        return None


def _tail(text: str, *, lines: int = TAIL_LINES) -> str:
    chunks = text.rstrip().splitlines()
    if len(chunks) <= lines:
        return "\n".join(chunks)
    return "\n".join(chunks[-lines:])


def _launch_script(repo_root: Path, src_path: Path, script: Path) -> subprocess.CompletedProcess[str]:
    launch = (
        "import runpy, sys; "
        f"sys.path.insert(0, {str(src_path)!r}); "
        f"runpy.run_path({str(script)!r}, run_name='__main__')"
    )
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-X", "utf8", "-c", launch],
        cwd=str(repo_root),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env=env,
    )


def _is_selected(entry: dict[str, Any], gates: tuple[str, ...]) -> bool:
    return str(entry.get("gate", "")).strip() in gates


def _skip_reason(entry: dict[str, Any]) -> str | None:
    gate = str(entry.get("gate", "")).strip()
    current_status = str(entry.get("current_status", "")).strip()
    required_asset_profile = str(entry.get("required_asset_profile", "")).strip()
    asset_profile = _asset_profile()
    run_known_broken = _run_known_broken()

    if gate in KNOWN_BLOCKED_GATES and not run_known_broken:
        return f"known blocked gate: {gate}"

    if current_status in {"known_broken", "remove_from_pure_release"} and not run_known_broken:
        return f"known blocked status: {current_status}"

    if required_asset_profile and required_asset_profile not in {asset_profile, "unknown"}:
        return f"requires asset profile {required_asset_profile}, current profile is {asset_profile}"

    if str(entry.get("expected_under_lm2_baseline", "")).strip() == "skip" and asset_profile == "lm2_baseline":
        return "marked skip under lm2_baseline"

    return None


def _acceptance(entry: dict[str, Any], proc: subprocess.CompletedProcess[str]) -> RunResult:
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    match_ratio = _parse_match_ratio(text)
    score_time_s = _parse_score_time_s(text)
    tokens = _parse_tokens(text)

    name = str(entry["path"])
    gate = str(entry.get("gate", ""))
    acceptance_kind = str(entry.get("acceptance_kind", "process_success"))
    min_match_raw = entry.get("min_match_ratio")
    min_match = float(min_match_raw) if min_match_raw is not None else None

    if acceptance_kind in {"process_success", "requires_asset_profile"}:
        accepted = proc.returncode == 0
        reason = "process returned 0" if accepted else f"process returned {proc.returncode}"
    elif acceptance_kind == "min_match_ratio":
        if proc.returncode != 0:
            accepted = False
            reason = f"process returned {proc.returncode}"
        elif min_match is None:
            accepted = True
            reason = "process returned 0; no min_match_ratio specified"
        elif match_ratio is None:
            accepted = False
            reason = f"no match ratio found; expected >= {min_match:.3f}"
        else:
            accepted = match_ratio >= min_match
            reason = f"match_ratio={match_ratio:.3f}; expected >= {min_match:.3f}"
    elif acceptance_kind == "near_solve_min_match":
        if min_match is None:
            accepted = False
            reason = "near-solve entry missing min_match_ratio"
        elif match_ratio is None:
            accepted = False
            reason = f"no match ratio found; expected near-solve >= {min_match:.3f}"
        else:
            accepted = match_ratio >= min_match
            rc_note = "returned 0" if proc.returncode == 0 else f"returned {proc.returncode}, accepted as near-solve"
            reason = f"{rc_note}; match_ratio={match_ratio:.3f}; expected >= {min_match:.3f}"
    elif acceptance_kind == "blocked_known_issue":
        accepted = False
        reason = "blocked known issue should not have been run"
    else:
        accepted = proc.returncode == 0
        reason = f"unknown acceptance_kind={acceptance_kind!r}; fell back to process return code"

    if accepted and acceptance_kind == "near_solve_min_match":
        status = "NEAR_SOLVE_ACCEPTED"
    elif accepted:
        status = "PASS"
    else:
        status = "FAIL"

    return RunResult(name, gate, proc.returncode, accepted, status, match_ratio, score_time_s, tokens, reason)


def main() -> int:
    base = Path(__file__).resolve().parent
    repo_root = base.parents[1]
    src_path = repo_root / "src"
    manifest = _load_manifest(base)
    profile = _gate_profile()
    asset_profile = _asset_profile()
    gates = _selected_gates()

    selected = [entry for entry in manifest["tutorials"] if _is_selected(entry, gates)]
    print(f"RDP V1 tutorial runner | gate={profile} | asset_profile={asset_profile}")
    print(f"Selected gates: {', '.join(gates)}")
    print(f"Selected entries: {len(selected)}")

    results: list[RunResult] = []
    skipped = 0

    for entry in selected:
        rel = str(entry["path"])
        script = base / rel
        skip = _skip_reason(entry)
        if skip is not None:
            skipped += 1
            print(f"SKIP {rel} | {skip}")
            continue
        if not script.is_file():
            result = RunResult(rel, str(entry.get("gate", "")), 127, False, "FAIL", None, None, None, "script missing")
            results.append(result)
            print(f"FAIL {rel} | script missing")
            if STOP_ON_FIRST_FAILURE:
                break
            continue
        if LIST_ONLY:
            print(f"LIST {rel} | {entry.get('title', '')}")
            continue

        print(f"RUN  {rel} | gate={entry.get('gate')} | title={entry.get('title', '')}")
        proc = _launch_script(repo_root, src_path, script)
        if ECHO_OUTPUT and proc.stdout:
            print(proc.stdout)
        if ECHO_OUTPUT and proc.stderr:
            print(proc.stderr, file=sys.stderr)

        result = _acceptance(entry, proc)
        results.append(result)
        metric_bits = []
        if result.match_ratio is not None:
            metric_bits.append(f"match={result.match_ratio:.3f}")
        if result.score_time_s is not None:
            metric_bits.append(f"score_time_s={result.score_time_s:.3f}")
        if result.tokens is not None:
            metric_bits.append(f"tokens={result.tokens}")
        metrics = " | " + ", ".join(metric_bits) if metric_bits else ""
        print(f"{result.status} {rel}{metrics} | {result.reason}")

        if not result.accepted and PRINT_FAILURE_TAIL:
            text = (proc.stdout or "") + "\n" + (proc.stderr or "")
            print("--- output tail ---")
            print(_tail(text))
            print("--- end tail ---")
        if not result.accepted and STOP_ON_FIRST_FAILURE:
            break

    failures = [r for r in results if not r.accepted]
    print("\nSummary")
    print(f"  selected : {len(selected)}")
    print(f"  skipped  : {skipped}")
    print(f"  run      : {len(results)}")
    print(f"  passed   : {len(results) - len(failures)}")
    print(f"  failed   : {len(failures)}")

    if failures:
        print("\nFailures")
        for failure in failures:
            print(f"  - {failure.name}: {failure.reason}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
