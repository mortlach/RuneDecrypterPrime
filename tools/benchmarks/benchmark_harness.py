"""Simple deterministic benchmark harness (IDE-first)

- Compares solvers on small budgets (CPU) and prints a CSV table.
- Also writes JSON/CSV under output/tools/benchmarks/<timestamp>__bench__<git>/.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from rune_decrypter_prime.api.wrappers.by_name import by_name
from rune_decrypter_prime.api.run import RunAPI
from rune_decrypter_prime.api.specs import KeySpec, SolverSpec, ScoringConfig
from rune_decrypter_prime.core.types import Direction, Device

def bench_case(name, cipher_name, key_spec, solver_spec, text, scoring):
    t0 = time.time()
    sol = RunAPI.run(text=text, cipher=by_name.cipher(cipher_name), key=key_spec,
                     solver=solver_spec, device=Device.CPU, scorer="rune",
                     scorer_params={"encoding_dir": Direction.LTR, "objective": "pct.logp.win10"},
                     telemetry_on=False, encoding_dir=Direction.LTR)
    dt = time.time() - t0
    return dict(name=name, score=sol.best_score, seconds=round(dt, 3))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_short_hash() -> str:
    try:
        value = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=_repo_root()).decode().strip()
        return value or "nogit"
    except Exception:
        return "nogit"


def _write_reports(rows):
    root = _repo_root()
    out_root = root / "output" / "tools" / "benchmarks"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"{stamp}__bench__{_git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    # CSV
    header = "name,score,seconds\n"
    csv = header + "\n".join(f"{r['name']},{r['score']},{r['seconds']}" for r in rows) + "\n"
    (run_dir / "results.csv").write_text(csv, encoding="utf-8")
    # JSON
    (run_dir / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return run_dir

def main():
    SEED = 1234
    text = [12,4,7,18,0,5,11,9,3,20,8,1,17,24,6,13,22,2,10,16]
    scoring = ScoringConfig(model="unigram", direction=Direction.LTR)
    rows = []
    rows.append(bench_case("vig-ga", "vigenere", KeySpec.repeat(len=6), SolverSpec.ga(pop_size=64, generations=40, seed=SEED), text, scoring))
    rows.append(bench_case("vig-sa", "vigenere", KeySpec.repeat(len=6), SolverSpec.sa(sa_iters=1000, seed=SEED), text, scoring))
    rows.append(bench_case("col-beam", "columnar", KeySpec.permutation(len=7), SolverSpec.beam(beam_width=64, seed=SEED), text, scoring))
    print("name,score,seconds")
    for r in rows:
        print(f"{r['name']},{r['score']},{r['seconds']}")
    run_dir = _write_reports(rows)
    rel = run_dir.relative_to(_repo_root())
    print(f"[bench] Reports written to {rel}")

if __name__ == "__main__":
    main()
