# No-WLI Flavor

Runner for periodic substitution + transposition benchmarking without WLI features.

Entrypoints:
- `runner.py` - full no-WLI pipeline runner
- `run_focus_p5_c1_c5.py` - focused launcher (`period=5`, `columns=1..5`)
- `run_focus_p5_c1_c5_a34.py` - focused launcher (`period=5`, `columns=1..5`, `A34->M34->B34`)

Examples:
- `python tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `python tools/benchmarks/periodic_sub_trans/no_wli/run_focus_p5_c1_c5.py`
- `python tools/benchmarks/periodic_sub_trans/no_wli/run_focus_p5_c1_c5_a34.py`
