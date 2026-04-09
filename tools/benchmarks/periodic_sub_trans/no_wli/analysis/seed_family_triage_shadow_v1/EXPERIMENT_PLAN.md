# Seed Family Triage Shadow v1 Plan

Question:
- Can the frozen stop and family-quality pack be turned into a useful shadow layer for prioritising seeds and families without pretending the solver can stop early?

Scope:
- all 12 frozen review seeds get seed-level triage rows
- the 6 frozen family-enriched seeds also get family-level priority rows and budget recommendations

Execution:
- read the four frozen bundles from hardcoded repo-relative paths
- validate bundle files and fixed seed contracts
- build deterministic seed-level triage rows
- build deterministic family-level priority rows and budget recommendations
- write one compact markdown report plus machine-readable outputs

Constraints:
- no CLI arguments
- no latest-bundle discovery
- no threshold changes
- no live runs
