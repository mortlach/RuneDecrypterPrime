# D4 summary and D5 handoff note

This note is for the next developer picking up D5 after the D4 V1 contract-hardening pass. It summarises what D4 changed, what D4 deliberately did not change, and the design principles that should continue into D5.

D4 should be read as a hardening and cleanup phase, not as a feature-expansion phase. The core rule is simple: V1 behaviour must be explicit, typed, testable, and visible in reports. Requested capabilities should run, block, or report an explicit non-ranking fallback. They should never silently disappear.

## Current D4 state

D4 has now covered the main planned hardening areas:

1. **Full-proof release gate**
   - The release proof workflow is a manual GitHub workflow.
   - It runs install smoke, full pytest, and V1 tutorials.
   - It runs on Windows and Ubuntu with Python 3.11.
   - Pytest uses `-ra`, so skips are visible rather than hidden.

2. **Scorer capability contract**
   - Public scorer paths expose `ScorerCapabilityReport`.
   - Requested production lanes must be active or blocked.
   - Report-only lanes remain visible but must not affect ranking, raw score, ordering, or tie-breaks.
   - Backend `CapabilityIssue` values survive into the public report.
   - Façade scorers must not hide backend lane state.

3. **Unified scorer boundary**
   - `UnifiedRuneScorer` is now treated as a public V1 runtime object, not a loose compatibility shim.
   - Direct construction requires `CipherConfig` and `ScoringConfig`.
   - Dict-like scorer params are rejected at construction time.
   - This matches the `build_scorer()` typed boundary.

4. **Solver report visibility**
   - Solver reports preserve `details["scorer_lanes"]` when capability data exists.
   - Capability-report failures and JSON serialisation failures become JSON-safe diagnostic payloads.
   - Lane visibility should not vanish because a report helper raised an exception.

5. **Stop reason schema**
   - Stop reasons classify into stable categories.
   - Success aliases include `target_score`, `stop_score`, and `test_key`.
   - Dynamic budget families include `no_improve_*` and `stall_*`.
   - Stop reasons are now part of the public report contract, not arbitrary strings.

6. **Typed builder config boundary**
   - `build_cipher()` and `build_scorer()` reject loose `dict` / `SimpleNamespace` configs.
   - Compatibility shims may still exist in focused places, but they must not bypass public V1 boundaries.

7. **Optional Torch runtime policy**
   - Torch is V1-supported where available.
   - Normal CI does not require Torch.
   - Torch tests are explicit and skipped visibly when Torch is unavailable.
   - If a user explicitly requests Torch and it is unavailable, RDP raises a clear error instead of silently falling back to NumPy.

8. **Scheduled stream lookup contract**
   - `scheduled_stream_lookup` remains V1 core.
   - The contract is narrow and explicit: one or two streams, explicit schedules, explicit degeneracy policy, literal fixed stream values, and tested backward/end anchoring.
   - Fixed stream text values such as `"12"` are rejected instead of split into characters.
   - Out-of-range fixed values are rejected, not silently modulo-reduced.

9. **D4 closure contract**
   - `d4_contract_closure.md` records the D4.0-D4.8 contract.
   - `test_d4_contract_closure.py` checks the closure document, source gates, test gates, and scope-lock entries.
   - The closure itself is now test-backed.

## What D4 deliberately did not do

D4 did not reopen V1 scope. It did not add a new scorer, a new solver, a new n-gram scoring mode, or a new release asset requirement.

D4 also did not attempt a broad mechanical purge of every `except Exception`, every compatibility helper, or every legacy path. That would be risky and noisy. Instead, D4 converted the dangerous cases into explicit contracts:

- requested production lanes cannot silently disappear;
- explicit Torch requests cannot silently fall back;
- scheduled stream config cannot silently coerce text or modulo literal values;
- stop reasons cannot escape the schema;
- report serialisation failures must be visible.

D5 may continue cleanup, but should keep this principle: clean the core where it strengthens a real contract, not because a pattern looks ugly in isolation.

## Review note: stale D3 wording

A pasted review note used during D4 discussion contained stale D3 text and ended with wording like “D3 is now ready for external review.” That was a report-copy issue, not a repo-state issue. The actual D4 repo docs are D4-specific. Do not copy stale D3 closure language into D5 material.

## Design principles to carry into D5

### 1. Contracts before convenience

If a public V1 object is part of the runtime surface, prefer typed config and explicit failure over compatibility convenience. Compatibility belongs in wrappers, migration helpers, or tests, not in core public constructors.

### 2. Run, block, or report

Any requested capability should have one of three outcomes:

- it runs;
- it blocks with a typed/clear error;
- it is explicitly report-only or unavailable in a visible diagnostic section.

Silent fallback is not acceptable for production V1 capabilities.

### 3. Report-only means no ranking effect

Diagnostic lanes can be useful, but they must not affect production rank, raw score, ordering, or tie-breaks unless explicitly promoted into V1 production scope.

### 4. Public reports are part of the API

Solver reports, stop reasons, scorer lane reports, and capability diagnostics are not afterthoughts. If a user needs them to understand what happened, the schema must be stable and test-backed.

### 5. Clean core code while touching it

When working in core runtime paths, take the opportunity to remove ambiguity, hidden coercion, and compatibility baggage. Keep the change focused, but leave the touched area cleaner and harder to misuse.

### 6. Avoid broad cleanup campaigns without a contract target

D4 showed that targeted cleanup works better than broad churn. Clean up broad `except Exception` only when there is a specific semantic risk: hidden scoring failure, hidden config failure, hidden report loss, or hidden fallback.

### 7. Partition work into meaningful chunks

D4 worked best when changes were grouped by reviewable contract blocks:

- full-proof gate;
- scorer/report/stop reason contracts;
- typed config and optional runtime boundaries;
- scheduled stream lookup contract;
- closure docs/tests.

For D5, avoid giant mixed commits. Also avoid tiny context-free pushes. A good block should be large enough to prove a complete contract, but small enough to review.

### 8. Use local source zips for speed, but GitHub for authority

Local source zips are useful for fast focused checks, especially when the repo is large or CI is slow. But GitHub branch state is authoritative. Before pushing, compare against the current branch. After pushing, verify with CI or at least focused tests.

### 9. New tests should prevent old bad behaviours from returning

When a bad design behaviour is found, add a test that names the behaviour directly. The goal is not just to fix today’s bug; it is to stop the codebase drifting back into the same failure mode.

## D5 starting recommendations

D5 should start with a fresh review of the current D4 head after CI. Recommended first steps:

1. Run/confirm the full-proof workflow on the current head.
2. If CI fails, fix failures before starting new D5 work.
3. Re-check the D4 closure test after any D5 boundary changes.
4. Keep D5 focused on core tidying and contract hardening.
5. Prefer source-backed docs and contract tests over narrative-only notes.

Good D5 targets may include:

- reducing remaining broad exception handlers where they affect core semantics;
- moving compatibility shims out of public runtime constructors;
- strengthening API/report schema tests;
- tightening docs that still describe historical behaviour rather than V1 contract;
- reducing bloat in touched core modules without reopening V1 feature scope.

## Final D4 acceptance condition

D4 should be considered implementation-complete when this note, the D4 closure docs, and the contract tests are present on branch. It should be considered release-complete only after the full-proof workflow passes on the current head.
