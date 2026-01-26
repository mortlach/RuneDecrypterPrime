Absolutely. Here’s a practical, shared workflow guide we can both follow whenever you give me a GitHub “file link index” (JSON/CSV) like `repo_links.json`.

I’m writing it as a **playbook**: what you provide, what I do, what “done” looks like, and how we avoid the usual failure modes (wrong branch, drifting commits, missing files, etc.).

---

# Workflow Playbook: Reviewing a GitHub branch using a file-link index (JSON/CSV)

## What this workflow is for

We use this when:

* The repo is too large to zip.
* We want me to review or cross-check specific parts of the code **without guessing paths**.
* We want discussions to be reproducible: “we were looking at *this exact file*”.

---

## Inputs you provide (minimal and sufficient)

### Always provide

1. **Branch name** (or commit SHA) you want me to use
   Example: `score_upgrade`

2. **File-link index** as JSON or CSV
   You already do this: `repo_links.json` (preferred) or `repo_links.csv`.

3. **Task scope statement** (one sentence)
   Example: “Cross-check scoring contract + runtime raw behaviour.”

### Ideally also provide (but optional)

4. **One “reference run” symptom** (what’s broken / unexpected)
   Example: “Solver no longer improves score on test X.”

5. **A shortlist of files** (5–20 paths) if you already know them
   Example: `src/.../rune_scorer.py`, `runtime.py`, `solver_base.py`.

---

## What the index *means* (so we both interpret it the same way)

Each row/entry in your index is a mapping:

* `path`: repo-relative path to a file
* `blob_url`: GitHub “view” page for that file at the branch/ref
* `raw_url`: direct raw text content URL for that file at the branch/ref
* `size`: size in bytes (useful for spotting binaries)

**Contract**: If a file isn’t in the index, I treat it as **out of scope** unless you explicitly add it or regenerate the index with a wider filter.

---

## The agreed rule: commit drift and reproducibility

### Best practice (recommended)

When you regenerate the index, include a small “header” note (even as a text message) with:

* branch name
* the commit SHA you want to pin to (if you care)

If you don’t pin a commit SHA, the index still works, but:

* The branch may move later and links may point to newer content than we discussed.

### When you *don’t* want pinning

If you’re iterating rapidly and don’t care about reproducing the exact code later, branch-only links are fine.

**We just need to agree which mode we’re in for each review.**

---

## Our step-by-step workflow (the bit we follow every time)

### Step 0 — You send “the bundle”

You send:

* `repo_links.json` (or `.csv`)
* branch/ref name
* task scope statement

### Step 1 — I sanity-check the index (no code opinions yet)

I do three checks before analysing anything:

1. **Index integrity**

* JSON parses cleanly
* It contains fields we need (`path`, `raw_url`)

2. **Link validity spot-check**

* Open 2–5 raw links from the list (core files you care about)
* Confirm they load and are readable

3. **Scope clarity**

* Confirm the index includes the likely target files (e.g. scoring/runtime/solvers)

**Outcome:** I report back: “Index is valid; here’s the set of files I’ll use.”

### Step 2 — We agree the “review set”

To avoid wandering around the repo:

* You either:

  * give me a shortlist of file paths, **or**
  * I propose one based on the scope (and I will only use files present in the index)

**Outcome:** a concrete list like:

* `src/.../scoring/base_scorer.py`
* `src/.../core/problem/runtime.py`
* etc.

### Step 3 — I only use what the index provides

For every file I discuss, I will:

* open it via `raw_url`
* quote small snippets only (no large copy)
* refer to exact function/class names and behaviour
* if needed, I will cite the raw link (so you can click it)

**Hard rule:** I do not “assume” missing files or invent APIs. If something is referenced but not present in index, I say: “Not in index; add it.”

### Step 4 — I produce an evidence-based deliverable

Depending on the task, I output one of:

* **Cross-check report** (what code does vs intended spec)
* **Implementation plan** (touchpoints, ordering, tests)
* **Spec rewrite** (MUST/SHOULD requirements) aligned to current code reality

**And I include:**

* the exact list of files reviewed
* any “unknowns” caused by missing files in the index
* the smallest next action to reduce uncertainty

### Step 5 — Iteration loop

You either:

* regenerate the index (if the branch changed), or
* add missing files / broaden the filter, or
* we move to patch planning

---

## Common failure modes and how we prevent them

### Failure mode A: “You reviewed the wrong code version”

Prevention:

* pin commit SHA (ideal), or
* you tell me “index generated after commit X”, or
* you regenerate index when you push changes

### Failure mode B: “The file exists in repo but isn’t in the index”

Prevention:

* treat the index as authoritative scope
* regenerate with a broader filter if needed

### Failure mode C: “Raw links load HTML or 404”

Prevention:

* I spot-check and tell you immediately
* usually caused by private repo, wrong branch name, or unusual filename encoding

### Failure mode D: “We get lost in architecture instead of fixing the symptom”

Prevention:

* we always keep one “baseline symptom test” in view (your reference run)
* we treat architecture as secondary until signal is confirmed

---

## Your quick checklist (what you do before sending an index)

* [ ] Confirm branch/ref is correct
* [ ] Generate index on that ref
* [ ] Ensure index includes the folders relevant to the task (e.g. `src/`, `tests/`)
* [ ] Optionally note commit SHA if you want reproducibility
* [ ] Send index + one sentence “what you want checked”

---

## My quick checklist (what I do when you send it)

* [ ] Parse index, confirm fields
* [ ] Spot-check raw links load
* [ ] Confirm required files are present
* [ ] Agree on a review set
* [ ] Only then start analysis

---

## “Template message” you can paste to start a review

Copy/paste and fill blanks:

> **Ref:** `score_upgrade` (commit: `________` if pinned)
> **Index:** `repo_links.json` attached
> **Scope:** Please cross-check __________ (e.g. scoring raw/pct contracts)
> **Must-review files:**
>
> * `src/...`
> * `src/...`
>   **Symptom / baseline:** __________

---

If you like, I can also add a tiny “house style” for review outputs (for example: “Findings / Evidence / Implication / Recommended next change / Tests”), but the key thing is the workflow above: **index is authoritative scope + raw links are the only source**.
