# Core Design

Status: staged V1 draft

Rune Decrypter Prime is a deterministic cryptanalysis toolkit for a 29-rune
alphabet.

It is Liber Primus-first, not Liber Primus-only. Liber Primus gives RDP a real
problem domain and many design constraints, but the core system is meant to
describe, run, score, and report decryption experiments clearly.

## What RDP Is Trying To Do

RDP is not trying to be a magic black box.

It is trying to make decryption experiments:

- repeatable
- inspectable
- honest about what evidence was used
- clear enough that a reader can understand why a run succeeded or failed

A good RDP run answers:

```text
What text was solved?
How was the text encoded?
What cipher and key model were used?
What solver searched the key space?
What scorer ranked candidate plaintext?
Why did the solver stop?
What truth or oracle data was used?
Where are the reports and logs?
```

## What RDP Is Not

RDP is not a promise that every possible solver setting is production-ready.

RDP is also not a place to hide:

- known plaintext
- known keys
- oracle stop scores
- scorer fallbacks
- optional backend failures
- report-only diagnostics

If those things are used, they must be visible.

## The Short Version Of A Run

A normal run has this shape:

```text
input text
  -> text encoding and word-location information
  -> cipher and key model
  -> solver proposes candidate keys
  -> cipher decrypts candidates
  -> scorer ranks candidate plaintext
  -> result, report, telemetry, and artifacts
```

The solver searches. The scorer ranks. The report explains.

Those jobs stay separate.

## Friendly At The Edge, Strict In The Core

Users and tutorials start with friendly choices:

```text
cipher family
solver
seed
source label
tutorial
```

Inside the runtime, those choices become explicit typed objects. This
keeps the core easier to test and harder to misread.

The important V1 surfaces are:

| Surface | Purpose |
| --- | --- |
| `RunSpec` | describes what will run |
| `RunResult` | pairs the solution with its solver report |
| `SolverReport` | records what happened during solver search |
| `ScorerReport` | records how scoring was configured and observed |
| RDP display summary | gives a stable human/share view of a run |

## RunSpec

`RunSpec` is the public description of a run.

It can describe:

- raw text
- normalized rune indices and WLI
- labelled source references
- cipher choice
- key shape
- solver settings
- scorer settings
- text encoding direction
- device
- telemetry policy

The goal is not to make every user write a `RunSpec` by hand. The goal is that
RDP can always explain what it was asked to run.

## SolverReport

`SolverReport` explains the search.

It records things like:

- solver name
- requested and effective seed
- normalized parameters
- stop reason
- best score
- best key
- work and timing data
- truth/oracle policy details when available

This matters because a plaintext by itself is not enough. A reviewer needs to
know how the run got there.

## ScorerReport

`ScorerReport` explains scoring.

Scoring is where many accidental changes can hide. A report makes the
objective, score, metrics, timing, telemetry, and diagnostics visible.

Report-only diagnostics are allowed to explain a run. They must not change
ranking, tie-breaks, candidate selection, or solver stopping.

## Text Encoding Direction

RDP supports text encoding directions such as:

```text
ltr
rtl
```

This matters because one rune can represent one, two, or three English letters.
For example, a word can contain rune tokens such as `AE`, `TH`, or `ING`.

The same English word can produce different rune-token boundaries depending on
the direction used to encode it. Reports print `encoding_dir` whenever
plaintext is interpreted.

## Tutorials

Tutorials use the real system.

That is valuable because a tutorial can teach a feature and also act as release
evidence. But a tutorial is not automatically a support promise for every
variant of the same idea.

Tutorials state:

- their cipher
- their solver
- their seed
- their encoding direction
- their acceptance threshold
- whether truth or oracle data was used

## Truth And Oracle Data

Known plaintext or known keys may appear in tutorials and review evidence.

That is allowed when it is reported. It is not allowed to quietly affect
production scoring or ranking.

Good rule:

```text
Truth data may explain or validate a run.
Truth data must not secretly steer production ranking.
```

## Outputs And Artifacts

RDP writes reviewable output under `output/`.

Console text is useful, but it is not the only evidence. A run can be
able to produce structured summaries, logs, telemetry, and artifacts that can be
reviewed later.

Paths in reports are repo-relative or output-relative where possible. They do
not expose private local machine paths.

## Stable And Moving Parts

Stable enough for users and simple tools:

- tutorial runner
- tutorial manifest
- `RunSpec`
- `RunResult`
- `SolverReport`
- `ScorerReport`
- RDP display summary
- generated output under `output/`

Not stable as public interface:

- exact console wording
- private helper modules
- temporary output folder names
- internal test-only helpers
- historical release-contract file layout

## How To Read The Rest Of The Docs

Start with:

```text
install.md
tutorials.md
runes_and_text.md
```

Then read reference pages only when you need exact behavior.
