Below is a clean README you can paste in as `lp_api_readme.md`. Itâ€™s written to match what you already have in code today (canonical page names, glyph spans, and section matching), and it also includes the â€œimage-aligned sections / paragraph lettersâ€ plan as a first-class use case.

It assumes youâ€™re using the existing `LPTranscript` parser and the main transcript helpers (`load_main_transcript`, section matching, etc.).

---

## `README.md` â€” Liber Primus transcript workbench (29-glyph puzzle parsing)

### What this is

This module parses a Liber Primus â€œtranscriptâ€ text file into a **fully indexed** structure so you can extract text/glyphs reliably:

* by **page / line / word**
* by **word-in-line** and **line-in-page**
* by **global glyph index** (including â€œcount backwards from the endâ€)
* by **sections** you define (e.g. â€œred rune sectionsâ€, â€œimage-aligned sectionsâ€, your own markers)
* and then take **intersections** like: `red_rune_section âˆ© page 54.jpg`

Core principle: build **one canonical glyph stream**, then define everything else as spans into that stream. 

---

### Transcript markers you already support

The transcript declares its delimiter symbols in a header (or defaults are used). These are treated as structural truth.

Common ones (as implemented):

* Word delimiter: `-`
* Clause: `.`
* Three-dot: `,`
* Paragraph marker line: `&`
* Segment marker line: `$`
* Chapter marker line: `Â§`
* Line break marker: `/`
* Page break marker line: `%` 

Notes:

* â€œParagraphâ€ and â€œsegmentâ€ markers are treated as **hard breaks** (they end the current line/word cleanly).
* Only **glyph characters** are stored in the glyph stream; delimiter characters are not. 

---

### The data model (how to think about it)

When you parse, you get:

* `doc.glyphs`: the full glyph-only stream
* `doc.words`: each word is a span into `glyphs`
* `doc.lines`: each line is a span into `words` and `glyphs`
* `doc.pages`: each page is a span into `lines`, `words`, and `glyphs`

And fast index maps so you can jump instantly:

`glyph â†’ word â†’ line â†’ page` (and backwards). 

---

## Quick start

### Load the main transcript (recommended)

If you use the provided helper, it loads the repoâ€™s main transcript file and **automatically attaches canonical page names** (`0.jpg` â€¦ `57.jpg`) to the last 58 pages. Earlier pages (if present) can be labelled `front-*`. 

```python
from rune_decrypter_prime.data.liber_primus.lp_main import load_main_transcript

doc = load_main_transcript()
print(doc.summary())
```

---

## Canonical page names (e.g. â€œ54.jpgâ€)

### Why this matters

You want to ask questions like:

* â€œGive me the glyphs from **54.jpg**â€
* â€œGive me the overlap of **54.jpg + 55.jpg** with a **red rune section**â€

That only works robustly if the transcript pages are mapped to canonical image filenames.

### What you have today

`load_main_transcript()` calls a helper that attaches canonical names to the **last 58 pages**:

* canon `0.jpg` maps to the transcript page whose index is `offset + 0`
* canon `57.jpg` maps to `offset + 57` 

You can access pages by canon name:

```python
p54 = doc.page_by_canon("54.jpg")
print(p54.text())
```

(If youâ€™re not using the main loader, you can attach your own catalogue via `doc.attach_page_catalogue(mapping_or_json)`.)

---

## Use case: â€œglyphs from 54.jpg and 55.jpgâ€

### Raw glyph stream (no delimiters)

```python
p54_span = doc.page_by_canon("54.jpg").glyph_span()
p55_span = doc.page_by_canon("55.jpg").glyph_span()

combined_glyphs = p54_span.text() + p55_span.text()
```

### Words instead of glyphs

```python
combined_words = p54_span.words() + p55_span.words()
```

---

## Use case: â€œfind a word by (chapter, page, line, word_in_line)â€

```python
wid = doc.word_id_at(chapter=0, page=0, line=0, word_in_line=2)
print(doc.word(wid).text())
```

This is useful when you want stable â€œcoordinate addressingâ€ while you are inspecting. 

---

## Use case: â€œget N glyphs starting at global index X (forward/backward)â€

```python
# from glyph index 1000, take 80 glyphs
span = doc.glyph_span(1000, 80)
print(span.text())

# count backwards from end: start=-200 means 200 from the end
tail = doc.glyph_span(-200, 80)
print(tail.text())

# a symmetric window around a glyph
window = doc.around_glyph(centre=1000, left=40, right=40)
print(window.text())
```

This is the simplest building block for â€œinspection during decryptionâ€: you can always refer to a glyph index and pull a window. 

---

# Sections

Pages are physical artefact boundaries (`%`).
Sections are analysis boundaries you impose on the same underlying stream.

Examples of section schemes you likely want:

* red rune sections
* image-aligned sections (page ranges)
* paragraph-letter addressing (e.g. â€œ2.câ€)
* custom marker-driven sections (â€œstart/end tagsâ€)

The key design is: a section should reduce to a **span of words/glyphs** so it can be intersected with pages, windows, search hits, etc.

---

## Red rune sections (already represented in `lp_data.py`)

Your `LP_DATA` already builds a split called `"red_runes"` as `LPSection` objects (words + ct_idx + WLI). 

The missing piece is linking those sections back into the transcript stream. Thatâ€™s what the matcher helpers do: they locate a sectionâ€™s rune-index sequence inside the transcriptâ€™s rune stream and return a `SectionMatch` including glyph and page boundaries. 

### Example: â€œoverlap of a red rune section with 54.jpg + 55.jpgâ€

```python
from rune_decrypter_prime.data.liber_primus.lp_data import LP_DATA
from rune_decrypter_prime.data.liber_primus.lp_main import match_lp_section

doc = load_main_transcript()

# Pick a red-rune section id from your LP_DATA split.
rr = LP_DATA.get_section(section_id=16, split="red_runes")  # example id
m = match_lp_section(doc, rr)

rr_span = doc.glyph_span(m.glyph_id_start, (m.glyph_id_end - m.glyph_id_start + 1))

p54_span = doc.page_by_canon("54.jpg").glyph_span()
p55_span = doc.page_by_canon("55.jpg").glyph_span()

chunk54 = rr_span.intersect(p54_span)
chunk55 = rr_span.intersect(p55_span)

combined = chunk54.text() + chunk55.text()
```

This is exactly the pattern you want for â€œsame red rune section across pages 54/55â€: define the section once, then take intersections.  

---

# Planned: image-aligned sections + paragraph letters (your â€œ1.a / 2.câ€ addressing)

You said you want to align sections to the image groupings (and then subdivide into paragraphs). The wiki page you linked is a reasonable external reference point for â€œpage identityâ€ and â€œlineation across page boundariesâ€. ([Uncovering Cicada][1])

## Proposed â€œimage sectionâ€ page ranges (your current draft)

You suggested:

* Section 1: `0.jpgâ€“2.jpg` (1 paragraph)
* Section 2: `3.jpgâ€“7.jpg` (4 paragraphs: aâ€“d)
* Section 3: `8.jpgâ€“14.jpg` (1 paragraph)
* Section 4: `15.jpgâ€“22.jpg` (1 paragraph)
* Section 5: `23.jpgâ€“26.jpg` (1 paragraph)
* Section 6: `27.jpgâ€“32.jpg` (1 paragraph)
* Section 7: `33.jpgâ€“39.jpg` (3 paragraphs: aâ€“c)
* Section 8: `40.jpgâ€“55.jpg` (TBD: you implied â€œtwoâ€ sub-blocks; keep provisional)
* Section 9: `56.jpg` (1 paragraph)
* Section 10: `57.jpg` (1 paragraph)

This is a good first cut because it gives you stable, human-friendly handles even before every boundary is perfect.

## How to implement this cleanly (design, not magic)

### Step 1 â€” make â€œimage sectionsâ€ a split based on page ranges

Because `PageRec` already has `word_start/word_end`, you can convert canonical page ranges into **word boundary indices** and call:

* `doc.add_split_from_boundaries("image_sections", boundaries_word_ids=[...], labels=[...])` 

That immediately enables:

* `doc.section("image_sections", 2)` â†’ span/words/glyphs for â€œ3.jpgâ€“7.jpgâ€

### Step 2 â€” make â€œimage paragraphsâ€ a second split

For paragraph letters like `2.a / 2.b / 2.c / 2.d`, you need paragraph boundaries inside an image section. There are two robust ways to do that:

**Option A (best): treat paragraph markers as first-class containers**

* Extend the parser to record paragraph boundaries when it sees standalone `&` lines.
* Build `ParagraphRec` spans similarly to `LineRec`.
* Then you can create â€œparagraph split within a page rangeâ€ deterministically.

**Option B (pragmatic): define paragraph boundaries in a small sidecar config**

* For each image section, list which transcript line indices (or word indices) start a new paragraph.
* Build a split from those boundaries (works even if the transcript formatting isnâ€™t perfect).

Either way, keep the external API the same: paragraphs are just sections in a split, with labels like `2.a`, `2.b`, etc.

## Suggested naming scheme

* `split="image_sections"`:

  * `section_id=1..10`, `label="1 (0â€“2)"`, `label="2 (3â€“7)"`, â€¦
* `split="image_paragraphs"`:

  * `section_id` sequential, `label="2.a"`, `label="2.b"`, â€¦

### TODO (small API improvement)

Add a convenience lookup:

* `doc.section_by_label(split="image_paragraphs", label="2.c")`

Right now you can store labels, but retrieval is by numeric `section_id`; label lookup is a very natural next step for â€œinspection toolingâ€.

---

# Summary: your key â€œinspectionâ€ calls

Once the two splits exist (even provisionally), your day-to-day work becomes simple and consistent:

* **Page glyphs**: `doc.page_by_canon("54.jpg").glyph_span().text()`
* **Section glyphs**: `doc.section("image_sections", 8).glyph_span().text()` (once defined)
* **Paragraph words**: `doc.section("image_paragraphs", k).words()`
* **Intersection**: `(red_rune_span).intersect(page_span)`
* **Local context**: `doc.around_glyph(i, left=40, right=40)`

Thatâ€™s the backbone of a â€œcomprehensive text parse and extract APIâ€ suitable for cipher analysis and debugging.

---

If you want, I can also rewrite this README so it explicitly matches *your* chosen section numbering (e.g. starting from 0 instead of 1, and using exactly `1.a / 2.c` rather than labels like `"2.c"`), but the structure above is already compatible with that.

[1]: https://uncovering-cicada.fandom.com/wiki/Liber_Primus_Unsolved_Pages?utm_source=chatgpt.com "Liber Primus Unsolved Pages - Uncovering Cicada Wiki"
