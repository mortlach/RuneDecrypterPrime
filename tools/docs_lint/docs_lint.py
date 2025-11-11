# RDP Docs Lint — general-audience friendly
# - Prints a helpful console summary
# - Syntax-checks fenced Python blocks in docs/
# - Computes coverage from project_symbol_index.txt, or falls back to scanning src/
# - Checks relative .md links
# - Writes JSON + Markdown reports

import argparse
import re, json, ast, os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

# ---------- CONFIG ----------
REPO_ROOT   = Path(__file__).resolve().parents[2]
DOCS_ROOT   = REPO_ROOT / "docs"
SRC_ROOT    = REPO_ROOT / "src"
# Default to the canonical output tree even when invoked directly,
# so runs never write outside the repo's output/ folder.
DEFAULT_OUTPUT_DIR = (REPO_ROOT / "output" / "tools" / "docs_lint" / "manual").resolve()

# Try these, in order
SYMBOL_FILES = [
    REPO_ROOT / "project_symbol_index.txt",
    REPO_ROOT / "tools" / "project_symbol_index.txt",
    REPO_ROOT / "tools" / "symbols" / "project_symbol_index.txt",
    REPO_ROOT / "tools" / "out" / "project_symbol_index.txt",
]

# Tweak as you like
CANON_ENUM_WORDS = ["Direction.LTR", "Direction.RTL", "Device.CPU"]
DENY_WORDS: List[str] = []  # keep empty for general audience

MD_FOLDERS = ["guides", "tutorials", "howto", "reference", "architecture", "appendices"]

# ---------- Symbol support ----------
def _rel(path: Path | str) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except Exception:
        return str(path)


def load_symbol_index() -> Tuple[Dict[str, int], Dict[str, int], str]:
    """Return (class_hits_map, function_hits_map, source_note). If no index, create from src/."""
    sym_path = next((p for p in SYMBOL_FILES if p.exists()), None)
    if sym_path:
        text = sym_path.read_text(encoding="utf-8", errors="ignore")
        classes, functions = set(), set()
        # Very forgiving parser: accept lines like "[class] pkg.mod QualName Name"
        line_re = re.compile(r'^\[(class|function)\]\s+(\S+)\s+(\S+)\s+(\S+)')
        for line in text.splitlines():
            m = line_re.match(line.strip())
            if not m:
                continue
            kind, _module, qual, name = m.groups()
            if kind == "class":
                classes.add(qual.split(".")[-1])
            elif kind == "function":
                functions.add(name.split("(")[0])
        return ({c: 0 for c in classes}, {f: 0 for f in functions}, f"loaded: {_rel(sym_path)}")
    # Fallback: scan src/ for top-level class/def names
    classes, functions = set(), set()
    for py in SRC_ROOT.rglob("*.py"):
        try:
            src = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except Exception:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.add(node.name)
    return ({c: 0 for c in classes}, {f: 0 for f in functions}, f"fallback scan of {_rel(SRC_ROOT)}")

# ---------- Markdown scanning ----------
@dataclass
class CodeBlockResult:
    file: str
    block_idx: int
    lang: str
    ok_syntax: bool
    errors: List[str]

@dataclass
class PageResult:
    file: str
    code_blocks: List[CodeBlockResult]
    deprecated_hits: List[str]
    canon_hits: List[str]

def extract_code_blocks(md_text: str):
    blocks = []
    # Capture language and content; be forgiving about trailing spaces
    fence_re = re.compile(r'```(\w+)?\s*\n(.*?)\n```', re.S)
    for m in fence_re.finditer(md_text):
        lang = (m.group(1) or "").strip().lower()
        code = m.group(2)
        blocks.append((lang, code))
    return blocks

def check_code_block(lang: str, code: str):
    ok, errors = True, []
    if lang in ("python", ""):
        try:
            ast.parse(code)
        except SyntaxError as e:
            ok = False
            errors.append(f"{e.__class__.__name__}: {e.msg} (line {e.lineno})")
    return ok, errors

def scan_markdown(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    blocks = extract_code_blocks(text)
    results, deprecated_hits, canon_hits = [], [], []
    rel_path = path.relative_to(REPO_ROOT)
    for i, (lang, code) in enumerate(blocks, start=1):
        ok, errs = check_code_block(lang, code)
        results.append(CodeBlockResult(str(rel_path), i, lang, ok, errs))
        # enums present?
        for w in CANON_ENUM_WORDS:
            if w in code:
                canon_hits.append(f"{path.name}:{w}")
        # deny-words?
        lower = code.lower()
        for dw in DENY_WORDS:
            if dw.lower() in lower:
                deprecated_hits.append(f"{path.name}:{dw}")
    return PageResult(str(rel_path), results, deprecated_hits, canon_hits)

def scan_all_markdown(docs_root: Path):
    pages = []
    for folder in MD_FOLDERS:
        root = docs_root / folder
        if not root.exists():
            continue
        for md in root.rglob("*.md"):
            pages.append(scan_markdown(md))
    return pages

def coverage_from_pages(pages: List[PageResult], class_map: Dict[str, int], fn_map: Dict[str, int]):
    # Count mentions by simple name anywhere in docs text
    all_text = []
    for p in pages:
        try:
            all_text.append((REPO_ROOT / p.file).read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            pass
    big = "\n".join(all_text)
    for c in list(class_map.keys()):
        class_map[c] = len(re.findall(rf'\b{re.escape(c)}\b', big))
    for f in list(fn_map.keys()):
        fn_map[f] = len(re.findall(rf'\b{re.escape(f)}\b', big))
    return class_map, fn_map

# ---------- Link check ----------
def find_md_links(text: str):
    return re.findall(r'\[[^\]]+\]\(([^)]+\.md)\)', text)

def link_check(docs_root: Path):
    missing = []
    for folder in MD_FOLDERS:
        root = docs_root / folder
        if not root.exists():
            continue
        for md in root.rglob("*.md"):
            text = md.read_text(encoding="utf-8", errors="ignore")
            for link in find_md_links(text):
                target = (md.parent / link).resolve()
                if not target.exists():
                    missing.append(f"{md.relative_to(docs_root)} -> {link}")
    return missing

# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="Rune Decrypter Prime docs lint")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory that will receive docs_lint_report.(json|md)",
    )
    args = parser.parse_args()

    output_dir = Path(args.out_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    class_hits_map, fn_hits_map, symbol_note = load_symbol_index()
    pages = scan_all_markdown(DOCS_ROOT)

    # Aggregate
    syntax_errors = [blk for p in pages for blk in p.code_blocks if not blk.ok_syntax]
    deprecated   = [hit for p in pages for hit in p.deprecated_hits]
    canon        = [hit for p in pages for hit in p.canon_hits]
    broken_links = link_check(DOCS_ROOT)

    # Coverage
    class_hits_map, fn_hits_map = coverage_from_pages(pages, class_hits_map, fn_hits_map)
    classes_total = len(class_hits_map); classes_doc = sum(1 for v in class_hits_map.values() if v > 0)
    fns_total     = len(fn_hits_map);   fns_doc     = sum(1 for v in fn_hits_map.values() if v > 0)

    report = {
        "pages_scanned": len(pages),
        "syntax_error_blocks": len(syntax_errors),
        "deprecated_hits": deprecated,
        "canon_hits_count": len(canon),
        "broken_links": broken_links,
        "coverage": {
            "classes_documented_nonzero": classes_doc,
            "classes_total": classes_total,
            "functions_documented_nonzero": fns_doc,
            "functions_total": fns_total,
        },
        "symbol_source": symbol_note,
        "timestamp": datetime.now().isoformat(),
        "syntax_errors_detail": [
            {
                "file": _rel(e.file),
                "block_index": e.block_idx,
                "lang": e.lang,
                "errors": e.errors,
            }
            for e in syntax_errors
        ],
    }

    # Write JSON
    (output_dir / "docs_lint_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Write Markdown
    md = []
    md.append(f"# Docs Lint Report — {report['timestamp']}")
    md.append(f"- Pages scanned: **{report['pages_scanned']}**")
    md.append(f"- Code blocks with syntax errors: **{report['syntax_error_blocks']}**")
    if syntax_errors:
        md.append("\n## Syntax errors")
        for e in report["syntax_errors_detail"][:200]:
            md.append(f"- {e['file']} (block {e['block_index']}): {', '.join(e['errors'])}")
        if len(report["syntax_errors_detail"]) > 200:
            md.append(f"...and {len(report['syntax_errors_detail'])-200} more")
    md.append(f"\n- Canonical enum hits in examples: **{report['canon_hits_count']}**")
    md.append(f"- Symbol source: `{report['symbol_source']}`")
    md.append("\n## Coverage")
    md.append(f"- Classes documented: **{classes_doc} / {classes_total}**")
    md.append(f"- Functions documented: **{fns_doc} / {fns_total}**")
    if broken_links:
        md.append("\n## Broken links")
        for b in broken_links[:200]:
            md.append(f"- {b}")
        if len(broken_links) > 200:
            md.append(f"...and {len(broken_links)-200} more")
    if deprecated:
        md.append("\n## Deprecated tokens (deny-list)")
        for d in deprecated[:100]:
            md.append(f"- {d}")
        if len(deprecated) > 100:
            md.append(f"...and {len(deprecated)-100} more")
    (output_dir / "docs_lint_report.md").write_text("\n".join(md), encoding="utf-8")

    # Console summary
    print(f"[docs-lint] Pages: {report['pages_scanned']}, "
          f"Syntax errors: {report['syntax_error_blocks']}, "
          f"Broken links: {len(broken_links)}, "
          f"Coverage(classes): {classes_doc}/{classes_total}, "
          f"Coverage(functions): {fns_doc}/{fns_total}")
    if syntax_errors:
        print("  Top syntax errors:")
        for e in report["syntax_errors_detail"][:10]:
            print(f"   - {e['file']} (block {e['block_index']}): {', '.join(e['errors'])}")
    if broken_links:
        print("  Example broken link:", broken_links[0])
    rel_out = _rel(output_dir)
    print(f"[docs-lint] Reports written to {rel_out}")

if __name__ == "__main__":
    main()
