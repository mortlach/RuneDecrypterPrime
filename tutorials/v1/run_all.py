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
GATE_PROFILE = "release"

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
    try:
        return GATE_PRESETS[GATE_PROFILE]
    except KeyError as exc:
        valid = ", ".join(sorted(GATE_PRESETS))
        raise ValueError(f"Unknown GATE_PROFILE={GATE_PROFILE!r}; expected one of: {valid}") from exc


def _parse_last_float(pattern: str, text: str) -> float | None:
    vals = re.findall(pattern, text, flags=re.IGNORECASE)
    if not vals:
        return None
    try:
        return float(vals[-1])
    except ValueError:
        return None


def _parse_match_ratio(text: str) -> float | None:
    return _parse_last_float(r"Match ratio(?:\s*\([^)]*\))?:\s*([0-9]+(?:\.[0-9]+)?)", text)


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

    if gate in KNOWN_BLOCKED_GATES and not RUN_KNOWN_BROKEN:
        return f"known blocked gate: {gate}"

    if current_status in {"known_broken", "remove_from_pure_release"} and not RUN_KNOWN_BROKEN:
        return f"known blocked status: {current_status}"

    if required_asset_profile and required_asset_profile not in {ASSET_PROFILE, "unknown"}:
        return f"requires asset profile {required_asset_profile}, current profile is {ASSET_PROFILE}"

    if str(entry.get("expected_under_lm2_baseline", "")).strip() == "skip" and ASSET_PROFILE == "lm2_baseline":
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

    return RunResult(
        name=name,
        gate=gate,
        returncode=int(proc.returncode),
        accepted=bool(accepted),
        status=status,
        match_ratio=match_ratio,
        score_time_s=score_time_s,
        tokens=tokens,
        reason=reason,
    )


def _print_compact_result(result: RunResult) -> None:
    fields = [
        result.status,
        result.name,
        f"gate={result.gate}",
        f"returncode={result.returncode}",
    ]
    if result.match_ratio is not None:
        fields.append(f"match={result.match_ratio:.3f}")
    if result.score_time_s is not None:
        fields.append(f"score_time_s={result.score_time_s:.3f}")
    if result.tokens is not None:
        fields.append(f"tokens={result.tokens}")
    fields.append(result.reason)
    print(" | ".join(fields))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    base = Path(__file__).resolve().parent
    repo_root = base.parents[1]
    src_path = repo_root / "src"
    manifest = _load_manifest(base)
    gates = _selected_gates()

    tutorials = manifest["tutorials"]
    selected = [entry for entry in tutorials if _is_selected(entry, gates)]

    skipped: list[tuple[str, str]] = []
    runnable: list[dict[str, Any]] = []
    for entry in selected:
        reason = _skip_reason(entry)
        if reason:
            skipped.append((str(entry.get("path", "<missing-path>")), reason))
        else:
            runnable.append(entry)

    print("============================================================")
    print("RDP tutorial gate runner")
    print(f"gate_profile : {GATE_PROFILE}")
    print(f"asset_profile: {ASSET_PROFILE}")
    print(f"selected gates: {', '.join(gates)}")
    print(f"selected entries: {len(selected)}")
    print(f"runnable entries: {len(runnable)}")
    print(f"skipped entries : {len(skipped)}")
    print("============================================================")

    if skipped:
        print("\nSkipped:")
        for path, reason in skipped:
            print(f"- {path}: {reason}")

    if LIST_ONLY:
        print("\nRunnable:")
        for entry in runnable:
            print(f"- {entry['path']} [{entry.get('gate')}]")
        return 0

    results: list[RunResult] = []

    for entry in runnable:
        script = base / str(entry["path"])
        print(f"\n=== Running {script.name} [{entry.get('gate')}] ===")
        if not script.exists():
            result = RunResult(
                name=str(entry["path"]),
                gate=str(entry.get("gate", "")),
                returncode=999,
                accepted=False,
                status="FAIL",
                match_ratio=None,
                score_time_s=None,
                tokens=None,
                reason=f"script not found: {script}",
            )
            results.append(result)
            _print_compact_result(result)
            if STOP_ON_FIRST_FAILURE:
                break
            continue

        proc = _launch_script(repo_root, src_path, script)

        if ECHO_OUTPUT:
            if proc.stdout:
                print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
            if proc.stderr:
                print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n")

        result = _acceptance(entry, proc)
        results.append(result)
        _print_compact_result(result)

        if not result.accepted and PRINT_FAILURE_TAIL:
            combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
            print("\n--- failure/near-solve output tail ---")
            print(_tail(combined))
            print("--- end tail ---")

        if STOP_ON_FIRST_FAILURE and not result.accepted:
            break

    passed = sum(1 for item in results if item.status == "PASS")
    near = sum(1 for item in results if item.status == "NEAR_SOLVE_ACCEPTED")
    failed = sum(1 for item in results if item.status == "FAIL")

    print("\n============================================================")
    print("Summary")
    print(f"gate_profile       : {GATE_PROFILE}")
    print(f"asset_profile      : {ASSET_PROFILE}")
    print(f"selected           : {len(selected)}")
    print(f"run                : {len(results)}")
    print(f"passed             : {passed}")
    print(f"near_solve_accepted: {near}")
    print(f"failed             : {failed}")
    print(f"skipped            : {len(skipped)}")
    print("============================================================")

    if failed:
        print("\nFailures:")
        for item in results:
            if item.status == "FAIL":
                print(f"- {item.name}: {item.reason}")
        return 1

    print("\nSelected tutorial gate completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
