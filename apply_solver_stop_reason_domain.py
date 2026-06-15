#!/usr/bin/env python3
'''
Apply the D7 solver stop-reason enum-domain split.

Run from the RuneDecrypterPrime repository root with Python 3.11+.

Files changed:
  - src/rune_decrypter_prime/api/solver_report.py
  - tests/api/test_solver_report_enum_domains.py

This script is intentionally idempotent:
  - if SolverStopReason is already present, it does not insert it again;
  - if the stop_reason comparison is already migrated, it leaves it alone;
  - if expected source anchors are missing, it fails loudly instead of guessing.
'''

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path.cwd()
SOLVER_REPORT = ROOT / "src" / "rune_decrypter_prime" / "api" / "solver_report.py"
TEST_FILE = ROOT / "tests" / "api" / "test_solver_report_enum_domains.py"

SOLVER_PARAM_BLOCK = '''class SolverParamKey(StrEnum):
    TEST_KEY = "test_key"


class OracleUse(StrEnum):
'''

SOLVER_PARAM_WITH_STOP_REASON_BLOCK = '''class SolverParamKey(StrEnum):
    TEST_KEY = "test_key"


class SolverStopReason(StrEnum):
    TEST_KEY = "test_key"


class OracleUse(StrEnum):
'''

OLD_REASON_COMPARISON = "reason == OracleUse.TEST_KEY.value"
NEW_REASON_COMPARISON = "reason == SolverStopReason.TEST_KEY.value"

OLD_ALL_EXPORT_BLOCK = '''    "SolverReportDetailsVersion",
    "TruthDataPolicy",
'''

NEW_ALL_EXPORT_BLOCK = '''    "SolverReportDetailsVersion",
    "SolverStopReason",
    "TruthDataPolicy",
'''

TEST_CONTENT = '''from __future__ import annotations

from rune_decrypter_prime.api.solver_report import (
    OracleUse,
    SolverParamKey,
    SolverReportDetailKey,
    SolverStopReason,
    TruthDataPolicy,
    build_solver_report,
)


def test_solver_report_test_key_wire_value_has_separate_domains() -> None:
    assert SolverParamKey.TEST_KEY.value == "test_key"
    assert SolverStopReason.TEST_KEY.value == "test_key"
    assert OracleUse.TEST_KEY.value == "test_key"
    assert SolverParamKey.TEST_KEY is not OracleUse.TEST_KEY
    assert SolverStopReason.TEST_KEY is not OracleUse.TEST_KEY


def test_solver_report_marks_oracle_use_from_solver_param_key() -> None:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=1,
        effective_seed=1,
        normalized_params={SolverParamKey.TEST_KEY.value: [1, 2, 3]},
    )

    details = report.to_json_dict()["details"]
    assert details[SolverReportDetailKey.ORACLE_USE.value] == OracleUse.TEST_KEY.value
    assert (
        details[SolverReportDetailKey.TRUTH_DATA_POLICY.value]
        == TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value
    )


def test_solver_report_marks_oracle_use_from_solver_stop_reason() -> None:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=1,
        effective_seed=1,
        normalized_params={},
        stop_reason=SolverStopReason.TEST_KEY.value,
    )

    details = report.to_json_dict()["details"]
    assert details[SolverReportDetailKey.ORACLE_USE.value] == OracleUse.TEST_KEY.value
    assert (
        details[SolverReportDetailKey.TRUTH_DATA_POLICY.value]
        == TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value
    )
'''


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"missing required file: {path}")


def apply_solver_report_change() -> bool:
    require_file(SOLVER_REPORT)
    text = SOLVER_REPORT.read_text(encoding="utf-8")
    original = text

    if "class SolverStopReason(StrEnum):" not in text:
        if SOLVER_PARAM_BLOCK not in text:
            fail(
                "could not find SolverParamKey -> OracleUse insertion anchor in "
                f"{SOLVER_REPORT}"
            )
        text = text.replace(SOLVER_PARAM_BLOCK, SOLVER_PARAM_WITH_STOP_REASON_BLOCK, 1)

    if OLD_REASON_COMPARISON in text:
        text = text.replace(OLD_REASON_COMPARISON, NEW_REASON_COMPARISON, 1)
    elif NEW_REASON_COMPARISON not in text:
        fail(
            "could not find either old or new stop_reason comparison in "
            f"{SOLVER_REPORT}"
        )

    if '"SolverStopReason",' not in text:
        if OLD_ALL_EXPORT_BLOCK not in text:
            fail(f"could not find __all__ export insertion anchor in {SOLVER_REPORT}")
        text = text.replace(OLD_ALL_EXPORT_BLOCK, NEW_ALL_EXPORT_BLOCK, 1)

    required = [
        "class SolverStopReason(StrEnum):",
        '    TEST_KEY = "test_key"',
        NEW_REASON_COMPARISON,
        '"SolverStopReason",',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        fail(f"post-change invariant failed for {SOLVER_REPORT}: missing {missing}")

    if OLD_REASON_COMPARISON in text:
        fail(f"old oracle-domain stop_reason comparison still present in {SOLVER_REPORT}")

    if text != original:
        SOLVER_REPORT.write_text(text, encoding="utf-8")
        return True
    return False


def write_test_file() -> bool:
    TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    old = TEST_FILE.read_text(encoding="utf-8") if TEST_FILE.exists() else None
    if old == TEST_CONTENT:
        return False
    TEST_FILE.write_text(TEST_CONTENT, encoding="utf-8")
    return True


def main() -> int:
    print("[RUN ] Apply D7 solver stop-reason enum-domain split")
    changed_source = apply_solver_report_change()
    changed_test = write_test_file()

    print(f"[INFO] source file: {SOLVER_REPORT}")
    print(f"[INFO] test file:   {TEST_FILE}")
    print(f"[INFO] source changed: {changed_source}")
    print(f"[INFO] test changed:   {changed_test}")
    print("[PASS] D7 solver stop-reason enum-domain split applied")
    print()
    print("Recommended verification:")
    print("  python -m pytest -q tests/contracts/test_enum_domain_ownership.py tests/api/test_solver_report_enum_domains.py")
    print("  python -m pytest -q -p no:cacheprovider tests/contracts tests/api/test_scheduled_stream_lookup_wrappers.py tests/ciphers/test_scheduled_stream_lookup_cipher.py tests/tutorials/test_scheduled_stream_lookup_pipeline_smoke.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
