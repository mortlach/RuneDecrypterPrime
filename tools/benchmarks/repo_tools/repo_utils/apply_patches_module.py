
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import argparse
import ast
import importlib.util
import json
import re

def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]

def _detect_newline_style(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"

def _read(path: Path) -> Tuple[str, str]:
    raw = path.read_text(encoding="utf-8")
    nl = _detect_newline_style(raw)
    return (raw.replace("\r\n", "\n"), nl)

def _write(path: Path, text: str, newline_style: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    if newline_style == "\r\n":
        text_to_write = text.replace("\n", "\r\n")
    else:
        text_to_write = text
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text_to_write)

def _line_start(text: str, pos: int) -> int:
    nl = text.rfind("\n", 0, pos); return 0 if nl == -1 else nl + 1

def _indent_at(text: str, pos: int) -> str:
    m = re.match(r"[ \t]*", text[_line_start(text, pos):]); return "" if not m else m.group(0)

def _indent_of_next_nonempty_line(text: str, pos: int) -> str:
    cur_indent = _indent_at(text, pos); idx = pos; end = len(text)
    while idx < end:
        ls = _line_start(text, idx); le = text.find("\n", ls); le = end if le == -1 else le
        line = text[ls:le]
        if line.strip():
            m = re.match(r"[ \t]*", line); return "" if not m else m.group(0)
        idx = le + 1
    return cur_indent

def _reindent_block(block: str, target_indent: str) -> str:
    lines = block.splitlines()
    non_empty = [ln for ln in lines if ln.strip()]
    base = min((len(re.match(r"[ \t]*", s).group(0)) for s in non_empty), default=0)
    out = []
    for ln in lines:
        core = ln[base:] if len(ln) >= base else ln.lstrip("\t ").rstrip("\n")
        out.append(target_indent + core)
    return "\n".join(out)

def _find_def_block(text: str, name: str) -> Tuple[int, int, str]:
    m = re.search(rf"(?m)^(?P<indent>[ \t]*)def\s+{re.escape(name)}\s*\(.*?\):\s*$", text)
    if not m: raise ValueError(f"replace_function: def {name}() not found")
    indent = m.group("indent"); start = m.start()
    m2 = re.search(rf"(?m)^(?:{re.escape(indent)}(?:def|class)\s+|$)", text[m.end():])
    end = len(text) if not m2 else m.end() + m2.start()
    return start, end, indent

def _class_header_end(text: str, cls: str) -> Tuple[int, str]:
    m = re.search(rf"(?m)^([ \t]*)class\s+{re.escape(cls)}\s*\(?.*?\)?:\s*$", text)
    if not m: raise ValueError(f"class {cls} not found")
    return m.end(), m.group(1)

def _list_classes(text: str) -> List[Tuple[str, int, str]]:
    out = []
    for m in re.finditer(r"(?m)^([ \t]*)class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(?.*?\)?:\s*$", text):
        out.append((m.group(2), m.end(), m.group(1)))
    return out

def _insert_lines(text: str, start_line: int, new_text: str) -> str:
    lines = text.splitlines(); idx = max(0, min(start_line - 1, len(lines)))
    block = new_text.splitlines(); out = lines[:idx] + block + lines[idx:]
    return "\n".join(out)

def _replace_lines(text: str, a: int, b: int, new_text: str) -> str:
    lines = text.splitlines()
    if a < 1 or b > len(lines) or a > b: raise ValueError(f"replace: bad range {a}-{b}")
    block = new_text.splitlines(); out = lines[:a - 1] + block + lines[b:]
    return "\n".join(out)

def _delete_lines(text: str, a: int, b: int) -> str:
    lines = text.splitlines()
    if a < 1 or b > len(lines) or a > b: raise ValueError(f"delete: bad range {a}-{b}")
    out = lines[:a - 1] + lines[b:]; return "\n".join(out)

def _replace_function(text: str, fn: str, repl: str) -> str:
    start, end, indent = _find_def_block(text, fn)
    repl_indented = _reindent_block(repl, indent)
    if not repl_indented.endswith("\n"): repl_indented += "\n"
    return text[:start] + repl_indented + text[end:]

def _smart_insert_method(text: str, repl: str, preferred_class: Optional[str] = None) -> str:
    classes = _list_classes(text); target_idx = None; target_indent = ""
    name_to_pos = {name: (pos, indent) for name, pos, indent in classes}
    if preferred_class and preferred_class in name_to_pos:
        target_idx, cls_indent = name_to_pos[preferred_class]; target_indent = cls_indent + "    "
    elif len(classes) == 1:
        _, pos, cls_indent = classes[0]; target_idx = pos; target_indent = cls_indent + "    "
    elif "RuntimeTablesProvider" in name_to_pos:
        pos, cls_indent = name_to_pos["RuntimeTablesProvider"]; target_idx = pos; target_indent = cls_indent + "    "
    block = repl
    if target_idx is not None:
        block = _reindent_block(block, target_indent); pre, suf = text[:target_idx], text[target_idx:]
        if pre and not pre.endswith("\n"): pre += "\n"
        if not block.endswith("\n"): block += "\n"
        return pre + block + suf
    block = _reindent_block(block, "")
    if not block.endswith("\n"):
        block += "\n"
    if text and not text.endswith("\n"):
        text += "\n"
    return text + block

def _upsert_function(text: str, fn: str, repl: str, in_class: Optional[str] = None) -> str:
    try: return _replace_function(text, fn, repl)
    except ValueError:
        looks_like_method = bool(re.match(r"\s*def\s+" + re.escape(fn) + r"\s*\(self[\),]", repl))
        if looks_like_method: return _smart_insert_method(text, repl, preferred_class=in_class)
        block = _reindent_block(repl, "")
        if not block.endswith("\n"):
            block += "\n"
        if text and not text.endswith("\n"):
            text += "\n"
        return text + block

def _insert_into_class_after_header(text: str, cls: str, new_text: str) -> str:
    idx, indent = _class_header_end(text, cls); block = _reindent_block(new_text, indent + "    ")
    pre, suf = text[:idx], text[idx:]
    if pre and not pre.endswith("\n"): pre += "\n"
    if not block.endswith("\n"): block += "\n"
    return pre + block + suf

def _find_matching_paren(text: str, open_pos: int) -> int:
    depth = 0; i = open_pos; n = len(text)
    while i < n:
        ch = text[i]
        if ch == "(": depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0: return i
        elif ch in ('"', "'"):
            q = ch; i += 1
            while i < n:
                if text[i] == "\\": i += 2; continue
                if text[i] == q: break
                i += 1
        i += 1
    return -1

def _insert_kwarg_into_call_region(text: str, anchor_after: int, new_line: str) -> str:
    open_pos = text.find("(", anchor_after)
    if open_pos == -1:
        pre, suf = text[:anchor_after], text[anchor_after:]
        ins = new_line if new_line.endswith("\n") else new_line + "\n"; return pre + ins + suf
    close_pos = _find_matching_paren(text, open_pos)
    if close_pos == -1:
        pre, suf = text[:anchor_after], text[anchor_after:]
        ins = new_line if new_line.endswith("\n") else new_line + "\n"; return pre + ins + suf
    args_region = text[open_pos + 1 : close_pos]; lines = args_region.splitlines()
    base_indent = _indent_of_next_nonempty_line(text, open_pos + 1)
    kw_line = _reindent_block(new_line.rstrip("\n"), base_indent)
    if not kw_line.endswith(","): kw_line += ","
    def is_positional(s: str) -> bool:
        s2 = s.strip(); return bool(s2) and ("=" not in s2.split("#", 1)[0])
    insert_idx = 0
    for i, ln in enumerate(lines):
        if is_positional(ln): insert_idx = i + 1
        else: break
    new_lines = lines[:insert_idx] + ([kw_line] if kw_line.strip() else []) + lines[insert_idx:]
    new_region = "\n".join(new_lines)
    return text[:open_pos + 1] + new_region + text[close_pos:]

def _insert_before_regex(text: str, pattern: str, new_text: str, occurrence: int = 1, debug_matches: Optional[List[int]] = None) -> str:
    matches = list(re.finditer(pattern, text, flags=re.MULTILINE | re.DOTALL))
    if debug_matches is not None: debug_matches.append(len(matches))
    if not matches or occurrence < 1 or occurrence > len(matches):
        raise ValueError(f"insert_before_regex: pattern not found or occurrence out of range: {pattern!r}")
    m = matches[occurrence - 1]; indent = _indent_of_next_nonempty_line(text, m.start())
    block = _reindent_block(new_text, indent)
    if not block.endswith("\n"): block += "\n"
    return text[:m.start()] + block + text[m.start():]

def _insert_after_regex(text: str, pattern: str, new_text: str, occurrence: int = 1, debug_matches: Optional[List[int]] = None) -> str:
    matches = list(re.finditer(pattern, text, flags=re.MULTILINE | re.DOTALL))
    if debug_matches is not None: debug_matches.append(len(matches))
    if not matches or occurrence < 1 or occurrence > len(matches):
        raise ValueError(f"insert_after_regex: pattern not found or occurrence out of range: {pattern!r}")
    m = matches[occurrence - 1]; at = m.end()
    if "=" in new_text and "(" in text[m.start():at + 200]:
        return _insert_kwarg_into_call_region(text, at - 1, new_text)
    indent = _indent_at(text, m.start()); block = _reindent_block(new_text, indent)
    pre, suf = text[:at], text[at:]
    if pre and not pre.endswith("\n"): pre += "\n"
    if not block.endswith("\n"): block += "\n"
    return pre + block + suf

def _replace_regex(text: str, pattern: str, replacement: str, debug_matches: Optional[List[int]] = None) -> str:
    def _do(m: re.Match) -> str:
        indent = _indent_at(text, m.start())
        repl = _reindent_block(replacement, indent)
        if not repl.endswith("\n"):
            repl += "\n"
        return repl
    new_text, n = re.subn(pattern, _do, text, flags=re.MULTILINE | re.DOTALL)
    if debug_matches is not None:
        debug_matches.append(n)
    if n == 0:
        raise ValueError(f"replace_regex: pattern not found: {pattern!r}")
    return new_text

def _line_number_for_pos(text: str, pos: int) -> int: return text.count("\n", 0, pos) + 1

def preflight_report(manifest: List[Dict[str, Any]], root: Path) -> Dict[str, Any]:
    root = root.resolve(); out: Dict[str, Any] = {"root": str(root), "files": []}
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for p in manifest: by_file.setdefault(p["file"], []).append(p)
    for rel, plist in by_file.items():
        fpath = root / rel; entry: Dict[str, Any] = {"file": rel, "exists": fpath.exists(), "actions": []}
        if not fpath.exists(): out["files"].append(entry); continue
        text, _nl = _read(fpath)
        for p in plist:
            info: Dict[str, Any] = {"action": p.get("action")}
            try:
                act = p["action"]
                if act in {"insert_before_regex", "insert_after_regex", "replace_regex"}:
                    pattern = p["pattern"]; matches = list(re.finditer(pattern, text, flags=re.MULTILINE | re.DOTALL))
                    info["pattern"] = pattern; info["matches"] = len(matches)
                    if matches:
                        locs = [{"line": _line_number_for_pos(text, m.start()), "preview": (text[m.start():m.end()].splitlines()[0][:120] if text[m.start():m.end()].splitlines() else "")} for m in matches[:3]]
                        info["locations"] = locs
                elif act == "replace_function":
                    try:
                        s, _e, _indent = _find_def_block(text, p["function_name"])
                        info["function_name"] = p["function_name"]; info["found_at_line"] = _line_number_for_pos(text, s)
                    except Exception:
                        info["function_name"] = p["function_name"]; info["found_at_line"] = None
                        classes = _list_classes(text); info["class_candidates"] = [name for name, _pos, _ind in classes]
                elif act == "upsert_function":
                    try:
                        s, _e, _indent = _find_def_block(text, p["function_name"])
                        info["function_name"] = p["function_name"]; info["mode"] = "replace"; info["found_at_line"] = _line_number_for_pos(text, s)
                    except Exception:
                        info["function_name"] = p["function_name"]; info["mode"] = "insert"
                        if p.get("in_class"):
                            try: _idx, _indent = _class_header_end(text, p["in_class"]); info["class_name"] = p["in_class"]
                            except Exception: info["class_name"] = None
                elif act == "insert_into_class_after_header":
                    _idx, _indent = _class_header_end(text, p["class_name"]); info["class_name"] = p["class_name"]
                else:
                    info["note"] = "line-anchored or non-regex action"
            except Exception as e:
                info["error"] = str(e)
            entry["actions"].append(info)
        out["files"].append(entry)
    return out

def _validate_python_syntax(text: str, filename: str) -> Optional[str]:
    try: ast.parse(text, filename=filename); return None
    except SyntaxError as e: return f"SyntaxError: {e.msg} at line {e.lineno}, col {e.offset}"

def apply_patches(manifest: List[Dict[str, Any]], root: Path, *, dry_run: bool = True, backup_ext: str = ".bak", debug: bool = True, validate_syntax: bool = True) -> Dict[str, Any]:
    root = root.resolve(); report: Dict[str, Any] = {"dry_run": dry_run, "root": str(root), "files": []}
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for p in manifest: by_file.setdefault(p["file"], []).append(p)
    for rel, plist in by_file.items():
        fpath = root / rel; entry: Dict[str, Any] = {"file": rel, "applied": 0, "errors": [], "matches": []}
        if not fpath.exists(): entry["errors"].append(f"file not found: {fpath}"); report["files"].append(entry); continue
        text, nl = _read(fpath); before_lines = len(text.splitlines()); original_text = text
        for p in plist:
            try:
                action = p["action"]; match_counts: List[int] = []
                if action == "insert":
                    text = _insert_lines(text, int(p["start_line"]), p.get("new_text", ""))
                elif action == "replace":
                    text = _replace_lines(text, int(p["start_line"]), int(p["end_line"]), p.get("new_text", ""))
                elif action == "delete":
                    text = _delete_lines(text, int(p["start_line"]), int(p["end_line"]))
                elif action == "replace_function":
                    try: text = _replace_function(text, p["function_name"], p.get("replacement", ""))
                    except Exception: text = _upsert_function(text, p["function_name"], p.get("replacement", ""), p.get("in_class"))
                elif action == "upsert_function":
                    text = _upsert_function(text, p["function_name"], p.get("replacement", ""), p.get("in_class"))
                elif action == "insert_into_class_after_header":
                    text = _insert_into_class_after_header(text, p["class_name"], p.get("new_text", ""))
                elif action == "insert_before_regex":
                    text = _insert_before_regex(text, p["pattern"], p.get("new_text", ""), int(p.get("occurrence", 1)), match_counts)
                elif action == "insert_after_regex":
                    text = _insert_after_regex(text, p["pattern"], p.get("new_text", ""), int(p.get("occurrence", 1)), match_counts)
                elif action == "replace_regex":
                    text = _replace_regex(text, p["pattern"], p.get("replacement", ""), match_counts)
                else:
                    raise ValueError(f"Unknown action: {action}")
                entry["applied"] += 1
                if debug and match_counts: entry["matches"].append({"action": action, "count": match_counts[0]})
            except Exception as e:
                entry["errors"].append(f"{p.get('action')} error: {e}")
        after_lines = len(text.splitlines()); entry.update({"before_lines": before_lines, "after_lines": after_lines, "delta": after_lines - before_lines})
        report["files"].append(entry)
        if not dry_run and original_text != text:
            if validate_syntax and fpath.suffix == ".py":
                err = _validate_python_syntax(text, filename=str(fpath))
                if err: entry["errors"].append(f"syntax_check_failed: {err}"); continue
            if backup_ext:
                bak_path = Path(str(fpath) + backup_ext)
                with open(bak_path, "w", encoding="utf-8", newline="") as f: f.write(original_text.replace("\n", nl))
            _write(fpath, text, newline_style=nl)
    return report

def load_manifest_from_py(py_path: Path) -> List[Dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("patch_manifest", str(py_path))
    mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)  # type: ignore
    data = getattr(mod, "MANIFEST", None)
    if not isinstance(data, list): raise ValueError("Python manifest must define MANIFEST = [ ... ]")
    return data

def _backup_path_for(original: Path, backup_ext: str = ".bak") -> Path: return Path(str(original) + backup_ext)

def revert_one(original: Path, *, backup_ext: str = ".bak", dry_run: bool = True, remove_backup: bool = False) -> Dict[str, Any]:
    original = original.resolve(); bak = _backup_path_for(original, backup_ext)
    report = {"original": str(original), "backup": str(bak), "exists_original": original.exists(), "exists_backup": bak.exists(), "restored": False, "removed_backup": False, "error": None, "dry_run": dry_run}
    try:
        if not bak.exists(): report["error"] = "backup not found"; return report
        if not dry_run:
            data = bak.read_bytes(); original.write_bytes(data); report["restored"] = True
            if remove_backup: bak.unlink(missing_ok=True); report["removed_backup"] = True
        else: report["restored"] = True
    except Exception as e: report["error"] = str(e)
    return report

def revert_many(root: Path, files: Optional[Iterable[str]] = None, *, backup_ext: str = ".bak", dry_run: bool = True, remove_backup: bool = False) -> Dict[str, Any]:
    root = root.resolve(); summary: Dict[str, Any] = {"root": str(root), "dry_run": dry_run, "backup_ext": backup_ext, "remove_backup": remove_backup, "items": []}
    if files is None:
        bak_paths = list(root.rglob(f"*{backup_ext}")); originals = [Path(str(p)[:-len(backup_ext)]) for p in bak_paths if str(p).endswith(backup_ext)]
    else: originals = [(root / rel).resolve() for rel in files]
    for orig in originals:
        rep = revert_one(orig, backup_ext=backup_ext, dry_run=dry_run, remove_backup=remove_backup); summary["items"].append(rep)
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply patch manifest modules/json.")
    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to manifest (.py with MANIFEST variable or JSON list)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_repo_root(),
        help="Repository root to apply patches against",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply patches instead of dry-run",
    )
    parser.add_argument(
        "--backup-ext",
        default=".bak",
        help="Backup extension when applying patches",
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    if manifest_path.suffix == ".py":
        manifest_data = load_manifest_from_py(manifest_path)
    else:
        manifest_data = load_manifest_from_json(manifest_path)

    report = apply_patches(
        manifest_data,
        args.root.resolve(),
        dry_run=not args.apply,
        backup_ext=args.backup_ext,
        debug=True,
        validate_syntax=True,
    )
    print(json.dumps(report, indent=2))
    # print(revert_many(root, dry_run=False))
    # # or one file:
    # print(revert_one(root / "scoring" / "unified_tables.py", dry_run=False, remove_backup=True))

