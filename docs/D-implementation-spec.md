# specctl — Implementation Specification

**Version:** 2.3 · **Date:** 2026-09-22 · **Status:** Normative
**Supersedes:** `archive/A-solution-spec-handoff.md` v1.0 — which is retained as history and MUST NOT be implemented from.
**Audience:** implementer (human or coding agent). §1.5 is for the solution owner.
**Companions:** `B-limitations-roadmap.md` — what this phase deliberately does not do, and when to extend it. `archive/C-spec-gaps.md` — the 31 findings against v1.0 that this document resolves; read it only to understand *why* a rule is what it is.
**Đọc trước:** `F-features.md` — vấn đề, phương pháp, và thứ tự tính năng. Tài liệu này là phần chi tiết kỹ thuật phía sau nó.

---

## Part 0 — Orientation

## 1. How to read this document

This document is **self-contained**. Everything needed to build `specctl` is here. No normative rule defers to another document.

### 1.1 Normative language

**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY** carry their RFC 2119 meanings. Text marked *Rationale:* or *Note:* is informative and imposes no requirement. Tables and code blocks inside a numbered section are normative unless the section says otherwise.

### 1.2 The standing rule

> If a normative rule here turns out to be impossible on the real source document, **stop and report it**. Do not invent a variant.

Where a rule leaves a genuine choice, pick the option that preserves source fidelity and record an issue (§8.4). Silent degradation is the one failure mode this design exists to prevent.

### 1.3 Reading order

| Section        | Read when                                                                           |
| -------------- | ----------------------------------------------------------------------------------- |
| 1–3           | Before writing any code. Orientation, problem, architecture.                        |
| **4–8** | **The contract.** Data model and file formats. Every component depends on it. |
| 9              | Cross-cutting CLI conventions and invariants. Applies to every command.             |
| 10–13         | Component specifications, one per command.                                          |
| 14–17         | The agent layer and the edit workflow.                                              |
| 18–21         | Tests, acceptance, runbook, schedule.                                               |
| Appendices     | Schemas, code registries, a worked example to copy literally, traceability.         |

### 1.4 Identifier namespace

One prefix, one meaning, throughout:

| Prefix                                                               | Meaning                       | Defined in |
| -------------------------------------------------------------------- | ----------------------------- | ---------- |
| `G1`–`G6`                                                       | Goals                         | §2.3      |
| `NG1`–`NG11`                                                    | Non-goals                     | §2.4      |
| `DEC-01`–`DEC-13`                                               | Architecture decisions        | §3.2      |
| `FMT-01`–`FMT-12`                                               | File and format rules         | §6        |
| `V01`–`V17`, `V04a`, `V04b`                                 | Validator rules               | §12.3     |
| `T-ING-nn`, `T-FMT-nn`, `T-VAL-nn`, `T-IDX-nn`, `T-EXP-nn` | Tests                         | §18       |
| `ACC-1`–`ACC-9`                                                 | Acceptance thresholds         | §19       |
| `snake_case`                                                       | Coverage issue and skip codes | Appendix B |

`SYS-000120` and similar are **block IDs** — data, not document references (§5). `GAP-nn` refers to `archive/C-spec-gaps.md` and appears only in Appendix G.

### 1.5 Owner inputs required

Three inputs are not the implementer's to decide. Each has a due date in the §21 schedule. None blocks the start of coding.

| #                   | Input                                                                                                         | Needed by              | Consequence if late                                                                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[OWNER-1]** | Confirmation of the fidelity metric definition (§10.12) and its threshold ACC-2                              | **Before W1 D1** | The W1 D1 go/no-go measurement has no agreed pass mark; the Markdown-as-store decision (DEC-01) cannot be closed                                    |
| **[OWNER-2]** | `references/target-structure.md` — the agreed target section structure, with one real before/after example | **W2 D6**        | Improvement skills are not written; week 2 shifts to further Problem-A work                                                                         |
| **[OWNER-3]** | The customer's position on cloud-model processing of spec content, recorded in §2.5                          | **Before W1 D2** | §2.5 says "local only" while DEC-05 selects a hosted agent. The tension is unresolved on paper, and the first agent session sends customer content |

*Note on [OWNER-3]: this may already be covered by the customer agreement. The requirement is that the document say so, because this document is what a coding agent and a reviewer work from.*

### 1.6 What changed in v2.3

| # | Decision | Sections changed |
| - | -------- | ---------------- |
| 12 | **`python-docx` is dropped.** Its object model hides `w:sdt`, `mc:AlternateContent`, `w:ins` and `w:del` — precisely what §10.5 must see — so a walker built on it would carry the silent-loss path the walker exists to close. Fixtures are raw OOXML, read with `lxml` | §18.3, App. E |
| 13 | **`degraded.docx` is built, not hand-authored**, since Word only writes valid OOXML | §18.3 |
| 14 | **Fixture contents are verified against the raw OOXML**, and `*.docx` is marked `binary` in `.gitattributes` | §18.3 |
| 15 | **The fidelity source side de-duplicates a text box** (F05). Word nests a box's paragraphs inside their anchor and writes the box under both `mc:Choice` and `mc:Fallback`, so the naive reading of §10.12 step 1 counts one sentence three times and fabricates a fourth string that nothing can match | §10.12 F4 |

### 1.7 What changed in v2.2

Three contradictions in the file format, found by implementing it. Each was discovered
because a conforming file failed to survive being written and read back.

| # | Decision | Sections changed |
| - | -------- | ---------------- |
| 9 | **The synthetic front-matter section is at `level: 1`**, with a real `#` heading line. `level: 0` cannot be written down — §6.1 gives a heading one to six `#` characters — so that section could be built in memory and never read back. Level 0 also made the preamble the *ancestor* of every chapter, prefixing every breadcrumb in the vault with `Front matter >` | §10.9, App. A.1 |
| 10 | **A heading block is exactly one line.** §6.1's grammar allowed content lines after the heading line, which §6.3 and Appendix D both contradict | §6.1 |
| 11 | **§10.11's YAML style rule replaced with a table.** It said "flow style only for `source`", while both worked front-matter blocks use flow sequences for `path`, `path_ids`, `bookmarks` and `refs_out`. The quoting rule is now stated precisely, and applies to YAML 1.1 *and* 1.2 spellings — `1e5` is a string to one and a float to the other, and the vault is read by Obsidian as well as by `specctl` | §10.11 |

### 1.8 What changed in v2.1

v2.1 resolves eight places where v2.0 contradicted itself or specified something unimplementable.
Nothing was added or removed in scope; every change makes an existing rule usable. The decision
record with the full before/after and the reasoning is `G-data-contract.md`.

| # | Decision | Sections changed |
| - | -------- | ---------------- |
| 1 | **Every part of a split gets a new ID**, and the original ID leaves the vault. v2.0 let one part keep the original ID while the registry marked that ID terminal | §5.4 L3, §7, §14, §15, App. D |
| 2 | **V04b applies only to `supersedes`.** v2.0 also applied it to `split_from`, so every split of N parts failed | §5.4 L2, §12.3, §12.5 |
| 3 | **`validate` writes nothing.** ID allocation and registry updates moved to `specctl assign-ids` and `specctl registry sync` | §9.1, §9.5, §12.1, §12.4, §12.5, §12.10 |
| 4 | **Edit workflow reordered:** `index` before the commit, `registry sync` and `log` in a second commit, squash merge forbidden | §16 E5–E6, §20 |
| 5 | **V05 compares content lines byte-for-byte and anchor attributes as an unordered set** — not the whole block byte-for-byte, which FMT-12 makes impossible | FMT-08, §6.3, §12.3, §12.8 |
| 6 | **`origin: ingest\|authored`** added to section front matter; `source` is `null` and `bookmarks` is `[]` for an authored section | §5.5, §6.2, App. A.1 |
| 7 | **Numeric tokens have boundaries:** no token inside an identifier, radix prefixes excluded, decimal-comma rule made explicit and configurable | §12.6 |
| 8 | **Fidelity:** `candidate_sections` defined, short segments matched only in their owning section at token boundaries, `to_plain_text` unescapes Markdown | §6.6, §8, §10.12 F7–F9 |

One consequence of decision 1 required a further change: §12.6 N4 now compares the **union** of a
split's parts against the original, as one finding. Comparing each part separately would report every
value that landed in a sibling as removed — a false alarm on every split.

### 1.9 What changed from v1.0

v1.0's §5 contradicted itself in five places, omitted two mechanisms the workflow depends on (block lineage, a stable re-ingest key), stated two acceptance thresholds against undefined metrics, and did not address four silent-data-loss paths in .docx parsing. All 31 findings are resolved here as ordinary spec text. Appendix G maps each finding to the section that resolves it, and each v1.0 section to its successor here.

Materially new: `specctl fmt` (§11), block lineage (§5.4), directional fidelity measurement (§10.12), a normative numeric-diff algorithm (§12.6), and `specctl.toml` (§9.2).

---

## 2. Problem, goals and constraints

### 2.1 Context

A system requirements specification (SYS spec, automotive, ASPICE SYS.2) from a Japanese customer, delivered as a single **Word .docx** file in agreed English translation. It is well structured by headings; the body contains prose, tables, images, Word shapes, equations and internal cross-references. The team wants to **improve** the spec — structure, presentation, parameter representation — with AI assistance, and to **understand and query** it.

### 2.2 Two problems

|            | **Problem A — Spec → Knowledge**                                       | **Problem B — Knowledge → Improvement**                                |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| Question   | How do we turn a .docx into something an agent can read and address precisely? | How do we edit the spec with context, control and evidence?                    |
| Input      | `SYS.docx`                                                                   | The vault produced by A                                                        |
| Output     | Markdown vault with stable IDs, links, generated indexes, coverage report      | Improved sections, change log, Excel deliverable                               |
| Components | `ingest`, the file contract, `index`, reading skills                       | Improvement skills, edit workflow,`fmt`, `validate`, backlinks, `export` |
| Risk       | Silent data loss during parsing                                                | AI silently changing meaning or values                                         |
| Timeline   | Week 1                                                                         | Weeks 2–3                                                                     |

**A is a precondition for B.** Without stable IDs there is no addressable unit to edit, no change report, and no row key for Excel.

### 2.3 Goals

- **G1 (A)** Convert the .docx into a Markdown vault where every block has a stable ID, with a coverage report proving what was and was not captured.
- **G2 (A)** Preserve Word internal hyperlinks, bookmarks and heading auto-numbering.
- **G3 (A)** Let an agent answer questions about the spec **with ID citations**.
- **G4 (B)** Improve a section via an agent and a skill, reviewed as a diff by a human, committed with rationale.
- **G5 (B)** Detect deterministically when an edit breaks IDs, locked blocks, tables, or changes numbers or units.
- **G6 (B)** Export to Excel with change status against a baseline.

### 2.4 Non-goals (this phase)1

NG1 No MCP server.
NG2 No database or search index.
NG3 No web UI. NG4 No multi-file corpus.
NG5 No Japanese-language support.
NG6 No write-back to .docx.
NG7 No local LLM.
NG8 No RAG chatbot.
NG9 No requirements-management features (attribute workflows, approvals, traceability matrices).
**NG10** No automated impact analysis beyond one hop — `backlinks.md` and ID grep are the tools.
**NG11** No concurrent editing — one user, one branch at a time; git is the only concurrency control.

*Note: NG5 means no Japanese tokenization, search or source document. The English translation still contains CJK characters in signal names and figure labels, and every rule here handles them (§6.6).*

### 2.5 Constraints

- Local only. One developer, ~3 weeks, AI-assisted coding.
- Runtime: Python 3.11+, git. Optional external binary: LibreOffice (shape and equation rendering fallback).
- `specctl` itself MUST make no network calls (§9.5).
- Agent runtime: **Claude Code in VS Code**. Human reviewer: the solution owner.
- Single user, multiple sessions, no auth.
- **[OWNER-3]** Customer position on cloud-model processing of spec content: _to be recorded here._

### 2.6 Definition of done

All thresholds in §19 met, the runbook in §20 executable end to end on the real spec file, and the pilot report produced.

---

## 3. Architecture

### 3.1 Shape

```
PROBLEM A: Spec → Knowledge                    PROBLEM B: Knowledge → Improvement
──────────────────────────────                 ─────────────────────────────────────
 source/SYS.docx                                vault/sections/*.md  (blocks with IDs)
    │                                               │
    │ specctl ingest              [§10]             │ /improve <section> <skill>
    ▼                                               ▼
 vault/                                          Claude Code + skills           [§14–16]
  ├─ sections/SYS-000120.md      [§4–8]            │  edits one section file on a branch
  ├─ assets/                                        ▼
  ├─ index.md, log.md,           [§13]           specctl fmt                    [§11]
  │  backlinks.md, coverage.md                      │  derived front matter, anchors, format
  └─ (git baseline tag)                             ▼
    │                                            specctl validate               [§12]
    ▼                                               │  IDs, lineage, locked blocks, numbers
 Claude Code reads / greps      [use as is]         ▼
 Obsidian browses               [use as is]      human review of the diff (VS Code)
                                                    │
                                                    ▼
                                                 git commit (rationale, skill)
                                                    │
                                                    ▼
                                                 specctl export xlsx            [§13.5]
```

**Build:** one Python package `specctl` with five commands — `ingest`, `fmt`, `validate`, `index`/`log`, `export` — plus the agent conventions and skills of §14–§15.
**Use as is:** Claude Code, VS Code diff, git, Obsidian, LibreOffice.

### 3.2 Decisions

| #      | Decision                                                                                                                             | Rationale                                                                                                                                                                                 | Rejected alternative                                                                   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| DEC-01 | **The Markdown vault is the source of truth.** One file per section; blocks carry stable IDs                                   | Human-readable, git-diffable, directly consumable by the agent, viewable in Obsidian, zero infrastructure                                                                                 | Canonical JSON store (more faithful, slower to build); a database (no multi-user need) |
| DEC-02 | **ID-first.** Every block gets an immutable ID at ingest                                                                       | IDs are what make edit tracking, backlinks, change reports and Excel rows possible. This is the core value                                                                                | Line numbers or heading numbers — both shift on edit                                  |
| DEC-03 | **Deterministic ingest.** No LLM and no network in the conversion path                                                         | The spec is contractual; a hallucinated or dropped sentence is unacceptable. An LLM may later*describe* a figure, never *produce* content                                             | LLM-based document extraction                                                          |
| DEC-04 | **Word metadata is read from OOXML directly** — bookmarks, hyperlinks, REF fields, numbering                                  | These are the only fully reliable cross-reference edges, and generic converters drop them                                                                                                 | Plain Pandoc/Docling conversion                                                        |
| DEC-05 | **Claude Code is the agent and the editor**; git is history and review                                                         | Sessions, skills, file editing and diff review already exist; building them would consume the entire budget                                                                               | A custom harness or web app                                                            |
| DEC-06 | **No MCP server and no search index yet**                                                                                      | One file; outline plus grep plus per-section reads are sufficient. Add when the pain is measured                                                                                          | `spec-mcp` and SQLite FTS/vector now                                                 |
| DEC-07 | **Obsidian is an optional viewer** over the same folder                                                                        | Costs nothing, adds graph and backlink browsing, no lock-in — a vault*is* a folder of Markdown                                                                                         | Obsidian as the storage backend                                                        |
| DEC-08 | **Writes are gated.** Agent edits working files → `fmt` → `validate` → human reviews the diff → commit                 | Prevents silent content drift in values, units and IDs                                                                                                                                    | The agent committing directly                                                          |
| DEC-09 | **Excel is an export view only**, never an input                                                                               | Excel cannot represent the structure; round-tripping would double-maintain                                                                                                                | Excel as the editing surface                                                           |
| DEC-10 | **Block lineage is explicit.** Splits and merges are declared in the file, not inferred                                        | Restructuring is the point of Problem B. Without declared lineage, every split or merge reads as deletion plus creation — to the validator, and to the customer in the Excel deliverable | Inferring lineage by text similarity (non-deterministic, and wrong under rewriting)    |
| DEC-11 | **Fidelity is measured directionally.** Coverage of source text, with additions reported separately                            | A net ratio of character counts cannot distinguish "nothing lost" from "1% lost and 1% added". The coverage claim is the whole basis for trusting the vault                               | A ratio of emitted characters to source characters                                     |
| DEC-12 | **Derived data is owned by tooling, never by hand.** `specctl fmt` computes it; humans and agents edit only authored content | Front matter restates what the body already says. Anything restated will drift, and the agent navigates by the restatement                                                                | Asking the agent to maintain front matter by hand                                      |
| DEC-13 | **Configuration is declared once**, in `specctl.toml`                                                                        | The same doc key, split level and thresholds are needed by four commands; retyping them is how runbooks silently diverge                                                                  | Per-command flags only                                                                 |

---

## Part 1 — The contract

Sections 4 through 8 are the data model. Every component reads and writes against it. A change here is a change to every component.

## 4. Repository layout

```
spec-workspace/                        # a git repository
├── specctl.toml                       # configuration (§9.2)                    committed
├── CLAUDE.md                          # agent conventions (§14)                 committed
├── .claude/skills/<skill>/SKILL.md    # agent skills (§15)                      committed
├── source/
│   └── SYS.docx                       # the original, NEVER modified            committed
├── references/
│   └── target-structure.md            # OWNER-AUTHORED (§1.5 [OWNER-2])         committed
├── vault/
│   ├── index.md                       # GENERATED — table of contents (§13.2)   committed
│   ├── log.md                         # GENERATED — append-only change log      committed
│   ├── backlinks.md                   # GENERATED — inbound references          committed
│   ├── coverage.md                    # GENERATED — human-readable coverage     committed
│   ├── sections/
│   │   └── SYS-000120.md              # one file per section (§6)               committed
│   └── assets/
│       ├── SYS-000151.png             # figures, rendered shapes                committed
│       └── SYS-000151.xml             # raw OOXML of fallback elements          committed
├── meta/
│   ├── ids.json                       # ID registry (§7)                        committed
│   └── coverage.json                  # machine-readable coverage (§8)          committed
├── eval/
│   ├── questions.yaml                 # golden set (§19 ACC-8)                  committed
│   └── runs/                          # dated result files                      committed
├── exports/                           # GENERATED xlsx                          git-ignored
└── tests/
    └── fixtures/                      # .docx fixtures + README (§18.3)         committed
```

`exports/` MUST be in `.gitignore`. Everything else listed as committed MUST be tracked. `source/SYS.docx` MUST NOT be modified by any command.

---

## 5. Identifiers and lifecycle

### 5.1 Format

- **`<DOCKEY>-<NNNNNN>`**, e.g. `SYS-000120`.
- `DOCKEY` matches `[A-Z][A-Z0-9]{1,7}` and is supplied at ingest.
- The counter is a plain decimal integer zero-padded to exactly 6 digits. The canonical regular expression is `^[A-Z][A-Z0-9]{1,7}-[0-9]{6}$`.
- The **lowercased ID** (`sys-000120`) is used only in `^id` block-reference markers (FMT-04) and in the fragment of a block-level wikilink (FMT-07).

### 5.2 Allocation

- IDs are allocated sequentially in document order at first ingest, starting at 1. No gaps, no step, no reservation scheme.
- `meta/ids.json.next` holds the next free counter value. Every allocation increments it.
- An ID, once allocated, is **never reused** — not after deletion, not after a merge, not across re-ingest.

### 5.3 Immutability

An ID MUST NOT change when the block's text, heading number, position, section or file changes. The ID is the only stable handle in the system; everything else — numbers, paths, breadcrumbs, order — is derived and may change freely.

**Section IDs** are the IDs of their heading block. A section file MUST be named `<section-id>.md`.

### 5.4 Lifecycle and lineage

Every ID in the registry carries a `status`:

| Status      | Meaning                                                                        | Lineage field              |
| ----------- | ------------------------------------------------------------------------------ | -------------------------- |
| `active`  | The block exists in the vault                                                  | —                         |
| `deleted` | The content was removed deliberately and is not represented by any other block | —                         |
| `merged`  | The block's content was absorbed into another block                            | `merged_into: <ID>`      |
| `split`   | The block was divided into two or more blocks                                  | `split_into: [<ID>, …]` |

Permitted transitions:

```
          ┌──────────────► deleted
          │
 active ──┼──────────────► merged    (content lives on in merged_into)
          │
          └──────────────► split     (content lives on in split_into)

 deleted / merged / split are terminal. An ID never returns to active.
```

**Lineage is declared in the file, not inferred.** When an editor merges or splits blocks, the surviving blocks state where their content came from, using the anchor attributes of §6.3:

- `supersedes:<ID>[,<ID>…]` — this block absorbed the content of those blocks. Each named block becomes `merged`.
- `split_from:<ID>` — this block was carved out of that block. The named block becomes `split` and leaves the vault.

*Rationale (DEC-10): the validator must be able to tell "this ID vanished because content was deleted" from "this ID vanished because its content is now in that block". Without the distinction, the only way to merge two paragraphs is to disable deletion protection for the whole run, and the Excel deliverable reports an editorial improvement as content deletion.*

Rules:

| R  | Rule                                                                                                                                                                                                                                                |
| -- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| L1 | A lineage attribute MUST name an ID that exists in the comparison base (§12.2). Naming an unknown ID is V04a.                                                                                                                                      |
| L2 | An ID MAY be named by at most one `supersedes` attribute in the whole vault. Two blocks naming the same `supersedes` target is V04b. A `split_from` target is **expected** to be named by every part of its split, so V04b never applies to `split_from`. |
| L3 | **Every** block resulting from a split MUST carry `split_from:<original-id>` and MUST be allocated a **new** ID. The original ID MUST NOT appear in the vault after the split; it becomes `split` with `split_into` listing every part. A split into N parts therefore consumes N new IDs and retires one. *Rationale: a terminal status means "not in the vault". Letting one part keep the original ID makes that ID simultaneously `active` and `split`, which no consumer can interpret — and it makes the Excel export report one part as `unchanged` when its text demonstrably got shorter.* |
| L4 | Lineage attributes are**permanent**. `specctl fmt` MUST NOT remove them, and they survive into future versions as the block's provenance.                                                                                                   |
| L5 | Lineage is file-agnostic: the named ID MAY live in another section file. The workflow restricts multi-file edits (§16), the data model does not.                                                                                                   |

### 5.5 New blocks and new sections

- A new block written by an editor has no anchor. `specctl assign-ids` allocates an ID and writes the anchor (§12.4).
- A new **section** — a new heading at a level ≤ `split_level` — requires its file to be named after an ID that does not yet exist. `specctl split-section` (§12.9) performs the move. A section created this way carries `origin: authored`, `source: null` and `bookmarks: []` (§6.2): it has no paragraph range in the .docx because it was never in the .docx.

---

## 6. Section file format

### 6.1 File grammar

A section file contains **one heading block and all content up to the next heading at a level ≤ the heading's own level**. Headings deeper than `split_level` remain inside the file as ordinary `heading` blocks.

```ebnf
section-file   = front-matter , blank-line , heading-block , { blank-line , block } , LF ;

front-matter   = "---" , LF , yaml-mapping , "---" , LF ;

heading-block  = heading-line ;                   (* exactly one line, per §6.3 *)
heading-line   = hashes , SP , [ number , SP ] , title , SP , anchor , LF ;
hashes         = "#" , { "#" } ;                  (* count = level, 1..6 *)

block          = anchor , LF , content-line , { LF , content-line } , [ LF , blockref ] ;

anchor         = "<!--" , SP , "id:" , ID , SP , "type:" , TYPE , { SP , attribute } , SP , "-->" ;
attribute      = key , ":" , value ;
key            = LOWERCASE , { LOWERCASE | DIGIT | "_" } ;
value          = VCHAR , { VCHAR } ;              (* no SP, no "-->" *)

blockref       = "^" , lowercase-id , LF ;
blank-line     = LF ;
```

| R      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FMT-01 | Front matter is YAML, delimited by`---` lines, and MUST validate against the schema for its file class (§6.2). Keys outside the schema are an error (V01).                                                                                                                                                                                                                                                                                  |
| FMT-02 | Every block carries**exactly one** anchor, the single canonical ID carrier. For `heading` blocks the anchor is appended to the heading line after one space. For every other type the anchor occupies its own line immediately before the block's first content line, with **no** blank line between them.                                                                                                                       |
| FMT-03 | Block types are`heading`, `paragraph`, `list`, `table`, `figure`, `formula`, `code`, `raw` (§6.3).                                                                                                                                                                                                                                                                                                                            |
| FMT-04 | A trailing block reference`^<lowercase-id>` is **REQUIRED** on every non-heading block that is the target of at least one wikilink anywhere in the vault, for any block type. It MAY be present on other `paragraph` and `list` blocks. It is derived from the anchor and never authoritative; `specctl fmt` adds required markers and removes orphaned ones. Heading blocks never carry one — they are addressed by file name. |
| FMT-05 | The heading line carries the rendered number from Word (`## 3.2 Braking control`). Body text MUST NOT contain section numbering.                                                                                                                                                                                                                                                                                                             |
| FMT-06 | Exactly one blank line separates consecutive blocks. The file ends with exactly one`LF`.                                                                                                                                                                                                                                                                                                                                                     |
| FMT-07 | Internal cross-references are wikilinks (§6.5). External links use standard Markdown link syntax with the original URL.                                                                                                                                                                                                                                                                                                                       |
| FMT-08 | Blocks with`locked:true` MUST NOT be modified by any agent. V05 compares them to the base per §12.8 — content lines byte-for-byte, anchor attributes as an unordered set.                                                                                                                                                                                                                                                                                                                      |
| FMT-09 | Files are UTF-8 without BOM, LF line endings, no trailing whitespace on any line, no tab characters outside fenced code blocks.                                                                                                                                                                                                                                                                                                                |
| FMT-10 | Generated files (§13) carry`generated: true` and MUST NOT be hand-edited.                                                                                                                                                                                                                                                                                                                                                                   |
| FMT-11 | Derived front matter (§6.2) is owned by`specctl fmt`. Humans and agents edit the body; `fmt` recomputes the front matter.                                                                                                                                                                                                                                                                                                                 |
| FMT-12 | Anchor attribute order is:`id`, `type`, then the remaining attributes in the order listed in §6.3, then lineage attributes. `specctl fmt` normalizes the order.                                                                                                                                                                                                                                                                         |

### 6.2 Front matter

**Section files** — schema `section` (Appendix A.1):

```yaml
---
id: SYS-000120
doc: SYS
number: "3.2"
title: Braking control
level: 2
parent: SYS-000100
order: 14
path: ["3", "3.2"]
path_ids: ["SYS-000100", "SYS-000120"]
breadcrumb: "SYS > 3 Braking system > 3.2 Braking control"
bookmarks: ["_Ref123456", "_Toc99887"]
refs_out: ["SYS-000245", "SYS-000301#^sys-000302"]
blocks: 9
words: 412
origin: ingest
source: { docx: "source/SYS.docx", paragraphs: [412, 447] }
ingest_version: 1
generated: false
---
```

**Key ownership** — this table is normative and is what `specctl fmt` (§11) and V15 implement:

| Key                | Owner             | Required                | Derived from                                         |
| ------------------ | ----------------- | ----------------------- | ---------------------------------------------------- |
| `id`             | ingest, immutable | yes                     | allocation (§5.2)                                   |
| `doc`            | ingest, immutable | yes                     | `--doc-key`                                        |
| `origin`         | ingest, immutable | yes                     | `ingest` for a section extracted from the .docx; `authored` for one created later by an editor |
| `source`         | ingest, immutable | yes                     | the package and paragraph indices when`origin: ingest`; MUST be `null` when `origin: authored` |
| `bookmarks`      | ingest, immutable | yes (may be`[]`)      | `w:bookmarkStart` names in the section; MUST be `[]` when `origin: authored` |
| `ingest_version` | ingest            | yes                     | §6.7                                                |
| `generated`      | constant`false` | yes                     | —                                                   |
| `number`         | **fmt**     | yes (may be`""`)      | the heading line                                     |
| `title`          | **fmt**     | yes                     | the heading line                                     |
| `level`          | **fmt**     | yes                     | the heading line's`#` count                        |
| `parent`         | **fmt**     | no — absent at level 1 | the document tree                                    |
| `order`          | **fmt**     | yes                     | the section's 0-based index in document order        |
| `path`           | **fmt**     | yes                     | ancestor heading numbers, root first                 |
| `path_ids`       | **fmt**     | yes                     | ancestor section IDs, root first, ending with`id`  |
| `breadcrumb`     | **fmt**     | yes                     | `doc` + ancestor `number title` pairs            |
| `refs_out`       | **fmt**     | yes (may be`[]`)      | wikilink targets in the body, deduplicated, sorted   |
| `blocks`         | **fmt**     | yes                     | anchor count in the file                             |
| `words`          | **fmt**     | yes                     | §6.6 word count over`to_plain_text` of all blocks |

*Rationale (DEC-12): every `fmt`-owned key restates something the body already states. The agent navigates by `breadcrumb`, so a stale breadcrumb is a navigation error with no warning. One command owns them all, and V15 reports drift.*

**Generated files** — schema `generated` (Appendix A.2). No other keys are permitted:

```yaml
---
generated: true
doc: SYS
kind: index            # index | log | backlinks | coverage
generated_at: "2026-09-21T10:00:00+07:00"
generator: "specctl index 0.1.0"
ingest_version: 1
---
```

### 6.3 Block types and anchor attributes

| Type          | Content shape                                             | `^id` allowed | `locked` default                                        | Type-specific attributes                                       |
| ------------- | --------------------------------------------------------- | --------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| `heading`   | one ATX heading line                                      | no              | `false`                                                 | —                                                             |
| `paragraph` | one Markdown paragraph                                    | yes             | `false`                                                 | —                                                             |
| `list`      | one Markdown list, nesting by indent                      | yes             | `false`                                                 | `ordered:true\|false`                                         |
| `table`     | GFM pipe table or HTML`<table>`                         | yes             | `false`                                                 | `format:pipe\|html` (required)                                |
| `figure`    | image line + italic caption line                          | yes             | **`true`**                                        | `asset:<filename>` (required)                                |
| `formula`   | `$…$` / `$$…$$`, or an image line                   | yes             | `false` for `latex`, **`true`** for `image` | `format:latex\|image`, `asset:` when `image`              |
| `code`      | fenced code block                                         | yes             | `false`                                                 | `lang:<identifier>`                                          |
| `raw`       | verbatim text extracted from an unrepresentable construct | yes             | **`true`**                                        | `fallback:true`, `asset:<filename>.xml`, `reason:<code>` |

Attributes available on **every** type:

| Attribute      | Values               | Meaning                                                                         |
| -------------- | -------------------- | ------------------------------------------------------------------------------- |
| `locked`     | `true` / `false` | Overrides the default. A locked block's content MUST match the base per §12.8 (V05). |
| `supersedes` | comma-separated IDs  | Lineage: this block absorbed those blocks (§5.4).                              |
| `split_from` | one ID               | Lineage: this block was carved out of that block (§5.4).                       |

Example anchors:

```markdown
<!-- id:SYS-000121 type:paragraph -->
<!-- id:SYS-000122 type:table format:pipe -->
<!-- id:SYS-000123 type:figure locked:true asset:SYS-000123.png -->
<!-- id:SYS-000151 type:raw locked:true fallback:true asset:SYS-000151.xml reason:shape_unrenderable -->
<!-- id:SYS-000121 type:paragraph supersedes:SYS-000122 -->
<!-- id:SYS-001205 type:paragraph split_from:SYS-000130 -->
```

### 6.4 Block representation rules

**Total-capture invariant (normative, and the basis of ACC-1 and ACC-2):**

> Every construct in the source document produces **at least one block with an ID** in the vault. When a construct cannot be represented in its intended form, it **degrades** — it never disappears. A degraded construct becomes a `raw` block with `locked:true` and `fallback:true`, carrying the extractable plain text inline and the verbatim OOXML in `assets/<ID>.xml`, accompanied by an issue entry (§8.4) naming the reason. Coverage counts a degraded block as *captured-with-fallback*, never as captured and never as skipped.

| Source construct                  | Markdown representation                                                                                        | Notes                                                                                                           |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Heading                           | `#`×level + rendered number + text + anchor                                                                 | Level from the Word outline level; number from §10.3                                                           |
| Paragraph                         | Plain Markdown; bold, italic and inline code preserved                                                         | Character styles beyond these are dropped and counted as`style_dropped`                                       |
| List (bulleted or numbered)       | One`list` block for the whole list, Markdown list syntax, nesting by indentation                             | Word auto-numbers are rendered as literal numbers (§10.3)                                                      |
| **Simple table**            | GFM pipe table,`format:pipe`                                                                                 | "Simple" = no merged cells, no block-level content in cells, no nested table (§10.6)                           |
| **Complex table**           | HTML`<table>` with `rowspan`/`colspan`, `format:html`                                                  | Cell text verbatim;`<br>` permitted inside a cell                                                             |
| Figure / image                    | `![caption](../assets/<ID>.<ext>)` + italic caption line, `locked:true`                                    | Image extracted from the package                                                                                |
| Shape / text box / SmartArt / OLE | Rendered image as for a figure, plus`assets/<ID>.xml` with the raw OOXML, `locked:true`, `fallback:true` | Text inside a text box is**also** emitted as a `raw` block so it is searchable (§10.12 counts it once) |
| Equation (OMML)                   | `$…$` or `$$…$$` when conversion succeeds; otherwise the image fallback                                  | §10.8. Failures are counted, never dropped                                                                     |
| Footnote                          | Markdown footnote syntax at the end of the section                                                             | Reference in place, definition at file end                                                                      |
| Field REF / internal hyperlink    | Wikilink per §6.5                                                                                             | Resolution in §10.4                                                                                            |
| Tracked insertion (`w:ins`)     | Emitted as ordinary body text                                                                                  | The accepted state (§10.5)                                                                                     |
| Tracked deletion (`w:del`)      | **Discarded**                                                                                            | Counted in`revisions.del_discarded`                                                                           |
| Comment (`w:comment`)           | Discarded; the anchored text is kept                                                                           | Counted                                                                                                         |
| TOC field result                  | Skipped                                                                                                        | `skipped.toc` (§8.3)                                                                                         |
| Header / footer                   | Skipped                                                                                                        | `skipped.header_footer`                                                                                       |
| Content control (`w:sdt`)       | Transparent — its contents are processed in place                                                             | §10.5                                                                                                          |

### 6.5 Cross-reference forms

Resolution maps a bookmark to its enclosing block, and that block to its **owning section**:

| Case                                           | Emitted form                                                                                                                |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Target block**is** its section's heading | `[[<SECTION-ID>\|<display text>]]`                                                                                         |
| Target block is any other block                | `[[<SECTION-ID>#^<lowercase block id>\|<display text>]]`, and the target block acquires a required `^id` marker (FMT-04) |
| External URL                                   | `[<display text>](<url>)`                                                                                                 |
| Unresolvable target                            | The display text as plain text, plus an`unresolved_ref` issue                                                             |

*Rationale: wikilinks resolve by file name, and only section IDs are file names. Emitting `[[SYS-000121]]` for a paragraph produces a link that is dead in Obsidian and fails V07, while being counted as successfully resolved.*

`refs_out` in front matter lists each distinct target exactly as written after the `|` is stripped — `SYS-000245` or `SYS-000301#^sys-000302` — sorted ascending.

### 6.6 Text normalization, plain text and word counts

These three functions have exactly one definition each. Four consumers use them: fidelity measurement (§10.12), the ID registry's `text_hash` and similarity matching (§10.10), the numeric diff (§12.6), and the Excel `Content` column (§13.5).

**`normalize_ws(s)` — case-preserving:**

1. Unicode NFKC.
2. Remove zero-width characters: `U+200B`–`U+200D`, `U+FEFF`, and the soft hyphen `U+00AD`.
3. Replace every run of Unicode whitespace — including `U+00A0`, tab, CR, LF — with a single `U+0020`.
4. Strip leading and trailing spaces.

**`normalize(s)` = `casefold(normalize_ws(s))`.**

> `normalize_ws` MUST be used wherever case carries meaning. Unit symbols do: `mV` and `MV` differ by nine orders of magnitude. The numeric diff (§12.6) therefore uses `normalize_ws`, never `normalize`.

**`to_plain_text(block)`** — one string per block, used for comparison and for export.

It MUST **unescape Markdown** as its final step: a backslash immediately preceding one of
`| * _ [ ] < > ` \` is removed, and `\\` becomes a single backslash. *The writer escapes a literal
`|` inside a pipe-table cell as `\|`. Without unescaping, the source segment `A|B` never matches the
emitted `A\|B`, and a paragraph that was captured perfectly is reported as lost.*


| Type                  | Result                                                                                               |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| `heading`           | `<number> <title>`, anchor removed                                                                 |
| `paragraph`         | The text with emphasis markers removed and each wikilink reduced to its display text                 |
| `list`              | One line per item, each prefixed with its literal marker and indentation                             |
| `table` `pipe`    | One line per data row, cells joined by`" \| "`; the header row included, the separator row excluded |
| `table` `html`    | One line per`<tr>`, cell text joined by `" \| "`, `<br>` replaced by a space, tags stripped     |
| `figure`            | `[FIGURE] <caption>`                                                                               |
| `formula` `latex` | The LaTeX source without the`$` delimiters                                                         |
| `formula` `image` | `[FORMULA] <alt text>`                                                                             |
| `code`              | The code text without the fence lines                                                                |
| `raw`               | The extracted plain text —**not** the OOXML                                                   |

**Word count** (used for `words`, `index.md` and V14):

```
words(s) = count of whitespace-separated tokens containing at least one non-CJK letter or digit
         + ceil( count of CJK characters / 2.5 )
```

CJK characters are those in `U+3040`–`U+30FF`, `U+3400`–`U+4DBF`, `U+4E00`–`U+9FFF`, `U+F900`–`U+FAFF`, `U+FF66`–`U+FF9F`. The divisor 2.5 approximates characters per word and is fixed, not configurable — it exists so the V14 threshold means the same thing in every section.

### 6.7 `ingest_version`

`ingest_version` is an integer recording the serialization contract a file was written against. It is incremented when a change to §6 makes previously written files non-conforming. `specctl validate` MUST report an error naming the required migration when a file's `ingest_version` is lower than the running tool's. The current value is **1**.

---

## 7. `meta/ids.json` — the ID registry

```json
{
  "version": 1,
  "doc_key": "SYS",
  "next": 1205,
  "blocks": {
    "SYS-000121": {
      "key": "SYS-000100/SYS-000120|paragraph|3|9f2a1c8b",
      "status": "active",
      "type": "paragraph",
      "section": "SYS-000120",
      "text_hash": "9f2a1c8b",
      "first_seen": "v0",
      "last_seen": "v1"
    },
    "SYS-000122": {
      "key": "SYS-000100/SYS-000120|paragraph|4|1de99042",
      "status": "merged",
      "merged_into": "SYS-000121",
      "type": "paragraph",
      "section": "SYS-000120",
      "text_hash": "1de99042",
      "first_seen": "v0",
      "last_seen": "v1"
    },
    "SYS-000130": {
      "key": "SYS-000100/SYS-000120|paragraph|5|77c0aa31",
      "status": "split",
      "split_into": ["SYS-001205", "SYS-001206"],
      "type": "paragraph",
      "section": "SYS-000120",
      "text_hash": "77c0aa31",
      "first_seen": "v0",
      "last_seen": "v1"
    }
  }
}
```

### 7.1 The match key

```
key = <ancestor section IDs, root first, "/"-separated> | <type> | <ordinal within section> | <text_hash>
```

- Ancestor section IDs come from the owning section's `path_ids`, which ends with the section's own ID.
- `ordinal within section` is the block's 0-based index among blocks of the **same type** in that section.
- `text_hash` is the first 8 hex characters of SHA-256 over `normalize(to_plain_text(block))`.

> The key MUST be built from ancestor **IDs**, never from heading numbers. Numbers renumber whenever a section is inserted, which would change every key in the subtree below the insertion and re-allocate every ID under it.

### 7.2 Registry rules

| R  | Rule                                                                                                                                    |
| -- | --------------------------------------------------------------------------------------------------------------------------------------- |
| I1 | `next` is monotonic. It is never decremented, and never reset.                                                                        |
| I2 | An entry is never removed from`blocks`. Terminal statuses are how history is kept.                                                    |
| I3 | `first_seen` and `last_seen` record the baseline tag or version label in which the block was first and last observed as `active`. |
| I4 | Entries with a terminal status keep their`key` and `text_hash` as written at the time of transition.                                |
| I5 | The file is serialized with sorted keys and 2-space indentation, so that diffs are readable and re-runs are byte-stable.                |

---

## 8. `meta/coverage.json` — the coverage report

```json
{
  "schema": 1,
  "source": "source/SYS.docx",
  "doc_key": "SYS",
  "ingest_version": 1,
  "generated_at": "2026-09-21T10:00:00+07:00",
  "specctl_version": "0.1.0",
  "counts": {
    "sections": 87,
    "blocks": 1204,
    "paragraphs": 902,
    "lists": 61,
    "tables":   { "total": 48, "pipe": 41, "html": 6, "degraded": 1 },
    "figures":  { "total": 23, "extracted": 23 },
    "shapes":   { "total": 9, "rendered": 8, "raw_only": 1 },
    "formulas": { "total": 12, "latex": 10, "image": 2 },
    "footnotes": 14
  },
  "links": {
    "word_links_found": 134,
    "resolved_section": 96,
    "resolved_block": 34,
    "unresolved": 4,
    "external": 11
  },
  "numbering": { "headings": 87, "resolved": 87, "unresolved": 0,
                 "lists": 61, "lists_resolved": 61 },
  "revisions": { "ins_accepted": 12, "del_discarded": 7, "comments_discarded": 3 },
  "skipped": {
    "toc":            { "paragraphs": 94, "chars": 4211 },
    "header_footer":  { "paragraphs": 6,  "chars": 312 }
  },
  "text_fidelity": {
    "scope": ["body", "footnotes", "textboxes"],
    "source_segments": 3184,
    "segments_covered": 3179,
    "coverage": 0.9984,
    "segments_short": 96,
    "segments_short_covered": 94,
    "coverage_long": 0.9990,
    "added_chars": 4127,
    "added_breakdown": { "heading_numbers": 1204, "list_numbers": 2611, "captions": 312 },
    "uncovered": [
      { "paragraph": 1044, "chars": 218, "reason": "table_parse_failed" }
    ]
  },
  "gates": { "links": "pass", "tables": "pass", "fidelity": "pass" },
  "issues": [
    { "severity": "warn",  "code": "unresolved_ref",     "paragraph": 812,  "detail": "_Ref55012 not found" },
    { "severity": "error", "code": "table_parse_failed", "paragraph": 1044, "detail": "degraded to SYS-000844" }
  ]
}
```

### 8.1 `links`

`word_links_found` counts internal link constructs only — `w:hyperlink` with `w:anchor`, and `REF` fields. External hyperlinks are counted separately in `external` and are not part of the resolution rate. TOC field links are skipped entirely (§8.3) and MUST NOT appear in any of these counts.

*Rationale: a Word TOC expands to a hundred or more bookmark links. Counting them makes the resolution rate mostly a measure of the TOC, and hides the handful of genuinely unresolved cross-references that matter.*

### 8.2 `text_fidelity`

Defined in §10.12. `coverage` is the ACC-2 metric. `added_chars` is reported for information and MUST NOT be netted against anything.

### 8.3 `skipped`

Every deliberate skip is recorded with its own code, a paragraph count and a character total, so that what was dropped on purpose is visible next to what was captured. The codes are fixed: `toc`, `header_footer`. Skipped text is excluded from the fidelity scope.

### 8.4 `issues`

Each entry is `{severity, code, paragraph, detail}` where `severity` is `error`, `warn` or `info`, `code` is from the registry in Appendix B, and `paragraph` is the source paragraph index. `issues` MUST be sorted by paragraph index.

`vault/coverage.md` renders the same data as tables plus the issue list, with `generated: true` front matter.

---

## Part 2 — Components

## 9. Common CLI conventions

### 9.1 Commands

```
specctl ingest SOURCE.docx --doc-key KEY --out DIR [options]   # §10
specctl fmt [PATHS...] [--check]                               # §11
specctl validate [PATHS...] [options]                          # §12   READ-ONLY
specctl assign-ids [PATHS...] [options]                        # §12.4
specctl split-section FILE --at HEADING-ID                     # §12.9
specctl registry sync [--base REF] [--label LABEL]             # §12.10
specctl index                                                  # §13.1
specctl log "message" [options]                                # §13.4
specctl export xlsx --out PATH [options]                       # §13.5
```

### 9.2 Configuration

Settings resolve in this order, first match wins: **command-line flag → environment variable `SPECCTL_<NAME>` → `./specctl.toml` → built-in default.**

```toml
[project]
doc_key        = "SYS"
split_level    = 2
default_branch = "main"
source         = "source/SYS.docx"
vault          = "vault"

[gates]
links    = 95      # percent
tables   = 90      # percent
fidelity = 0.99    # ratio

[validate]
large_section_words = 1500
decimal_comma       = false   # true when the source writes decimals as "1,5" (§12.6)
extra_units         = []      # project-specific unit symbols (Appendix C)

[export]
out        = "exports/SYS.xlsx"
compare_to = "SYS-baseline-v0"
```

**Environment variable names.** `<NAME>` is the setting's **flat name**, uppercased — one
rule, and no ambiguity between sections. The flat name is also what `--verbose` prints and
what the code exposes, so every setting has exactly one spelling throughout the tool.

| Flat name | `specctl.toml` | Environment variable |
| --------- | -------------- | -------------------- |
| `doc_key` | `project.doc_key` | `SPECCTL_DOC_KEY` |
| `split_level` | `project.split_level` | `SPECCTL_SPLIT_LEVEL` |
| `default_branch` | `project.default_branch` | `SPECCTL_DEFAULT_BRANCH` |
| `source` | `project.source` | `SPECCTL_SOURCE` |
| `vault` | `project.vault` | `SPECCTL_VAULT` |
| `gate_links` | `gates.links` | `SPECCTL_GATE_LINKS` |
| `gate_tables` | `gates.tables` | `SPECCTL_GATE_TABLES` |
| `gate_fidelity` | `gates.fidelity` | `SPECCTL_GATE_FIDELITY` |
| `large_section_words` | `validate.large_section_words` | `SPECCTL_LARGE_SECTION_WORDS` |
| `decimal_comma` | `validate.decimal_comma` | `SPECCTL_DECIMAL_COMMA` |
| `extra_units` | `validate.extra_units` | `SPECCTL_EXTRA_UNITS` |
| `export_out` | `export.out` | `SPECCTL_EXPORT_OUT` |
| `export_compare_to` | `export.compare_to` | `SPECCTL_EXPORT_COMPARE_TO` |

A list-valued setting is comma-separated in an environment variable.

**Unknown sections and keys in `specctl.toml` are errors** (exit `4`), never ignored. *A typo
that is silently ignored is precisely how a runbook and the tool it documents drift apart —
the failure DEC-13 exists to prevent.*

`./specctl.toml` means the current directory. There is **no** upward search: the effective
configuration must not depend on where in the tree the operator happened to stand.

`--verbose` MUST print the fully resolved configuration and the source of each value, **to
stderr** — stdout carries the report, and a caller piping `--format json` must get only JSON.

### 9.3 Global flags

| Flag                   | Meaning                                                                                       |
| ---------------------- | --------------------------------------------------------------------------------------------- |
| `--now ISO8601`      | Fixes the clock. Every timestamp written in the run uses it. Required for reproducible tests. |
| `--format text\|json` | Output format where the command produces a report. Default`text`.                           |
| `--verbose`          | Print resolved configuration and per-step progress to stderr.                                 |
| `--version`          | Print the`specctl` version and exit 0.                                                      |

### 9.4 Exit codes

| Code  | Meaning                                                     |
| ----- | ----------------------------------------------------------- |
| `0` | Success, no findings above`info`                          |
| `1` | Warnings only                                               |
| `2` | Errors present, or a coverage gate breached                 |
| `3` | Unrecoverable input error — the source could not be parsed |
| `4` | Usage or configuration error                                |

There is no sixth code. A command that is not built yet exits `4`, naming the feature that
will build it — inventing a code this table does not define would break the pre-commit hook
of §20, which distinguishes only these five.

### 9.5 Cross-cutting invariants

These apply to every command and are individually tested (§18).

| #                             | Invariant                                                                                                                                                                                                                                                 |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Determinism**         | Given the same inputs, configuration and`--now`, every command MUST produce byte-identical output. Every place the implementation sorts, the sort key MUST be total — no reliance on dict or filesystem ordering.                                      |
| **No network**          | `specctl` MUST NOT make any network call. *This is what makes DEC-03 mechanically testable: with no network there is no LLM in the ingest path, whatever the code appears to do.*                                                                     |
| **Atomic writes**       | `ingest` MUST build the vault in a temporary directory and move it into place on success. A crashed or gate-failed run MUST NOT leave a partially written vault. Other commands write each file atomically (write to a sibling temp file, then rename). |
| **Idempotency**         | `fmt`, `index` and `export` MUST be idempotent: running twice changes nothing the second time. `ingest --reingest` is idempotent per §18 T-ING-05.                                                                                               |
| **Source is read-only** | No command may write to`source/`.                                                                                                                                                                                                                       |
| **Read-only commands**  | `validate`, and any command invoked with `--check`, MUST NOT write to any path — not the vault, not `meta/`, not a temp file inside the repository. They are called repeatedly and from the pre-commit hook. The commands that write are `ingest`, `fmt`, `assign-ids`, `split-section`, `registry sync`, `index`, `log` and `export`. |
| **Performance budget**  | On the real document (~1200 blocks, ~90 sections):`ingest` < 60 s, `fmt` < 5 s, `validate` < 5 s, `index` < 5 s, `export` < 20 s. Exceeding a budget is a defect, not a tuning opportunity.                                                     |

---

## 10. `specctl ingest`

### 10.1 CLI

```
specctl ingest SOURCE.docx --doc-key SYS --out vault/ [options]

  --split-level N              heading level that starts a new file (default 2)
  --assets-dir PATH            default <out>/assets
  --render-shapes/--no-render-shapes    LibreOffice rendering (default on)
  --reingest                   reuse meta/ids.json to keep IDs stable (§10.10)
  --fail-under-links PCT       default 95
  --fail-under-tables PCT      default 90
  --fail-under-fidelity RATIO  default 0.99
  --no-gates                   disable all three gates (use on the W1 D1 exploratory run)
  --now ISO8601
  --dry-run                    write only meta/coverage.json and vault/coverage.md
```

Exit codes per §9.4; `2` specifically on a gate breach, with the breached gate named.

> `ingest` MUST NOT invoke git. Committing and tagging are the runbook's job (§20).

### 10.2 Pipeline

1. **Unzip and load** `document.xml`, `styles.xml`, `numbering.xml`, `footnotes.xml`, `endnotes.xml`, `_rels/*`, `media/*`, and the header/footer parts (for the skip accounting only).
2. **Build the block stream** in document order (§10.5). Each raw item records its source paragraph index.
3. **Resolve numbering** for headings and lists (§10.3).
4. **Collect anchors** — bookmarks, hyperlink targets, REF field instructions (§10.4).
5. **Extract media** — images from the package; shapes, text boxes, SmartArt and OLE identified via `w:drawing`, `w:pict`, `mc:AlternateContent`, `w:object`.
6. **Render fallbacks** (§10.7) when `--render-shapes`.
7. **Decide table representation** (§10.6).
8. **Convert equations** (§10.8).
9. **Segment into sections** (§10.9).
10. **Allocate IDs** (§10.10).
11. **Resolve cross-references** into wikilinks (§10.4, §6.5). Unresolved targets become plain text plus an issue.
12. **Measure fidelity** (§10.12), evaluate gates, then **serialize** the vault, assets, `meta/ids.json`, `meta/coverage.json` and the generated files (§13) — atomically, per §9.5.

### 10.3 Numbering resolution

Heading and list numbers are computed from `numbering.xml` plus style outline levels, by maintaining a counter per `(numId, ilvl)`.

```
counters := {}                       # (numId, ilvl) -> int
for item in block_stream:
    numPr := effective numbering properties of item
             (direct w:numPr, else the paragraph style chain, else none)
    if numPr is none:
        item.number := ""            # unnumbered heading or plain paragraph
        continue
    (numId, ilvl) := numPr
    abstract := abstract numbering definition for numId
    lvl      := abstract.levels[ilvl]

    if lvl.numFmt == "none":
        item.number := ""
    else:
        counters[(numId, ilvl)] := counters.get((numId, ilvl), lvl.start - 1) + 1
        for deeper in ilvl+1 .. 8:                 # a level restarts its descendants
            counters.pop((numId, deeper), None)
        item.number := render(lvl.lvlText, counters, numId, abstract)

    if item.number == "" and item is a heading:
        record issue: numbering_unresolved at item.paragraph
```

`render()` substitutes `%1`…`%9` in `lvlText` with the counters of levels 0…8 of the same `numId`, each formatted per that level's `numFmt` (`decimal`, `upperRoman`, `lowerLetter`, `bullet`, …). `lvlRestart` and `startOverride` MUST be honoured.

Failure is never fatal: an unresolvable number yields an empty number, the text is emitted unchanged, and `numbering.unresolved` is incremented. If more than 10% of headings are unresolved, `ingest` SHOULD additionally emit a `warn` issue recommending the LibreOffice-rendered fallback described in §21.

### 10.4 Anchors and cross-references

Collect, in one pass over the block stream:

- **Bookmarks** — `w:bookmarkStart/@w:name`, mapped to the enclosing block. Names beginning `_Toc` that fall inside a TOC field are skipped with the field (§10.5).
- **Hyperlinks** — `w:hyperlink/@w:anchor` (internal) and `@r:id` → the relationship target (external).
- **REF fields** — `w:instrText` containing `REF <bookmark>`; the display text is the rendered field result (the runs between `separate` and `end`).

Resolution then follows §6.5. A target bookmark that is unknown, or that resolves to a skipped construct, produces plain display text and an `unresolved_ref` issue carrying the bookmark name and paragraph index.

Textual references without a field — "see section 3.2" — are **not** resolved in this phase. Each is recorded as an `info` issue with code `textual_ref_candidate` and the matched string.

### 10.5 Block-stream walking

This step is where content is silently lost if it is written casually. The walker is defined recursively and MUST descend into containers it does not recognise.

```
def walk(node, ctx):
    for child in node.children:
        if child is w:p or w:tbl:
            if ctx.in_toc_field or ctx.in_deletion:
                account_skip(child); continue
            emit(child, ctx)

        elif child is w:sdt:                       # content control
            walk(child.find(w:sdtContent), ctx)    # transparent

        elif child is mc:AlternateContent:
            walk(child.find(mc:Choice) or child.find(mc:Fallback), ctx)

        elif child is w:ins:                       # accepted insertion
            walk(child, ctx)

        elif child is w:del:                       # rejected/pending deletion
            count_revision("del_discarded", child)
            # NOT walked: its w:delText is not current content

        elif child is w:smartTag or child is w:customXml:
            walk(child, ctx)

        elif child contains any w:p or w:tbl descendant:
            record_issue(info, "unknown_container", child.tag)
            walk(child, ctx)                       # degrade to captured-with-a-note

        else:
            handle_leaf(child, ctx)
```

| R  | Rule                                                                                                                                                                                       |
| -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| W1 | Content inside`w:ins` is current content and MUST be emitted. Content inside `w:del`/`w:delText` MUST be discarded. Both are counted in `revisions`.                               |
| W2 | If`revisions.ins_accepted + revisions.del_discarded > 0`, emit a `warn` issue `source_has_unresolved_revisions` — the source should be reviewed before it is treated as a baseline. |
| W3 | Comments (`w:commentRangeStart`/`End`, `w:commentReference`) are discarded; the text they annotate is kept. Counted.                                                                 |
| W4 | A TOC field —`w:fldSimple` or an `w:instrText` field whose instruction begins `TOC`, and paragraphs styled `TOC \d+` — is skipped in full and accounted under `skipped.toc`.   |
| W5 | Headers, footers, endnote separators and the document background are skipped and accounted under`skipped.header_footer`.                                                                 |
| W6 | An unrecognised element that contains paragraphs or tables MUST be descended into, and recorded once as`unknown_container`. Never dropped.                                               |

*Rationale for W1: a walker that simply collects `w:t` descendants emits deleted text as current requirement text. In a contractual document that is content fabrication arrived at by parsing rather than by hallucination — the failure DEC-03 exists to prevent.*

> **The shape W1 applies to.** `w:ins` and `w:del` are **run-level** elements: Word writes
> them inside `w:p`, wrapping runs, and records an inserted or deleted paragraph *mark*
> separately as `w:ins`/`w:del` inside `w:pPr/w:rPr`. A whole `w:p` wrapped in a `w:ins` is
> well-formed XML that `lxml` reads and an `//w:ins` check accepts, and schema-following
> readers discard it without a word. The fixture builder emitted exactly that shape until an
> independent reader was pointed at it; the walker MUST handle the run-level form, and
> `tests/support/fixtures.py` requires the fixtures to be in it.
>
> It follows that a paragraph a reviewer inserted once carries **two** `w:ins` elements. The
> counters of W2 count content revisions, so a revision on the paragraph mark is counted only
> when no content revision of that kind was found in the same paragraph — otherwise every
> inserted paragraph in the source would be reported twice and the number would say nothing
> about how dirty the document is. A paragraph split or merged with no text changed is a real
> unresolved revision and is still counted, which is why the mark is not simply ignored.

### 10.6 Table representation

A table is **simple** — and therefore a pipe table — if and only if all of:

- no cell carries `w:gridSpan` or `w:vMerge`;
- every cell contains exactly one paragraph and no nested table, list, image or equation;
- no cell's text contains a newline after normalization;
- the row widths are uniform.

Otherwise it is **complex** and is serialized as HTML with `rowspan`/`colspan`, `format:html`, cell text verbatim, `<br>` permitted for in-cell line breaks.

If serialization fails in either branch, the table degrades per the total-capture invariant: a `raw locked fallback` block with `reason:table_parse_failed`, the cell text in document order as its plain text, the OOXML in `assets/<ID>.xml`, and an `error` issue. `counts.tables.degraded` is incremented. Degraded tables count against the ACC-4 gate.

### 10.7 Media, shapes and fallback rendering

Images referenced by `w:drawing`/`a:blip` are extracted from the package directly and written to `assets/<ID>.<ext>`.

Shapes, text boxes, SmartArt and OLE objects have no extractable bitmap. When `--render-shapes` is on:

1. **Primary path.** Convert the document once with `soffice --headless --convert-to html`. LibreOffice writes one image file per drawn object, in document order. Match them to the unrenderable objects of the block stream **by order of appearance**, which the walker already knows — no page-layout reasoning is involved.
2. **Fallback.** If the counts do not match, or LibreOffice is unavailable, render the page containing the object to a whole-page PNG and reference that.
3. **Always**, in both paths, write the verbatim OOXML to `assets/<ID>.xml` and emit the object as a `figure` block plus a `raw locked fallback` block carrying any text extracted from inside it.

`counts.shapes.rendered` and `counts.shapes.raw_only` record the split. If neither path produces an image, the object still yields the `raw` block — the invariant holds.

> §21 schedules the LibreOffice behaviour as a **W1 D1 spike**. It is a binary question — does LibreOffice emit one image per drawn object on the real file — answerable in an hour, and the fallback is already specified, so the spike cannot block the schedule.

### 10.8 Equations

OMML is converted in-process:

1. Apply the `OMML2MML.XSL` stylesheet (vendored into `specctl/ingest/xsl/`) to obtain MathML.
2. Convert MathML to LaTeX with a pure-Python converter.
3. On success emit a `formula` block with `format:latex`; inline if the equation is inline, display (`$$`) if it is its own paragraph.
4. On failure emit `format:image` with the rendered fallback of §10.7, and record a `formula_conversion_failed` issue.

`counts.formulas.{latex,image}` record the split. Pandoc is not used.

### 10.9 Segmentation

- Headings at levels `1 .. split_level` each start a new section file.
- Headings deeper than `split_level` stay inside the current file as ordinary `heading` blocks.
- Content appearing **before the first heading** — cover page, document control, scope statement, revision history — is collected into a synthetic front-matter section that takes the first allocated ID, with `number: ""`, **`level: 1`**, `title` from the document's title property (falling back to `"Front matter"`), and `generated: false`. Its heading block is a real ATX line — `# Front matter <!-- id:… type:heading -->` — with no number, since FMT-05 puts the rendered number on the heading line and this section has none. It is an ordinary editable section in every other respect.

*Rationale: `level: 0` cannot be written down. §6.1 gives a heading line one to six `#`
characters, so a level-0 section has no representable heading line: it could be built in
memory and never read back from disk. Level 0 also made the preamble the **ancestor** of
every numbered chapter, prefixing every breadcrumb in the vault with `Front matter >` —
the revision history is not chapter 3's parent. At level 1 it is a sibling of chapter 1,
which is what it is.*

*Rationale: an ASPICE SYS spec always carries a revision history before its first numbered heading. It is contractual content, and without this rule it has no file to live in.*

### 10.10 ID allocation and re-ingest matching

On a first ingest, IDs are allocated sequentially in document order (§5.2).

On `--reingest`, blocks are matched against `meta/ids.json` **per section**, as a single global assignment pass — never first-match:

```
for each section S (in document order):
    old := registry entries with status=active and section == S.id
    new := blocks parsed for S

    candidates := []
    for o in old, for n in new:
        if o.type != n.type: continue
        tier := 1 if o.key == key(n)                                  # exact key
             else 2 if o.path_ids == n.path_ids and o.text_hash == hash(n)
             else 3 if o.path_ids == n.path_ids and o.ordinal == n.ordinal
                       and similarity(o.text, n.text) >= 0.85
             else none
        if tier: candidates.append((tier, -similarity, o.ordinal, n.ordinal, o, n))

    sort candidates ascending            # tier, then best similarity, then document order
    for (.., o, n) in candidates:
        if o unused and n unused: assign n.id := o.id; mark both used

    for n in new not assigned:  n.id := allocate()          # new block
    for o in old not assigned:  o.status := "deleted"       # disappeared
```

| R  | Rule                                                                                                                                                                                                                       |
| -- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1 | The candidate sort key MUST be total.`(tier, -similarity, old_ordinal, new_ordinal)` is total because ordinals are unique within a section and type.                                                                     |
| M2 | Each old ID and each new block is consumed at most once.*Without this, two near-identical boilerplate paragraphs — which specs are full of — can be matched to each other's IDs, silently transposing their history.*  |
| M3 | `similarity` is `rapidfuzz.fuzz.ratio` over `normalize(to_plain_text(block))`, scaled to 0–1. The 0.85 threshold is fixed.                                                                                          |
| M4 | A section whose own heading block fails to match is matched by tier 3 against the previous ingest's heading at the same`path_ids` prefix and ordinal, so that renaming a heading keeps the section ID and its file name. |
| M5 | `ingest --reingest` MUST print a summary: matched, new, deleted, and the count of blocks whose section changed.                                                                                                          |

### 10.11 Serialization

The writer emits, for each section, in this order: front matter (§6.2, keys in the order listed there), a blank line, the heading block, then each remaining block separated by exactly one blank line, each preceded (or, for the heading, followed) by its anchor per FMT-02, with a `^id` marker where FMT-04 requires one. YAML is written as follows, which is what the worked front matter of §6.2 and Appendix D
show character for character:

| Value | Style |
| ----- | ----- |
| The front matter as a whole | Block style, one key per line, in §6.2's order |
| A sequence of scalars —`path`, `path_ids`, `bookmarks`, `refs_out` | **Flow** style: `["3", "3.2"]`. Empty is `[]` |
| A string **inside** a flow sequence | Always double-quoted. Inside brackets the quotes cost nothing and remove every ambiguity |
| `source` | Flow mapping:`{ docx: "source/SYS.docx", paragraphs: [412, 447] }`, or `null` when `origin: authored` |
| A top-level scalar | Plain when it is unmistakably a string; **double-quoted** otherwise — `number: "3.2"` in particular |

A top-level scalar is written plain only when it matches `^[A-Za-z0-9][A-Za-z0-9 _-]*$`
and is not a value a YAML reader might take for a number, a boolean or null. The second
test is applied against **both** YAML 1.1 and YAML 1.2 spellings, not just the one the
writer's own parser implements: `1e5` is the string `"1e5"` to a YAML 1.1 reader and the
float `100000.0` to a YAML 1.2 one, and the vault is read by Obsidian and by editors as
well as by `specctl`. Over-quoting is always safe; being read differently by the viewer
than by the validator is a silent disagreement about what the spec says.

`parent` is **omitted entirely** when absent (§6.2), never written as `null`.

### 10.12 Fidelity measurement

The metric answers one question: **what fraction of the source text can be found in the vault?**

```
# 1. Source side — independent of the writer, read straight from OOXML
source_segments := []
for p in every paragraph and table cell in scope:          # scope = body, footnotes, textboxes
    if p was skipped (TOC, header/footer) or discarded (w:del): continue
    s := normalize(text_of(p))
    if s != "": source_segments.append(s)

# 2. Emitted side — one haystack per section, built from the written files
haystack := {}
for section in vault:
    haystack[section.id] := normalize(" ".join(to_plain_text(b) for b in section.blocks))

# 3. Directional coverage
covered := 0
for seg in source_segments:
    if len(seg) >= 12:
        hit := any(seg in haystack[sid] for sid in candidate_sections(seg))
    else:
        # short segments: owning section only, and only at a token boundary
        hit := token_bounded_find(seg, haystack[owning_section(seg)])
    if hit: covered += 1
    else:   uncovered.append({paragraph, chars: len(seg), reason})

coverage := covered / len(source_segments)

# 4. Additions, reported separately and never netted
added_chars := sum of characters the writer introduced:
               rendered heading numbers, literal list numbers, figure captions
```

| R  | Rule                                                                                                                                                                                                                                                 |
| -- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1 | Coverage is**directional**. Text the writer adds cannot raise it. *A net character ratio scores 1.00 on a vault that dropped 1% of paragraphs and added 1% of numbering, and can exceed 1 — at which point it is not interpretable at all.* |
| F2 | Scope is exactly`body`, `footnotes`, `textboxes`. Headers, footers and TOC results are out of scope and are accounted in `skipped`.                                                                                                          |
| F3 | The source side is computed against the**accepted revision state** (§10.5 W1), so a discarded `w:del` run is never counted as uncovered.                                                                                                    |
| F4 | Text emitted twice — a text box appears both in its rendered block and in its`raw` block — counts once on the source side and contributes nothing extra to coverage. **On the source side this has to be constructed, not assumed.** A text box's paragraphs are nested *inside* the paragraph that anchors it, and Word writes the box twice — DrawingML under `mc:Choice`, VML under `mc:Fallback`. Step 1's loop over paragraphs therefore MUST take one branch only (`mc:Choice`, else `mc:Fallback`) and MUST exclude `w:txbxContent` text from the anchoring paragraph's own text. A plain join over `w:t` descendants yields the sentence three times, and the third is the two branches concatenated — a string no writer can emit, so it counts as uncovered for ever and depresses ACC-2 by roughly one segment per text box. |
| F5 | Every uncovered segment MUST be listed in`text_fidelity.uncovered` with its paragraph index, character count and reason. A failing number must be actionable, not merely low.                                                                      |
| F6 | `coverage` is the ACC-2 metric and the `--fail-under-fidelity` gate.                                                                                                                                                                             |
| F7 | **`candidate_sections(seg)`** is: the section owning the source paragraph `seg` came from, then that section's parent, then its children, then every remaining section in document order. The segmenter (§10.9) already assigned every source paragraph to a section, so `owning_section` is a lookup, not a search. The order exists to make the first hit deterministic and the scan cheap; for a long segment every section is eligible. |
| F8 | A segment whose `normalize`d form is **shorter than 12 characters** is matched **only inside its owning section**, and only where the match is delimited by a non-alphanumeric character or a string boundary on both sides. *Under plain substring containment vault-wide, `"Yes"`, `"N/A"`, `"1"` and `"OK"` match somewhere by accident, and coverage rises with the size of the vault rather than with what was captured.* The threshold is 12 characters and is **fixed**, not configurable — like the CJK divisor of §6.6, it exists so the ACC-2 number means the same thing in every run. |
| F9 | `text_fidelity` MUST report `segments_short`, `segments_short_covered` and `coverage_long` alongside `coverage`. The gate stays on `coverage` over all segments; the breakdown is what makes a passing number auditable. |

---

## 11. `specctl fmt`

### 11.1 CLI

```
specctl fmt [PATHS...] [--check] [--format text|json]
```

With no paths, every section file in the vault. `--check` reports without writing and exits `1` if anything would change. Exit `0` clean, `1` changes needed or made, `2` a file could not be parsed.

### 11.2 Responsibilities

`fmt` owns everything derived. It MUST NOT change authored content — body text, authored front-matter keys (§6.2), or lineage attributes.

| # | Action                                                                                                           |
| - | ---------------------------------------------------------------------------------------------------------------- |
| 1 | Recompute every`fmt`-owned front-matter key from the file bodies and the document tree (§6.2 ownership table) |
| 2 | Add required`^id` markers and remove orphaned ones (FMT-04)                                                    |
| 3 | Normalize anchor attribute order (FMT-12)                                                                        |
| 4 | Enforce FMT-09 formatting: UTF-8 without BOM, LF, no trailing whitespace, no stray tabs                          |
| 5 | Enforce FMT-06 blank-line separation and the single trailing`LF`                                               |
| 6 | Rewrite front matter with keys in the §6.2 order                                                                |

`fmt` is idempotent (§9.5) and MUST be run before `validate` in the edit workflow (§16), so that derived drift never presents as a content finding.

### 11.3 Document-tree computation

`parent`, `order`, `path`, `path_ids` and `breadcrumb` require the whole vault, not one file. `fmt` therefore always loads every section file, builds the tree from `level` and document `order`, and then writes only the files that change.

The tree is built by reading each section's heading level and sorting sections by their existing `order`; a section whose `order` is absent or duplicated is placed after its predecessors in file-name order, and an `info` finding is reported.

---

## 12. `specctl validate`

### 12.1 CLI

```
specctl validate [PATHS...] [options]

  --base REF          git ref to compare against (see §12.2)
  --allow-delete      permit blocks to disappear without lineage
  --format text|json
```

Exit `0` clean, `1` warnings only, `2` any error.

> **`validate` writes nothing.** Not a section file, not `meta/ids.json`, not a temp file inside the
> vault. It is called repeatedly, and from the pre-commit hook, so a side effect would mean two runs
> on the same tree disagree. The two operations that *do* write — allocating IDs for new blocks, and
> recording terminal statuses in the registry — are separate commands (§12.4, §12.10).
> *This is the one rule in §12 that no flag may override.*

### 12.2 Base resolution

`--base` defaults to **`merge-base(HEAD, <default_branch>)`** — the point the current branch diverged. On the default branch itself it defaults to `HEAD`. The resolved ref and its short SHA MUST be printed in the summary line.

*Rationale: with `HEAD` as the default, running `validate` on an edit branch after committing compares the working tree against your own edits, and every comparison rule — V04, V05, V10, V12 — silently reports clean.*

### 12.3 Rules

| ID   | Severity                                      | Auto-fix         | Rule                                                                                                                                                               |
| ---- | --------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| V01  | error                                         | —               | Front matter parses and validates against the schema for its file class;`id` matches the file name                                                               |
| V02  | error                                         | —               | Every block has exactly one anchor; anchor syntax and attributes are valid for the block's type (§6.3)                                                            |
| V03  | error                                         | —               | No duplicate block ID anywhere in the vault                                                                                                                        |
| V04  | error                                         | —               | No ID present in`--base` has vanished without lineage (§12.5)                                                                                                   |
| V04a | error                                         | —               | A lineage attribute names an ID that does not exist in`--base`                                                                                                   |
| V04b | error                                         | —               | Two blocks name the same`supersedes` target. Never applicable to `split_from` (§5.4 L2)                                                                        |
| V05  | error                                         | —               | `locked:true` blocks match `--base` per §12.8                                                                                                                  |
| V06  | error                                         | —               | Pipe tables have a consistent column count; HTML tables parse and are well-formed                                                                                  |
| V07  | error                                         | —               | Wikilink targets exist: the section file for`[[ID]]`, and additionally the `^id` marker for `[[ID#^blockid]]`                                                |
| V08  | error                                         | —               | Every asset referenced by a`figure`, `formula` or `raw` block exists on disk                                                                                 |
| V09  | warn                                          | `fmt`          | Front-matter`blocks` count disagrees with the anchor count                                                                                                       |
| V10  | **warn — always reported prominently** | —               | A numeric value or unit changed inside a block (§12.6)                                                                                                            |
| V11  | warn                                          | `assign-ids` | A block has no anchor                                                                                                                                                |
| V12  | warn                                          | —               | Heading`level` or `number` changed relative to `--base`                                                                                                      |
| V13  | error / warn                                  | `fmt`          | **error** when a block that is a wikilink target lacks its required `^id` marker; **warn** when a marker is present but inconsistent with its anchor |
| V14  | info                                          | —               | Section exceeds`validate.large_section_words` (default 1500) — a candidate for splitting when next edited                                                       |
| V15  | warn                                          | `fmt`          | Derived front matter disagrees with the body or the document tree (§6.2)                                                                                          |
| V16  | warn                                          | `fmt`          | FMT-09 / FMT-06 formatting violation                                                                                                                               |
| V17  | error                                         | —               | A file's`ingest_version` is lower than the running tool's (§6.7)                                                                                                |

### 12.4 `specctl assign-ids`

```
specctl assign-ids [PATHS...] [--label LABEL] [--format text|json]
```

Allocates an ID to every **anchorless** block and writes its anchor. It MUST leave every other byte
of every file unchanged, and it MUST NOT create, move, rename or delete any file. Every allocation
increments `meta/ids.json.next` and writes a registry entry with `status: active` and `first_seen`
set to `--label` (default: the most recent baseline tag reachable from `HEAD`).

An anchorless **heading** at a level ≤ `split_level` gets its ID like any other block, plus an
`info` finding naming `specctl split-section` as the next step. `assign-ids` does **not** move the
content into a new file.

*Rationale: "leave every other byte unchanged" and "move this content into a different file" cannot
both be guarantees of one command. Separating them is what makes the byte-stability guarantee
testable (T-VAL-07), and file creation reviewable on its own.*

### 12.5 V04 — lineage-aware deletion check

```
base_ids    := active IDs in --base
working_ids := IDs present in the working tree
superseded  := multiset of IDs named in a supersedes: attribute in the working tree
split_srcs  := set of IDs named in a split_from: attribute in the working tree
claimed     := superseded ∪ split_srcs        # accounted for by lineage, either way

for id in base_ids - working_ids:
    if id in claimed:
        continue                                  # lineage accounts for it
    if --allow-delete:
        record info "block deleted (accepted)"        # registry updated later, by §12.10
    else:
        record V04 error "block deleted (declare lineage, or use --allow-delete)"

for id in claimed - base_ids:                     record V04a error
for id in superseded with multiplicity > 1:       record V04b error
# split_srcs is deliberately exempt: a split into N parts names its source N times (§5.4 L2)
```

V04 only **reports**. Turning these findings into registry state — `merged` with `merged_into`,
`split` with `split_into` listing every part, `deleted` for an accepted deletion — is the job of
`specctl registry sync` (§12.10), which runs after the commit.

*Rationale (DEC-10): without this clause the only way to merge two paragraphs is `--allow-delete`, which switches off deletion protection for the entire run — including the accidental deletions V04 exists to catch.*

### 12.6 V10 — numeric and unit change detection

V10 is the design's primary defence against an agent silently altering a value. It is defined precisely because a vague version is either noisy enough to be ignored or quiet enough to be useless.

**Token grammar.** A numeric token is:

```
number  = [ "+" | "-" | "±" ] , digit , { digit | "," | "." } , [ ( "e" | "E" ) , [ "+" | "-" ] , digit , { digit } ] ;
token   = number , [ [ SP ] , unit ] ;
range   = token , ( "–" | "—" | "-" ) , token ;        (* yields two tokens, both flagged range *)
```

`unit` is a symbol from the vocabulary in Appendix C, matched **case-sensitively** against `normalize_ws` text (§6.6).

**Boundaries.** The grammar alone matches the `2` in `Sig2`. Two boundary rules are therefore
normative, and are applied before anything else:

| Rule | Effect |
|---|---|
| A `number` MUST be preceded by start-of-string, whitespace, or one of `( [ { < " ' = : ; / – — -`. A digit directly preceded by a letter, digit, `_`, `#`, `$` or `%` never starts a token | `Sig2`, `CAN_2`, `A1`, `P0` yield nothing |
| A `number` MUST be followed by end-of-string, whitespace, a unit, or one of `) ] } > " ' . , ; : ? ! / – — -`. A trailing `.` or `,` counts only when itself followed by whitespace or end-of-string — otherwise it belongs to the number | `50 ms.` at a sentence end yields `50 ms`, not `50.` |

**Unit adjacency.** When a number is followed with **no space** by one or more letters:

- letters in the vocabulary → that unit. `50ms` is `(50, "ms")`, identical to `50 ms`.
- letters not in the vocabulary → **the whole token is excluded.** `1F`, `2x`, `3rd`, `4th` yield nothing.

With a space, a trailing word not in the vocabulary is not a unit, and the number is still extracted
with `unit: null` — `50 widgets` is `(50, null)`.

**Radix prefixes.** A token matching `0[xXbBoO][0-9A-Fa-f_]+` is excluded entirely. `0x1F` is an
address or a mask, never a measurement, and reading it as the number `0` would report a change
every time a hex literal was reformatted.

**Decimal separator.** `1,5` and `1,234` cannot both be read the same way, so the rule is explicit:

| Input | Reading | Why |
|---|---|---|
| `1,234`, `12,345,678` | thousands separator → `1234`, `12345678` | Matches `\d{1,3}(,\d{3})+` exactly |
| `1,5`, `1,23`, `1,2345` | decimal separator → `1.5`, `1.23`, `1.2345` | The comma is not followed by exactly three digits |
| `1,234.5` | comma thousands, dot decimal → `1234.5` | Both present: the **last** separator is the decimal one |
| `1.234,5` | dot thousands, comma decimal → `1234.5` | Same rule |

If the source document writes decimals with commas throughout, set `[validate] decimal_comma = true`
in `specctl.toml`; the comma then always reads as the decimal separator and the dot as thousands.
Declared once, per DEC-13 — never guessed per token.

**Exclusions.** These are never numeric tokens:

| Excluded                                                                                                         | Reason                    |
| ---------------------------------------------------------------------------------------------------------------- | ------------------------- |
| Anything matching`[A-Z][A-Z0-9]{1,7}-[0-9]{6}`                                                                 | Block IDs                 |
| Text inside a wikilink target (before the`\|`)                                                                  | Link plumbing             |
| Anything on a heading line                                                                                       | Section numbers           |
| `\d+(\.\d+)+` preceded by `section`, `clause`, `§`, `Figure`, `Table`, `Annex` (case-insensitive) | Cross-reference numbering |
| Text inside a fenced`code` block                                                                               | Code, not requirements    |

**Comparison.** Per block, build the **multiset** of `(value, unit)` pairs — value normalized by stripping thousands separators and parsing to a decimal — for the base text and the working text, then report the symmetric difference:

```
removed := base_multiset - working_multiset
added   := working_multiset - base_multiset

if removed is empty and added is empty:     no finding
elif len(removed) == 1 and len(added) == 1: report `V10  <id>  number changed: "<old>" -> "<new>"`
else:                                       report `V10  <id>  numbers removed: [...]  added: [...]`
```

| R  | Rule                                                                                                                                                                                                                      |
| -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| N1 | The comparison is a multiset difference, never a positional alignment. It is therefore invariant under reordering and rewriting — which matters, because a restructure is exactly when a value could be slipped through. |
| N2 | The`old -> new` arrow form is emitted **only** on an unambiguous one-for-one substitution. In every other case both lists are printed.                                                                            |
| N3 | Unit comparison is case-sensitive (`mV` ≠ `MV`), so V10 uses `normalize_ws`, never `normalize`.                                                                                                                  |
| N4 | Lineage **groups** blocks before comparing; a part of a split is never compared on its own. A merge compares the survivor against the union of its `supersedes` targets' base text. A split compares the union of **every** block naming `split_from:X` against `X`'s base text, as **one** finding reported against `X`. A new block with no lineage has an empty base multiset. *Since §5.4 L3 gives every part of a split a new ID, comparing each part separately would report every value that landed in a sibling as removed — a false alarm on every split, which is the operation Problem B performs most.* |
| N5 | The same routine produces the`Numeric change` column of the Excel export (§13.5). One implementation, two consumers.                                                                                                   |

### 12.7 Output

```
SYS-000120.md
  V10  warn   SYS-000121  number changed: "50 ms" -> "80 ms"
  V05  error  SYS-000123  locked figure block modified
  V04  error  SYS-000129  block deleted (declare lineage, or use --allow-delete)
  V07  error  SYS-000131  wikilink target SYS-000999 does not exist

Summary: 3 errors, 1 warning, 2 files checked, base=merge-base(HEAD,main)=a1b2c3d
Affected by inbound references: SYS-000245, SYS-000301 (see backlinks.md)
```

JSON output is an object `{base, base_sha, files_checked, findings: [...], summary: {...}}` where each finding is `{file, rule, severity, block_id, message, old, new}`. `old` and `new` are `null` unless the rule produced a pair.

The "Affected by inbound references" line lists every block outside the changed files that links **into** a changed block, read from `backlinks.md`. It is informational and does not affect the exit code.

### 12.8 V05 — how a locked block is compared

"Byte-identical" cannot be taken literally, because FMT-12 lets `specctl fmt` normalize anchor
attribute order, and `fmt` runs before `validate` in every workflow. A literal byte comparison would
therefore fail on a locked block that nobody touched.

V05 compares two things, and nothing else:

| Part | Comparison |
|---|---|
| The block's **content lines** — every line after the anchor, up to but excluding the `^id` marker | Byte-for-byte |
| The anchor's **attributes** | As an unordered mapping of key to value. Order is irrelevant; a changed, added or removed key or value is a V05 error |

The anchor **line** is never byte-compared, and the `^id` marker is excluded entirely — it is derived
and `fmt` owns it (FMT-04).

*Rationale: V05 exists to catch a changed figure caption or a rewritten fallback. It does not exist
to catch attribute reordering, which is exactly what the formatter is supposed to do.*

### 12.9 `specctl split-section`

```
specctl split-section FILE --at HEADING-ID [--format text|json]
```

The file-creating half of §5.5. `HEADING-ID` names a heading block inside `FILE` at a level
≤ `split_level`, which already has an ID (allocated by `assign-ids`). The command:

1. creates `vault/sections/<HEADING-ID>.md`;
2. moves the heading block and every block up to the next heading at a level ≤ its own into it;
3. writes that file's authored front matter — `id`, `doc`, `origin: authored`, `source: null`,
   `bookmarks: []`, `ingest_version`, `generated: false`;
4. removes the moved content from `FILE`;
5. leaves **every derived key, in both files and in every other section, to `specctl fmt`**.

It writes no derived front matter of its own. Run `specctl fmt` immediately after.

### 12.10 `specctl registry sync`

```
specctl registry sync [--base REF] [--label LABEL] [--format text|json]
```

The only command that writes terminal statuses into `meta/ids.json`. It runs **after** the commit,
because `last_seen` and the Excel rationale join both need a commit that exists.

Reading the working tree and `--base` (resolved as in §12.2), it writes:

| Registry change | Trigger |
|---|---|
| `merged`, with `merged_into` | The ID is named by exactly one `supersedes:` attribute |
| `split`, with `split_into` listing **every** part | The ID is named by one or more `split_from:` attributes |
| `deleted` | The ID is in `--base`, absent from the working tree, and named by no lineage attribute |
| `last_seen := LABEL` | Every ID still `active` |

It MUST refuse to run — exit `2`, writing nothing — if `specctl validate` would report any error on
the same tree. *A registry built from a tree with a duplicate ID or a dangling lineage target records
the wrong history permanently, and I2 says entries are never removed.*

`--label` defaults to the most recent baseline tag reachable from `HEAD`.

---

## 13. Generators and the exporter

### 13.1 `specctl index`

```
specctl index [--check]
```

Regenerates `vault/index.md`, `vault/backlinks.md` and `vault/coverage.md`. It MUST NOT touch `log.md`, which is append-only. `--check` exits `1` if any would change. Idempotent.

### 13.2 `vault/index.md`

Front matter `generated: true`, `kind: index`. Body: a nested list of all sections in document order — number, title, wikilink, ID, block count, word count.

```markdown
- 3 Braking system — [[SYS-000100]] · `SYS-000100` · 4 blocks · 180 words
  - 3.2 Braking control — [[SYS-000120]] · `SYS-000120` · 9 blocks · 412 words
```

This is the agent's **primary map**. It MUST stay small — target under 40 KB — and MUST be regenerated after every commit. If it exceeds 40 KB, emit a `warn` recommending a deeper `split_level` on the next re-ingest.

### 13.3 `vault/backlinks.md`

For every ID that is a link target: the ID, its owning section, and the list of blocks referencing it, generated by scanning wikilinks across the vault. It MUST be the exact inverse of the outbound links (T-IDX-02). Sorted by target ID, then by source ID.

### 13.4 `vault/log.md` and `specctl log`

```
specctl log "message" [--section ID] [--skill NAME] [--model NAME] [--now ISO8601]
```

Appends one row to an append-only table. `log.md` is `generated: true` but is **never regenerated** — `specctl index` MUST NOT rewrite it.

```
| 2026-09-24T14:12+07:00 | a1b2c3d | SYS-000120 | restructure-section | claude-opus-5 | split step 3 into two steps for clarity | mod=5 new=1 del=0 merged=1 split=0 | numeric: none |
```

Columns: timestamp, short SHA, section ID, skill, model, rationale, block counts, numeric-change summary. The counts and the numeric summary are taken from the `validate --format json` output of the run being logged.

### 13.5 `specctl export xlsx`

```
specctl export xlsx --out exports/SYS.xlsx [--ref HEAD] [--compare-to SYS-baseline-v0]
```

**Sheet "Spec"** — one row per block, ordered by `(section.order, block index in file)`:

| Column      | Content                                                                                                              |
| ----------- | -------------------------------------------------------------------------------------------------------------------- |
| ID          | Block ID                                                                                                             |
| Section     | Section number (`3.2`)                                                                                             |
| Breadcrumb  | Full path                                                                                                            |
| Level       | Heading level of the owning section                                                                                  |
| Order       | Global block index — the position of`(section.order, block index)` in the sorted sequence over the whole vault    |
| Type        | Block type                                                                                                           |
| Content     | `to_plain_text(block)` (§6.6)                                                                                     |
| Change      | `unchanged` / `modified` / `new` / `deleted` / `merged` / `split` — only when `--compare-to` is given |
| Old content | Previous text when`modified`, `deleted`, `merged` or `split`                                                 |
| Rationale   | From`log.md` (§13.6)                                                                                              |
| Commit      | Short SHA                                                                                                            |

**Sheet "Changes"** — only rows where `Change != unchanged`, plus a `Numeric change` column populated by the §12.6 routine recomputed at export time.

### 13.6 Change classification and rationale

Change detection is **by ID and lineage**, never by position:

```
for each block b in --ref:
    if b.id not in base:
        if b has split_from A:      Change := "split";     Old := text of A in base
        elif b has supersedes S:    Change := "merged";    Old := concatenated text of S in base
        else:                       Change := "new";       Old := ""
    elif normalize(text(b)) == normalize(base_text(b.id)):
                                    Change := "unchanged"
    else:                           Change := "modified";  Old := base_text(b.id)

for each id in base not in --ref and not claimed by lineage:
                                    Change := "deleted";   Old := base_text(id)
```

`Rationale` and `Commit` are resolved from `vault/log.md`: the most recent row whose section ID matches the block's owning section and whose commit is an ancestor of `--ref`. **Attribution is section-level, not block-level**, and the sheet header MUST say so. A block changed outside the logged workflow gets the SHA of the last commit touching its file and an empty rationale — itself a useful signal that the workflow was bypassed.

### 13.7 Presentation rules

Freeze the header row, set sensible column widths, wrap `Content` and `Old content`. Images are **not** embedded: the caption and the asset file name are written instead.

---

## Part 3 — The agent layer

## 14. `CLAUDE.md`

The repository's `CLAUDE.md` MUST state at least the following. It is a deliverable of this project, written in W1 D5.

1. **Read `vault/index.md` first** to locate content. Never read the whole vault.
2. **Cite IDs** in every answer (`SYS-000121`). Never paraphrase spec content without a citation.
3. **Never edit** `vault/index.md`, `log.md`, `backlinks.md`, `coverage.md`, `meta/`, or `source/`.
4. **Never modify** blocks marked `locked:true`; never remove or alter an anchor; never renumber an ID.
5. **Never hand-edit derived front matter** (§6.2). Edit the heading line and run `specctl fmt`.
6. **Never change a numeric value or a unit** unless the user asked explicitly. If a change appears necessary, propose it in chat instead.
7. **Declare lineage.** When merging blocks, put `supersedes:` on the survivor. When splitting, delete the original anchor and put `split_from:<original-id>` on **every** new part — no part keeps the original ID. Never let a block simply disappear.
8. To edit: create a branch `edit/<section-id>-<slug>`, edit only the target section file, run `specctl fmt` then `specctl validate`, report the summary **verbatim**, and wait for human approval before committing.
9. Commit message format per §17.
10. Use `rg` with ID patterns to find references; `backlinks.md` is authoritative.

## 15. Skills

Standard Agent Skills format under `.claude/skills/<name>/SKILL.md`: required front matter `name` and `description`, tool-specific extras under `metadata`.

| Skill                     | Problem | Purpose                                                                          | Output                          |
| ------------------------- | ------- | -------------------------------------------------------------------------------- | ------------------------------- |
| `spec-navigate`         | A       | How to use`index.md`, breadcrumbs, `backlinks.md` and ripgrep patterns       | Answer with citations           |
| `understand-section`    | A       | Read a section plus its inbound and outbound references, and summarize precisely | Structured summary with IDs     |
| `answer-with-citations` | A       | Q&A protocol: locate, read, answer, cite, state uncertainty                      | Answer                          |
| `restructure-section`   | B       | Apply the agreed target structure to a section                                   | Edited file + change summary    |
| `rewrite-presentation`  | B       | Normalize presentation — lists, tables, terminology — without changing meaning | Edited file                     |
| `improve-workflow`      | B       | The full edit loop of §16                                                       | Commit                          |
| `write-eval-questions`  | A/B     | Draft golden-set questions from a section, with expected answer and source IDs   | `eval/questions.yaml` entries |

Every `SKILL.md` MUST contain: when to use, preconditions, a step-by-step procedure, hard constraints (the "never" list), and a worked example.

`restructure-section` MUST reference `references/target-structure.md` ([OWNER-2]) and MUST include the lineage procedure:

```markdown
## Lineage (required when restructuring)
- Merging blocks: keep one anchor, add `supersedes:<other-id>[,<id>...]` to it, delete the other anchors.
- Splitting a block: keep the original anchor on the first part; every other part gets a new
  anchor carrying `split_from:<original-id>` and no id (`specctl assign-ids` fills the id in).
  The original anchor is deleted — no part keeps the original ID.
- Never delete a block outright. If content must go, propose it and wait for approval.
```

Example front matter:

```markdown
---
name: restructure-section
description: Restructure one spec section to the agreed target structure without changing meaning, values, or units. Use when the user asks to restructure or reorganize a section.
metadata:
  version: "2.0"
  problem: "B"
  applies_to: "section"
  allowed_changes: "reorder, split, merge, rewrite prose"
  forbidden: "numeric values, units, locked blocks, anchors, IDs, derived front matter"
---
```

## 16. Edit workflow (normative)

```
 1. git checkout -b edit/SYS-000120-restructure
 2. agent edits vault/sections/SYS-000120.md only, declaring lineage for any split or merge
 3. specctl assign-ids                       (only if the agent wrote new blocks)
 4. specctl fmt
 5. specctl validate --format json           (read-only)
 6. agent reports: rules triggered, numeric changes, lineage declared, inbound references affected
 7. human reviews the diff in VS Code; edits by hand if needed
 8. specctl fmt && specctl validate          (must be clean, or every finding explicitly accepted)
 9. specctl index                            (BEFORE the commit — see E5)
10. git commit                               (§17) — content + regenerated index, one commit
11. specctl registry sync                    (§12.10 — needs the commit)
12. specctl log "<rationale>" --section SYS-000120 --skill restructure-section
13. git commit -m "[SYS] registry + log for <short-sha of 10>"
14. git checkout main && git merge --no-ff edit/SYS-000120-restructure
```

*Steps 11–13 are a second commit on purpose. `registry sync` and `log` both need a commit that
already exists — `log` records its short SHA, and that SHA is what joins a rationale to an Excel row
(§13.6). They cannot run before step 10, and their output cannot go into step 10's commit.*

| R  | Rule                                                                                                                                                                                                                                                   |
| -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| E1 | One edit session touches**one** section file. Touching more requires explicit user approval, stated in the commit message. *The data model permits cross-section lineage (§5.4 L5); this restriction is about reviewability, not capability.* |
| E2 | `fmt` runs **before** `validate`, so derived drift never presents as a content finding.                                                                                                                                                      |
| E3 | The agent reports the validator summary verbatim. It MUST NOT summarize or soften findings.                                                                                                                                                            |
| E4 | The agent MUST NOT commit. Steps 10 and 13 are the human's.                                                                                                                                                                                            |
| E5 | `specctl index` runs **before** the commit, and its output goes into the same commit as the content. *The pre-commit hook of §20 runs `index --check`. With `index` after the commit, that check fails on every single commit — the hook is unusable, and the first thing anyone does with an unusable hook is bypass it.* |
| E6 | An edit branch MUST be merged with `--no-ff`, and MUST NOT be squashed or rebase-merged. *A squash replaces the SHAs that `log.md` rows name. The rationale join of §13.6 then finds nothing, and the `Rationale` column of the customer deliverable is silently empty — the one column that answers "why did this change".* `git config branch.<name>.mergeoptions --no-ff` and a repository policy that disables squash merging are both recommended. |

## 17. Commit message format

```
[SYS][3.2] <one-line rationale>

Skill: restructure-section
Model: claude-opus-5                 (optional — omit rather than guess)
Blocks: modified=5 new=1 deleted=0 merged=1 split=0
Numeric-changes: none
Files: vault/sections/SYS-000120.md
Reviewed-by: <owner>
```

The `Blocks:` and `Numeric-changes:` lines are taken from `validate --format json`. `Model:` is optional: an agent cannot always report its own model ID reliably, and a guessed value in a contractual audit trail is worse than an absent one.

---

## Part 4 — Quality and delivery

## 18. Test matrix

Every rule and every threshold maps to a named test. No orphans in either direction.

### 18.1 Ingest

| T        | Test                                                                                                                                                                                                                                          | Covers                 |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| T-ING-01 | The construct fixture ingests: 3 heading levels, numbered and bulleted lists, a simple table, a merged-cell table, an image, a text box, an equation, an internal cross-reference, a footnote. Every construct appears with the expected type | §6.3, §6.4           |
| T-ING-02 | Every block has a unique well-formed anchor; front-matter`blocks` equals the anchor count                                                                                                                                                   | FMT-02, ACC-1          |
| T-ING-03 | `text_fidelity.coverage ≥ 0.99` on the fixture and on the real document | §10.12, ACC-2 |
| T-ING-03b | A fixture whose only uncaptured paragraph is the short string`"Yes"` reports it as uncovered — it does not match another section by accident | §10.12 F8 |
| T-ING-03c | A table cell containing a literal`\|` is emitted escaped and still counts as covered | §6.6, §10.12 F8 |
| T-ING-04 | Every internal link resolves to an existing target or appears in`issues`; block-level targets use the `#^` form                                                                                                                           | §6.5, ACC-3           |
| T-ING-05 | Two runs with`--reingest --now X` produce byte-identical `vault/sections/**` and `vault/assets/**` and allocate zero new IDs                                                                                                            | §9.5, ACC-5           |
| T-ING-06 | Renaming a heading's text and re-ingesting keeps the section ID and file name                                                                                                                                                                 | §10.10 M4, ACC-5      |
| T-ING-07 | Inserting a new section before an existing one re-ingests with**zero** ID changes below it                                                                                                                                              | §7.1, ACC-5           |
| T-ING-08 | Two near-identical paragraphs in one section keep their own IDs across a re-ingest                                                                                                                                                            | §10.10 M2             |
| T-ING-09 | `--dry-run` writes only the coverage files                                                                                                                                                                                                  | §10.1                 |
| T-ING-10 | A deliberately malformed table degrades to a`raw locked fallback` block with an ID, an `error` issue, and its cell text still covered by fidelity                                                                                         | §6.4 invariant, ACC-4 |
| T-ING-11 | A fixture with one tracked insertion and one tracked deletion emits the insertion, discards the deletion, and counts both                                                                                                                     | §10.5 W1              |
| T-ING-12 | A fixture wrapping paragraphs in`w:sdt` emits them; a fixture with a TOC field skips it and excludes it from link counts                                                                                                                    | §10.5 W4, W6          |
| T-ING-13 | Content before the first heading lands in the synthetic front-matter section                                                                                                                                                                  | §10.9                 |
| T-ING-14 | A gate breach exits`2`, names the gate, and leaves no vault behind                                                                                                                                                                          | §9.4, §9.5           |
| T-ING-15 | No network socket is opened during a full ingest                                                                                                                                                                                              | §9.5                  |

### 18.2 Other components

| T        | Test                                                                                                                                                | Covers         |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| T-FMT-01 | `fmt` recomputes every derived key after a heading rename, including descendants' breadcrumbs                                                     | §6.2, DEC-12  |
| T-FMT-02 | `fmt` is idempotent; `--check` exits `1` before and `0` after                                                                               | §9.5          |
| T-FMT-03 | `fmt` adds a required `^id` marker when a block becomes a link target, and removes it when it stops being one                                   | FMT-04         |
| T-VAL-01 | Each of V01–V17 has one fixture that triggers it and one that does not                                                                             | §12.3, ACC-7  |
| T-VAL-02 | Changing "50 ms" to "80 ms" produces exactly one V10 with the arrow form                                                                            | §12.6         |
| T-VAL-03 | Reordering sentences without changing values produces**no** V10; moving a value between blocks produces V10 on both                           | §12.6 N1      |
| T-VAL-04 | `mV` → `MV` produces V10                                                                                                                       | §12.6 N3      |
| T-VAL-05 | Editing a locked figure caption produces V05                                                                                                        | FMT-08         |
| T-VAL-06 | A merge declared with`supersedes:` passes V04; the same merge without it fails V04; a bogus target fails V04a; a doubly-named `supersedes` target fails V04b | §12.5 |
| T-VAL-06b | A split into three parts, each carrying`split_from:X` and a **new** ID, passes V04 and V04b; `X` is absent from the vault afterwards | §5.4 L2–L3 |
| T-VAL-06c | That same split produces**one** V10 finding against `X`, comparing the union of the parts — not one finding per part | §12.6 N4 |
| T-VAL-07 | `assign-ids` allocates IDs only to anchorless blocks, leaves every other byte unchanged, and creates no file | §12.4 |
| T-VAL-07b | `split-section` moves a heading and its content into a new file with `origin: authored`, `source: null`, `bookmarks: []`, and that file validates | §5.5, §12.9, A.1 |
| T-VAL-10 | Reordering a locked block's anchor attributes produces**no** V05; editing one of its content lines does | §12.8 |
| T-VAL-11 | `Sig2`, `CAN_2`, `0x1F` and `3rd` yield no numeric token; `50ms` and `50 ms` yield the same one; `1,5` reads as 1.5 and `1,234` as 1234 | §12.6 |
| T-VAL-12 | `validate`, and every `--check` invocation, leave the working tree byte-identical — verified by hashing the repository before and after | §9.5 |
| T-VAL-13 | `registry sync` refuses to write and exits `2` on a tree where `validate` reports an error | §12.10 |
| T-VAL-08 | On an edit branch with commits, a bare`validate` compares against the merge-base and still reports the changes                                    | §12.2         |
| T-VAL-09 | Exit code is`2` with any error, `1` with warnings only, `0` clean                                                                             | §9.4          |
| T-IDX-01 | `index.md` lists every section exactly once and every link resolves                                                                               | §13.2         |
| T-IDX-02 | `backlinks.md` is the exact inverse of the outbound links                                                                                         | §13.3         |
| T-IDX-03 | `index` is idempotent; it never rewrites `log.md`                                                                                               | §13.1, §13.4 |
| T-EXP-01 | Exporting at baseline with`--compare-to` the same ref yields every row `unchanged`                                                              | §13.6         |
| T-EXP-02 | After a known edit, exactly the edited block is`modified` with correct old and new text                                                           | §13.6         |
| T-EXP-03 | A moved block — same ID, different position — is`unchanged` in content and shows the new order                                                  | §13.5         |
| T-EXP-04 | A declared merge exports as`merged` with the concatenated old text; a split exports as `split`                                                  | §13.6         |
| T-EXP-05 | A complex HTML table flattens without losing cell text                                                                                              | §6.6          |

### 18.3 Fixtures

`tests/fixtures/` with a `README.md` recording the provenance of each file.

| Fixture             | How produced                                                                                                                              |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `constructs.docx` | **Hand-authored in Word** and committed. Only Word can produce a real content control, SmartArt or an OLE object, which T-ING-01 requires |
| `revisions.docx`  | Hand-authored: one tracked insertion, one tracked deletion, one comment, **saved without accepting them**                           |
| `containers.docx` | Hand-authored: paragraphs inside`w:sdt`, a TOC field, a header and a footer                                                             |
| `degraded.docx`   | **Built from raw OOXML** by `tests/support/docx.py`. Word always writes *valid* OOXML, so a table representable in neither form cannot be authored in it |
| `built_constructs.docx`, `built_revisions.docx`, `built_containers.docx` | Built from raw OOXML and committed. **Stand-ins** for the three hand-authored files, carrying the same constructs, so §10 is testable while those are outstanding |
| `simple_*.docx`   | Built from raw OOXML at test time by the same module — headings, lists, simple tables, cross-references                             |

**A stand-in and the fixture it stands in for share one requirement list**, defined once in
`tests/support/fixtures.py`. A stand-in MUST NOT carry its own shorter list: it would drift
into covering less than the hand-authored file is required to, and the gap would surface as
a walker bug months later. `require(name)` resolves to the hand-authored file whenever it is
present and to the stand-in otherwise, so delivering the Word files switches every test over
without a line of test code changing. Tests MUST keep reporting the outstanding
hand-authored files: a stand-in keeps work moving, it does not close the item.

Built fixtures are committed and MUST be reproducible from their builders, which are pure
functions of constants — `python scripts/build_fixtures.py --check` compares each committed
package part by part against a fresh build. This is what makes a committed binary reviewable
at all: a hand-edited fixture is the one change no diff shows.

**What a built fixture cannot settle.** It proves the walker handles a construct; it cannot
prove the construct is in the shape *Word* emits, because `lxml` reads anything well-formed.
That question goes to an independent reader (§18.4 pandoc oracle), and it has already
returned a real answer — see the note under W1 in §10.5.

**Fixture contents are verified, not assumed.** `tests/test_fixtures.py` inspects each
file's raw OOXML and fails naming the construct that is absent, because Word does not
always save what the author intended: accepting tracked changes before saving removes the
`w:del`, emptying a content control makes Word drop the `w:sdt`, a TOC pasted as text has
no field codes, and a picture inserted as a link stores no image part. Each of those
yields a fixture that opens correctly and tests nothing — and the failure then surfaces in
§10.5 as "the walker loses text", blaming the walker for a construct that was never in the
file.

`*.docx` MUST be marked `binary` in `.gitattributes`. A .docx is a ZIP; if git ever
normalizes its line endings the archive is corrupt, and the corruption is invisible until
something opens it.

*Note on `python-docx`: it is **not** used, for fixtures or anywhere else. Its object
model hides exactly the elements §10.5 must see — `w:sdt`, `mc:AlternateContent`, `w:ins`
and `w:del` — so building the walker on it would create the silent-loss path the walker
exists to close. Fixtures are written as raw OOXML and read with `lxml`: one model of the
document, not two.*

---

### 18.4 The independent-reader oracle

`pandoc` is used as a **test oracle only**. Nothing in `specctl/` imports it, it is not a
dependency, and every test using it skips when it is absent.

| | |
|---|---|
| **Used for** | Arbitration. Text pandoc recovers that our walker does not is a bug in our walker, surfaced on a fixture instead of on the customer's document. It is also the only check that a *built* fixture is the OOXML Word writes rather than OOXML our own parser happens to accept |
| **Not used for** | Conversion. It drops what it cannot represent **silently** and exits 0, while §6.4 requires a converter that knows it degraded, so the construct survives as a `raw locked fallback` block with its OOXML and a named reason |

Two kinds of test live there. **Recorded baselines** pin what pandoc loses (text box
content, the cells of a table it cannot represent, a custom list-number prefix) and what it
handles well (bookmarks, anchored links, run-level tracked changes). A baseline going red
means pandoc improved — re-run the comparison and re-evaluate rather than deleting the test.
**Oracles proper** compare our walker against it segment by segment on the fixtures, and
check that an independent reader can open every built fixture at all.

## 19. Acceptance thresholds

| #     | Metric                                                     | Source                              | Threshold                             |
| ----- | ---------------------------------------------------------- | ----------------------------------- | ------------------------------------- |
| ACC-1 | Blocks with valid unique IDs                               | `validate` V01–V03               | 100%                                  |
| ACC-2 | `text_fidelity.coverage`                                 | `coverage.json` §10.12           | ≥ 0.99 —**[OWNER-1]**         |
| ACC-3 | Internal links resolved to wikilinks                       | `coverage.json` `links`         | ≥ 95%, remainder listed in`issues` |
| ACC-4 | Tables preserved as pipe or HTML                           | `coverage.json` `counts.tables` | ≥ 90%, remainder degraded and listed |
| ACC-5 | Re-ingest ID stability                                     | T-ING-05 … T-ING-08                | 100%                                  |
| ACC-6 | Sections improved end to end                               | git history                         | ≥ 3                                  |
| ACC-7 | Validator detection on the fixture suite                   | T-VAL-01                            | 100%                                  |
| ACC-8 | Golden-set answers correct, owner-judged                   | `eval/runs/`                      | ≥ 80%                                |
| ACC-9 | Excel export opens; change columns correct on a known edit | T-EXP-01 … T-EXP-04                | Pass                                  |

Every threshold names a field that this document defines. A threshold stated against an undefined metric is not a threshold.

---

## 20. Runbook

```bash
# one-time
pip install -e .                                  # or: uv sync
specctl ingest source/SYS.docx --doc-key SYS --out vault/ --no-gates    # D1 exploratory
open vault/coverage.md                            # review; decide the gates
specctl ingest source/SYS.docx --doc-key SYS --out vault/               # gated run
git add -A && git commit -m "[SYS] baseline" && git tag SYS-baseline-v0

# understanding (Problem A) — in VS Code with Claude Code
#   "Using spec-navigate, what does section 3.2 require, and what references it?"

# improving (Problem B)
git checkout -b edit/SYS-000120-restructure
#   "Using restructure-section, restructure SYS-000120."
specctl assign-ids && specctl fmt && specctl validate
# review the diff, approve
specctl index                                     # before the commit (§16 E5)
git commit                                        # message per §17
specctl registry sync
specctl log "restructured 3.2" --section SYS-000120 --skill restructure-section
git commit -m "[SYS] registry + log for $(git rev-parse --short HEAD)"
git checkout main && git merge --no-ff edit/SYS-000120-restructure   # never squash (§16 E6)

# deliverable
specctl export xlsx --out exports/SYS.xlsx --compare-to SYS-baseline-v0
```

**Pre-commit hook** (recommended from day one — it is the cheapest defence against a bypassed workflow):

```bash
#!/bin/sh
specctl fmt --check && specctl validate && specctl index --check
```

All three are read-only, so the hook has no side effects and can run as often as git calls it. It
passes at step 10 because step 9 regenerated the index, and at step 13 because neither `log.md` nor
`meta/ids.json` is index output (§13.1).

---

## 21. Plan and risks

### 21.1 Schedule

| Week                  | Problem | Deliverable                                                                                                                                                                                                  | Done when                                                                                       |
| --------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| **W1 D1**       | A       | **Two spikes.** (a) Fidelity gate: exploratory ingest of the real file, measure coverage, tables, links, numbering. (b) LibreOffice probe: does `--convert-to html` emit one image per drawn object? | A go/no-go note. If tables fall below 90% or coverage below 0.99, escalate. [OWNER-1] confirmed |
| **W1 D2**       | A       | First rough vault + 10 trial questions answered by Claude Code                                                                                                                                               | Owner sees value on day 2. [OWNER-3] recorded                                                   |
| **W1 D3–D4**   | A       | `ingest` complete per §10; T-ING-01…15 green                                                                                                                                                             | Coverage report on the real file,`coverage ≥ 0.99`                                           |
| **W1 D5**       | A       | `CLAUDE.md`, `index`/`backlinks`/`log`, `fmt`, skills `spec-navigate`, `understand-section`, `answer-with-citations`; baseline tag                                                           | Agent answers with citations                                                                    |
| **W2 D6**       | B       | **[OWNER-2]** `references/target-structure.md` with one real before/after example                                                                                                                    | **Gate: no example, no improvement skills**                                               |
| **W2 D7–D8**   | B       | Skills`restructure-section`, `rewrite-presentation`, `improve-workflow`; the edit loop runs on one section                                                                                             | One section improved end to end, lineage declared                                               |
| **W2 D9**       | B       | `validate` per §12, including lineage and numeric diff; T-VAL-01…09 green                                                                                                                                | Validator catches every fixture violation                                                       |
| **W2 D10**      | B       | `export xlsx` per §13.5; T-EXP-01…05 green                                                                                                                                                               | Excel produced with change columns                                                              |
| **W3 D11–D12** | A/B     | Golden set of 20–30 questions, run before and after                                                                                                                                                         | Owner-confirmed accuracy numbers                                                                |
| **W3 D13**      | A       | Lint pass —`fmt` and `validate` over the whole vault                                                                                                                                                    | Zero errors in the vault                                                                        |
| **W3 D14**      | B       | Improve 3–5 sections total                                                                                                                                                                                  | Diffs reviewed and merged                                                                       |
| **W3 D15**      | —      | Pilot report, README, handover                                                                                                                                                                               | Report delivered                                                                                |

### 21.2 Risks

| Risk                                               | Response                                                                                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| The extractor consumes the whole budget            | Hard timebox W1 D1–D4. After that, remaining unparsed items are fixed by hand — it is one file                                    |
| LibreOffice does not emit one image per object     | The §10.7 fallback is already specified; the D1 spike answers this before it can cost a day                                        |
| Complex tables fail the ACC-4 gate                 | Switch them to HTML; if still failing, degrade per §6.4, flag`locked`, and note the limitation in the pilot report               |
| The agent silently changes values                  | V10 is always reported; the human reviews the diff; locked blocks are byte-compared                                                 |
| Numbering cannot be resolved from`numbering.xml` | §10.3 falls back to unnumbered text plus a coverage entry; the LibreOffice HTML conversion can supply rendered numbering if needed |
| No target-structure example by W2 D6               | Improvement skills are not written; week 2 shifts to more Problem-A work (owner decision)                                           |
| Scope creep toward MCP, search index or UI         | Any such request goes to`B-limitations-roadmap.md`, not into this phase                                                           |

---

## Appendices

### Appendix A — JSON Schemas

Four schemas ship inside the package at `specctl/schemas/` and are enforced by V01 and by the writers.

**A.1 `section.schema.json`** — section front matter. Required: `id`, `doc`, `number`, `title`, `level`, `order`, `path`, `path_ids`, `breadcrumb`, `bookmarks`, `refs_out`, `blocks`, `words`, `origin`, `source`, `ingest_version`, `generated`. Optional: `parent`. `additionalProperties: false`.

`origin` is `ingest` or `authored`. The schema makes `source` conditional on it: an object when
`origin` is `ingest`, and `null` with `bookmarks: []` when `origin` is `authored` — a section an
editor created has no paragraph range in the .docx, because it was never in the .docx.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "specctl section front matter",
  "type": "object",
  "additionalProperties": false,
  "required": ["id","doc","number","title","level","order","path","path_ids",
               "breadcrumb","bookmarks","refs_out","blocks","words","origin",
               "source","ingest_version","generated"],
  "allOf": [
    { "if":   { "properties": { "origin": { "const": "authored" } } },
      "then": { "properties": { "source":    { "type": "null" },
                                "bookmarks": { "maxItems": 0 } } } },
    { "if":   { "properties": { "origin": { "const": "ingest" } } },
      "then": { "required": ["source"],
                "properties": { "source": { "type": "object" } } } }
  ],
  "properties": {
    "id":        { "type": "string", "pattern": "^[A-Z][A-Z0-9]{1,7}-[0-9]{6}$" },
    "doc":       { "type": "string", "pattern": "^[A-Z][A-Z0-9]{1,7}$" },
    "number":    { "type": "string" },
    "title":     { "type": "string", "minLength": 1 },
    "level":     { "type": "integer", "minimum": 1, "maximum": 6 },
    "parent":    { "type": "string", "pattern": "^[A-Z][A-Z0-9]{1,7}-[0-9]{6}$" },
    "order":     { "type": "integer", "minimum": 0 },
    "path":      { "type": "array", "items": { "type": "string" } },
    "path_ids":  { "type": "array", "items": { "type": "string",
                     "pattern": "^[A-Z][A-Z0-9]{1,7}-[0-9]{6}$" }, "minItems": 1 },
    "breadcrumb":{ "type": "string" },
    "bookmarks": { "type": "array", "items": { "type": "string" } },
    "refs_out":  { "type": "array", "items": { "type": "string" } },
    "blocks":    { "type": "integer", "minimum": 1 },
    "words":     { "type": "integer", "minimum": 0 },
    "origin":    { "enum": ["ingest", "authored"] },
    "source":    { "type": ["object", "null"], "additionalProperties": false,
                   "required": ["docx","paragraphs"],
                   "properties": {
                     "docx": { "type": "string" },
                     "paragraphs": { "type": "array", "minItems": 2, "maxItems": 2,
                                     "items": { "type": "integer", "minimum": 0 } } } },
    "ingest_version": { "type": "integer", "minimum": 1 },
    "generated": { "const": false }
  }
}
```

**A.2 `generated.schema.json`** — required `generated` (const `true`), `doc`, `kind` (enum `index`/`log`/`backlinks`/`coverage`), `generated_at`, `generator`, `ingest_version`. `additionalProperties: false`.

**A.3 `ids.schema.json`** — per §7, with `status` enum `active`/`deleted`/`merged`/`split`, `merged_into` required when `status` is `merged`, `split_into` required when `status` is `split`.

**A.4 `coverage.schema.json`** — per §8.

**A.5 `findings.schema.json`** — the `validate --format json` output of §12.7.

### Appendix B — Issue and skip codes

| Code                                | Severity | Raised by | Meaning                                                       |
| ----------------------------------- | -------- | --------- | ------------------------------------------------------------- |
| `unresolved_ref`                  | warn     | §10.4    | A bookmark target was not found                               |
| `textual_ref_candidate`           | info     | §10.4    | Prose refers to a section without a field                     |
| `numbering_unresolved`            | warn     | §10.3    | A heading number could not be computed                        |
| `table_parse_failed`              | error    | §10.6    | A table degraded to`raw`                                    |
| `formula_conversion_failed`       | warn     | §10.8    | OMML did not convert; the image fallback was used             |
| `shape_unrenderable`              | warn     | §10.7    | No image could be produced;`raw` + OOXML only               |
| `style_dropped`                   | info     | §6.4     | A character style outside bold/italic/code was dropped        |
| `unknown_container`               | info     | §10.5    | An unrecognised element containing content was descended into |
| `source_has_unresolved_revisions` | warn     | §10.5 W2 | The source carries tracked changes                            |
| `index_too_large`                 | warn     | §13.2    | `index.md` exceeds 40 KB                                    |
| `skipped.toc`                     | —       | §10.5 W4 | TOC field results                                             |
| `skipped.header_footer`           | —       | §10.5 W5 | Headers and footers                                           |

### Appendix C — Unit vocabulary for V10

Shipped as `specctl/validate/units.txt`, one symbol per line, matched case-sensitively. Base set:

```
%  ‰  °  °C  °F  K
s  ms  µs  us  ns  min  h  d
Hz  kHz  MHz  GHz  rpm
m  mm  cm  km  in  ft
g  kg  mg  t  N  Nm  kN
V  mV  kV  A  mA  µA  Ω  kΩ  MΩ  W  kW  mW  Wh  kWh  Ah  mAh
Pa  kPa  MPa  bar  mbar  psi
B  kB  MB  GB  bit  kbit  Mbit  baud
```

The list is project-extensible: `specctl.toml` MAY add `[validate] extra_units = [...]`. A trailing token not in the vocabulary is not treated as a unit, and the number is still compared.

### Appendix D — Worked example

`vault/sections/SYS-000120.md`, complete and conforming. **Copy this shape literally.**

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
path_ids: ["SYS-000100", "SYS-000120"]
breadcrumb: "SYS > 3 Braking system > 3.2 Braking control"
bookmarks: ["_Ref123456", "_Toc99887"]
refs_out: ["SYS-000245"]
blocks: 4
words: 61
origin: ingest
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

**After a merge** — `SYS-000124` absorbed into `SYS-000121`:

```markdown
<!-- id:SYS-000121 type:paragraph supersedes:SYS-000124 -->
The system shall apply braking torque within 50 ms after the pedal signal exceeds
the threshold defined in [[SYS-000245|5.1 Signal thresholds]]. The torque ramp shall
not exceed 400 Nm/s.
^sys-000121
```

`meta/ids.json` then records `SYS-000124` as `{"status": "merged", "merged_into": "SYS-000121"}`, V04 passes without `--allow-delete`, and the Excel export reports the row as `merged` with both original texts in `Old content`.

**After a split** — `SYS-000130` divided in two:

```markdown
<!-- id:SYS-001205 type:paragraph split_from:SYS-000130 -->
The system shall monitor wheel speed at 100 Hz.
^sys-001205

<!-- id:SYS-001206 type:paragraph split_from:SYS-000130 -->
The system shall raise a fault when the wheel speed signal is absent for 200 ms.
^sys-001206
```

`SYS-000130` is **gone from the vault**. `meta/ids.json` records it as
`{"status": "split", "split_into": ["SYS-001205", "SYS-001206"]}`, so a citation of the retired ID
still resolves to where its content went. Both parts export as `split`, each carrying
`SYS-000130`'s text in `Old content`.

### Appendix E — Python package layout

```
specctl/
├── cli.py                    # typer app, config resolution (§9.2)
├── config.py
├── model.py                  # Block, Section, Document, Anchor dataclasses
├── textutil.py               # normalize, normalize_ws, to_plain_text, words (§6.6)
├── ingest/
│   ├── package.py            # docx zip + xml loading
│   ├── report.py             # issue codes, skip accounting, revision counts (§8)
│   ├── walk.py               # block stream, sdt/ins/del/TOC handling (§10.5)
│   ├── numbering.py          # §10.3
│   ├── anchors.py            # bookmarks, hyperlinks, REF fields (§10.4)
│   ├── media.py              # images, shapes, LibreOffice rendering (§10.7)
│   ├── tables.py             # pipe vs html decision (§10.6)
│   ├── equations.py          # OMML → MathML → LaTeX (§10.8)
│   ├── segment.py            # §10.9
│   ├── ids.py                # allocation, registry, re-ingest matching (§10.10)
│   ├── fidelity.py           # §10.12
│   └── writer.py             # §10.11
├── fmtcmd/frontmatter.py     # §11
├── validate/
│   ├── rules.py              # V01–V17, V05 comparison per §12.8
│   ├── numeric.py            # §12.6 — tokens, boundaries, lineage grouping (N4)
│   ├── lineage.py            # §12.5 — reporting only, never writes
│   └── units.txt
├── idcmd/
│   ├── assign.py             # §12.4  specctl assign-ids
│   ├── split.py              # §12.9  specctl split-section
│   └── sync.py               # §12.10 specctl registry sync
├── indexgen/{index,backlinks,log,coverage}.py
├── exportx/xlsx.py
└── schemas/*.json
tests/fixtures/*.docx
```

Dependencies: `lxml`, `typer`, `openpyxl`, `pyyaml`, `rapidfuzz`, `jsonschema`, `pytest`,
`hypothesis`. Optional external binary: `libreoffice`. Pandoc is **not** used, and neither
is `python-docx` (§18.3) — the walker reads `document.xml` through `lxml` directly, so the
document has one model rather than two.

### Appendix F — Glossary

| Term            | Meaning                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------ |
| Vault           | The`vault/` folder of Markdown files — also what Obsidian opens                         |
| Anchor          | The`<!-- id:… -->` comment binding a Markdown block to its stable ID                    |
| Block reference | The trailing`^sys-000121` marker making a block addressable by wikilink                  |
| Locked block    | A block agents must not modify — figures, shapes, raw fallbacks                           |
| Lineage         | A declared`supersedes`/`split_from` relation recording where content went              |
| Degraded block  | A construct that could not be represented, preserved as`raw` + OOXML rather than dropped |
| Baseline        | A git tag marking a comparable version of the spec                                         |
| Coverage        | Proof of what the extractor captured, degraded, skipped or failed on                       |
| Fidelity gate   | The W1 D1 measurement deciding whether Markdown is a sufficient store                      |
| Golden set      | Owner-approved questions with expected answers, used to measure quality                    |

### Appendix G — Traceability

**G.1 Gap resolutions.** Every finding in `archive/C-spec-gaps.md` and where it is resolved here.

| Gap                              | Resolved in                   |
| -------------------------------- | ----------------------------- |
| GAP-01 front-matter schema       | §6.2, Appendix A.1/A.2       |
| GAP-02 anchor placement          | FMT-02, §6.1                 |
| GAP-03`^id` on link targets    | FMT-04, V13                   |
| GAP-04 non-heading link targets  | §6.5, §10.4, V07            |
| GAP-05 byte-identical vault      | §9.3`--now`, T-ING-05      |
| GAP-06 block lineage             | DEC-10, §5.4, §12.5, §13.6 |
| GAP-07 re-ingest key             | §7.1, §10.10                |
| GAP-08 derived front matter      | DEC-12, §11, V15             |
| GAP-09`eval/`, `references/` | §4                           |
| GAP-10 preamble and levels       | §10.9                        |
| GAP-11 total-capture invariant   | §6.4                         |
| GAP-12 fidelity metric           | DEC-11, §10.12, ACC-2        |
| GAP-13 numeric diff              | §12.6, Appendix C            |
| GAP-14 shape rendering           | §10.7, §21.1 W1 D1          |
| GAP-15 OMML conversion           | §10.8                        |
| GAP-16 per-metric gates          | §10.1, §9.2                 |
| GAP-17 Excel rationale           | §13.6                        |
| GAP-18`--base` default         | §12.2                        |
| GAP-19 global block order        | §13.5                        |
| GAP-20 tracked changes           | §10.5 W1–W2, T-ING-11       |
| GAP-21`w:sdt`                  | §10.5, T-ING-12              |
| GAP-22 TOC, headers, footers     | §10.5 W4–W5, §8.3          |
| GAP-23 git in ingest             | §10.1, §20                  |
| GAP-24 formatting rule           | V16, §11.2                   |
| GAP-25 commit message file       | §20                          |
| GAP-26 config file               | DEC-13, §9.2                 |
| GAP-27`Model:` trailer         | §17                          |
| GAP-28 fixtures                  | §18.3                        |
| GAP-29 CJK word count            | §6.6                         |
| GAP-30`ingest_version`         | §6.7, V17                    |
| GAP-31 new sections and moves    | §5.5, §16 E1                |

**G.2 v1.0 section map.**

| A v1.0                            | Here                         |
| --------------------------------- | ---------------------------- |
| §1 How to use                    | §1                          |
| §2 Problem statement             | §2                          |
| §3 Solution decisions D1–D9     | §3.2 DEC-01…DEC-09         |
| §4 Architecture                  | §3.1                        |
| §5.1 Layout                      | §4                          |
| §5.2 Identifiers                 | §5                          |
| §5.3 Section file format F1–F10 | §6.1–§6.3, FMT-01…FMT-12 |
| §5.4 Block representation        | §6.4                        |
| §6 Extractor                     | §10                         |
| §7 Validator                     | §12                         |
| §8 Excel exporter                | §13.5–§13.7               |
| §9 Index generator               | §13.1–§13.4               |
| §10 Agent layer                  | §14–§17                   |
| §11 Runbook                      | §20                         |
| §12 Plan                         | §21.1                       |
| §13 Acceptance thresholds        | §19                         |
| §14 Risks                        | §21.2                       |
| §15 Appendix                     | Appendices D, E, F           |

**Dropped from v1.0, deliberately:**

| Dropped                                         | Why                                                                                          |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `--fail-under PCT` (single scalar)            | One value cannot express three different thresholds — replaced by per-metric gates (§10.1) |
| Ingest step 12 "commit and tag" and`--no-git` | Ingest no longer touches git; the runbook owns it (§20)                                     |
| `pandoc` as a dependency                      | Unreachable from a direct-OOXML pipeline; replaced by the XSLT path (§10.8)                 |
| PDF page-region cropping for shapes             | No element-to-region mapping exists; replaced by the HTML path (§10.7)                      |
| `text_fidelity.ratio`                         | Net metric, replaced by directional coverage (§10.12)                                       |
| `git commit -F .git/COMMIT_MSG`               | Writing into`.git/`; the runbook uses the normal commit path (§20)                        |
