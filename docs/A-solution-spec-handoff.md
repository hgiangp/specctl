# Spec Improvement — Solution Spec & Implementation Handoff

**Version:** 1.0 · **Date:** 2026-09-20 · **Status:** Ready for implementation
**Audience:** coding agent (primary), solution owner (review)
**Companion document:** `B-limitations-roadmap.md` — what this design deliberately does *not* do, and when to extend it.

---

## 1. How to use this document

| Section     | Read when                                                                                      |
| ----------- | ---------------------------------------------------------------------------------------------- |
| 2–4        | Before writing any code. Problem, decisions, architecture.                                     |
| **5** | **Normative.** File and data conventions. Every component depends on it. Do not deviate. |
| 6–9        | Component specs. Each has CLI signature, behaviour, and acceptance tests.                      |
| 10–11      | Agent layer and day-to-day runbook.                                                            |
| 12–14      | Plan, acceptance thresholds, risks.                                                            |
| 15          | Worked examples. Copy these shapes literally.                                                  |

**Rules for the implementer**

1. Section 5 is a contract. If a rule there is impossible on real data, stop and report, do not invent a variant.
2. Everything is deterministic unless explicitly marked LLM-assisted. No LLM in the ingest path.
3. Every component is a CLI command first. Anything else (MCP, UI) is out of scope for this phase.
4. Prefer boring, standard-library-ish Python. No service, no database, no web server.
5. If a rule is ambiguous, pick the option that preserves source fidelity and log a warning.

---

## 2. Problem statement

### 2.1 Context

A system requirements specification (SYS spec, automotive / ASPICE SYS.2) from a Japanese customer, delivered as a single **Word .docx** file (English translation, agreed for this pilot). Well-structured headings; body contains prose, tables, images, Word shapes, and internal cross-references. The team wants to **improve the spec** (structure, presentation, parameter representation) with AI assistance, and to be able to **understand and query** it.

### 2.2 Two distinct problems

|            | **Problem A — Spec → Knowledge**                                       | **Problem B — Knowledge → Improvement**                         |
| ---------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| Question   | How do we turn a .docx into something an agent can read and address precisely? | How do we edit the spec with context, control, and evidence?            |
| Input      | `spec.docx`                                                                  | The vault produced by A                                                 |
| Output     | Markdown vault with stable IDs, links, generated indexes, coverage report      | Improved sections, change log, Excel deliverable                        |
| Components | Extractor, file conventions, index generator, reading skills                   | Improvement skills, edit workflow, validator, backlinks, Excel exporter |
| Risk       | Silent data loss during parsing                                                | AI silently changing meaning or values                                  |
| Timeline   | Week 1                                                                         | Weeks 2–3                                                              |

**A is a precondition for B.** Without stable IDs there is no addressable unit to edit, no change report, and no row key for Excel.

### 2.3 Goals

- **G1 (A)** Convert the .docx into a Markdown vault where every block has a stable ID, with a coverage report proving what was and was not captured.
- **G2 (A)** Preserve Word internal hyperlinks/bookmarks and heading auto-numbering.
- **G3 (A)** Let an agent answer questions about the spec **with ID citations**.
- **G4 (B)** Improve a section via an agent + skill, reviewed as a diff by a human, committed with rationale.
- **G5 (B)** Detect, in a deterministic way, when an edit breaks IDs, locked blocks, tables, or changes numbers/units.
- **G6 (B)** Export to Excel with change status against a baseline.

### 2.4 Non-goals (this phase)

NG1 No MCP server. NG2 No database or search index. NG3 No web UI. NG4 No multi-file corpus. NG5 No Japanese support. NG6 No write-back to .docx. NG7 No local LLM. NG8 No RAG chatbot. NG9 No requirements-management features (attributes workflow, approvals, traceability).

### 2.5 Constraints

- Local only. One developer, ~3 weeks, AI-assisted coding.
- Runtime: Python 3.11+, git, optional LibreOffice and Pandoc.
- Agent runtime: **Claude Code in VS Code**. Human reviewer: the solution owner.
- Single user, multiple sessions, no auth, no concurrency control beyond git.

### 2.6 Definition of done

All acceptance thresholds in §13 met, the runbook in §11 executable end to end on the real spec file, and the pilot report produced.

---

## 3. Solution decisions

| #  | Decision                                                                                                     | Rationale                                                                                                                      | Rejected alternative                                                                                  |
| -- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| D1 | **Markdown vault is the source of truth**: one file per section, blocks carry stable IDs               | Human-readable, git-diffable, directly consumable by the agent, viewable in Obsidian, zero infrastructure                      | Canonical JSON store (more faithful, slower to build — see B §4.1); PostgreSQL (no multi-user need) |
| D2 | **ID-first**. Every block gets an immutable ID at ingest                                               | IDs are what make edit tracking, backlinks, change reports and Excel rows possible. This is the core value                     | Line numbers or heading numbers (both shift on edit)                                                  |
| D3 | **Deterministic ingest**, no LLM in the conversion path                                                | The spec is contractual; a hallucinated sentence is unacceptable. LLM may later*describe* figures, never *produce* content | LLM-based document extraction                                                                         |
| D4 | **Word metadata is extracted from OOXML directly** (bookmarks, hyperlinks, REF fields, numbering)      | These are the only fully reliable cross-reference edges, and generic converters drop them                                      | Plain Pandoc/Docling conversion only                                                                  |
| D5 | **Claude Code is the agent and the editor**; git is history and review                                 | Sessions, skills, file editing and diff review already exist; building them would consume the entire budget                    | Custom harness / web app                                                                              |
| D6 | **No MCP server, no search index yet**                                                                 | Single file; outline + grep + per-section reads are sufficient. Add when the pain is measured (see B §4.2, §4.3)             | spec-mcp + SQLite FTS/vector now                                                                      |
| D7 | **Obsidian is an optional viewer** over the same folder                                                | Costs nothing, adds graph/backlink browsing, no lock-in — a vault*is* a folder of Markdown                                  | Obsidian as the storage/backend                                                                       |
| D8 | **Writes are gated**: agent edits working files, a validator runs, human reviews the diff, then commit | Prevents silent content drift (values, units, IDs)                                                                             | Agent committing directly                                                                             |
| D9 | **Excel is an export view only**, never an input                                                       | Excel cannot represent the structure; round-tripping would double-maintain                                                     | Excel as editing surface                                                                              |

---

## 4. Architecture

```
PROBLEM A: Spec → Knowledge                      PROBLEM B: Knowledge → Improvement
──────────────────────────────                   ─────────────────────────────────────
 spec.docx                                        vault (sections with IDs)
    │                                                 │
    │ specctl ingest            [BUILD: §6]           │ /improve <section> <skill>
    ▼                                                 ▼
 vault/                                           Claude Code + skills        [BUILD: §10]
  ├─ sections/SYS-000120.md    [CONTRACT: §5]         │  edits section file on a git branch
  ├─ assets/                                          ▼
  ├─ index.md, log.md,         [BUILD: §9]        specctl validate            [BUILD: §7]
  │  backlinks.md, coverage.md                        │  IDs, locked blocks, tables, numbers
  └─ .git (baseline tag)                              ▼
    │                                              human review of diff (VS Code)
    ▼                                                 │
 Claude Code reads/greps       [USE AS IS]            ▼
 Obsidian browses              [USE AS IS]        git commit (rationale, skill)
                                                      │
                                                      ▼
                                                  specctl export xlsx         [BUILD: §8]
```

**Build:** one Python package `specctl` (extractor, validator, index generator, exporter) plus agent conventions and skills.
**Use as is:** Claude Code, VS Code diff, git, Obsidian, Pandoc/LibreOffice (helpers inside the extractor).

---

## 5. Data model and file conventions (NORMATIVE)

### 5.1 Repository layout

```
spec-workspace/                     # a git repository
├── CLAUDE.md                       # agent conventions (§10.1)
├── .claude/skills/<skill>/SKILL.md # agent skills (§10.2)
├── source/
│   └── SYS.docx                    # the original, never modified
├── vault/
│   ├── index.md                    # GENERATED — table of contents (§9.1)
│   ├── log.md                      # GENERATED — change log (§9.2)
│   ├── backlinks.md                # GENERATED — inbound references (§9.3)
│   ├── coverage.md                 # GENERATED — human-readable coverage (§6.4)
│   ├── sections/
│   │   └── SYS-000120.md           # one file per section (§5.3)
│   └── assets/
│       ├── SYS-000151.png          # figures, rendered shapes
│       └── SYS-000151.xml          # raw OOXML of fallback elements
├── meta/
│   ├── ids.json                    # ID registry for re-ingest stability (§6.5)
│   └── coverage.json               # machine-readable coverage (§6.4)
├── exports/                        # GENERATED xlsx (git-ignored)
└── tests/
```

`vault/`, `meta/`, `source/`, `CLAUDE.md`, `.claude/` are committed. `exports/` is ignored.

### 5.2 Identifiers

- **Format:** `<DOCKEY>-<NNNNNN>`, e.g. `SYS-000120`. `DOCKEY` is `[A-Z][A-Z0-9]{1,7}`, supplied at ingest. Counter is zero-padded to 6 digits.
- **Allocation:** sequential in document order at first ingest, step 10 is **not** used — plain increment.
- **Immutability:** an ID is never reused, never renumbered, and never changes when the text, heading number, or position changes.
- **Section IDs** are the IDs of their heading block. A section file is named `<section-id>.md`.
- **New blocks** created during editing have no anchor; `specctl validate --assign-ids` allocates them from the registry.
- **Deleted blocks**: their IDs are retired in `meta/ids.json` with `status: deleted`.

### 5.3 Section file format

A section file contains **one heading block and all content until the next heading of the same or higher level**. Sub-headings deeper than the split level stay inside the same file (see `split_level`, default 2).

```markdown
---
id: SYS-000120
doc: SYS
number: "3.2"
title: Braking control
level: 2
parent: SYS-000100
order: 14
path: ["3", "3.2"]
breadcrumb: "SYS > 3 Braking system > 3.2 Braking control"
bookmarks: ["_Ref123456", "_Toc99887"]
refs_out: ["SYS-000245", "SYS-000301"]
blocks: 9
source: { docx: "source/SYS.docx", paragraphs: [412, 447] }
ingest_version: 1
generated: false
---

## 3.2 Braking control <!-- id:SYS-000120 type:heading -->

<!-- id:SYS-000121 type:paragraph -->
The system shall apply braking torque within 50 ms after the pedal signal
exceeds the threshold defined in [[SYS-000245|5.1 Signal thresholds]].
^sys-000121

<!-- id:SYS-000122 type:table format:pipe -->
| Signal | Unit | Range |
|---|---|---|
| BrakePedalPos | % | 0–100 |

<!-- id:SYS-000123 type:figure locked:true asset:SYS-000123.png -->
![Figure 3-2: Braking state machine](../assets/SYS-000123.png)
*Figure 3-2: Braking state machine*
```

**Rules**

| R   | Rule                                                                                                                                                                                   |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1  | Front matter is YAML and contains exactly the keys above. Unknown keys are an error.                                                                                                   |
| F2  | **Every block is preceded by an HTML comment anchor** `<!-- id:<ID> type:<TYPE> [key:value ...] -->`. The anchor is the single canonical ID carrier.                           |
| F3  | Block types:`heading`, `paragraph`, `list`, `table`, `figure`, `formula`, `code`, `raw`.                                                                               |
| F4  | A trailing Obsidian block reference`^sys-000121` (lowercased ID) MAY be emitted for `paragraph` and `list` blocks, for Obsidian convenience. It is derived, never authoritative. |
| F5  | The heading line carries the rendered number from Word (`## 3.2 Braking control`). Body text never contains section numbering.                                                       |
| F6  | Internal cross-references are wikilinks:`[[<TARGET-ID>\|<display text>]]`. Block-level targets use `[[<SECTION-ID>#^<lowercased block id>]]`.                                       |
| F7  | External links keep normal Markdown link syntax with the original URL.                                                                                                                 |
| F8  | Blocks with`locked:true` (figures, shapes, raw fallbacks) must not be modified by any agent.                                                                                         |
| F9  | Files are UTF-8, LF line endings, one blank line between blocks, no trailing whitespace.                                                                                               |
| F10 | Generated files (`index.md`, `log.md`, `backlinks.md`, `coverage.md`) have `generated: true` in front matter and must never be hand-edited.                                  |

### 5.4 Block representation rules

| Source construct                  | Markdown representation                                                                                                            | Notes                                                                        |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Heading                           | `#`×level + rendered number + text                                                                                              | Level from Word outline level                                                |
| Paragraph                         | Plain Markdown; bold/italic/code preserved                                                                                         | Character styles beyond these are dropped and logged                         |
| List (bulleted/numbered)          | One`list` block for the whole list, Markdown list syntax, nesting by indent                                                      | Word auto-numbers are rendered as literal numbers                            |
| **Simple table**            | GFM pipe table,`format:pipe`                                                                                                     | "Simple" = no merged cells, no block content in cells, no nested tables      |
| **Complex table**           | HTML`<table>` with `rowspan`/`colspan`, `format:html`                                                                      | Cells may contain`<br>`; keep cell text verbatim                           |
| Figure / image                    | `![caption](../assets/<ID>.<ext>)` + italic caption line, `locked:true`                                                        | Image extracted from the package                                             |
| Shape / text box / SmartArt / OLE | Rendered to PNG via LibreOffice, same as figure, plus`assets/<ID>.xml` holding the raw OOXML, `locked:true`, `fallback:true` | Text inside a text box is ALSO emitted as a`raw` block so it is searchable |
| Equation (OMML)                   | `$...$` or `$$...$$` if conversion succeeds, else image fallback                                                               | Conversion failures are logged, never silently dropped                       |
| Footnote                          | Markdown footnote syntax at the end of the section                                                                                 |                                                                              |
| Field REF / internal hyperlink    | Wikilink per F6                                                                                                                    | Resolution rules in §6.3                                                    |
| Tracked change / comment          | Ignored, but counted in coverage as`skipped`                                                                                     |                                                                              |

### 5.5 Generated files

See §9. All generated files carry `generated: true`.

---

## 6. Component 1 — Extractor (Problem A)

### 6.1 CLI

```
specctl ingest SOURCE.docx --doc-key SYS --out vault/ [options]

  --split-level N        heading level that starts a new file (default 2)
  --assets-dir PATH      default vault/assets
  --render-shapes/--no-render-shapes   LibreOffice rendering (default on)
  --reingest             reuse meta/ids.json to keep IDs stable (§6.5)
  --fail-under PCT       exit non-zero if link or table coverage < PCT (default 0)
  --dry-run              write only the coverage report
```

Exit codes: `0` success, `2` coverage below `--fail-under`, `3` unrecoverable parse error.

### 6.2 Pipeline

1. **Unzip and load** the package: `document.xml`, `styles.xml`, `numbering.xml`, `footnotes.xml`, `_rels/*`, `media/*`.
2. **Build the block stream** in document order. Each raw item records its source paragraph index.
3. **Resolve numbering.** Compute heading and list numbers from `numbering.xml` + style outline levels, maintaining counters. If numbering cannot be computed for an item, record `numbering_unresolved` in coverage and emit the text without a number.
4. **Collect anchors.** Bookmarks (`w:bookmarkStart/@w:name`), hyperlink targets (`w:hyperlink/@w:anchor`, `r:id`), REF field instructions (`w:instrText` containing `REF`). Map bookmark name → enclosing block.
5. **Extract media.** Images from the package; shapes/text boxes/SmartArt/OLE identified via `w:drawing`, `w:pict`, `mc:AlternateContent`, `w:object`.
6. **Render fallbacks.** If `--render-shapes`, convert the docx to PDF via LibreOffice once, then crop/export the page region for each unrenderable element; if cropping is unreliable, export the whole page image and reference it. Always write raw OOXML beside it.
7. **Segment into sections** by `--split-level`.
8. **Allocate IDs** (§6.5).
9. **Resolve cross-references**: bookmark name → block → ID. Unresolved targets become plain text and are logged.
10. **Serialize** section files per §5.3, write assets.
11. **Generate** `index.md`, `log.md` (initial entry), `backlinks.md`, `coverage.md` / `coverage.json`.
12. **Git**: if the repo is clean, commit and tag `SYS-baseline-v0` (skip if `--no-git`).

### 6.3 Cross-reference resolution

| Case                                                       | Handling                                                                                                        |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Hyperlink with`w:anchor` matching a known bookmark       | `[[TARGET-ID\|<display text>]]`, edge kind `word_link`                                                       |
| REF field pointing to a bookmark                           | Same, display text = rendered field result                                                                      |
| Hyperlink to an external URL                               | Standard Markdown link                                                                                          |
| Bookmark not found / target outside document               | Keep display text, log`unresolved_ref` with the paragraph index                                               |
| Textual reference without a field (e.g. "see section 3.2") | **Not resolved in this phase.** Recorded in coverage as `textual_ref_candidate` with the matched string |

### 6.4 Coverage report

`meta/coverage.json`:

```json
{
  "source": "source/SYS.docx",
  "doc_key": "SYS",
  "ingest_version": 1,
  "generated_at": "2026-09-21T10:00:00+07:00",
  "counts": {
    "sections": 87, "blocks": 1204,
    "paragraphs": 902, "lists": 61,
    "tables": { "total": 48, "pipe": 41, "html": 6, "failed": 1 },
    "figures": 23, "shapes": { "total": 9, "rendered": 8, "raw_only": 1 },
    "formulas": { "total": 12, "latex": 10, "image": 2 }
  },
  "links": { "word_links_found": 134, "resolved": 130, "unresolved": 4 },
  "numbering": { "headings": 87, "resolved": 87, "unresolved": 0 },
  "text_fidelity": { "source_chars": 412839, "emitted_chars": 411902, "ratio": 0.9977 },
  "issues": [
    { "severity": "warn", "code": "unresolved_ref", "paragraph": 812, "detail": "_Ref55012 not found" },
    { "severity": "error", "code": "table_parse_failed", "paragraph": 1044 }
  ]
}
```

`text_fidelity.ratio` compares normalized text extracted independently from OOXML with the text emitted into the vault. This is the primary automated proof that nothing was silently dropped.

`vault/coverage.md` renders the same data as a table plus the issue list.

### 6.5 Re-ingest and ID stability

`meta/ids.json`:

```json
{
  "next": 1205,
  "blocks": {
    "SYS-000121": {
      "key": "3.2|paragraph|3|9f2a1c8b",
      "status": "active",
      "first_seen": "v0",
      "text_hash": "9f2a1c8b"
    }
  }
}
```

- `key` = `<heading path>|<type>|<ordinal within section>|<text hash>`.
- On `--reingest`, match candidates in this order: (1) exact `key`; (2) same heading path + type + text hash; (3) same heading path + type + ordinal with text similarity ≥ 0.85; otherwise allocate a new ID and mark the old one `deleted`.
- Print a re-ingest summary: matched, new, deleted, moved.

### 6.6 Acceptance tests (extractor)

| T  | Test                                                                                                                                                                                                                                                                    |
| -- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1 | Ingest a crafted fixture .docx containing: 3 heading levels, numbered and bulleted lists, a simple table, a merged-cell table, an image, a text box, an equation, an internal cross-reference, a footnote. Every construct appears in the vault with the expected type. |
| A2 | Every block in every section file has a unique, well-formed anchor; front matter`blocks` equals the anchor count.                                                                                                                                                     |
| A3 | `text_fidelity.ratio ≥ 0.99` on the fixture and on the real spec.                                                                                                                                                                                                    |
| A4 | Every`word_link` resolves to an existing ID, or is listed in `issues`.                                                                                                                                                                                              |
| A5 | Running ingest twice on the same file with`--reingest` produces a byte-identical vault and zero new IDs.                                                                                                                                                              |
| A6 | Renaming a heading's text and re-ingesting keeps the section ID (matched by path + ordinal + similarity).                                                                                                                                                               |
| A7 | `specctl ingest --dry-run` writes no vault files.                                                                                                                                                                                                                     |

---

## 7. Component 2 — Validator (Problem B)

### 7.1 CLI

```
specctl validate [PATHS...] [options]

  --base REF             git ref to compare against (default: HEAD)
  --assign-ids           allocate IDs for new blocks and rewrite files in place
  --allow-delete         permit blocks to disappear (otherwise error)
  --format text|json     default text
```

Exit codes: `0` clean, `1` warnings only, `2` errors.

### 7.2 Rules

| ID  | Severity                                      | Rule                                                                                        |
| --- | --------------------------------------------- | ------------------------------------------------------------------------------------------- |
| V01 | error                                         | Front matter parses, contains required keys,`id` matches the file name                    |
| V02 | error                                         | Every block has an anchor; anchor syntax valid                                              |
| V03 | error                                         | No duplicate IDs across the vault                                                           |
| V04 | error                                         | No ID present in`--base` has silently vanished (unless `--allow-delete`)                |
| V05 | error                                         | `locked:true` blocks are byte-identical to `--base`                                     |
| V06 | error                                         | Pipe tables have a consistent column count; HTML tables parse and are well-formed           |
| V07 | error                                         | Wikilink targets exist in the vault                                                         |
| V08 | error                                         | Asset files referenced by figure blocks exist                                               |
| V09 | warn                                          | Block text changed but front matter`blocks` count not updated (auto-fixable)              |
| V10 | **warn — always reported prominently** | Any numeric value or unit changed inside a block (report old → new, per block)             |
| V11 | warn                                          | New blocks without anchors (fixable with`--assign-ids`)                                   |
| V12 | warn                                          | Heading level or`number` changed relative to `--base`                                   |
| V13 | warn                                          | Trailing`^id` markers inconsistent with anchors (auto-fixable)                            |
| V14 | info                                          | Section size above a threshold (default 1500 words) — candidate for splitting when editing |

### 7.3 Output

```
SYS-000120.md
  V10  warn   SYS-000121  number changed: "50 ms" -> "80 ms"
  V05  error  SYS-000123  locked figure block modified
  V04  error  SYS-000129  block deleted (use --allow-delete to accept)
  V07  error  SYS-000131  wikilink target SYS-000999 does not exist

Summary: 3 errors, 1 warning, 2 files checked, base=HEAD
Affected by inbound references: SYS-000245, SYS-000301 (see backlinks.md)
```

JSON output mirrors this structure (`{file, rule, severity, block_id, message, old, new}`).

### 7.4 Acceptance tests (validator)

| T  | Test                                                                                                |
| -- | --------------------------------------------------------------------------------------------------- |
| B1 | Each rule V01–V13 has a fixture that triggers it and one that does not.                            |
| B2 | Changing "50 ms" to "80 ms" produces exactly one V10 with old and new values.                       |
| B3 | Editing a locked figure caption produces V05.                                                       |
| B4 | `--assign-ids` allocates IDs only to anchorless blocks and leaves everything else byte-identical. |
| B5 | Exit code is 2 when any error is present, 1 when only warnings, 0 when clean.                       |

---

## 8. Component 3 — Excel exporter (Problem B)

### 8.1 CLI

```
specctl export xlsx --out exports/SYS.xlsx [--ref HEAD] [--compare-to SYS-baseline-v0]
```

### 8.2 Sheet "Spec"

| Column      | Content                                                                                                         |
| ----------- | --------------------------------------------------------------------------------------------------------------- |
| ID          | Block ID                                                                                                        |
| Section     | Section number (`3.2`)                                                                                        |
| Breadcrumb  | Full path                                                                                                       |
| Level       | Heading level of the owning section                                                                             |
| Order       | Global document order index                                                                                     |
| Type        | Block type                                                                                                      |
| Content     | Plain text; tables flattened as`cell \| cell` per row separated by newlines; figures as `[FIGURE] <caption>` |
| Change      | `unchanged` / `modified` / `new` / `deleted` (only when `--compare-to` given)                         |
| Old content | Previous text when`modified` or `deleted`                                                                   |
| Rationale   | Commit rationale of the last commit touching that block                                                         |
| Commit      | Short SHA                                                                                                       |

### 8.3 Sheet "Changes"

Only rows where `Change != unchanged`, plus a `Numeric change` column populated from validator rule V10 data recomputed at export time.

### 8.4 Rules

- Change detection is by **ID**, never by position.
- Text comparison is on normalized text (collapse whitespace).
- Freeze the header row, set column widths, wrap `Content`.
- Images are **not** embedded; the caption and asset file name are written instead.

### 8.5 Acceptance tests

| T  | Test                                                                                         |
| -- | -------------------------------------------------------------------------------------------- |
| C1 | Export at baseline with`--compare-to` the same ref yields all rows `unchanged`.          |
| C2 | After a known edit, exactly the edited block is`modified` with correct old/new text.       |
| C3 | A moved block (same ID, different order) is`unchanged` in content and shows the new order. |
| C4 | A complex HTML table is flattened without losing cell text.                                  |

---

## 9. Component 4 — Index generator (Problems A and B)

```
specctl index            # regenerate index.md, backlinks.md, coverage.md
specctl log "message"    # append an entry to log.md
```

### 9.1 `vault/index.md`

Front matter `generated: true`. Body: a nested list of all sections — number, title, wikilink, ID, block count, word count. This is the agent's **primary map**; it must stay small (target < 40 KB) and be regenerated after every commit.

### 9.2 `vault/log.md`

Append-only table: timestamp, git SHA, section ID, skill used, model, rationale, counts (modified/new/deleted), numeric changes flagged.

### 9.3 `vault/backlinks.md`

For every ID that is a link target: the ID, its section, and the list of blocks referencing it. Generated by scanning wikilinks. This is the stand-in for a graph/impact tool in this phase.

### 9.4 Acceptance tests

| T  | Test                                                                                |
| -- | ----------------------------------------------------------------------------------- |
| D1 | `index.md` lists every section exactly once, all links resolve.                   |
| D2 | `backlinks.md` is the exact inverse of the outbound links found in section files. |
| D3 | Regenerating twice produces identical output (deterministic ordering).              |

---

## 10. Agent layer

### 10.1 `CLAUDE.md` (conventions the agent must follow)

Must state, at minimum:

1. **Read `vault/index.md` first** to locate content; never read the whole vault.
2. **Cite IDs** in every answer (`SYS-000121`), never paraphrase without a citation.
3. **Never edit** `vault/index.md`, `log.md`, `backlinks.md`, `coverage.md`, `meta/`, or `source/`.
4. **Never modify** blocks marked `locked:true`, never remove or alter anchors, never renumber IDs.
5. **Never change numeric values or units** unless the user asked explicitly; if a change seems required, propose it in the chat instead.
6. To edit: create a branch `edit/<section-id>-<slug>`, edit only the target section file, run `specctl validate --base main`, report the summary, and wait for human approval before committing.
7. Commit message format (§10.4).
8. Use `rg` (ripgrep) with ID patterns for backlinks; `backlinks.md` is authoritative.

### 10.2 Skills (`.claude/skills/<name>/SKILL.md`)

Standard Agent Skills format: required front matter `name`, `description`; tool-specific extras go under `metadata`.

| Skill                     | Problem | Purpose                                                                                 | Output                          |
| ------------------------- | ------- | --------------------------------------------------------------------------------------- | ------------------------------- |
| `spec-navigate`         | A       | How to use`index.md`, breadcrumbs, `backlinks.md`, ripgrep patterns                 | Answer with citations           |
| `understand-section`    | A       | Read a section plus its inbound/outbound references and summarize precisely             | Structured summary with IDs     |
| `answer-with-citations` | A       | Q&A protocol: locate, read, answer, cite, state uncertainty                             | Answer                          |
| `restructure-section`   | B       | Apply the agreed target structure to a section                                          | Edited file + change summary    |
| `rewrite-presentation`  | B       | Normalize presentation (lists, tables, terminology) without changing meaning            | Edited file                     |
| `improve-workflow`      | B       | The full edit loop: branch → edit → validate → report → wait for approval → commit | Commit                          |
| `write-eval-questions`  | A/B     | Draft golden-set questions from a section, with expected answer and source IDs          | `eval/questions.yaml` entries |

Each `SKILL.md` must contain: when to use, preconditions, step-by-step procedure, hard constraints (the "never" list), and a worked example. `restructure-section` must reference `references/target-structure.md` (owner-provided, see §12 week 2).

### 10.3 Edit workflow (normative)

```
1. git checkout -b edit/SYS-000120-restructure
2. agent edits vault/sections/SYS-000120.md only
3. specctl validate --base main
4. agent reports: rules triggered, numeric changes, inbound references affected
5. human reviews diff in VS Code, edits by hand if needed
6. specctl validate --base main  (must be clean or accepted)
7. git commit  (message format below)
8. specctl index && specctl log "<rationale>"
9. merge to main
```

### 10.4 Commit message format

```
[SYS][3.2] <one-line rationale>

Skill: restructure-section
Model: claude-<model-id>
Blocks: modified=5 new=1 deleted=0
Numeric-changes: none
Reviewed-by: <owner>
```

---

## 11. Runbook

```bash
# one-time
pip install -e .                                   # or: uv sync
specctl ingest source/SYS.docx --doc-key SYS --out vault/
open vault/coverage.md                             # review, fix leftovers by hand
git add -A && git commit -m "[SYS] baseline" && git tag SYS-baseline-v0

# understanding (Problem A)
# in VS Code + Claude Code:
#   "Using spec-navigate, what does section 3.2 require, and what references it?"

# improving (Problem B)
git checkout -b edit/SYS-000120-restructure
#   "Using restructure-section, restructure SYS-000120."
specctl validate --base main
# review diff, approve
git commit -F .git/COMMIT_MSG && specctl index && specctl log "restructured 3.2"
git checkout main && git merge edit/SYS-000120-restructure

# deliverable
specctl export xlsx --out exports/SYS.xlsx --compare-to SYS-baseline-v0
```

---

## 12. Plan and definition of done

| Week                  | Problem | Deliverable                                                                                                                                          | Done when                                                                  |
| --------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **W1 D1**       | A       | Fidelity gate: run a throwaway conversion of the real file, measure tables, figures, shapes, links, numbering                                        | A go/no-go note; if Markdown loses > 10% of tables, escalate (see B §4.1) |
| **W1 D2**       | A       | First rough vault + 10 trial questions answered by Claude Code                                                                                       | Owner sees value on day 2                                                  |
| **W1 D3–D4**   | A       | `specctl ingest` complete per §6, tests A1–A7 green                                                                                              | Coverage report on the real file,`text_fidelity ≥ 0.99`                 |
| **W1 D5**       | A       | `CLAUDE.md`, `index.md`, `log.md`, `backlinks.md`, skills `spec-navigate`, `understand-section`, `answer-with-citations`; baseline tag | Agent answers with citations                                               |
| **W2 D6**       | B       | Owner provides`references/target-structure.md` with one real before/after example                                                                  | **Gate: no example, no improvement skills**                          |
| **W2 D7–D8**   | B       | Skills`restructure-section`, `rewrite-presentation`, `improve-workflow`; edit loop runs on one section                                         | One section improved end to end                                            |
| **W2 D9**       | B       | `specctl validate` per §7, tests B1–B5 green                                                                                                     | Validator catches all fixture violations                                   |
| **W2 D10**      | B       | `specctl export xlsx` per §8, tests C1–C4 green                                                                                                  | Excel produced with change columns                                         |
| **W3 D11–D12** | A/B     | Golden set of 20–30 questions, run before and after                                                                                                 | Owner-confirmed accuracy numbers                                           |
| **W3 D13**      | A       | Lint pass (`validate` over the whole vault), fix data issues                                                                                       | Zero errors in the vault                                                   |
| **W3 D14**      | B       | Improve 3–5 sections total                                                                                                                          | Diffs reviewed and merged                                                  |
| **W3 D15**      | —      | Pilot report + README + handover                                                                                                                     | Report delivered                                                           |

---

## 13. Acceptance thresholds

| # | Metric                                                     | Threshold                             |
| - | ---------------------------------------------------------- | ------------------------------------- |
| 1 | Blocks with valid unique IDs                               | 100%                                  |
| 2 | `text_fidelity.ratio`                                    | ≥ 0.99                               |
| 3 | Word internal links resolved to wikilinks                  | ≥ 95% (remainder listed in coverage) |
| 4 | Tables preserved as pipe or HTML                           | ≥ 90% (remainder listed)             |
| 5 | Re-ingest ID stability (A5)                                | 100%                                  |
| 6 | Sections improved end to end                               | ≥ 3                                  |
| 7 | Validator detection on fixture suite                       | 100%                                  |
| 8 | Golden-set answers correct (owner-judged)                  | ≥ 80%                                |
| 9 | Excel export opens, change columns correct on a known edit | Pass                                  |

---

## 14. Risks and responses

| Risk                                               | Response                                                                                                                                             |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Extractor consumes the whole budget                | Hard timebox W1 D1–D4. After that, remaining unparsed items are fixed by hand — it is one file                                                     |
| Fidelity gate fails (complex tables)               | Switch those tables to HTML; if still failing, store them as raw OOXML + rendered image, flag`locked`, and note the limitation in the pilot report |
| Agent silently changes values                      | V10 always reported; human reviews diff;`locked` blocks byte-compared                                                                              |
| Numbering cannot be resolved from`numbering.xml` | Fall back to LibreOffice-rendered numbering, or keep heading text without numbers and record it in coverage                                          |
| No target-structure example by W2 D6               | Improvement skills are not written; week 2 shifts to more Problem-A work (owner decision)                                                            |
| Scope creep toward MCP/index/UI                    | Any such request goes to`B-limitations-roadmap.md`, not into this phase                                                                            |

---

## 15. Appendix

### 15.1 Minimal `SKILL.md` shape

```markdown
---
name: restructure-section
description: Restructure one spec section to the agreed target structure without changing meaning, values, or units. Use when the user asks to restructure or reorganize a section.
metadata:
  version: "1.0"
  problem: "B"
  applies_to: "section"
  allowed_changes: "reorder, split, merge, rewrite prose"
  forbidden: "numeric values, units, locked blocks, anchors, IDs"
---

## Preconditions
- The section file is open on a branch `edit/<id>-<slug>`.
- `references/target-structure.md` has been read.

## Procedure
1. Read the section file and its front matter.
2. Read `backlinks.md` for inbound references to blocks in this section.
3. Propose the restructuring in chat (bullet list) and wait for confirmation.
4. Apply edits to the file, one block at a time; keep every anchor.
5. Run `specctl validate --base main`; report the summary verbatim.
6. Stop. Wait for human approval before committing.

## Hard constraints
- Never modify text inside `locked:true` blocks.
- Never change a number or a unit. If one looks wrong, report it instead.
- Never delete a block; if content must go, propose it and wait.
```

### 15.2 `log.md` row

```
| 2026-09-24T14:12+07:00 | a1b2c3d | SYS-000120 | restructure-section | claude-opus-5 | split step 3 into two steps for clarity | mod=5 new=1 del=0 | numeric: none |
```

### 15.3 Suggested Python layout

```
specctl/
├── cli.py                 # typer app
├── ingest/
│   ├── package.py         # docx zip + xml loading
│   ├── numbering.py       # numbering.xml resolution
│   ├── blocks.py          # block stream construction
│   ├── anchors.py         # bookmarks, hyperlinks, REF fields
│   ├── media.py           # images, shapes, LibreOffice rendering
│   ├── tables.py          # pipe vs html decision + serialization
│   ├── segment.py         # section splitting
│   ├── ids.py             # allocation + registry + re-ingest matching
│   └── writer.py          # markdown serialization
├── validate/rules.py
├── exportx/xlsx.py
├── indexgen/{index,backlinks,log}.py
└── model.py               # Block, Section, Document dataclasses
tests/fixtures/*.docx
```

Dependencies: `python-docx`, `lxml`, `typer`, `openpyxl`, `pyyaml`, `rapidfuzz`, `pytest`. Optional external binaries: `libreoffice`, `pandoc` (equations).

### 15.4 Glossary

| Term          | Meaning                                                                 |
| ------------- | ----------------------------------------------------------------------- |
| Vault         | The`vault/` folder of Markdown files — also what Obsidian opens      |
| Anchor        | `<!-- id:... -->` comment that binds a Markdown block to a stable ID  |
| Locked block  | A block agents must not modify (figures, shapes, raw fallbacks)         |
| Baseline      | A git tag marking a comparable version of the spec                      |
| Coverage      | Proof of what the extractor captured, fell back on, or failed on        |
| Fidelity gate | The day-1 measurement deciding whether Markdown is a sufficient store   |
| Golden set    | Owner-approved questions with expected answers, used to measure quality |
