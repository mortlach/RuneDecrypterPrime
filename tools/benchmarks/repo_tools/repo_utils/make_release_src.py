# -*- coding: utf-8 -*-
"""
make_release_src.py — Build a clean, tester-ready “src” snapshot.

Outputs to:
  <ROOT>/output/release/
with ALL source + docs + data/ rebased into rune_decrypter_prime/ ,
and language_model/lmp pruned to exactly the n-gram orders requested.

This script matches the canonical layout you posted:
data/
  language_model/
    lmp/
      char/{ltr,rtl}
      wli/{ltr,rtl}
      ecdf/
        char/{ltr,rtl}
        wli/{ltr,rtl}
"""

from __future__ import annotations
from pathlib import Path
import shutil
import hashlib
import json
import re
from typing import Iterable

# ============================== CONFIG ==================================

def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]


ROOT = _repo_root()
OUT_DIR = ROOT / "output" / "release"

# Where to place data inside the built snapshot (always under the package)
DATA_DEST_BASE = "rune_decrypter_prime/data"

# Detect the source data root (first existing wins)
DATA_SRC_CANDIDATES: list[str] = [
    "src/rune_decrypter_prime/data",
    "data",
    "rune_decrypter_prime/data",
    "rune_decrypter_prime/data_dev",
]

# Ensure these subdirectories under data/ always exist in the release
DATA_FORCE_DIRS = {
    "liber_primus",
    "cipher_tests",
}

INCLUDE_DIRS: list[str] = [
    "src/rune_decrypter_prime/backends",
    "src/rune_decrypter_prime/ciphers",
    "src/rune_decrypter_prime/core",
    "src/rune_decrypter_prime/examples",
    "src/rune_decrypter_prime/io",
    "src/rune_decrypter_prime/solvers",
    "src/rune_decrypter_prime/scoring",
    "src/rune_decrypter_prime/tutorials",
    "src/rune_decrypter_prime/patche_old_ui",
    "src/rune_decrypter_prime/utils",
    "src/rune_decrypter_prime/keyops",
]

INCLUDE_FILES: list[str] = [
    "src/rune_decrypter_prime/__init__.py",
    "README.md",
    "INSTALL.md",
    "TUTORIALS.md",
]

# Allowed file types for non-data copying
ALLOWED_EXTS = {
    ".py", ".txt", ".md",
    ".json", ".npz",
    ".bin", ".zst", ".bin.zst",
    ".cpp", ".h", ".hpp", ".pyd",
}

EXCLUDED_DIR_NAMES = {
    ".git", ".idea", ".vscode",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "build", "dist", ".eggs", ".venv", "venv",
    "out", "logs", "log",
    "dev",
}

EXCLUDED_PATH_PREFIXES = {
    Path("src/rune_decrypter_prime/ciphers/legacy"),
    Path("src/rune_decrypter_prime/scoring/language_model/build_lib"),
    Path("output"), Path("output/logs"), Path("output/trace"),
    Path("output/tests"), Path("output/tutorials"), Path("output/share"),
    Path("tests/output"), Path("tests/output/logs"), Path("tests/output/trace"),
    Path("docs"), Path(".github"),
}

# ---------- Language Model (LMP) pruning, as per your canonical tree ----------
LM_BASE_REL = Path("language_model/lmp")  # relative to data root
LM_DIRECTIONS = {"ltr", "rtl"}
LM_MODELS = {"char", "wli"}         # top-level models
LM_META_KEEP = [                    # LM metadata to keep even if not matching orders
    Path("language_model/__init__.py"),
    Path("language_model/lmp/index.json"),
]

# Orders to include (1..4). You said: “char and wli and ecdf should be copied always and for specified 1,2,3,4 grams”.
LM_ALLOWED_ORDERS = {1, 2}  # ← change to {1,2,3,4} if you want all four
INCLUDE_ECDF = True         # ← you said ecdf should be copied (subject to orders)

DRY_RUN = False
VERBOSE = True

# ============================ HELPERS ===================================

def posix(p: Path) -> str:
    return str(p).replace("\\", "/")

def ensure_clean_dir(dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def write_manifest(root: Path) -> None:
    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rows.append({
                "path": posix(p.relative_to(root)),
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            })
    (root / "MANIFEST.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

def is_under_prefix(path: Path, root: Path, prefix: Path) -> bool:
    try:
        path.relative_to(root / prefix)
        return True
    except Exception:
        return False

def should_skip_dir(d: Path, root: Path) -> bool:
    if d.name in EXCLUDED_DIR_NAMES:
        return True
    for pref in EXCLUDED_PATH_PREFIXES:
        if is_under_prefix(d, root, pref):
            return True
    return False

def has_allowed_ext(f: Path) -> bool:
    suf = f.suffix.lower()
    if suf in ALLOWED_EXTS:
        return True
    s2 = "".join(s.lower() for s in f.suffixes[-2:])
    if s2 in ALLOWED_EXTS:
        return True
    s3 = "".join(s.lower() for s in f.suffixes[-3:])
    return s3 in ALLOWED_EXTS

def copy_file(src: Path, dst: Path, copied: list[Path], tag: str = "") -> None:
    if DRY_RUN:
        print(f"[DRY] {tag:7} {posix(src)}  →  {posix(dst)}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(dst)
    if VERBOSE:
        print(f"[COPY] {tag:7} {posix(src)}  →  {posix(dst)}")

# ============================ DATA COPY =================================

def choose_data_root() -> Path | None:
    print("\n[Data source search]")
    for rel in DATA_SRC_CANDIDATES:
        p = ROOT / rel
        print(f"  check: {posix(p)}")
        if p.exists():
            print(f"[INFO] Using data source root: {posix(p)}")
            return p
    print("[WARN] data/ directory not found in any candidate.")
    return None

def mirror_data_dirs(src_data: Path, dst_root: Path) -> None:
    dest_data = dst_root / DATA_DEST_BASE
    dest_data.mkdir(parents=True, exist_ok=True)
    if not src_data.exists():
        return
    for d in src_data.rglob("*"):
        if d.is_dir():
            if should_skip_dir(d, ROOT):
                continue
            rel = d.relative_to(src_data)
            (dest_data / rel).mkdir(parents=True, exist_ok=True)
    for force_name in DATA_FORCE_DIRS:
        (dest_data / force_name).mkdir(parents=True, exist_ok=True)

def copy_non_lm_data(src_data: Path, dst_root: Path, copied: list[Path]) -> dict:
    """
    Copy everything under data/** EXCEPT data/language_model/**
    """
    stats = {"scanned": 0, "copied": 0, "dirs_skipped": 0}
    lm_root = src_data / "language_model"
    for p in src_data.rglob("*"):
        if p.is_dir():
            if should_skip_dir(p, ROOT):
                stats["dirs_skipped"] += 1
            continue
        # skip the LM tree here; handled by dedicated pass
        try:
            p.relative_to(lm_root)
            continue
        except Exception:
            pass

        stats["scanned"] += 1
        rel = p.relative_to(src_data)
        dst = dst_root / DATA_DEST_BASE / rel
        copy_file(p, dst, copied, tag="normal")
        stats["copied"] += 1
    return stats

# ============================ LM (LMP) COPY =============================

# RegEx to detect "order" from filenames:
#   - For model zst files: last numeric token is the n-gram (e.g., ..._2_nose.bin.zst → 2)
NUM_IN_NAME_RE = re.compile(r"(?:^|[_\-])([0-9]+)(?:[^0-9]|$)")
#   - For ecdf npz files: use n1/n2... tokens (e.g., ..._n3_... → 3)
ECDF_ORDER_RE  = re.compile(r"(?:^|[_\-])n([0-9]+)(?:[^0-9]|$)", re.IGNORECASE)

def infer_order_from_name(name: str, allowed: set[int] | None = None, ecdf: bool = False) -> int | None:
    if ecdf:
        m = ECDF_ORDER_RE.search(name)
        n = int(m.group(1)) if m else None
        if n is None:
            return None
        return n if (not allowed or n in allowed) else None
    # normal (zst) path: take the LAST numeric token that is in allowed (if provided)
    nums = [int(m.group(1)) for m in NUM_IN_NAME_RE.finditer(name)]
    if not nums:
        return None
    if allowed:
        for n in reversed(nums):
            if n in allowed:
                return n
        return None
    return nums[-1]

def copy_lmp_tree(src_data: Path, dst_root: Path, copied: list[Path]) -> dict:
    """
    Copy:
      data/language_model/lmp/char/{ltr,rtl}/*.zst matching LM_ALLOWED_ORDERS
      data/language_model/lmp/wli/{ltr,rtl}/*.zst matching LM_ALLOWED_ORDERS
      data/language_model/lmp/ecdf/{char,wli}/{ltr,rtl}/*.npz matching orders if INCLUDE_ECDF
    Also copy LM metadata listed in LM_META_KEEP.
    """
    stats = {"scanned": 0, "copied": 0, "skipped": 0, "meta": 0}
    lmp_root = src_data / LM_BASE_REL
    if not lmp_root.exists():
        print(f"[INFO] No {posix(LM_BASE_REL)} directory under data/, skipping LM pass.")
        return stats

    # 1) Copy metadata first
    for rel in LM_META_KEEP:
        p = src_data / rel
        if p.exists() and p.is_file():
            dst = dst_root / DATA_DEST_BASE / rel
            copy_file(p, dst, copied, tag="LMmeta")
            stats["copied"] += 1
            stats["meta"] += 1

    # 2) Copy CHAR/WLI models
    for model in LM_MODELS:
        for direction in LM_DIRECTIONS:
            base = lmp_root / model / direction
            if not base.exists():
                continue
            for f in base.iterdir():
                if f.is_dir():
                    continue
                stats["scanned"] += 1
                n = infer_order_from_name(f.name, allowed=LM_ALLOWED_ORDERS, ecdf=False)
                if n is None:
                    stats["skipped"] += 1
                    if VERBOSE:
                        print(f"[SKIP] LM-{model:<4} {posix(f)} — reason: order-miss (allowed={sorted(LM_ALLOWED_ORDERS)})")
                    continue
                rel = f.relative_to(src_data)
                dst = dst_root / DATA_DEST_BASE / rel
                copy_file(f, dst, copied, tag=f"LM-{model}")
                stats["copied"] += 1

    # 3) Copy ECDF if requested
    ecdf_root = lmp_root / "ecdf"
    if INCLUDE_ECDF and ecdf_root.exists():
        for model in LM_MODELS:
            for direction in LM_DIRECTIONS:
                base = ecdf_root / model / direction
                if not base.exists():
                    continue
                for f in base.iterdir():
                    if f.is_dir():
                        continue
                    stats["scanned"] += 1
                    n = infer_order_from_name(f.name, allowed=LM_ALLOWED_ORDERS, ecdf=True)
                    if n is None:
                        stats["skipped"] += 1
                        if VERBOSE:
                            print(f"[SKIP] LM-ecdf {posix(f)} — reason: order-miss (allowed={sorted(LM_ALLOWED_ORDERS)})")
                        continue
                    rel = f.relative_to(src_data)
                    dst = dst_root / DATA_DEST_BASE / rel
                    copy_file(f, dst, copied, tag="LM-ecdf")
                    stats["copied"] += 1
    elif not INCLUDE_ECDF:
        print("[INFO] ECDF disabled; skipping ecdf subtree.")

    return stats

# ============================ MAIN BUILD ================================

def copy_src_dirs(root: Path, dst_root: Path, dirs: Iterable[str], copied: list[Path]) -> dict:
    stats = {"scanned": 0, "copied": 0, "skipped": 0, "dirs_skipped": 0}
    for rel in dirs:
        src = root / rel
        if not src.exists():
            print(f"[INFO] Missing source dir (skipped): {rel}")
            continue
        for p in src.rglob("*"):
            if p.is_dir():
                if should_skip_dir(p, root):
                    stats["dirs_skipped"] += 1
                continue
            stats["scanned"] += 1
            # apply ext allowlist to non-data code
            if not has_allowed_ext(p):
                stats["skipped"] += 1
                continue
            dst = dst_root / p.relative_to(root)
            copy_file(p, dst, copied, tag="src")
            stats["copied"] += 1
    return stats

def copy_top_files(root: Path, dst_root: Path, files: Iterable[str], copied: list[Path]) -> dict:
    stats = {"copied": 0, "skipped": 0}
    for rel in files:
        src = root / rel
        if src.exists() and src.is_file() and has_allowed_ext(src):
            dst = dst_root / rel
            copy_file(src, dst, copied, tag="top")
            stats["copied"] += 1
        else:
            if VERBOSE:
                print(f"[SKIP]   top  {posix(src)}")
            stats["skipped"] += 1
    return stats

def build_release() -> dict:
    print("=== Building release snapshot ===")
    print(f"ROOT   : {posix(ROOT)}")
    print(f"OUT_DIR: {posix(OUT_DIR)}")
    print(f"DATA DEST: '{DATA_DEST_BASE}'")
    print("LM cfg :", json.dumps({
        "orders": sorted(LM_ALLOWED_ORDERS),
        "models": sorted(LM_MODELS),
        "directions": sorted(LM_DIRECTIONS),
        "include_ecdf": bool(INCLUDE_ECDF),
    }, indent=2))

    ensure_clean_dir(OUT_DIR)
    copied: list[Path] = []

    # 0) data root choice
    src_data_root = choose_data_root()

    # 1) mirror data dirs (so empty dirs exist)
    if src_data_root:
        mirror_data_dirs(src_data_root, OUT_DIR)

    # 2) copy source trees (code, etc.)
    src_stats = copy_src_dirs(ROOT, OUT_DIR, INCLUDE_DIRS, copied)

    # 3) copy non-LM data
    nond_stats = {"scanned": 0, "copied": 0, "dirs_skipped": 0}
    if src_data_root:
        nond_stats = copy_non_lm_data(src_data_root, OUT_DIR, copied)

    # 4) copy LMP per rules
    lm_stats = {"scanned": 0, "copied": 0, "skipped": 0, "meta": 0}
    if src_data_root:
        lm_stats = copy_lmp_tree(src_data_root, OUT_DIR, copied)

    # 5) copy top-level files
    top_stats = copy_top_files(ROOT, OUT_DIR, INCLUDE_FILES, copied)

    if not DRY_RUN:
        write_manifest(OUT_DIR)

    total_bytes = sum(p.stat().st_size for p in copied) if not DRY_RUN else 0

    # Summary
    print("\n=== Release Summary ===")
    print(f"Out dir : {posix(OUT_DIR)}")
    print(f"Files   : {len(copied)}")
    if not DRY_RUN:
        print(f"Bytes   : {total_bytes:,}")

    print("\n[Source trees]")
    print(f"  scanned={src_stats['scanned']}  copied={src_stats['copied']}  skipped={src_stats['skipped']}  dirs_skipped={src_stats['dirs_skipped']}")

    if src_data_root:
        print("\n[Non-LM data]")
        print(f"  scanned={nond_stats['scanned']}  copied={nond_stats['copied']}  dirs_skipped={nond_stats['dirs_skipped']}")

        print("\n[LM (lmp) data]")
        print(f"  scanned={lm_stats['scanned']}  copied={lm_stats['copied']}  skipped={lm_stats['skipped']}  meta={lm_stats['meta']}")

        print("\n[Data root chosen]")
        print(f"  {posix(src_data_root)}")
    else:
        print("\n[Data root chosen]")
        print("  <none>")

    print()
    return {"files": len(copied), "bytes": total_bytes, "out_dir": posix(OUT_DIR)}

# ============================ ENTRYPOINT ================================

if __name__ == "__main__":
    build_release()
