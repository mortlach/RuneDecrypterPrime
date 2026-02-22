# tools/benchmarks/repo_tools/repo_utils/run_patches.py
from pathlib import Path
import sys
from apply_patches_module import load_manifest_from_py, preflight_report, apply_patches


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]


ROOT = _repo_root()
MANI = ROOT / "output" / "tools" / "benchmarks" / "repo_tools" / "patches" / "patch_fix.py"


def _summarize(report: dict) -> dict:
    files = report.get("files", [])
    total_actions = sum(int(f.get("applied", 0)) for f in files)
    files_with_errors = [(f.get("file"), f.get("errors", [])) for f in files if f.get("errors")]
    missing = [(fn, errs) for fn, errs in files_with_errors if any("file not found" in e for e in errs)]
    changed = sum(1 for f in files if int(f.get("applied", 0)) > 0)
    return {
        "total_files": len(files),
        "changed_files": changed,
        "total_actions": total_actions,
        "errors": files_with_errors,
        "missing": missing,
        "ok": (not files_with_errors) and (total_actions > 0),
    }

def _print_summary(title: str, report: dict) -> None:
    s = _summarize(report)
    mark = "✅" if s["ok"] else ("⚠️" if s["errors"] else "ℹ️")
    print("\n" + "=" * 72)
    print(f"{mark} {title} SUMMARY")
    print("-" * 72)
    print(f"root:           {report.get('root')}")
    print(f"files seen:     {s['total_files']}")
    print(f"actions total:  {s['total_actions']}")
    print(f"files changed:  {s['changed_files']}")
    if s["missing"]:
        print(f"missing files:  {len(s['missing'])}")
        for fn, errs in s["missing"][:8]:
            print(f"  - {fn}")
        if len(s["missing"]) > 8:
            print(f"  ... (+{len(s['missing']) - 8} more)")
    if s["errors"]:
        print(f"errors:         {sum(len(errs) for _, errs in s['errors'])} across {len(s['errors'])} file(s)")
        for fn, errs in s["errors"][:6]:
            print(f"  - {fn}")
            for e in errs[:3]:
                print(f"      • {e}")
        if len(s["errors"]) > 6:
            print(f"  ... (+{len(s['errors']) - 6} more files with errors)")
    print("=" * 72 + "\n")
    return None

def main():
    print(f"[patch] ROOT = {ROOT}")
    print(f"[patch] MANIFEST = {MANI}")
    manifest = load_manifest_from_py(MANI)

    # 1) Preflight (just to show matches/locations up-front)
    pre = preflight_report(manifest, ROOT)
    print(pre)

    # 2) Dry-run apply
    dry = apply_patches(manifest, ROOT, dry_run=True)
    print(dry)
    _print_summary("DRY-RUN", dry)

    s_dry = _summarize(dry)
    if s_dry["errors"]:
        print("❌ Dry-run found errors. Aborting real apply to keep things safe.")
        sys.exit(1)
    if s_dry["total_actions"] == 0:
        print("ℹ️ Dry-run applied 0 actions (nothing to do).")
        sys.exit(0)

    # 3) Real apply (only if dry-run had no errors)
    real = apply_patches(manifest, ROOT, dry_run=False)
    print(real)
    _print_summary("APPLY", real)

    s_real = _summarize(real)
    if s_real["errors"]:
        print("❌ Apply completed WITH ERRORS. Please review the summary above.")
        sys.exit(2)
    else:
        print("✅ Apply completed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
