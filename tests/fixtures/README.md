# Test fixtures

`.docx` inputs for the ingest tests, and where each one came from (§18.3).

## Two files per case, on purpose

| Origin | Which files | Why |
|---|---|---|
| **Hand-authored in Word**, committed | `constructs.docx`, `revisions.docx`, `containers.docx` | Word emits the OOXML the customer's file is made of. Some constructs — SmartArt, OLE objects, a real content control — only Word can produce. **Still outstanding** |
| **Built from raw OOXML** by `tests/support/docx.py` | `built_constructs.docx`, `built_revisions.docx`, `built_containers.docx`, `degraded.docx` | Word always writes *valid* OOXML, so a table representable in neither form cannot be authored in it. The three `built_*` files are **stand-ins** carrying the same constructs, so F05 is testable while the Word files are outstanding |

A stand-in and the file it stands in for are checked against **one** requirement list,
defined once in `tests/support/fixtures.py`. The stand-in therefore cannot quietly cover
less than the Word file is required to, and `require("constructs.docx")` switches to the
hand-authored file the moment it lands — no test changes.

> **A stand-in is not a delivery.** `tests/test_fixtures.py` keeps reporting the three
> Word files as outstanding for exactly that reason. What a built file cannot prove is
> that the walker handles what *Word* writes, and that is the whole reason the
> hand-authored ones are the primary path.

## Built files are regenerated, not edited

```bash
python scripts/build_fixtures.py            # rewrite them
python scripts/build_fixtures.py --check    # verify the committed files still match
```

The builders are pure functions of constants, so a build today produces the bytes that
were committed. That is what makes a committed binary reviewable: you regenerate it and
compare. `test_a_committed_built_fixture_still_matches_its_builder` runs the check, because
a hand-edited binary is the one change no diff shows.

## Why the contents are checked, not just the file names

`tests/test_fixtures.py` inspects the raw OOXML of each file and fails if a required
construct is not there. This is not ceremony — **Word does not always save what you
think**:

| What happens | What you get |
|---|---|
| Accepting tracked changes before saving | No `w:del`. The fixture opens fine and tests nothing |
| Emptying a content control | Word drops the `w:sdt` wrapper on save |
| Pasting a table of contents as text | No TOC field codes, so nothing to skip |
| Inserting a picture with "link to file" | No image part in the package at all |

Each of those surfaces later as "the walker loses text", and the walker gets blamed for a
construct that was never in the file. The checks put the failure where the cause is.

The same trap catches a *built* file, and did: the builder originally wrote a tracked
change as a whole `w:p` wrapped in a `w:ins`. That parses, and it satisfies a `//w:ins`
check — but Word writes `w:ins` **inside** the paragraph around runs, with the inserted
paragraph *mark* recorded in `w:pPr/w:rPr`, and readers that follow the schema drop the
wrapped form silently. A walker developed against it would have passed every test here and
lost inserted requirements on the customer's document. Two checks close that now: a
requirement on the run-level shape, and
`test_the_revisions_fixture_really_carries_word_style_tracked_changes`, which puts the
question to an independent reader instead of to our own parser.

Run `python -m pytest tests/test_fixtures.py -v` after adding a file; a failure names the
missing construct and how to add it in Word.

## What each file must contain

### `constructs.docx` — every representable construct, in one document
*Covers T-ING-01, T-ING-02, §6.3, §6.4. Stand-in: `built_constructs.docx`.*

1. Three paragraphs styled **Heading 1**, **Heading 2** and **Heading 3**.
2. A **numbered list** and a **bulleted list** (two lists, so Word gives each its own `numId`).
3. A plain table with **no merged cells** — the pipe-table branch of §10.6.
4. A second table with **merged cells** — the HTML branch.
5. An **embedded image**. Insert > Picture, embedded; *not* "link to file", which stores no image part. The package must end up with a part under `word/media/`.
6. A **text box** with text in it.
7. An **equation** via Insert > Equation — an OMML one, not a picture of one.
8. An **internal cross-reference** (Insert > Cross-reference) to a heading or bookmark in the same document. This is the edge §10.4 reads from OOXML and ordinary converters drop.
9. A **footnote** (References > Insert Footnote).

Optional but useful if Word will produce them: SmartArt, an OLE object, a shape. They
exercise the §10.7 fallback path; the suite does not require them, and the stand-in cannot
produce them at all — which is one of the things only the hand-authored file can settle.

### `revisions.docx` — tracked changes
*Covers T-ING-11, §10.5 W1–W2. Stand-in: `built_revisions.docx`.*

1. One **tracked insertion**: turn on Track Changes, type a sentence.
2. One **tracked deletion**: with Track Changes on, delete a sentence.
3. One **comment** (Review > New Comment).

> **Do not accept or reject the changes before saving.** Accepting removes the `w:del`,
> and the fixture stops testing the one thing it exists for. `w:delText` is a different
> element from `w:t`, so a walker that merely collects `w:t` descendants emits deleted
> text as a live requirement — content fabricated by parsing rather than by hallucination,
> which is the failure DEC-03 exists to prevent.

### `containers.docx` — wrappers to see through, content to skip
*Covers T-ING-12, §10.5 W4–W6, §8.3. Stand-in: `built_containers.docx`.*

1. A **content control** (Developer > Rich Text Content Control) wrapping a paragraph, with text inside it.
2. A **table of contents** (References > Table of Contents), field codes intact.
3. A **header** with text.
4. A **footer** with text.

### `degraded.docx` — built, not authored
*Covers T-ING-10, §6.4 invariant, §10.6.*

Produced by `tests.support.docx.malformed_table_document()`. Two independent breaks, so
neither serialization branch can succeed: the grid declares three columns while the first
row's `gridSpan` values total five, and a `vMerge` continuation appears with no `restart`
row above it. Text follows the table, to prove the degrade does not swallow what comes
after it.

## Adding a hand-authored file

1. Save it into this directory under the name above.
2. `python -m pytest tests/test_fixtures.py -v`
3. Commit. `.gitattributes` marks `*.docx` as binary, so git never rewrites the zip.

Deliver all three together. Half a set is the dangerous state: the suite goes green on
whatever happens to be there and silently stops covering the rest, so a partial delivery
fails rather than skips.
