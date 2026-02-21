from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_RANGES_PATH = HERE / "ranges_v1_1.json"
DEFAULT_OUTPUT_PATH = HERE / "knob_reference_v1_1.md"


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _fmt_value(value: Any) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, str):
        return f"`{value}`"
    return f"`{value}`"


def _fmt_range(spec: dict[str, Any]) -> str:
    parts: list[str] = []
    if spec.get("min_value") is not None or spec.get("max_value") is not None:
        lo = spec.get("min_value", "-inf")
        hi = spec.get("max_value", "+inf")
        parts.append(f"value: [{lo}, {hi}]")
    if spec.get("min_item_value") is not None or spec.get("max_item_value") is not None:
        lo = spec.get("min_item_value", "-inf")
        hi = spec.get("max_item_value", "+inf")
        parts.append(f"map values: [{lo}, {hi}]")
    item_keys = spec.get("allowed_item_keys", [])
    if isinstance(item_keys, list) and item_keys:
        parts.append("map keys: {" + ", ".join(str(int(x)) for x in item_keys) + "}")
    if not parts:
        return "-"
    return "; ".join(parts)


def build_markdown(ranges_path: Path, output_path: Path) -> None:
    data = json.loads(ranges_path.read_text(encoding="utf-8"))
    version = str(data.get("version", "unknown"))
    knobs = data.get("knobs", [])
    if not isinstance(knobs, list):
        raise ValueError("ranges_v1_1.json must contain a list at key 'knobs'")

    lines: list[str] = []
    lines.append(f"# Community Config Reference ({version})")
    lines.append("")
    lines.append("Generated from `ranges_v1_1.json`.")
    lines.append("")
    lines.append("| Key | Label | Type | Default | Range | Mode | Meaning |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for item in knobs:
        if not isinstance(item, dict):
            continue
        key = _md_escape(str(item.get("key", "")))
        label = _md_escape(str(item.get("label", key)))
        value_type = _md_escape(str(item.get("value_type", "")))
        default = _fmt_value(item.get("default"))
        value_range = _md_escape(_fmt_range(item))
        mode = _md_escape(str(item.get("mode", "basic")))
        meaning = _md_escape(str(item.get("meaning", "")))
        lines.append(
            f"| `{key}` | {label} | `{value_type}` | {default} | {value_range} | `{mode}` | {meaning} |"
        )

    sampling_spaces = data.get("sampling_spaces", {})
    if isinstance(sampling_spaces, dict) and sampling_spaces:
        lines.append("")
        lines.append("## Sampling Spaces")
        lines.append("")
        for name in sorted(sampling_spaces.keys()):
            space = sampling_spaces.get(name)
            if not isinstance(space, dict):
                continue
            desc = _md_escape(str(space.get("description", "")))
            lines.append(f"- `{name}`: {desc}")

    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    build_markdown(DEFAULT_RANGES_PATH, DEFAULT_OUTPUT_PATH)
    print(f"Wrote {DEFAULT_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

