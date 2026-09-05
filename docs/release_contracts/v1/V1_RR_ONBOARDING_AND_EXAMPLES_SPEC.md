# V1-RR onboarding and examples migration specification

Status: approved implementation plan; owner decisions recorded in Section 16

Date: 2026-09-05

## 1. Purpose

This change will give Rune Decrypter Prime one coherent route for a capable new
user while preserving the existing body of runnable research and solver
examples.

The migration has four outcomes:

1. replace the accidental `introductory` versus `advanced` grading with a
   purpose-based distinction;
2. create a short `getting_started` route that introduces RDP's ordinary public
   workflow without becoming a Python or cryptography course;
3. retain the existing V1 scripts as a browseable `examples` library, with
   honest information about purpose, dependencies, runtime and acceptance;
4. rewrite the active documentation as one causal story: why RDP exists, how to
   run it, how to understand the result, and where to go for a particular kind
   of problem.

This is a tutorial and documentation migration. It does not reopen the V1
public API, package ownership or solver design.

## 2. Authority and constraints

This work is governed by:

- [`RDP_CORE_DESIGN_PRINCIPLES.md`](RDP_CORE_DESIGN_PRINCIPLES.md);
- [`V1_AUTHORITY_AND_DECISIONS.md`](V1_AUTHORITY_AND_DECISIONS.md);
- the accepted AN1-AN4 public and package contracts;
- the V1-RR task brief;
- later owner decisions recorded in this specification.

The controlling design rules are:

- provide one ordinary route for a normal task;
- keep normal-user imports on `from rdp import api`;
- reveal specialist complexity only when it is used;
- keep requested and effective behaviour visible;
- prefer the correct design with fewer concepts and maintenance obligations;
- preserve deterministic, test-backed behaviour;
- do not confuse a successful example with a broader scientific claim.

The accepted baseline is:

```text
3749891c6244fbf9c1832013da220f888ba2bb04
```

The provisional first-pass head reviewed while writing this plan is:

```text
27286eae8cb7db1a1a67c361aa3b326f679c7bd8
```

The first-pass commits must be preserved on a safety branch before the working
branch is reconstructed. No destructive Git operation and no push is authorised
by this document alone.

## 3. Reader and purpose

### Primary reader

The primary reader is technically capable but new to RDP. Likely readers
include:

- an independent Liber Primus or classical-cipher researcher;
- a software or scientific engineer assessing the framework;
- an investigator who wants repeatable evidence rather than plausible-looking
  output;
- a serious hobby researcher who can read and edit ordinary Python.

The reader is assumed to:

- have Python 3.11 or newer;
- know how to run or edit a Python file;
- understand basic terms such as plaintext, ciphertext and key after a short
  definition;
- be willing to inspect a result rather than expect a one-button decoder.

The reader is not assumed to understand:

- RDP's repository or implementation-module layout;
- rune tokenisation, WLI or encoding direction;
- solver and scorer internals;
- language-model asset profiles;
- native extension builds;
- tutorial governance or release-review machinery.

The original high-school wording is treated only as a warning against needless
jargon. It is not the public audience definition. The getting-started route is
not intended to teach Python, general cryptography or the history of Cicada
3301.

### Secondary readers

The examples library also serves:

- experienced RDP users looking for a nearby working configuration;
- contributors checking solver and cipher behaviour;
- release reviewers running representative or full-asset evidence;
- researchers inspecting partial, robust or long-running recipes.

These readers should not be forced through the getting-started sequence.

## 4. The story

The documentation should follow the reason a reader needs each idea.

1. Liber Primus and similar work produce many outputs that look interesting.
   Looking interesting is not evidence.
2. RDP exists to make the input, cipher, key model, search, scoring, seed and
   result explicit enough to repeat and inspect.
3. A known-key round trip establishes the basic text and cipher boundary.
4. A small search shows what changes when the key is not known.
5. A repeating-key search shows the same request model on a more realistic
   problem without adding specialist machinery.
6. A real Liber Primus source connects the ordinary mechanism to the project
   that shaped it.
7. From there, readers choose an example by the problem they have. They do not
   graduate into an undifferentiated collection labelled advanced.

This gives the route a deliberate difficulty curve without describing the
reader by difficulty level.

## 5. Target repository structure

```text
tutorials/v1/
    getting_started/
        01_known_key.py
        02_first_search.py
        03_repeating_key_search.py
        04_reproducible_runs.py
        05_known_interruptors.py
        06_partial_recovery.py
        07_liber_primus_source.py
        __init__.py
    examples/
        *.py
        __init__.py
    data/
    support/
    README.md
    __init__.py
    run_tutorials.py
```

The structure deliberately remains shallow.

- `getting_started/` owns the ordered normal-user route.
- `examples/` owns the retained runnable script library.
- `data/` and `support/` remain shared repository-only support.
- `README.md` is the one human-readable index.
- `run_tutorials.py` owns curated execution groups, not educational metadata.

No manifest, source hash list, tag registry or output parser is added.

### Design references, not authorities

The structure also follows useful patterns in comparable technical projects:

- [Diataxis](https://diataxis.fr/tutorials-how-to/) distinguishes the reader's
  need from the material's difficulty. Basic/advanced and study/work are not the
  same division.
- [OR-Tools](https://github.com/google/or-tools) separates its guided start from
  its code examples.
- [angr](https://docs.angr.io/en/latest/examples.html) catalogues examples by
  problem, concepts and runtime, and describes partial assistance honestly.
- [CyberChef](https://github.com/gchq/cyberchef) gives brief factual context
  about its origin without turning the README into a biography.
- [`cryptography`](https://cryptography.io/en/latest/) uses personality at an
  important boundary while keeping its technical contract exact.

RDP should borrow the useful separation and restraint, not another project's
terminology or personality.

## 6. Getting-started route

### 6.1 `01_known_key.py`

Purpose: establish the ordinary known-key route before introducing search.

The script must:

- import only `from rdp import api`;
- present a short readable Latin phrase, its visible runes and its reviewed
  rune-index representation rather than opening with an unexplained tuple;
- construct a Vigenere cipher specification;
- call `api.encrypt` and `api.decrypt` with a known repeating key;
- print a plain result before any technical detail;
- assert semantic round-trip equality;
- use only packaged or built-in data;
- run quickly and deterministically from an installed package.

The file explains only the concepts needed for the operation: the cipher is the
rule and the key supplies the repeating values.

The accepted known-key operations take rune indices. `RawTextInput` is a
`RunSpec` input, and the root public namespace does not expose a general
Latin-to-rune conversion operation. Therefore this file must keep the three
reviewed representations together as literals and say why. It must not import
an internal encoder or expand the V1 API for presentation convenience.

### 6.2 `02_first_search.py`

Purpose: show the difference between applying a known key and asking RDP to
search for one.

The script should use a small rail-fence problem because its key space is easy
to see and its exact answer is cheap to verify.

It must:

- use only the public API;
- keep the full request visible in one place;
- identify what RDP is given and what it must find;
- use a fixed seed;
- use bundled scoring data only;
- print recovered key, recovered text, stop reason and exact-recovery status;
- assert the expected key and plaintext;
- avoid repository helpers, internal imports and path manipulation.

`RunSpec` is introduced as the record of the requested run, not as a class the
reader is expected to study.

### 6.3 `03_repeating_key_search.py`

Purpose: demonstrate that the same request shape works when the unknown key has
several repeating values.

It must:

- use a short Vigenere problem with a genuine solver search;
- use `api.RawTextInput` if the live public route supports the example cleanly;
- use public defaults unless an explicit value is necessary to make the example
  deterministic or understandable;
- identify key length separately from recovered key values;
- print the recovered readable text before the report detail;
- assert exact recovery;
- remain short enough to feel interactive.

The current experimental fixture took roughly 16 seconds locally. It is a design
probe, not an accepted final example. The implementation pass must tune or
replace it using measured evidence; it must not claim that runtime is quick
without checking.

### 6.4 `04_reproducible_runs.py`

Purpose: make determinism visible as an ordinary part of a run rather than a
release-engineering footnote.

It must:

- use only the public API and bundled assets;
- run one small request twice with the same fixed seed;
- compare the recovered key, plaintext, status and reported effective seed;
- explain that a seed is part of the run specification, not a claim that every
  device and dependency combination is interchangeable;
- print the comparison plainly;
- fail if the promised repeated result differs.

The implementation should reuse a small request shape already introduced in the
route. It must not add an artificial framework merely to share a few constants.

### 6.5 `05_known_interruptors.py`

Purpose: introduce a Liber Primus-relevant feature at the point where the
ordinary cipher model genuinely changes.

It must:

- use `api.InterruptorConfig.exact` rather than unknown-position search;
- use a small reviewed ciphertext fixture so construction does not require an
  internal encryption helper;
- show which symbols are left untouched and which core text is searched;
- use only the public API and bundled assets;
- print the recovered text and interruptor positions;
- assert exact recovery and unchanged interruptor symbols.

This file explains the known-position case only. Search strategies and
combinatorial limits remain in the examples library.

### 6.6 `06_partial_recovery.py`

Purpose: show how to read an honest bounded result when the search does not
recover every rune.

It must:

- use a deterministic, deliberately bounded public run;
- use only bundled assets;
- print the recovered text, match ratio, stop reason and work limit;
- make known truth used for validation visible;
- assert a stable accepted range rather than exact recovery;
- distinguish tutorial acceptance from production scoring;
- state plainly that partial evidence is not an exact solve.

The fixture and bounds must be established experimentally during implementation.
If a stable, quick and truthful partial example cannot be produced without
internal machinery, this stop requires an owner review; it must not be faked
with truncated output or an arbitrary altered answer.

### 6.7 `07_liber_primus_source.py`

Purpose: connect the ordinary API to the real domain that shaped RDP.

It must:

- use the public Liber Primus source interface;
- load one bundled, named and already-solved source such as Welcome Pilgrim;
- show the human source name, source label, text direction and bounded content
  preview;
- distinguish source material, a solve recipe, known truth and a solver result;
- avoid implying that loading a source solves it;
- direct the reader to the retained Welcome Pilgrim worked example;
- avoid internal `Runeglish`, workbook-loader or repository-path machinery.

If the public source object cannot provide a readable bounded preview without an
internal import, the script must show only the truthful public metadata and rune
indices. That is a product fact to document, not a reason to bypass the API.

### Common file shape

Each getting-started file should use the same quiet structure:

```text
Purpose
Given
Ask RDP
Result
Evidence of success
Where next
```

Do not add exercises, quizzes, contributor terminology or a long conceptual
preface. Brief comments should explain why a line exists, not translate every
line of Python into prose.

## 7. Adding further getting-started files

Seven files are now planned for the broader V1 route. They remain a coherent
sequence, not a quota to fill with unrelated capabilities.

A further file may be proposed only when it closes a demonstrated gap in the
story. A valid addition must do at least one of the following:

- bridge a real jump in difficulty between retained steps;
- introduce a V1 concept required for ordinary use;
- demonstrate a materially different public operation;
- make an important result or failure mode understandable;
- connect an ordinary RDP operation to a real Liber Primus workflow.

Before adding it, record:

- the gap that exists without it;
- why a paragraph in the current files or docs is insufficient;
- what new public concept it introduces;
- its asset requirement and measured runtime;
- the semantic condition that proves it worked.

Do not add a getting-started file merely because another cipher exists or a
configuration value can be changed.

Candidate gaps to assess during implementation, not pre-approved additions,
are:

- a public failure example if the normal validation boundary remains unclear;
- a feature that is part of ordinary V1 use but still has no readable public
  example after the seven planned stops;
- a missing bridge between source-labelled input and a worked solve.

Unknown-position interruptor search, robustness campaigns, composite problems
and large-asset scoring do not enter this route unless later evidence shows that
ordinary use is otherwise impossible to explain.

## 8. Existing examples migration

### Preservation rule

All 26 runnable `Tutorial_*.py` files present at the accepted baseline are
preserved as working material.

- The 25 files currently under `tutorials/v1/advanced/` move together to
  `tutorials/v1/examples/`.
- The former `Tutorial_Start_Here.py` content is restored as an example with an
  accurate role. It must no longer compete with the real first route.
- Existing scientific acceptance, seeds, asset dependencies and truth/oracle
  disclosure are preserved unless a concrete defect is found.
- Moving a file does not authorise solver tuning or scientific result changes.

The retained files may be renamed wherever that improves clarity. Their target
names use lowercase `snake_case`, omit the redundant `Tutorial_` prefix and
describe the actual problem. The directory already says that they are examples.
The former `Tutorial_Start_Here.py` becomes a descriptive Vigenere example rather
than retaining any claim to be the entry point.

### What an example is

An example is a runnable answer to a recognisable RDP problem. It may be:

- a straightforward worked solve;
- a specialist cipher or solver recipe;
- a robustness recipe;
- a partial-recovery case;
- a Liber Primus workbook bridge;
- a long qualification program.

Examples are not required to form an ordered course. They may use repository
support or exact internal owners when their purpose genuinely requires it, but
the index must disclose that they are source-checkout examples rather than the
normal installed-package route.

### Example index

`tutorials/v1/README.md` becomes the only complete human-readable catalogue.
Each row records:

| Field | Meaning |
| --- | --- |
| File | Direct runnable path. |
| Purpose | The problem or behaviour demonstrated. |
| Cipher / solver | The main runtime components. |
| Surface | Public API only or repository/internal support. |
| Assets | Bundled or full V1 assets. |
| Runtime | Measured order of magnitude, not an unsupported promise. |
| Result | Exact, thresholded partial, robust evidence or qualification. |
| Truth/oracle | Whether known answers affect setup, stopping or validation. |

The catalogue should group examples by problem family in prose or tables. It
should not require matching classification fields in each source file.

### Adding a new example

A new example is justified when it contributes at least one of:

- a useful step in the difficulty curve;
- a novel V1 problem shape;
- a feature with no clear working example;
- an important contrast between two supported modes;
- a real source or reproducibility case that existing scripts do not cover.

It must also:

- have one stated purpose;
- run from the documented location;
- declare its asset and approximate runtime class;
- use a deterministic seed when the algorithm is stochastic;
- own a stable semantic success or accepted-partial condition;
- disclose known key, plaintext and oracle use;
- avoid test-only fixtures;
- provide a reason to exist beyond changed constants.

If the value is mainly regression protection, it belongs in `tests/`. If it is a
developer experiment with no stable result, it belongs in the relevant
development area rather than the public examples catalogue.

## 9. Runner contract

`tutorials/v1/run_tutorials.py` remains a small, directly editable Python
runner. V1 does not add command-line configuration or a second runner.

Proposed run groups are:

| Group | Contract |
| --- | --- |
| `GETTING_STARTED` | The complete ordered starting route. |
| `RELEASE` | The starting route plus a small, fast and representative example set. |
| `BUNDLED_EXAMPLES` | Runnable examples that use only the bundled asset profile and exclude long qualifications. |
| `FULL_ASSET_EXAMPLES` | A bounded representative set that proves the full V1 assets. |
| `QUALIFICATION` | The explicitly named long-running qualification programs. |

There is no harmless-sounding group that silently includes several-hour work.

Runner rules:

- discover the ordered route by its numeric filenames;
- discover the examples directory from its Python files while excluding
  `__init__.py`;
- retain only small explicit exception sets for assets, release selection and
  qualification runtime;
- fail clearly if an explicitly selected file is missing;
- execute each script in a subprocess;
- treat the script's exit status as its semantic acceptance result;
- retain compact console output and complete per-script logs;
- announce full-asset and qualification selections before execution;
- do not parse prose output;
- do not hash source;
- do not duplicate the human catalogue.

The exact `RELEASE` members are selected after measuring the migrated scripts.
They should cover different behaviour, avoid duplicating the starting route and
remain suitable for ordinary Windows and Linux push gates.

## 10. Documentation information architecture

The normal reader route becomes:

```text
README
  -> installation
  -> getting started
  -> runes and text
  -> examples index
  -> task guides
  -> reference and expert material
```

### Repository README

The README should open with:

1. what RDP is;
2. why repeatability and visible evidence matter;
3. its Liber Primus-first but not Liber Primus-only scope;
4. the simple public identity `mortlach`, without a professional biography;
5. the shortest installed-package example;
6. installation and source-checkout routes.

CI matrices, package-proof details and internal contract evidence move below the
user route.

### Installation

`docs/setup/installation.md` must distinguish:

- using an installed wheel;
- using a source checkout;
- the complete `python install.py` V1 development/research setup;
- bundled assets;
- full LM1-LM4 assets;
- optional Torch and native build requirements.

The wheel and sdist currently prune `tutorials/`. Therefore:

- the README and getting-started guide must contain a tested, copyable public
  API example that works with the installed wheel;
- file paths under `tutorials/v1/` must be labelled as source-checkout paths;
- this migration does not add an installed tutorial namespace or public entry
  point.

### Getting-started guide

`docs/guides/quickstart.md` should become the prose companion to
`getting_started/`, or be renamed only if link migration proves worthwhile. It
must explain the result of each stop without copying the whole source file.

### Runes and text

Promote the useful material from `v1_docs/runes_and_text.md` into the canonical
docs tree after checking every statement against the public API. It should
explain English text, rune text, indices, canonical spelling, direction and WLI
only to the depth needed to interpret a run correctly.

### Examples index

`docs/tutorials/index.md` becomes the user-facing route into the repository
catalogue. It should present:

- the ordered getting-started route;
- problem-oriented example groups;
- dependencies and runtime warnings;
- the distinction between examples, solved LP workbooks, tests and maintainer
  tools.

### Duplicate and stale pages

During implementation:

- merge any unique useful content from `docs/howto/beginner_guide.md` into the
  canonical getting-started guide;
- reduce or remove `docs/user/README.md` as a competing front door;
- remove the nine short superseded/retired tutorial signposts after confirming
  and updating their inbound links;
- selectively promote useful `v1_docs/` material before describing that tree as
  historical;
- preserve release-contract evidence that tests consume.

## 11. Voice and style

### Voice target

The prose should sound like a local technical expert explaining why each part
matters to another capable person.

It should be:

- plain and concise, with British spelling;
- causal rather than encyclopaedic;
- sceptical of claims that are not backed by evidence;
- self-aware about the project's scale and origins;
- dry in small doses;
- confident about tested behaviour and explicit about everything else;
- technical where the detail changes what a reader should do.

It should not be:

- generic product prose;
- a school text;
- an academic imitation;
- faux-mysterious Cicada prose;
- self-congratulation;
- a CV embedded in a README;
- jokey in error messages, contracts or scientific qualifications.

Use one understated dry line where it sharpens a boundary. Do not stack jokes or
write around a weak claim with personality.

### Narrative rule

Do not flatten the explanation into a list of features. Establish the problem,
then the consequence, then the design response.

Preferred shape:

```text
Plausible plaintext is easy to produce.
Therefore a result needs visible evidence.
RDP keeps the run specification, seed, scoring and stopping reason inspectable.
Here is the smallest run that demonstrates that contract.
```

### Owner context

The public identity is simply `mortlach`.

Do not name a profession, employer, laboratory, scientific facility or
leadership title. Do not add a biography to justify the project. The influence
of operational engineering may be present in the writing through explicit
state, repeatability and visible failure, but it is not presented as authority.

A sufficient attribution is:

> RDP is an independent project by mortlach.

### Useful dry register

Suitable:

> An exact result in a constructed example proves the example. It does not make
> the remaining Liber Primus pages any more solved.

Suitable:

> The subject matter already has enough mystery. The run configuration does not
> need to add any.

Avoid promotional adjectives such as revolutionary, seamless, effortless,
world-class and cutting-edge. Prefer the exact capability and its evidence.

## 12. Migration map

### Tutorial source

| Current/provisional owner | Target action |
| --- | --- |
| `tutorials/v1/introductory/` | Replace with `getting_started/`; reuse sound code only after rewriting the narrative and inputs. |
| `tutorials/v1/advanced/` | Move all 25 scripts to `examples/`. |
| baseline `Tutorial_Start_Here.py` | Restore under an accurate lowercase example name; do not restore it as the entry point. |
| `tutorials/v1/support/` | Retain; update relative-path assumptions only where required. |
| `tutorials/v1/data/` | Retain; do not turn shared test fixtures into user inputs. |
| `tutorials/v1/run_tutorials.py` | Adapt to the new owners and run groups. |
| deleted manifest and helper runner | Do not restore unless a concrete uncovered requirement is demonstrated. |

### Direct consumers

The implementation pass must update together:

- tutorial tests that name `introductory/` or `advanced/`;
- workflow tests and GitHub workflows that select runner groups;
- robustness tooling that names tutorial paths;
- asset-profile tests that inspect full-asset examples;
- expert GUI and stability docs that treat the directories as interfaces;
- root and tutorial READMEs;
- installation, quickstart, structure and tutorial docs;
- canonical V1 release acceptance text;
- staged docs that are promoted into the canonical tree.

Historical evidence may retain historical paths when it is clearly dated and
not presented as the live route.

## 13. Test strategy

Tests protect behaviour, scientific evidence and user-visible routes. They do
not protect the accidental taxonomy.

### Focused implementation checks

1. Compile every changed Python file.
2. Run every getting-started file directly from a source checkout.
3. Run the same public snippets outside the repository against the installed
   package.
4. Verify exact or explicitly accepted semantic outcomes.
5. Verify fixed seeds and repeated result equality where deterministic behaviour
   is promised.
6. Run the selected `RELEASE` group.
7. Run focused tests for each moved example family.
8. Verify full-asset and qualification exclusions without launching long work.
9. Check active documentation links and paths.
10. Validate the exact 141-path public surface and 32 root exports.

### Test migration rules

- Replace `advanced` path constants with `examples` where the test protects real
  behaviour.
- Rename tests whose assertions encode the old difficulty label.
- Retain tests for solver budgets, seeds, truth separation, semantic acceptance,
  asset profiles and long-runtime warnings.
- Remove or rewrite assertions that merely require every script to live in one
  named tier.
- Do not restore source hashes or the deleted manifest contract.
- Do not snapshot exact console prose when a stable semantic assertion is
  sufficient.
- Do not require an exact total number of examples; additions must be possible
  without editing an unrelated count assertion.

### Final release proof

After the content and structure are settled, run the complete V1-RR release
proof once, including ordinary and full-asset tests, the complete starting
route, representative examples, workbooks, package construction and isolated
wheel smoke tests. Cross-platform GitHub gates remain a push-time checkpoint.

Repository-wide Ruff debt is not part of this migration. Changed files should
not introduce avoidable new findings, but this work does not become a mass style
cleanup.

## 14. Implementation sequence and commits

### Stage 0: preserve and reconstruct

- create a named safety branch at `27286eae8cb7db1a1a67c361aa3b326f679c7bd8`;
- verify the safety reference;
- reconstruct `prelease/v1-release-readiness` from the accepted baseline only
  after explicit owner approval;
- reapply independent asset-ignore and public-surface protection changes as
  bounded commits;
- do not cherry-pick the mixed first-pass tutorial/docs commit.

### Commit 1: create the getting-started route

Proposed message:

```text
tutorials: add the V1 getting-started route
```

Work:

- add the seven planned files;
- add focused public-API, deterministic and semantic tests;
- include the installed-package copyable smoke example;
- measure and record runtime.

### Commit 2: preserve and organise the example library

Proposed message:

```text
tutorials: organise retained V1 examples by purpose
```

Work:

- move the 25 current scripts together and give them clear lowercase names;
- restore the former Start Here content under a descriptive Vigenere name;
- adapt imports and path-sensitive tests;
- add the single catalogue;
- do not retune solvers as part of the move.

### Commit 3: simplify tutorial execution

Proposed message:

```text
tutorials: simplify V1 example run groups
```

Work:

- implement the five run groups;
- update workflows and asset-profile contracts;
- retain semantic process-exit acceptance and logs;
- remove old taxonomy-only assertions.

### Commit 4: establish the user documentation route

Proposed message:

```text
docs: establish the V1 user route and project voice
```

Work:

- rewrite the README opening and route;
- correct installation and distribution language;
- align quickstart, runes/text and examples index;
- create one small active roadmap for genuine post-release work;
- promote checked staged material;
- remove duplicate active entry points and stale signposts;
- update expert references without copying release-review history into user
  pages.

### Commit 5: retain independent release protections

Keep the asset-ignore and public-surface snapshot work independently reviewable.
If these are reapplied before the tutorial commits, preserve their separate
commit identities rather than folding them into documentation work.

## 15. Acceptance criteria

The migration is complete when:

- one obvious getting-started route exists;
- it assumes technical competence without assuming RDP knowledge;
- it uses only the supported public API and immediately available inputs;
- its results are readable, deterministic and semantically checked;
- every accepted-baseline example remains available under `examples/`;
- examples are selected by purpose, assets and runtime rather than a blanket
  difficulty claim;
- the three long qualifications cannot enter an ordinary run accidentally;
- the runner has no manifest, hashes or prose parser;
- the README explains what RDP is before discussing release machinery;
- source-checkout and installed-wheel instructions are truthful;
- the project voice is recognisable, restrained and evidence-led;
- active docs contain no competing first routes or stale live paths;
- public API and package contracts remain unchanged;
- focused and final validation pass;
- the branch is clean and unpushed pending owner review.

## 16. Owner decisions recorded

The owner resolved the three design choices on 2026-09-05:

1. **Public identity:** use `mortlach`, and no further professional identity.
2. **Filenames:** rename retained files wherever needed for clarity. The
   implementation convention is lowercase `snake_case` without a redundant
   example prefix.
3. **Starting route:** design the broader route before implementation. The
   resulting plan contains seven purposeful stops.

## 17. Follow-up and explicitly deferred work

- repository-wide Ruff cleanup;
- a general cryptography curriculum;
- a Python course;
- solver or public-API redesign;
- packaging tutorials as a new installed namespace;
- a CLI for selecting examples;
- broad retuning of existing scientific recipes;
- new P7/C7 campaigns or cipher-development work during this migration;
- new manifests, registries or provenance machinery for tutorial source.

P7/C7 is deferred from this migration, not forgotten. The documentation commit
must create an active `docs/ROADMAP.md` entry that:

- points to the existing `cipher_development/periodic_columnar_staged/` tooling
  and its qualified warm-start example;
- records that the next scientific question, budget and acceptance rule still
  need to be chosen;
- requires a bounded campaign plan before long work begins;
- keeps that future campaign outside ordinary tutorial, CI and release gates.
