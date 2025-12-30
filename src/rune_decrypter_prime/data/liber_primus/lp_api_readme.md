README.md — LP Transcript Parser (29-glyph puzzle workbench)
What this is

This module parses a “Liber Primus transcript” style text file into a fully indexed structure so you can reliably extract:

by page / line / word

by word-in-line and line-in-page

by global glyph index (including “count backwards from the end”)

by custom sections (e.g. “red rune sections”, or your own markers)

The transcript format itself declares the delimiters (word -, line /, page %, chapter §, etc.), which we treat as authoritative structure. 

Key idea (how the data is stored)

We build one canonical stream:

glyphs: every non-delimiter character (your 29-glyph alphabet plus any other symbols present)

words: each word is a span into glyphs

lines: each line is a span into words and glyphs

pages: each page is a span into lines, words, and glyphs

Then we build fast index maps so you can jump instantly between:
glyph -> word -> line -> page and back again.

Files

Suggested layout:

your_project/
  lp_transcript.py          # parser + view objects (LPTranscript, PageView, LineView, …)
  pasted.txt                # your master transcript
  page_catalogue.json       # (optional) mapping transcript pages -> canonical image names like 54.jpg
  README.md

Quick start
from pathlib import Path
from lp_transcript import LPTranscript

doc = LPTranscript.from_file(Path("pasted.txt"))
print(doc.summary())

# Page text
print(doc.page(0).text())

# A window around a specific glyph index
print(doc.around_glyph(centre=1000, left=40, right=40).text())

# Find a word by (chapter, page, line, word_in_line)
wid = doc.word_id_at(chapter=0, page=0, line=0, word_in_line=2)
print(doc.word(wid).text())

Extract characters from consecutive pages (the general method)

If you want “all glyphs from page A then page B”:

span_a = doc.page(page_id_a).glyph_span()
span_b = doc.page(page_id_b).glyph_span()

combined = span_a.text() + span_b.text()


That gives you the raw glyph stream (no delimiters). If you want words instead:

words = doc.page(page_id_a).glyph_span().words() + doc.page(page_id_b).glyph_span().words()

Your example: “chars from 54.jpg and 55.jpg”

Right now, there’s a missing link:

Your canonical page names (54.jpg, 55.jpg) exist as real image filenames in the Cicada artefact set.

But the transcript does not (yet) include a per-page canonical name marker.

So the parser cannot currently answer: “give me the text for 54.jpg” unless you provide a mapping.

That said, you already have an important clue in your existing data code: your red-rune mini-records include "page": "54.jpg" (and similar), so you clearly intend to track these canonical filenames in metadata. 

The clean solution: a page catalogue (sidecar JSON)

Create a page_catalogue.json that maps transcript page indices to canonical image names.

Example:

{
  "0":  {"canon": "0.jpg"},
  "1":  {"canon": "1.jpg"},
  "2":  {"canon": "2.jpg"},
  "...": {"canon": "..."},
  "54": {"canon": "54.jpg"},
  "55": {"canon": "55.jpg"}
}


Then you add a thin helper in your code (or just load it in your analysis script) to look up:

page_id = canon_to_page_id["54.jpg"]

and then:

page54 = doc.page(page_id).glyph_span().text()


Once you have the mapping for 54 and 55:

p54 = doc.page(canon_to_page_id["54.jpg"]).glyph_span().text()
p55 = doc.page(canon_to_page_id["55.jpg"]).glyph_span().text()
combined = p54 + p55

“Same red rune section” across 54/55

Conceptually, you want:

identify the red rune section range in the transcript (as word boundaries), and

intersect that range with the pages for 54.jpg and 55.jpg.

Your current lp_data.py already treats “red rune sections” as a split that produces per-section words, ct_idx, and wli. 

That’s exactly the right idea: “section” is a view over the canonical word stream.

So, once your parser has (a) canonical page names, and (b) a split for red-runes, you can do:

sec = doc.section("red_runes", some_id) → get section glyph span / words

locate which pages overlap that section (by comparing glyph ranges)

take just the overlap with pages 54.jpg and 55.jpg

TODO / refactor note: add canonical page names into the transcript model

If you want this to be first-class (recommended), add the concept of page metadata to the parser:

Option A: sidecar JSON (best “don’t touch the transcript” option)

Keep the transcript purely textual and stable.

Add page_catalogue.json as the official source of canonical names.

Parser loads it optionally and attaches PageRec.canon_name.

This keeps your transcript format unchanged.

Option B: inline page header markers (best “single file is truth” option)

Introduce a new syntax that does not collide with existing delimiters, for example:

a metadata line immediately before each % page break:

@page canon=54.jpg
%


or

@page 54.jpg
%


Then the parser:

recognises lines starting with @page

stores that value as canon_name for the next PageRec

This makes “give me 54.jpg” a native call:

doc.page_by_canon("54.jpg").glyph_span().text()

Why this is worth doing

Without canonical names in either:

the transcript itself, or

an attached catalogue,

you can only refer to pages by “page index in this particular transcript file”, which is brittle whenever the transcript is edited/reflowed.

Practical next step (minimal effort, maximum payoff)

Add page_catalogue.json for the pages you care about first (e.g. 40–60, including 54/55).

Add a tiny helper in your analysis notebook/script to build canon_to_page_id.

Later, decide whether you want Option A (sidecar forever) or Option B (inline @page).

If you want, I can also write the small helper functions the README assumes (load_page_catalogue(), page_by_canon(), and a “page overlap with section” utility) in the same style as the parser, but I’ve kept this response focused on the README + the canonical-name refactor plan you asked for.

we need to extend it to sections (which are nto yet fully defeind - but we can 
and by red rune secitons 
so write that as another uise case eevne if it cant be done


Below is an add-on section you can paste straight into the README (or merge into the “Use cases” section). It treats sections (including “red rune sections”) as first-class views over the same canonical word/glyph stream — even if you haven’t fully defined how the section boundaries are discovered yet.

Sections and “red rune sections” (planned, but designed-in)
Why sections are a separate concept from pages

Pages are a physical artefact boundary (a % delimiter in the transcript).

Sections are an analysis boundary you impose on the text. A section can:

start mid-page and end mid-page,

span multiple pages,

overlap with other section schemes (e.g. “red rune sections” vs “chapter-like” blocks),

be defined in several different ways depending on your current hypothesis.

So in the API we treat sections as named splits (a “split” is one way of slicing the word stream), and each split contains section records that are just ranges of words.

Mental model

The transcript parses into glyphs -> words -> lines -> pages

A split defines section_id -> [word_start, word_end)

Everything you want is then a span:

section text

section glyph window

section words

“word index within section”

“line index within section” (derived by grouping words by their global line IDs)

This is why “sections” are easy to add even before you know exactly how to detect them: the infrastructure is just ranges.

Use case: define a section split (even if boundaries are provisional)
Option 1: explicit boundaries (most robust, most boring, best to start)

If you can write down section boundaries as word indices (or you can generate them offline once), you can add them immediately:

doc.add_split_from_boundaries(
    "red_runes",
    boundaries_word_ids=[0, 1200, 2400, len(doc.words)],
    labels=["RR-0", "RR-1", "RR-2"],
)
sec = doc.section("red_runes", 1)
print(sec.text())


This already gives you:

sec.words() (WordView objects)

sec.text() (lines reconstructed using global line breaks)

sec.glyph_span().text() (pure glyph stream)

Even if the boundaries are “wrong”, this still works as a stable interface for your tooling.

Option 2: split by markers (works once you introduce reliable markers)

If you add sentinel tokens to the transcript (or maintain a cleaned “analysis transcript” copy), you can split by known patterns:

doc.add_split_by_word_patterns(
    "red_runes",
    patterns=[["<<RR12>>"], ["<<RR13>>"], ["<<RR14>>"]],
    start_section_id=12,
)
rr13 = doc.section("red_runes", 13)


This is a very practical workflow: you can keep the “raw transcript” pristine, and maintain a parallel “analysis transcript” that includes your markers.

Use case: “give me the part of section RR that is on pages 54.jpg and 55.jpg”
What we can do today

We can already do:

page spans: doc.page(i).glyph_span()

section spans: doc.section("red_runes", k).glyph_span()

What’s missing (two small bits of plumbing)

Canonical page names (54.jpg, 55.jpg) are not yet part of the transcript’s page records.
You’ll need either:

a sidecar page_catalogue.json, or

inline @page canon=54.jpg metadata lines.

Overlap helper: a function that intersects two glyph spans (or word spans).

Proposed API (planned)
# once canonical names exist
p54 = doc.page_by_canon("54.jpg").glyph_span()
p55 = doc.page_by_canon("55.jpg").glyph_span()

rr = doc.section("red_runes", 13).glyph_span()

# overlap/intersection helper (planned)
chunk54 = rr.intersect(p54)   # returns GlyphSpan
chunk55 = rr.intersect(p55)

combined = chunk54.text() + chunk55.text()

TODO / refactor note (what we need to implement)

Add two small utilities:

A) Canonical page name mapping

doc.attach_page_catalogue(path_or_dict)
Populates PageRec.canon_name and builds an inverse map.

doc.page_by_canon("54.jpg") -> PageView

This keeps “54.jpg” stable even if you later reflow the transcript and page indices shift.

B) Span intersection

GlyphSpan.intersect(other: GlyphSpan) -> GlyphSpan
Returns the overlap [max(starts), min(ends)) (or an empty span).

This enables:

section ∩ page

section ∩ (glyph window around index)

page ∩ (search match range)

Why this is the right level of abstraction

It avoids hard-coding “red rune section logic” into the parser.

Instead, you make red rune sections just one split among many:

split="red_runes"

split="solved_vs_unsolved"

split="my_candidate_breaks"

split="chapter_blocks"

All of them share the same fast random access, and all of them can be intersected with pages/canonical images.

Use case: “word-in-section” and “line-in-section”

Even before you have red rune boundaries nailed down, you can still build tools that ask:

What is the k-th word in this section?

What is line n within this section, where “line” respects the transcript’s / markers?

Planned conveniences:

sec = doc.section("red_runes", 13)

# word in section
w = sec.words()[25]
print(w.text())

# line in section (derived by grouping words by global line id)
for i, line_text in enumerate(sec.lines_text()):
    print(i, line_text)


(Under the hood, lines_text() just groups section words by the global line ID each word belongs to.)