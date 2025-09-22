# ============================================================
# rune_decrypter_prime/io/telemetry_utils.py
# ============================================================
from __future__ import annotations
import os, json, datetime, uuid
from pathlib import Path
from rune_decrypter_prime.core.config import Solution

# todo meh in two places
def dump_telemetry(sol: Solution, base_dir: str | Path = "out/logs") -> Path:
    """
    Dump Solution.meta["telemetry"] and ["run_meta"] to a unique JSON file.

    Creates a folder per run under base_dir/<date>/<uuid4>/telemetry.json

    Returns the path to the JSON file.
    """
    base = Path(base_dir)
    date_str = datetime.datetime.utcnow().strftime("%Y%m%d")
    run_id = str(uuid.uuid4())[:8]
    out_dir = base / date_str / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "telemetry.json"
    data = {
        "telemetry": sol.meta.get("telemetry", {}),
        "run_meta": sol.meta.get("run_meta", {}),
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return out_file
