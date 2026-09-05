# Experiment support

Shared experiment execution, archives, ledgers and replay support live here. Start at
`experiment.py` for the experiment interface, then `replay.py` for replay entry points.
The `replay_binding`, `replay_execution`, `replay_evidence` and `replay_provenance`
modules separate those responsibilities. `archive.py` and `ledger.py` retain evidence;
`text_scoring_comparison.py` supports comparisons. Reuse these owners for new
investigations rather than adding another campaign framework.

Continue with the [related guide](../README.md).
