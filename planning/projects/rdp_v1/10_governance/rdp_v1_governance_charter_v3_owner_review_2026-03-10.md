# RDP v1 governance charter — owner review draft 3
_Date: 2026-03-10_

## 1. Purpose

This charter defines the governing intent for RDP v1.

It is the owner-level source of truth for what v1 is, what it must support, where boundaries sit, and how convergence work should be judged.

The codebase is now in a finishing and convergence phase, not a broad feature-invention phase. The main job is to harden, simplify, and prove the real system that already exists, while removing drift, hidden policy, and fragmented ownership.

This charter is intentionally owner-led. Code review findings may inform it, but they do not overrule it.

---

## 2. What RDP v1 is

RDP v1 is a rune-solving framework.

It is **Liber Primus-first**, but not *Liber Primus*-only.

Its real present use is to support the strongest credible narrowly defined LP attacks the project can mount, using the best understanding already gained from practical work and community testing.

At the same time, it should remain a real framework rather than a one-off LP script pile. The same shared contracts should support built-in methods, extensions, tutorials, campaign workflows, and future non-LP problem sources.

---

## 3. Boundary model

### 3.1 Public boundary

The API and boundary layer own the public config shape and any forgiving normalisation.

This is where looser user-facing input may be accepted and converted into the strict internal forms used by the real system.

### 3.2 Core

Core owns the fixed typed solving interface.

Core also owns:
- typed method, cipher, key, and problem contracts
- scoring runtime
- ScorerReport and SolverReport
- formal rescoring support
- output and privacy policy
- shared artefact writing
- shared asset logic

### 3.3 Campaign layer

Campaigns sit above core runs.

Campaigns orchestrate serious attack workflows across defined problem spaces. They vary allowed tuning dimensions, execute real runs, apply stage policy, and integrate the resulting evidence.

Campaigns must wrap core runs. They must not become a second solving architecture.

### 3.4 Tools

Tools are auxiliary only.

Important architecture must not quietly live in `tools/`.

---

## 4. One true public run entrypoint

There should be one true public run entrypoint: **RunSpec**.

RunSpec is the public solve description used by tutorials, API use, GUI or web front ends, direct runs, and campaign-generated runs.

Campaigns may generate or organise concrete RunSpecs, but they do not replace them.

There must not be a rival second solve-description language.

---

## 5. Solving families and cross-cutting capabilities

### 5.1 First-release built-in solving families

The first release should treat these as the main built-in solving families:
- monoalphabetic substitution
- periodic substitution
- periodic substitution with transposition

Interrupter-bearing cases, reading-order handling, text transforms, and related attack assumptions are important, but they are generally treated as cross-cutting capability or campaign-level dimensions rather than separate top-level solving families in the same sense.

### 5.2 First-class cross-cutting capabilities

The following are first-class cross-cutting capabilities, not separate solving families in the same sense:
- reading-order handling
- text-transform handling
- transposition of text before cipher application where relevant
- interrupter handling where relevant
- device-aware execution
- rescoring
- ScorerReport
- SolverReport
- campaign wrapping

### 5.3 Support matrix rule

The v1 support story must be made explicit in a feature-support matrix.

That matrix should say:
- which solving families are first-class in the first release
- which cross-cutting capabilities are guaranteed
- whether support is universal, where relevant, intentionally limited, or not part of the supported combination
- how unsupported combinations fail clearly and consistently

The matrix should eventually be proven by tests rather than left as a loose document only.

---

## 6. LP support and tutorials

### 6.1 Liber Primus support

LP support is first-class.

RDP v1 should include a first-class *Liber Primus* domain module, even if it is not physically inside the strict solving package.

### 6.2 Tutorials and examples

Tutorials are a first-class teaching surface.

They must use the real supported system, not a toy layer.

This includes re-solving solved LP pages as teaching material.

Tutorial ciphers such as railfence, simple columnar transposition, Vigenère, autokey, key drag, and similar examples may be supported as tutorial exemplars and framework proofs without automatically becoming first-release built-in solving families.

The presence of a tutorial or old test does not by itself make a feature part of the v1 public support promise.

---

## 7. Extension is first-class

RDP v1 should support clean extension.

Users should be able to add new:
- ciphers
- key families or key operations
- scorers
- problems or problem sources
- campaign components

and have them work through the normal shared contracts.

This must not require side-door hacks or one-off wiring.

---

## 8. Device support

CUDA is a first-class v1 capability where relevant.

This does not mean every line of code must run on the GPU. It means:
- the supported workflows should work properly in a real mixed CPU/GPU environment
- GPU-backed scoring or compute should be usable as a normal option where sensible
- included methods should not be designed in a way that blocks device use for no good reason

CPU-only behaviour is still acceptable where GPU use is not sensible.

---

## 9. Anti-drift rules

These are the internal engineering rules that should guide implementation even when old code already exists.

### 9.1 Core is strict

Core is strict. Forgiveness lives only in explicit normalisation layers at the boundary.

### 9.2 Typed core

Core should use enums and typed objects, not loose strings.

### 9.3 No magic strings in core

Core should not rely on ad hoc string values with hidden meaning.

### 9.4 No silent behaviour changes

No changes to defaults, ordering, filtering, scoring behaviour, path handling, privacy rules, or output meaning should happen quietly.

If behaviour changes, it should be made clear in code, tests, and notes.

### 9.5 No bypass hacks

No feature-specific hacks should bypass shared contracts.

### 9.6 No campaign policy leaking into core

Benchmark or campaign behaviour should not quietly become core behaviour unless that is an explicit design decision.

### 9.7 Shared output rules

Output writing should use one shared writer and one shared rule set across the repo where possible.

### 9.8 Tests and contracts first

Meaningful tests and clear contracts should come before structural tidy-up.

### 9.9 Avoid shim layers

Do not add shim layers unless there is a clear purpose and a likely removal path.

### 9.10 New first-class features must fit the pattern

Do not bolt new major features on sideways. They should fit the common system pattern.

---

## 10. Scoring and reporting governance

### 10.1 Scoring is core

Scoring in RDP v1 is a core capability.

Scorers are real supported solving tools.

They may be used:
- as main solving scores
- for staged solving
- for candidate filtering
- for later rescoring and comparison
- for reporting and summaries

### 10.2 Included core scoring capabilities

At minimum, v1 should include:
- n-gram scoring
- span-hamming with words

These should be properly implemented, maintained, data-backed, and tested.

### 10.3 One generic scoring interface

Core should provide one generic scoring interface.

That means one common way for the system to call scorers, collect their results, and combine them, even if the internal details differ.

### 10.4 Search score versus report score

There is not a hard wall between a score used during solving and a score shown in a report. The same metric may be used for both.

However, they still play different roles:
- a search score helps the solver decide what to keep, reject, or rank
- a report score helps explain or summarise what happened

Core should support both roles without splitting them into unrelated systems.

### 10.5 ScorerReport

ScorerReport is a stable core concept.

It should support both candidate-level detail and higher-level summaries.

### 10.6 SolverReport

SolverReport is a stable core concept.

It is the smallest stable run summary that lets the user understand what was run, how it was run, what mattered, what came out, and why it stopped.

At minimum it must support reconstruction and clear linked artefact references using logical or relative references only.

---

## 11. Formal rescoring governance

Formal rescoring is part of v1.

The system should retain enough state to reconstruct and rescore results later in a reliable way.

### 11.1 Minimum retained state

The minimum retained state is:
- `ciphertext` or canonical input text actually used
- `cipher_kind`
- `method_kind`
- full `key_state`
- `alphabet_version` or alphabet id
- `transform_state`
- `interrupter_state` where relevant
- `normalisation_version` if normalisation affects reconstruction
- `candidate_id` or result id
- `run_id`
- `core_version`
- logical asset ids or versions needed to interpret the reconstructed text correctly

### 11.2 Reconstruction rule

Retain the smallest state that guarantees deterministic reconstruction of the candidate text for later rescoring.

If deterministic reconstruction is not guaranteed, store the candidate text explicitly.

---

## 12. Campaign governance

### 12.1 What a campaign is

A campaign in RDP is the framework for **optimising the optimiser** against a specific problem and a specific range of input assumptions.

A campaign is not just a single run, and not merely a loose batch of runs. It is an orchestrated, data-integrated way to explore and compare meaningful variations in run configuration for a narrowly defined attack problem.

For v1, the real use of campaigns is LP-first. Campaigns exist to help RDP mount the strongest credible narrowly defined LP attacks the project can currently support.

### 12.2 Campaign relationship to core

Campaigns sit above core runs.

They may define stages, sweeps, retries, survivor selection, concentration, and later rescoring.

They must organise or generate real RunSpecs rather than bypassing the shared run contract.

### 12.3 Campaign tuning dimensions

Campaign variation must come from a **chosen countable subset** of real valid run settings, assumptions, or ranges.

Some tuning ranges may be small and some large, but they should be expressible clearly.

The campaign layer must not invent unrelated mystery knobs with no honest relationship to the real run world.

### 12.4 Campaign stages

Stages are first-class campaign structure.

For LP work they are expected to be central rather than optional garnish.

The campaign layer must support layered attack structures such as exploration, selection, survivor carry-forward, later concentration, optional rescoring, and explicit stopping behaviour.

### 12.5 Generic campaign framework capabilities

The generic campaign framework should support:
- execute one stage
- execute staged sequences
- fan out a parameter sweep
- collect stage results
- apply selection rules
- carry survivors or selected results into the next stage
- emit campaign-level summaries and telemetry views
- stop, fail, or continue in a structured way

### 12.6 Campaign-level outputs

A campaign should emit:
- campaign summary
- stage summaries
- linked run reports
- comparison summaries
- telemetry summaries
- clear logical artefact references

At minimum, campaign outputs must preserve enough information to reconstruct what was run and what came out, even if more detail needs to be recollected later.

### 12.7 Campaign policy hooks

The campaign layer should own decisions like:
- retry with more seeds
- retry with a different scorer mix
- rescore survivors with a heavier scorer
- widen or narrow a sweep
- stop after poor yield
- continue collecting candidates until explicit diversity, survivor, count, or budget targets are met

Simple bounded control loops are allowed where needed.

Deeply magical adaptive logic is not part of the generic campaign framework.

### 12.8 Campaign defaults

The framework may provide a small standard set of stage and policy defaults.

Those defaults should be sufficient for the full LP campaign the project actually needs, while remaining extensible rather than restrictive.

### 12.9 Out of scope for the generic campaign framework

The generic campaign framework should not allow or depend on:
- a second config language unrelated to the core RunSpec
- campaign-local output-writing rules
- campaign-specific scorer contracts
- deeply magical adaptive logic
- arbitrary parallel side-door architecture

---

## 13. Output and privacy contract

Portable outputs must be privacy-safe by default.

### 13.1 Absolute paths

Absolute paths must not appear in portable outputs.

### 13.2 Redaction

Redaction is on by default.

### 13.3 Console output

Console output must follow the same privacy rules as structured files.

### 13.4 JSONL event streams

JSONL event streams should contain portable, structured, privacy-safe run facts.

They must not become a dumping ground for local machine state.

### 13.5 Traces

Detailed traces should not be part of the normal default output contract unless explicitly enabled.

### 13.6 Output location

All normal run artefacts should live under repo-root `output/` with one shared folder policy.

### 13.7 Ownership of output rules

Core owns the shared artefact-writing logic, redaction rules, and path policy.

Campaigns and runners may choose what to emit, but they must use the shared writer.

---

## 14. Repo shape governance

The intended repo shape for v1 is:

### 14.1 Strict solving area

A strict solving area for the typed solving contracts, scoring, reports, output rules, and shared logic.

The exact final name of this area is still open.

### 14.2 `campaigns/`

A first-class top-level area.

This should include:
- a generic campaign framework
- specific campaign implementations built on that framework

### 14.3 Liber Primus domain module

A first-class LP module, even if it is not physically inside the strict solving package.

### 14.4 Tutorials and examples

A first-class teaching surface, clearly separate from machine-readable problem definitions.

### 14.5 `tools/`

Auxiliary only.

Important architecture should not quietly live in `tools/`.

---

## 15. Asset and data governance

RDP v1 should distinguish clearly between different kinds of data.

### 15.1 Repo asset sources

Compact, portable, versioned source forms stored in the repo where sensible.

### 15.2 Installed or materialised runtime assets

Unpacked or built forms used locally at runtime under `assets/`.

### 15.3 Small packaged data

Small data that is genuinely small enough to ship directly with the code.

### 15.4 Folder rule

In repo:
- compact source assets kept in a dedicated asset-source area
- manifests kept alongside those source assets or in a clearly linked manifest area
- genuinely small packaged data may live inside the relevant module if that is the cleanest place

At runtime:
- `assets/` for installed or materialised usable assets
- `output/` for run outputs only
- never mix generated output and installed assets

### 15.5 Manifest rule

Every significant asset set should have a manifest with at least:
- `asset_id`
- `asset_kind`
- `asset_version`
- `source_format`
- `materialised_format`
- `build_or_unpack_rule`
- `logical_role`
- `integrity_info`
- `compatibility_info`
- `human_description`

Where relevant, manifests may also include privacy notes.

### 15.6 Runtime rule

Core and campaigns should refer to assets by logical id and version, not by hard-coded local path assumptions.

---

## 16. Proof standard for v1

RDP v1 needs both **solve-proof** and **contract-proof**.

### 16.1 Solve-proof

The built-in first-class workflows must solve real representative problems and support the intended LP attack work honestly.

### 16.2 Contract-proof

The public support promises must be testable and tested.

This includes:
- RunSpec acceptance and validation
- clear failure for unsupported combinations
- ScorerReport and SolverReport availability where promised
- formal rescoring reconstruction where promised
- campaign progression and outputs where promised
- shared output/privacy rules
- support-matrix behaviour

---

## 17. Remaining lock-down items

The remaining owner-level lock-down items before implementation planning are now small and specific:
- final wording of the formal campaign spec
- final wording of the refactor plan built from this charter and the campaign spec
- final support-matrix wording and test intent

Everything else should now move toward implementation planning rather than further broad design debate.
