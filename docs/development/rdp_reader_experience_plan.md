# RDP reader experience: implementation plan

Date: 2026-09-05

Status: implemented; targeted verification complete. Publication is recorded in
the branch history and delivery message.

## Purpose and authority

Make RDP understandable both through its runnable examples and by browsing its
source. Explain each RDP concept where the reader first needs it, give every
maintained project folder a useful local orientation, and remove setup and
presentation clutter from the examples' main narrative.

This is the follow-up to the
[onboarding migration specification](../release_contracts/v1/V1_RR_ONBOARDING_AND_EXAMPLES_SPEC.md).
Its audience, lowercase `mortlach` attribution, preservation of existing examples
and separation of getting started from worked examples remain in force. Later
owner instructions control: explain RDP concepts, mention custom key development,
provide folder READMEs, explain useful options and their effects, and never run
broad or long tests without an explicit request. The owner subsequently authorised implementation and GitHub publication.

Follow the [core design principles](../release_contracts/v1/RDP_CORE_DESIGN_PRINCIPLES.md)
and [accepted V1 decisions](../release_contracts/v1/V1_AUTHORITY_AND_DECISIONS.md).
This work does not expand the API or reorganise the engine.

## Starting state

- Repository: `mortlach/RuneDecrypterPrime`.
- Working branch: `prelease/v1-release-readiness`.
- Last reported published migration commit:
  [`468c35c1e1c7a75d58414d4e06b325cabd05a526`](https://github.com/mortlach/RuneDecrypterPrime/commit/468c35c1e1c7a75d58414d4e06b325cabd05a526).
- Local committed migration head: `0f2526b`; publication previously used a
  separate commit containing the same tree. Do not assume identical ancestry.
- Existing local drafts modify seven starting scripts, three worked examples,
  the runner, guides, indexes and related tests. Untracked drafts include stops
  08–10, an anatomy-of-a-run guide and two folder READMEs.
- These drafts predate this plan. Preserve and review them before further edits;
  their presence is not evidence of acceptance, execution or publication.

Recheck the branch and relevant diff when implementation begins. Continue from
the current work; do not reset the branch or reconstruct the migration again.

## Reader, voice and explanatory pattern

The reader can read Python and has a cryptanalytic or development question.
They are new to RDP's conventions. Write with technical confidence, ordinary
language and restrained dry humour. Public identity is exactly `mortlach`, with
no biography. Avoid school language, promotional language, forced jokes and
repeated warnings that drown out the explanation.

At the first use of a concept across the starting sequence, put a short comment
immediately before the relevant code. It should explain:

1. what the object represents;
2. what job it does in the cryptanalytic process;
3. why this example uses this form;
4. the nearby alternatives and where to investigate further, when useful.

Later examples briefly recall the idea and explain their new choice. Do not
repeat the entire introduction or narrate ordinary Python syntax. Keep input,
cipher, key space, solver, scoring and result visible in the code.

The agreed key introduction, including the owner's final addition, is:

```python
# KeySpec defines which candidate keys the solver may consider.
# Here the unknown is one integer: the number of rails.
# Other problems use a repeating vector of values or a permutation,
# such as the order of columns in a columnar transposition.
# Custom key types and their search operations can also be implemented
# as part of cipher development; see docs/howto/add_cipher.md.
key_space = api.KeySpec.scalar(minimum=2, maximum=8)
```

Explain concrete keys at their first use too: they contain actual key values;
`KeySpec` describes the allowed candidates. Use `repeating(...)` as the current
public constructor for the repeating-vector example; do not invent `vector(...)`.

The extension sentence introduces a contributor route. Detailed documentation
must explain the key layout, valid search operations, runtime integration and
any separately approved public binding. It must not promise that arbitrary
custom classes can be passed straight into the existing public `KeySpec`.

### Useful options and what to change

Where a choice matters, explain a few relevant alternatives so the reader can
see what else RDP can do and what they might change for their own problem.
Keep the explanation close to the setting or component it concerns. A short
comment can point to a fuller guide; a folder README can include a small
"Useful options" section when that folder owns configurable behaviour.

For each selected option, explain what it controls, why the example chose its
value, and the practical effect or constraint of changing it. Distinguish a
library default from a value chosen for the example. Mention dependencies when
relevant, such as larger model assets or compatibility with the chosen cipher.
Check option names and behaviour against the current implementation.

Examples of the intended explanation:

| Choice | Useful context |
| --- | --- |
| Scalar key bounds | These delimit candidate rail counts. Excluding the true count makes recovery impossible within that space. |
| Repeating key length | This fixes how many values are unknown. Searching a range of lengths changes the problem and its cost. |
| Beam width | This controls how many candidates are retained at the relevant search stage. A wider beam can retain alternatives at greater cost; it does not guarantee recovery. |
| Solver family | Explain why this recipe uses beam search, GA, SA or hybrid, and point to a compatible alternative where useful. |
| Scoring evidence | Explain the selected character or word-information contribution, what a change would measure, and any required inputs or assets. |
| Result detail | Show where to request or inspect more detail when investigating a run, without making verbose reporting dominate every example. |

These are selected explanations, not a requirement to enumerate every option in
every file. Keep ordinary configuration choices separate from implementing an
extension. In source-folder READMEs, explain the public configuration entry point
before any internal extension mechanism, where both are relevant.

### Formatting and presentation

- Use one descriptive H1 and a shallow, consistent heading hierarchy in Markdown.
- Leave blank lines around headings, lists, tables and fenced code blocks.
- Use backticks for identifiers and short paths; use relative Markdown links to
  actual local files and guides. Keep prose paths consistent with the current tree.
- Use fenced `python` blocks for code, with readable multiline requests and
  ordinary straight quotes. Keep commands in their own appropriate code block.
- Use short tables for comparisons and file-role maps; use paragraphs or lists
  when cells would become long explanations. Avoid nested lists where possible.
- Put comments immediately before the relevant code, with enough spacing to
  distinguish the input, request and result. Avoid long banner comments and
  excessive emphasis or horizontal rules.
- Use rendered Markdown headings when converting old text READMEs; remove old
  underline banners, conversation residue and unnecessary identifier escaping.
- Read the finished files as a person browsing GitHub would. Check heading
  order, fences, table structure and links; inspect a rendered view where
  available. Do not introduce a documentation build system for this polish.

## README style references

The ten supplied READMEs are style examples only. They illustrate the desired
level of explanation: a clear purpose, a useful map of files, concise design
notes, relevant options and a route to extension. Their short descriptions of
what algorithms and components do are a useful model for the new prose.

Write fresh content from the current source and accepted contracts. Do not
insert the old text, mechanically update old names, or treat the attachments as
a technical source to migrate. Adapt the structure to each folder; there is no
fixed template to fill or requirement to reproduce every heading.

The supplied files remain unchanged and are not copied into the repository.

## Work packages and order

### 1. Review drafts and establish the explanatory thread

Read the existing local changes against the published version. Retain useful
work, correct inaccuracies and remove unnecessary expansion within the affected
files. In particular, formatting a long example more neatly does not by itself
make the example easier to follow.

Use the existing seven stops as the established route:

| Stop | Explanation to establish or strengthen |
| --- | --- |
| 01: known key | Rune/index representations, cipher rule and concrete key; applying a supplied key. |
| 02: first search | Candidate key space, scalar and alternative shapes, custom-key extension pointer, solver and scorer roles, the assembled request. |
| 03: repeating key | Key length versus contents, repeating values, raw rune input and word information. |
| 04: reproducibility | What the seed controls and which other conditions belong with a repeatable result. |
| 05: interruptors | What is preserved and how the configured cipher/key stepping handles those positions; supplied positions versus searched positions. |
| 06: partial recovery | Work budget, stopping and reference agreement; what the returned candidate establishes. |
| 07: LP source | Named source, payload and metadata; the transition to a real-source investigation. |

Keep the rationale beside the settings that embody it. Introduce defaults and
explicit overrides accurately; avoid presenting an example-specific choice as
a universal requirement.

### 2. Consider additional starting examples

Review the three existing drafts individually:

- `08_reading_a_result.py`: useful if it demonstrates inspecting and acting on
  result fields beyond the explanations already beside earlier runs.
- `09_changing_search_budget.py`: useful if it makes one controlled comparison
  beyond the partial-recovery example, with short, bounded work.
- `10_prepare_a_real_source_search.py`: useful if it connects a source payload
  to a valid request without suggesting that an unexecuted search has solved it.

Keep, combine or reposition them according to the story. Ten files is not a
target. Another example is admissible when it fills a demonstrated gap,
introduces a different problem shape or makes a supported feature usable.
Do not add a custom-key implementation tutorial merely to support the brief
extension pointer; link to the contributor material.

New stops must remain public-API-only, use bundled inputs and fit a short local
run. Preserve the value of specialised material in `examples/`.

### 3. Clean the worked examples and execution setup

Start with the three already edited examples: columnar transposition, repeating
multiplication and scheduled-stream lookup. Establish a readable pattern there,
then apply the relevant cleanup to the remaining retained examples.

- Remove repeated `sys.path`, repository-root and source-path injection from
  reader-facing scripts. Use the installed package plus a documented repository
  module execution route for scripts needing `tutorials` support.
- Keep the shared runner simple and align its subprocess invocation and working
  directory with that route. Direct public-only scripts should retain their
  straightforward installed-package use where supported.
- Reuse existing `support/` owners for repetitive display and fixture plumbing.
  Helpers should have concrete jobs and explicit imports. Avoid a generic
  bootstrap facade, wildcard imports or a helper that hides the whole solve.
- Keep cipher, key model, search budget, scorer, supplied evidence and semantic
  acceptance in the main file. Keep any reference-derived stop threshold visible.
- Prefer reporting the executed request; remove misleading or unnecessary
  parallel display configurations after checking why they exist.
- Preserve the scientific recipe and its expected result. If cleanup requires
  changing those, stop that part and present the specific decision.

Preserve all retained examples and their asset/runtime distinctions. Keep
qualification programs excluded from ordinary selections. Adding a new starting
file must not silently turn the release selection into a long run; review group
membership and documented runtime when the route changes.

### 4. Provide folder READMEs throughout the maintained project

Inventory the tracked project folders, including existing README formats such
as `README.txt`, before creating replacements. Merge useful existing content
into one local `README.md`; do not leave competing local introductions.

Cover all main folders and maintained subfolders that a reader can browse:

- root-level `assets`, `cipher_development`, `docs`, `requirements`, `solving`,
  `src`, `tests`, `tools`, `tutorials` and retained historical `v1_docs`;
- `src/rdp` and every implementation domain: `api`, `backends`, `core`,
  `ciphers`, `keyops`, `solvers`, `scoring`, `telemetry`, `data` and `io`;
- their nested packages, including core configuration/problem/engine, scoring
  implementations, LP and word data, and solver progress;
- tutorial starting files, examples, support and data; maintained documentation,
  test, tool, solving and cipher-development subfolders.

For each folder, explain its purpose in RDP, the roles of its important files
and children, its connections to neighbouring components, where to start reading
and where to find further detail. State public versus internal use where it
helps the reader choose an entry point. Small folders may need only a paragraph.

Use the supplied READMEs as a model for clear design notes and extension guidance.
Where appropriate, add a few useful configuration choices with their effects,
and a short explanation of how this component can be extended. Link to the
current contributor guide for implementation details. Omit empty or irrelevant
sections; a data folder does not need invented solver options.

Do not recursively add documentation to generated output, caches, installed
dependencies, Git internals or external asset packs. Do not inspect local LM
asset content for this task. Historical material needs a clear status and route
to current documentation, not a fresh rewrite.

Use a working inventory to avoid omissions, not a permanent manifest or a new
registry. File roles can be grouped; there is no requirement to catalogue every
fixture or repeat API signatures. No exact folder-count or README-wording tests.

### 5. Connect and correct the guides

Update `docs/development/docs_style.md` with the comment and folder policies.
Align the README, installation guidance, quickstart and tutorial catalogue with
the final route and invocation method. Preserve wheel-versus-checkout accuracy.

Review `docs/guides/anatomy_of_a_run.md` as the longer explanation linked from
short comments. Merge overlap with existing guides so it has one clear role.
The quickstart should explain why the pieces fit together before sending readers
to further pages. Folder READMEs provide local maps and link to these guides.

Repair `docs/guides/keyops.md`: it currently mentions `repeat` and `const`, which
do not match the inspected public constructors. Align its extension explanation
with `docs/howto/add_cipher.md`, `src/rdp/api/specs.py` and the actual key-operation
owners. Check related destination pages before introducing new links to them.

Keep P7/C7 follow-up visible in the existing roadmap, tied to the existing staged
tools. Campaign execution, new cipher development and scientific recipe tuning
remain separate work.

## Implementation checkpoints

Use the work packages above as one implementation sequence; no additional
planning pack is required. Begin with a small representative set to establish
the prose and code pattern, then carry it through the remaining scope.

| Stage | Concrete review point |
| --- | --- |
| 1. Reconcile drafts | Identify the existing edits worth keeping and confirm the current branch state without discarding work. |
| 2. Establish the pattern | Polish first-search comments, one worked example and the `api` and `keyops` folder READMEs, including options and extension pointers. |
| 3. Complete the runnable route | Apply the pattern across starting files and examples; resolve the three proposed additions and finish setup cleanup. |
| 4. Complete folder orientation | Cover maintained folders with fresh explanations grounded in current source, following the agreed style. |
| 5. Join the documentation | Align guides, catalogues, execution instructions, extension links and style guidance; inspect formatting. |
| 6. Close and publish | Run only necessary short checks, report omissions accurately and provide the verified GitHub link under the publication rules below. |

At each stage report the useful result, any real decision and the next bounded
step. Routine editorial choices do not require another approval cycle. Preserve
semantic behaviour and update affected consumers within the same coherent change.

## Verification, completion and publication

Use small, targeted checks only. For prose changes, read the diff and check
changed links, paths and API names against source. No executable test is needed
merely to prove a paragraph exists.

For invocation or helper changes, use focused import/runner checks and short
affected examples. Run only the smallest existing semantic checks needed to
confirm preservation of behaviour. New tests are warranted for a real risk,
such as failure propagation or accidental qualification selection, not exact
prose, file counts or formatting. Do not run the full suite, CI-light suite,
full-asset proof, slow solver tests or campaigns unless explicitly requested.
Check expected duration before starting executable verification.

Complete the work in reviewable groups: starting-route comments and additions;
example/setup cleanup; folder READMEs; guide consolidation. Update directly
affected consumers with each group so intermediate commits remain coherent.
Do not commit unrelated existing changes without reviewing them.

Completion means a reader can follow the starting scripts, identify the main
RDP objects and their alternatives, understand a few useful changes they can
make, find the custom-development route, browse each maintained folder with a
useful explanation, and select a worked example without wading through repeated
setup code. Formatting must support that reading path. Existing semantic claims
and V1 boundaries remain intact.

At implementation handoff, identify exactly what was checked and what remains
unrun. Make the completed work visible on the authorised GitHub branch and give
a verified branch/commit link; do not silently finish with local-only work. Honour
the owner's existing publication authorisation, reconcile the differing local
and published ancestry without a force push, and disclose any access blocker.
Check automatic workflow triggers against the owner's restriction on broad and
long tests before publishing; raise a concrete conflict rather than silently
changing workflow policy or starting expensive verification.

## Decisions and limits

No owner question blocks this plan. Custom-key wording, audience, identity,
concept-level comments and folder orientation are settled. The number of new
examples is an editorial outcome, not a quota.

Ask the owner only when evidence exposes a genuine choice: a required scientific
recipe change, new public API capability, conflicting execution requirement or
publication gate that would require prohibited verification. Record the specific
conflict and keep progressing on independent work.

## Implementation record

The reader-experience pass adds the three reviewed starting stops, explains RDP
objects and useful alternatives at first use, and retains all 26 worked examples.
Repeated import-path setup is removed from the examples; the runner launches
repository modules. The columnar, multiplication and supplied-stream examples
keep their recipes visible with less presentation plumbing.

Every maintained tracked project folder now has a Markdown README. The two
source README text files are replaced by current Markdown introductions; their
existing documentation check follows the new paths. Folder notes are newly
written from the current code, using the supplied old files only as style models.
Key-space, solver and scoring guides now explain current options and extension
routes. The catalogue identifies columnar's actual hybrid solver.

Verification was limited to the short starting route, runner behaviour,
changed documentation/package-path checks, and five worked examples. The first three
passed in approximately 4.2, 17.7 and 21.4 seconds on this CPU. No full repository
suite, CI-light suite, full-asset proof or qualification campaign was run.
Duplicate display requests were also removed from straightforward retained
examples with their executed request expressions preserved. The rail-fence and
exact-interruptor examples passed after that presentation change.

The broad automatic push gate is skipped for this publication at commit level,
in accordance with the owner's test restriction; workflow policy is unchanged.
