# Documentation style

This is the agreed voice for RDP documentation, guides, tutorial comments and
folder READMEs. Use it for new material and later editing passes.

## Voice

Write in `mortlach`'s voice: direct, practical and natural, with clear grammar
and correct spelling. Assume the reader is technically capable and new to RDP.
Explain what we are doing, why we need it and what we can change. Use “we” when
walking through a shared example, and “you” when describing the reader's choices.

A little dry humour is welcome when it comes naturally. Leave it out when
unsure. Do not add jokes to meet a quota, imitate typos or invent biographical
details. Public attribution is exactly `mortlach`.

Prefer ordinary verbs and concrete explanations. “Tell RDP which keys to try”
is usually clearer than “define the admissible candidate-space contract”. Keep
technical names where they help the reader find the corresponding code.
Explain a limitation where it affects a choice; avoid turning every paragraph
into a warning about what the example does not prove.

For example, replace:

> RDP's cipher boundary uses rune indices. All three reviewed forms are kept
> together here so no transliteration step is hidden inside the example.

with:

> RDP works with 29 runes, numbered from 0 to 28. Here is our message in English,
> in runes, and as those numbers. The encrypt/decrypt functions take the numbers;
> the other two lines are here so we can read what we're working with.

The comments in [the known-key example](../../tutorials/v1/getting_started/01_known_key.py)
are the starting reference for this voice. Keep the useful detail: a warmer
sentence should still explain the concept, its purpose and relevant options.
This is an orientation to RDP, not a Python lesson or a cryptography course.

## Folder README policy

Readers are expected to inspect the repository as well as the rendered docs.
Each main project folder and meaningful reader-facing subfolder should therefore
contain a short `README.md` that states:

- the folder's purpose in RDP;
- what generally belongs there;
- important boundaries, especially public API versus repository support;
- how its files are normally entered or run;
- where a reader should go next.

These are local orientation notes, not copies of the main documentation. Do not
add identical boilerplate to every implementation leaf package. Repo-wide
coverage should be established from a reviewed folder inventory.

## Tutorial runner policy

Public V1 tutorial runners must not require or advertise RDP environment
variables. Individual examples should run as repository modules so their source
does not contain path injection.

Allowed:

- clear constants in the runner file
- one public tutorial runner with named run-set and console-output constants
- one human catalogue with asset, runtime and truth-use notes

Avoid:

- `RDP_TUTORIAL_*` environment variables
- `PYTHONPATH` instructions
- shell-specific setup
- CLI-heavy tutorial control
- separate config files unless the config is genuinely reused by more than one
  runner

The normal V1 tutorial command is:

```text
python tutorials/v1/run_tutorials.py
```

An individual numbered stop or worked example uses module form:

```text
python -m tutorials.v1.getting_started.02_first_search
python -m tutorials.v1.examples.columnar_transposition
```

For full human-facing printout review, edit the same runner and set:

```python
CONSOLE_OUTPUT = ConsoleOutput.FULL
```

## Explain RDP at the point of use

Before a concept first appears, explain what it represents, why the run needs it
and a few relevant alternatives. Comments explain RDP and the cryptanalytic
process; they should not narrate Python. Explain a concrete key separately from
its candidate space, and mention custom key types as part of cipher development.

For useful options, say what changes, why this example chose its value and what
changing it costs or requires. Distinguish an example setting from a library
default. Link to fuller guidance instead of listing every parameter.

Folder READMEs describe purpose, key files, relationships and entry points.
Include useful options and extension notes where the folder owns those choices.
Write from current source. Older README attachments are style references only.

## Formatting

Use one H1 and short descriptive subheadings. Leave blank lines around headings,
lists, tables and code fences. Use backticks for identifiers, relative links for
files and fenced Python blocks for examples. Prefer short comparisons to wide
tables full of paragraphs. Keep request construction readable and comments near
the settings they explain. Avoid repeated banners, excessive emphasis and
machine-generated directory dumps. Public attribution is exactly `mortlach`.
