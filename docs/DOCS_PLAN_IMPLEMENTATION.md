# Documentation Rollout - Staged Implementation Plan

This plan turns `docs/DOCS_PLAN.md` into actionable phases. Each stage lists the target files, goals, and validation steps so we can execute in small, reviewable chunks.

---

## Stage 0 - Prep ( 🚀 Complete before edits )
1. Confirm `docs/DOCS_PLAN.md` is the latest contract (done).
2. Snapshot current docs/tests (`pytest tests -q`) so regressions are visible.
3. Create tracking issue checklist (per stage) to log progress.

Deliverable: `docs/DOCS_PLAN_IMPLEMENTATION.md` (this file).

---

## Stage 1 - Front Door & Indexes
**Targets**
- `README.md`
- `docs/README.md`
- `docs/INDEX.md` (or create if missing)
- `docs/guides/troubleshooting.md`
- Cross-link `docs/guides/documentation_playbook.md`

**Steps**
1. Ensure README quickstart mirrors plan (Hands-on vs Deep-dive) and links to troubleshooting + doc playbook.
2. Update docs index to list every section with "Hands-on / Deep-dive" tags.
3. Expand troubleshooting appendix (verify structure matches DOCS_PLAN §12).
4. Add pointers from index to new appendix and playbook.

**Validation**
- Proofread for neutral voice.
- `rg` for outdated paths ("out/", "C:\").
- `pytest tests -q` (sanity).

--- 

## Stage 2 - Core Guides (Architecture, Philosophy, Extending)
**Targets**
- `docs/guides/architecture.md`
- `docs/guides/philosophy.md`
- `docs/guides/extending_hands_on_to_experts.md`

**Steps**
1. Add "What it is / Why it matters / How to use it (Hands-on & Deep-dive)" sections per guide.
2. Insert ASCII diagram + module references in architecture guide.
3. Clarify mission + contracts in philosophy.
4. Build ladder (tutorial -> cipher -> solver) in extending guide, referencing tutorials + tests.

**Validation**
- Each guide references relevant tests (e.g., telemetry contract, tutorial regressions).
- Links back to outputs/telemetry/troubleshooting as needed.

---

## Stage 3 - Component Deep Dives (Outputs, Scoring, Telemetry)
**Targets**
- `docs/guides/outputs.md`
- `docs/guides/scoring_deep.md`
- `docs/guides/telemetry.md` (create/update)

**Steps**
1. Outputs: explain folder layout, show `output/<kind>/...` tree, include Hands-on/Deep-dive instructions.
2. Scoring: follow plan §7 (backend matrix, examples, tests, benchmarks).
3. Telemetry: document `telemetry.run`, `solver_progress`, `solution.meta["work"]`, link to schema test.

**Validation**
- Ensure each guide lists code paths (e.g., `src/rune_decrypter_prime/telemetry/pipeline.py`).
- Add FAQ/How-to blocks per plan.

---

## Stage 4 - Tutorials & Cookbook
**Targets**
- `docs/tutorials/*.md` (or top-level page)
- `docs/howto/*.md` (recipe pages)

**Steps**
1. For each tutorial, add overview + expected outputs + quality thresholds.
2. Align "How-to" recipes with plan (Add a cipher, Add a solver, Read telemetry).
3. Tag each recipe Hands-on/Deep-dive; include verification tests + output paths.

**Validation**
- Tutorials link back to quickstart and troubleshooting.
- Recipes reference actual code/tests.

---

## Stage 5 - Reference & Glossary
**Targets**
- `docs/reference/*`
- `docs/appendices/glossary.md`
- `docs/tests_docs/*`

**Steps**
1. Make sure every reference entry states "What it represents", key paths, and cross-links to relevant guides.
2. Update glossary definitions (link to first-use sections).
3. tests_docs: document Tier-A vs full suite, include telemetry contract mention.

**Validation**
- `rg` ensures no stale folder names/paths.
- `pytest tests -q` after final edits.

---

## Stage 6 - Tooling & Automation (Optional but recommended)
1. Add docs lint checklist (verify cross-links, headings) to CI (`tools/docs_lint`).
2. Document how to run symbol index + release tooling in `docs/tests_docs/tools.md`.
3. Capture doc contribution workflow in `CONTRIBUTING.md`.

---

## Completion Criteria
- All guides follow "What/Why/How/Hands-on/Deep-dive" structure.
- Troubleshooting appendix + doc playbook linked everywhere they're referenced in plan.
- No references to deprecated files/paths.
- Full test suite green (`pytest tests -q`).



