# Test fixtures

`.docx` inputs for the ingest tests, and where each one came from (§18.3).

Two origins:

| Origin | Which files | Why |
|---|---|---|
| **Hand-authored in Word**, committed | `constructs.docx`, `revisions.docx`, `containers.docx` | Word emits the same OOXML the customer's file does. A committed binary is byte-stable, so a test that passes today passes tomorrow. Some constructs — SmartArt, OLE objects, a real content control — only Word can produce |
| **Built from raw OOXML** by `tests/support/docx.py` | `degraded.docx` | Word always writes *valid* OOXML, so a table representable in neither form cannot be authored in it. Also used for regression cases found later against the real document, where a minimal reproduction in code beats another binary nobody can review |

`degraded.docx` does not have to be committed: the suite builds it into a temporary
directory when it is absent. Committing it is still useful as a record of the exact bytes
the degrade path was verified against.

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

Run `python -m pytest tests/test_fixtures.py -v` after adding a file; a failure names the
missing construct and how to add it in Word.

## What each file must contain

### `constructs.docx` — every representable construct, in one document
*Covers T-ING-01, T-ING-02, §6.3, §6.4.*

1. Three paragraphs styled **Heading 1**, **Heading 2** and **Heading 3**.
2. A **numbered list** and a **bulleted list** (two lists, so Word gives each its own `numId`).
3. A plain table with **no merged cells** — the pipe-table branch of §10.6.
4. A second table with **merged cells** — the HTML branch.
5. An **embedded image**. Insert > Picture, embedded; *not* "link to file", which stores no image part.
6. A **text box** with text in it.
7. An **equation** via Insert > Equation — an OMML one, not a picture of one.
8. An **internal cross-reference** (Insert > Cross-reference) to a heading or bookmark in the same document. This is the edge §10.4 reads from OOXML and ordinary converters drop.
9. A **footnote** (References > Insert Footnote).

Optional but useful if Word will produce them: SmartArt, an OLE object, a shape. They
exercise the §10.7 fallback path; the suite does not require them.

### `revisions.docx` — tracked changes
*Covers T-ING-11, §10.5 W1–W2.*

1. One **tracked insertion**: turn on Track Changes, type a sentence.
2. One **tracked deletion**: with Track Changes on, delete a sentence.
3. One **comment** (Review > New Comment).

> **Do not accept or reject the changes before saving.** Accepting removes the `w:del`,
> and the fixture stops testing the one thing it exists for. `w:delText` is a different
> element from `w:t`, so a walker that merely collects `w:t` descendants emits deleted
> text as a live requirement — content fabricated by parsing rather than by hallucination,
> which is the failure DEC-03 exists to prevent.

### `containers.docx` — wrappers to see through, content to skip
*Covers T-ING-12, §10.5 W4–W6, §8.3.*

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

## Adding a file

1. Save it into this directory under the name above.
2. `python -m pytest tests/test_fixtures.py -v`
3. Commit. `.gitattributes` marks `*.docx` as binary, so git never rewrites the zip.
