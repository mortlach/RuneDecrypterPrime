# Engine execution

The engine constructs and runs the requested components, then finalises the returned state.

## Where to look

- [builders.py](builders.py) — Create the cipher and selected scorer; check requested capabilities.
- [engine.py](engine.py) — Select and execute the solver with its random state.
- [finalization.py](finalization.py) — Complete the solution and attach scoring information.

## Choices and extension

Start in `engine.py` when following a run. Use `builders.py` for backend or capability questions and `finalization.py` for the final report. Settings should be changed through the public request; engine extensions must preserve status and cleanup behaviour.

Continue with the [guide](../../../../docs/guides/pipeline.md) or the [package map](../../README.md).
