# tools/v1_audit_runner.py
# -*- coding: utf-8 -*-
"""
v1_audit_runner - repository audits + pytest.

What this does (no flags, no args):
  • Audits the real package tree (rune_decrypter_prime/...), not the repo root:
      - no magic direction tokens in code:  fwd / rev / 'ltr' / 'rtl'
      - no device magic strings outside backend mapping: cpu / cuda / cuda:N
      - no legacy telemetry keys (only *_time_s)
      - pipeline telemetry fields referenced (text_encoding_direction, input_permutation)
      - API normalization surface is present in api/normalize.py
      - scoring language-model path mapping exists (Direction → 'fwd'/'rev')
  • Runs your pytest suite in tests/ (if present)

How to use:
  - Run this module with Python.
  - To toggle audits/tests, flip RUN_AUDITS_BY_DEFAULT / RUN_TESTS_BY_DEFAULT below.

Notes:
  - We ignore comments (and try to skip docstrings) so audits don’t false-flag strings in docs.
  - Allowlists keep 'fwd'/'rev' only in scoring/language_model/paths.py, and device strings only in backends/*.
"""

from __future__ import annotations
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Dict, Optional

# -------------------------- minimal config (edit here) -----------------------
RUN_AUDITS_BY_DEFAULT = True
RUN_TESTS_BY_DEFAULT = True

DEFAULT_TEST_DIR = "tests"
PKG_NAME = "rune_decrypter_prime"   # your package folder name

WRITE_JSON_REPORT = False
JSON_REPORT_NAME = "v1_audit_report.json"

# ------------------------------- data model ----------------------------------
@dataclass
class Finding:
    file: str
    line: int
    kind: str
    text: str

@dataclass
class AuditReport:
    root: str
    magic_strings: List[Finding]
    device_strings: List[Finding]
    telemetry_legacy: List[Finding]
    telemetry_pipe_refs: List[Finding]
    api_surface: Dict[str, bool]
    scoring_paths_map_ok: bool

# ------------------------------- repo helpers --------------------------------
def _find_repo_root() -> Path:
    """
    Walk upward from this file until a directory containing src/<PKG_NAME>/ exists.
    """
    here = Path(__file__).resolve()
    cur = here.parent
    for _ in range(12):
        if (cur / "src" / PKG_NAME).is_dir():
            return cur
        cur = cur.parent
    return here.parents[4]

def _pkg_path(root: Path) -> Path:
    return root / "src" / PKG_NAME

# ------------------------------- scan helpers --------------------------------
def _strip_docstrings_and_comments(text: str) -> str:
    """
    Best-effort: remove triple-quoted docstrings and # comments so audits
    don’t match literals that live only in docs.
    """
    out_lines: List[str] = []
    in_triple = False
    triple_delim: Optional[str] = None
    for line in text.splitlines():
        l = line
        # handle triple quotes
        if not in_triple:
            if '"""' in l or "'''" in l:
                # enter docstring
                if '"""' in l and (l.count('"""') % 2 == 1):
                    in_triple, triple_delim = True, '"""'
                elif "'''" in l and (l.count("'''") % 2 == 1):
                    in_triple, triple_delim = True, "'''"
                # if starts and ends on same line (even count), keep only code before first quote
        else:
            # we are inside a triple-quoted block
            if triple_delim and triple_delim in l:
                # leave block if odd count (closing)
                if l.count(triple_delim) % 2 == 1:
                    in_triple, triple_delim = False, None
            continue  # skip docstring lines
        if in_triple:
            continue
        # strip line comments
        if "#" in l:
            l = l.split("#", 1)[0]
        out_lines.append(l)
    return "\n".join(out_lines)

def _read_clean(p: Path) -> str:
    try:
        raw = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    return _strip_docstrings_and_comments(raw)

def _scan_for_patterns(root: Path, files: Iterable[Path], patterns: Iterable[str],
                       allow_files: set[str] | None = None) -> List[Finding]:
    allow = allow_files or set()
    findings: List[Finding] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        txt = _read_clean(path)
        for i, line in enumerate(txt.splitlines(), start=1):
            for pat in patterns:
                if re.search(pat, line):
                    if rel in allow:
                        continue
                    findings.append(Finding(rel, i, pat, line.rstrip()))
    return findings

def _iter_py_files(root: Path, rel_dirs: Iterable[str]) -> Iterable[Path]:
    for d in rel_dirs:
        base = root / d
        if not base.exists():
            continue
        yield from base.rglob("*.py")

def _module_has_functions(path: Path, names: Iterable[str]) -> Dict[str, bool]:
    src = _read_clean(path)
    return {n: (re.search(rf"def\s+{re.escape(n)}\s*\(", src) is not None) for n in names}

def _any_file_contains(root: Path, rel_candidates: List[str], needles: List[str]) -> bool:
    for rel in rel_candidates:
        p = root / rel
        if p.is_file():
            src = (p.read_text(encoding="utf-8", errors="ignore"))
            if all(n in src for n in needles):
                return True
    # fallback: search scoring/language_model for a *paths.py
    lm = root / PKG_NAME / "scoring" / "language_model"
    if lm.exists():
        for p in lm.rglob("*.py"):
            try:
                src = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if all(n in src for n in needles):
                return True
    return False

# ------------------------------- audits --------------------------------------
def run_audits() -> AuditReport:
    root = _find_repo_root()
    pkg = _pkg_path(root)

    # Build include sets
    scan_dirs = [
        f"{PKG_NAME}/core",
        f"{PKG_NAME}/optimizers",
        f"{PKG_NAME}/backends",
        f"{PKG_NAME}/io",
        f"{PKG_NAME}/scoring",
        f"{PKG_NAME}/ciphers",
        f"{PKG_NAME}/keyops",
    ]
    py_files = list(_iter_py_files(root, scan_dirs))

    # Allow lists
    allow_fwd_rev = {
        f"{PKG_NAME}/scoring/language_model/paths.py",
    }
    allow_ltr_rtl = {
        f"{PKG_NAME}/core/types.py",
        f"{PKG_NAME}/io/telemetry_utils.py",
        f"{PKG_NAME}/core/telemetry.py",  # if present
    }
    allow_device = {
        f"{PKG_NAME}/backends/device.py",
        f"{PKG_NAME}/backends/xp.py",
    }

    # Patterns
    pat_dir_tokens = [r"\bfwd\b", r"\brev\b"]
    pat_dir_canon  = [r"['\"]ltr['\"]", r"['\"]rtl['\"]"]
    pat_device     = [r"\bcpu\b", r"\bcuda\b", r"cuda:[0-9]+"]
    pat_tel_legacy = [r"\bdecrypt_time\b(?!_s)", r"\bscore_time\b(?!_s)"]
    pat_tel_pipe   = [r"text_encoding_direction", r"input_permutation"]

    # 1) Magic direction tokens (fwd/rev) outside allowlist
    magic = _scan_for_patterns(root, py_files, pat_dir_tokens, allow_files=allow_fwd_rev)
    # 2) Canonical 'ltr'/'rtl' literals restricted
    magic += _scan_for_patterns(root, py_files, pat_dir_canon, allow_files=allow_ltr_rtl)
    # 3) Device strings restricted to backends file(s)
    device = _scan_for_patterns(root, py_files, pat_device, allow_files=allow_device)
    # 4) Telemetry keys & pipeline refs (only scan core/io)
    tel_files = list(_iter_py_files(root, [f"{PKG_NAME}/core", f"{PKG_NAME}/io"]))
    tel_legacy = _scan_for_patterns(root, tel_files, pat_tel_legacy, allow_files=set())
    tel_pipe   = _scan_for_patterns(root, tel_files, pat_tel_pipe, allow_files=set())

    # 5) API normalization surface
    api_norm = pkg / "api" / "normalize.py"
    api_surface = {}
    if api_norm.exists():
        api_surface = _module_has_functions(api_norm, [
            "normalize_encoding_dir",
            "normalize_device",
            "normalize_text_permutation",
            "normalize_scorer_impl",
            "normalize_optimizer_name",
        ])
    else:
        # mark all missing if the module doesn't exist
        api_surface = {k: False for k in [
            "normalize_encoding_dir",
            "normalize_device",
            "normalize_text_permutation",
            "normalize_scorer_impl",
            "normalize_optimizer_name",
        ]}

    # 6) Scoring language-model path mapper present (Direction -> 'fwd'/'rev')
    scoring_candidates = [f"{PKG_NAME}/scoring/language_model/paths.py"]
    scoring_paths_ok = _any_file_contains(root, scoring_candidates, ["fwd", "rev"])

    rep = AuditReport(
        root=str(root),
        magic_strings=magic,
        device_strings=device,
        telemetry_legacy=tel_legacy,
        telemetry_pipe_refs=tel_pipe,
        api_surface=api_surface,
        scoring_paths_map_ok=scoring_paths_ok,
    )

    _print_report(rep)
    if WRITE_JSON_REPORT:
        out = Path(__file__).with_name(JSON_REPORT_NAME)
        out.write_text(json.dumps(asdict(rep), indent=2), encoding="utf-8")
        print(f"\nJSON report written to {out}")

    return rep

def _print_report(rep: AuditReport) -> None:
    def _pp(title: str, findings: List[Finding], ok_msg="OK"):
        if not findings:
            print(f"[PASS] {title}: {ok_msg}")
        else:
            print(f"[FAIL] {title}: {len(findings)} issue(s)")
            for f in findings[:200]:
                print(f"  - {f.file}:{f.line}  {f.text}")
            if len(findings) > 200:
                print(f"  (+{len(findings)-200} more)")

    print("\n== v1 static audits ==")
    _pp("No magic direction tokens in code (fwd/rev/'ltr'/'rtl') outside allowlist", rep.magic_strings)
    _pp("No device magic strings outside backends mapping (cpu/cuda/cuda:N)", rep.device_strings)
    _pp("No legacy telemetry keys (decrypt_time/score_time without _s)", rep.telemetry_legacy)

    if rep.telemetry_pipe_refs:
        print(f"[PASS] Pipeline telemetry references present ({len(rep.telemetry_pipe_refs)} hits)")
    else:
        print("[WARN] No references to pipeline telemetry fields found; verify emission paths.")

    print("\nAPI normalization surface:")
    for k, ok in rep.api_surface.items():
        print(("  [OK] " if ok else "  [MISSING] ") + k)

    print("\nScoring paths mapping (Direction -> 'fwd'/'rev'):")
    print("  [OK] present" if rep.scoring_paths_map_ok else "  [MISSING] mapping not detected")

# ------------------------------- pytest runner --------------------------------
def run_tests(pytest_k: str | None = None, extra_args: list[str] | None = None) -> int:
    """
    Programmatically run pytest on tests/ if it exists under repo root.
    Set pytest_k / extra_args from the Python console if you want a subset.
    """
    try:
        import pytest  # type: ignore
    except Exception:
        print("PyTest is not installed. `pip install pytest`")
        return 3

    root = _find_repo_root()
    test_dir = root / DEFAULT_TEST_DIR
    args: list[str] = []
    if test_dir.exists():
        args.append(str(test_dir))
    else:
        print(f"[WARN] Test folder not found: {test_dir}")

    if pytest_k:
        args += ["-k", pytest_k]
    if extra_args:
        args += list(extra_args)

    print("\n== running pytest ==")
    print("pytest", " ".join(args))
    return pytest.main(args)

# ------------------------------- main combo ----------------------------------
def run_all() -> int:
    code = 0
    if RUN_AUDITS_BY_DEFAULT:
        rep = run_audits()
        if rep.magic_strings or rep.device_strings or rep.telemetry_legacy or not all(rep.api_surface.values()) or not rep.scoring_paths_map_ok:
            code = 2
    if RUN_TESTS_BY_DEFAULT:
        tcode = run_tests()
        code = code or tcode
    return code

if __name__ == "__main__":
    sys.exit(run_all())
