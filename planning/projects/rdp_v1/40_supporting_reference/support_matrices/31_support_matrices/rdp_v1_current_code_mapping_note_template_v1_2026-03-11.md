# RDP v1 current-code mapping note
## template and starter content

_Date: 2026-03-11_

## Purpose

This note satisfies the refactor-plan requirement for an explicit mapping from current code into the formal target surfaces before major implementation planning begins.

It exists to stop agents or maintainers guessing where the real behaviour lives.

## How to use this note

For each area below, fill in:
- current owner or de facto owner
- target owner after convergence
- why this area matters
- what must not be weakened
- likely files touched first
- tests that currently protect parity
- main risks
- first safe slice

---

## 1. Run/front-door area

### Current main files
- `src/rune_decrypter_prime/api/run.py`
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/api/normalize.py`
- `src/rune_decrypter_prime/core/config/run.py`

### Related tests
- `tests/api/`
- `tests/api_contract/`
- `tests/ui_normalize/`

### Current role
Present public-ish run/config boundary split across API specs, normalisation, and core config.

### Target role
One real RunSpec-fronted public entrypoint with a forgiving boundary and strict core.

### Must not be weakened
- no second public run language
- no silent defaults drift
- campaign-generated runs must still fit the shared contract

### Main risks
- side-door entrypoints staying alive
- bridge code becoming permanent
- boundary forgiveness leaking into core

### First safe slice
Inventory current entrypoints and overlaps before introducing the minimum RunSpec contract.

---

## 2. Scoring/report area

### Current main files
- `src/rune_decrypter_prime/scoring/scorer_report.py`
- `src/rune_decrypter_prime/scoring/scorer_report_builder.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/word_ngram_report.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`

### Related tests
- `tests/scoring/`
- `tests/tools/`
- `tests/telemetry/`

### Current role
Core report plumbing plus runner-local projection logic.

### Target role
Shared report contracts with stable ScorerReport, narrow SolverReport, and explicit rescoring/reconstruction state.

### Must not be weakened
- no-WLI parity
- report usefulness for debugging and later comparison
- reconstruction / rescoring path

### Main risks
- ad hoc row projection drift
- report duplication
- under-specified SolverReport

### First safe slice
Write the minimum ScorerReport and SolverReport contracts before trying to tidy projections.

---

## 3. Outer campaign area

### Current main files
- `tools/benchmarks/community/examples/campaign_config_v1_1.json`
- `tools/benchmarks/community/generate_manifest.py`
- `tools/benchmarks/community/run_shard.py`
- `tools/benchmarks/community/_run_single_job.py`
- `tools/benchmarks/community/_campaign_common.py`

### Related tests
- `tests/community/`

### Current role
Outer campaign definition, manifesting, sharding, and execution control.

### Target role
Seed of the formal CampaignSpec boundary and outer campaign surface.

### Must not be weakened
- deterministic shardable execution
- manifest clarity
- campaign reconstruction honesty

### Main risks
- treating this as disposable glue
- losing reproducibility while “simplifying”

### First safe slice
Write minimum CampaignSpec using this outer shape as the seed.

---

## 4. Inner stage-engine area

### Current main files
- `tools/benchmarks/periodic_sub_trans/common/stage_spec.py`
- `tools/benchmarks/periodic_sub_trans/common/policy_spec.py`
- `tools/benchmarks/periodic_sub_trans/common/stage_engine.py`
- runner-specific directories under:
  - `tools/benchmarks/periodic_sub_trans/no_wli/`
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/`

### Related tests
- `tests/tools/`
- `tests/community/`

### Current role
Serious staged-attack machinery with stage sequencing, pool shaping, policy slices, and runner-local orchestration.

### Target role
Strong inner engine and policy core, widened and wrapped inside a first-class campaigns surface.

### Must not be weakened
- stage seriousness
- survivor carry-forward
- retries / bounded loops
- no-WLI flagship path

### Main risks
- collapsing real behaviour into toy wrappers
- flattening useful stage/policy distinctions
- moving files before contract tests exist

### First safe slice
Document the current stage/policy/event shape and preserve it while defining the outer façade.

---

## 5. Output/privacy area

### Current main files
- `src/rune_decrypter_prime/core/config/logging_config.py`
- `src/rune_decrypter_prime/io/run_logger.py`
- `tools/benchmarks/periodic_sub_trans/common/io_reports.py`
- `tools/benchmarks/periodic_sub_trans/common/trace_writer.py`
- `tools/benchmarks/periodic_sub_trans/common/paths.py`
- output helpers inside community campaign tooling

### Related tests
- `tests/test_logging_paths.py`
- privacy/path tests under `tests/tools/`

### Current role
Fragmented set of output, trace, logging, and privacy owners.

### Target role
One shared output/privacy owner with clear JSON/JSONL, redaction, and artefact-ref rules.

### Must not be weakened
- no absolute path leakage
- portable outputs
- stable writer rules across runs and campaigns

### Main risks
- missed writer side paths
- accidental path leakage from old codepaths
- campaign-local output systems surviving forever

### First safe slice
Inventory every current writer and policy owner before converging them.

---

## 6. LP/assets area

### Current main files
- `assets_manifest_v1.json`
- `src/rune_decrypter_prime/data/asset_paths.py`
- `src/rune_decrypter_prime/data/liber_primus/lp_master.py`
- `src/rune_decrypter_prime/data/liber_primus/lp_adapter.py`

### Related tests
- `tests/data/`
- `tests/guardrails/`

### Current role
Real LP domain support and asset location/materialisation groundwork.

### Target role
First-class LP domain and governed asset/reference rules.

### Must not be weakened
- LP-first usability
- portable asset refs
- honest separation of source assets, runtime assets, and outputs

### Main risks
- hidden local path assumptions
- LP helpers bypassing shared contracts

### First safe slice
Freeze minimum asset-manifest and LP problem-source contract expectations before moving ownership.

---

## 7. Mapping table template

| Area | Current owner / de facto owner | Target owner | Must not weaken | Main risks | First safe slice | Guardrail tests |
|---|---|---|---|---|---|---|
| Run/front door | | | | | | |
| Scoring/reports | | | | | | |
| Outer campaign | | | | | | |
| Inner stage engine | | | | | | |
| Output/privacy | | | | | | |
| LP/assets | | | | | | |

---

## 8. Sign-off questions

Before calling this note complete, answer:
- can an agent identify the correct starting files without guessing?
- are outer and inner campaign surfaces clearly separated?
- is the parity source named where docs are abstract?
- are known risks concrete rather than vague?
- does every area have a first safe slice and related test gates?
