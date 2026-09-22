# Spec Gap Register — review of `A-solution-spec-handoff.md` v1.0

**Version:** 1.0 · **Date:** 2026-09-21 · **Status:** For review
**Reviews:** `A-solution-spec-handoff.md` v1.0 (2026-09-20)
**Companion:** `B-limitations-roadmap.md` — deliberate omissions. This document is about *unintended* ones.
**Audience:** implementer (primary), solution owner (§6 and the entries marked *owner decision*)

---

## 1. Why this document exists

A v1.0 is marked *Ready for implementation* and instructs the implementer:

> Section 5 is a contract. If a rule there is impossible on real data, stop and report, do not invent a variant.

This register is that report, filed before coding rather than during it. It covers three kinds of finding:

- **§5 contradicts itself** — a rule cannot be implemented because another rule forbids the same thing (GAP-01–GAP-05).
- **A mechanism the design depends on is missing** — the implementer would have to invent it, and any invention would be wrong somewhere downstream (GAP-06–GAP-11).
- **An algorithm behind an acceptance threshold is undefined** — the threshold in §13 is unmeasurable or unmeetable as written (GAP-12–GAP-23).

Nothing here disputes A's decisions (D1–D9). The ID-first Markdown vault is the right bet, and §2's split of Problem A from Problem B is the reason the gaps are this shallow. The findings are about the contract's precision, not its direction.

**A v1.0 is unmodified.** Each entry carries replacement text precise enough to paste into a v1.1, but adopting them is a separate decision, per-ID.

### 1.1 Severity

| | Meaning | When to resolve |
| --- | --- | --- |
| **S1 Blocker** | Contradicts the §5 contract, or an acceptance threshold in §13 cannot be met as written | Before any code |
| **S2 Major** | The implementer must invent an algorithm A leaves undefined; the invention is load-bearing | Before the owning component (§6/§7/§8) |
| **S3 Minor** | Omission or inconsistency with a local fix | During implementation |

### 1.2 Summary

Gap IDs are `GAP-nn`. A's own `G1`–`G6` are goals (§2.3) and unrelated; no other prefix in A or B is reused here.

| ID | A-ref | Title | Severity |
| --- | --- | --- | --- |
| GAP-01 | §5.3 F1, F10 | Front-matter schema is self-contradictory | S1 |
| GAP-02 | §5.3 F2 vs example | Anchor placement: "preceded by" vs. the heading example | S1 |
| GAP-03 | §5.3 F4 vs F6 | Block-level links need `^id` markers F4 makes optional | S1 |
| GAP-04 | §6.3 vs §5.3 F6 | Cross-refs to non-heading blocks resolve to dead links | S1 |
| GAP-05 | §6.6 A5 vs §6.2 | "Byte-identical vault" is untestable against timestamped output | S1 |
| GAP-06 | §7.2 V04, §8.4, §15.1 | No block lineage for split and merge | S1 |
| GAP-07 | §6.5 | Re-ingest key is built on heading numbers, which churn | S1 |
| GAP-08 | §9, §5.3 | Nothing regenerates derived front matter | S1 |
| GAP-09 | §5.1 | `eval/` and `references/` are used but absent from the layout | S1 |
| GAP-10 | §5.3, §6.2 | Preamble and levels above `split_level` are undefined | S1 |
| GAP-11 | §13 #1 vs §6.4 | "Never silently drop" is implied everywhere, stated nowhere | S1 |
| GAP-12 | §6.4 | `text_fidelity.ratio` is a net figure and cannot prove its claim | S2 |
| GAP-13 | §7.2 V10, §7.3 | Numeric-change detection has no tokenizer and no pairing rule | S2 |
| GAP-14 | §6.2 step 6 | Shape rendering has no element-to-region mechanism | S2 |
| GAP-15 | §5.4 | OMML to LaTeX path is unreachable as described | S2 |
| GAP-16 | §6.1 vs §13 | One `--fail-under` scalar for three different thresholds | S2 |
| GAP-17 | §8.2 | Excel `Rationale` needs per-block blame that is never specified | S2 |
| GAP-18 | §7.1 | `--base` defaults to `HEAD`, which silences the validator on a branch | S2 |
| GAP-19 | §5.3 vs §8.2 | Global block order is required by Excel and never defined | S2 |
| GAP-20 | §5.4 | Tracked changes: `w:del` text will be emitted as current | S2 |
| GAP-21 | §6.2 step 2 | `w:sdt` content controls vanish without error | S2 |
| GAP-22 | §6.2 | TOC field, cover page, revision history, headers/footers undecided | S2 |
| GAP-23 | §6.1 vs §6.2, §11 | `--no-git` is undocumented; ingest and the runbook both commit | S3 |
| GAP-24 | §7.2 | No validator rule enforces F9 formatting | S3 |
| GAP-25 | §11 | Runbook writes a commit message into `.git/` | S3 |
| GAP-26 | §6.1, §7.1, §8.1 | No config file; options repeat across commands | S3 |
| GAP-27 | §10.4 | `Model:` trailer assumes the agent knows its own model ID | S3 |
| GAP-28 | §6.6 A1 | The A1 fixture cannot be authored with `python-docx` | S3 |
| GAP-29 | §9.1, §7.2 V14 | Word counts break on CJK, which survives the translation | S3 |
| GAP-30 | §5.3 | `ingest_version` has no bump or migration semantics | S3 |
| GAP-31 | §10.3 | Moving a block between sections and creating a section are impossible | S3 |

Counts: 11 S1, 11 S2, 9 S3.

---

## 2. S1 — Blockers

### 2.1 Group A: §5 contradicts itself

#### GAP-01 — Front-matter schema is self-contradictory

**A-ref:** §5.3 rules F1 and F10 · **Affects:** V01, §9

**What A says**

> **F1** Front matter is YAML and contains exactly the keys above. Unknown keys are an error.
> **F10** Generated files (`index.md`, `log.md`, `backlinks.md`, `coverage.md`) have `generated: true` in front matter and must never be hand-edited.

**Why it fails**

"The keys above" is the section-file list: `id`, `doc`, `number`, `title`, `level`, `parent`, `order`, `path`, `breadcrumb`, `bookmarks`, `refs_out`, `blocks`, `source`, `ingest_version`, `generated`. `index.md` has no `id`, no `number`, no `parent`, no `source`. Under F1 every generated file is an error, and V01 ("front matter parses, contains required keys, `id` matches the file name") cannot run on them at all. A also never separates *required* from *optional*: is `bookmarks: []` legal, is `refs_out` required when empty, is `source.paragraphs` mandatory?

**Recommended resolution**

Two schemas, both shipped as JSON Schema inside `specctl` and both enforced by V01:

- **Section schema** — required: `id`, `doc`, `number`, `title`, `level`, `order`, `path`, `path_ids` (see GAP-07), `breadcrumb`, `blocks`, `source`, `ingest_version`, `generated`. Optional: `parent` (absent at top level), `bookmarks` (default `[]`), `refs_out` (default `[]`).
- **Generated schema** — required: `generated: true`, `doc`, `ingest_version`, `generated_at`, `generator` (the command that wrote it). No other keys permitted.

Restate F1 as: *front matter validates against the schema for its file class; keys outside the schema are an error.*

#### GAP-02 — Anchor placement: "preceded by" vs. the heading example

**A-ref:** §5.3 rule F2 vs. the §5.3 example · **Affects:** every parser and writer in the system

**What A says**

> **F2** **Every block is preceded by an HTML comment anchor** `<!-- id:<ID> type:<TYPE> [key:value ...] -->`. The anchor is the single canonical ID carrier.

and, three lines earlier, in the normative example:

```markdown
## 3.2 Braking control <!-- id:SYS-000120 type:heading -->
```

**Why it fails**

The heading anchor *trails on the heading line*; F2 says anchors *precede*. A parser written to F2 finds no anchor on the heading and reports V02 on every section file in the vault. A parser written to the example rejects every non-heading block. The two cannot both be honoured, and F2 is the rule the whole ID system rests on.

The example is the better design — a preceding comment line would break Markdown heading detection in some renderers and would sit awkwardly above the `##` in Obsidian — so the rule should move, not the example.

**Recommended resolution**

Replace F2 with:

> **F2** Every block carries exactly one HTML comment anchor `<!-- id:<ID> type:<TYPE> [key:value ...] -->`, the single canonical ID carrier. For `heading` blocks the anchor is appended to the heading line, separated by one space. For every other block type the anchor occupies its own line immediately before the block's first line, with no blank line between them. Anchor attributes are `key:value` pairs separated by single spaces; values contain no spaces.

#### GAP-03 — Block-level links need `^id` markers F4 makes optional

**A-ref:** §5.3 rules F4 and F6 · **Affects:** V07, V13, §6.3, §9.3

**What A says**

> **F4** A trailing Obsidian block reference `^sys-000121` (lowercased ID) MAY be emitted for `paragraph` and `list` blocks, for Obsidian convenience. It is derived, never authoritative.
> **F6** … Block-level targets use `[[<SECTION-ID>#^<lowercased block id>]]`.

**Why it fails**

F6's link form resolves only if the target block actually carries a `^id` marker. F4 makes that marker (a) optional and (b) available only to `paragraph` and `list`. So:

- A bookmark on a `table` or `figure` block has no addressable form at all — F6 offers one and F4 forbids the marker that makes it work.
- Even for a paragraph, an optional marker means a link emitted by §6.3 may or may not resolve depending on a choice the writer is free to make either way.

V07 ("wikilink targets exist in the vault") would then fail on links the extractor itself produced.

**Recommended resolution**

Replace F4 with:

> **F4** A trailing block reference `^<lowercased id>` is **required** on every non-heading block that is the target of at least one wikilink, for any block type. It MAY be emitted on other `paragraph` and `list` blocks for Obsidian convenience. It is derived from the anchor, never authoritative; `specctl fmt` adds missing required markers and removes orphaned ones.

Promote **V13** from warn to **error** for the required case (a link target missing its marker), keeping warn for cosmetic inconsistency. Heading blocks need no marker: they are addressed by file name.

#### GAP-04 — Cross-refs to non-heading blocks resolve to dead links

**A-ref:** §6.3 vs. §5.3 F6, §5.1 · **Affects:** §13 threshold #3, V07, Obsidian browsing (D7)

**What A says**

> | Hyperlink with `w:anchor` matching a known bookmark | `[[TARGET-ID\|<display text>]]`, edge kind `word_link` |

and §6.2 step 9: "Resolve cross-references: bookmark name → block → ID."

**Why it fails**

Wikilinks resolve by **file name**, and §5.2 names files `<section-id>.md` — only heading blocks are file names. Word bookmarks in a real spec point at paragraphs, table cells and figure captions at least as often as at headings. For every such bookmark, §6.3 emits `[[SYS-000121|…]]` where `SYS-000121` is a paragraph: a dead link in Obsidian, and a V07 error in the vault the extractor just produced. F6 defines the correct form for exactly this case but §6.3 never uses it.

This directly threatens §13 threshold #3 (≥ 95% of Word internal links resolved), because the failures are not reported as `unresolved_ref` — they are reported as *resolved*.

**Recommended resolution**

Replace the first two rows of the §6.3 table with:

> Resolution maps the bookmark to its enclosing block, then to that block's **owning section**. If the target block is the section's heading, emit `[[<SECTION-ID>|<display text>]]`. Otherwise emit `[[<SECTION-ID>#^<lowercased block id>|<display text>]]` and mark the target block as requiring a `^id` marker (F4). Edge kind `word_link` in both cases.

Extend **V07** to validate both forms: the section file exists, and for the `#^` form the marker exists inside it.

#### GAP-05 — "Byte-identical vault" is untestable against timestamped output

**A-ref:** §6.6 test A5 vs. §6.2 step 11 · **Affects:** §13 threshold #5

**What A says**

> **A5** Running ingest twice on the same file with `--reingest` produces a byte-identical vault and zero new IDs.
> **§6.2 step 11** Generate `index.md`, `log.md` (initial entry), `backlinks.md`, `coverage.md` / `coverage.json`.

**Why it fails**

`coverage.md` renders `generated_at` (§6.4 shows `"generated_at": "2026-09-21T10:00:00+07:00"`), and `log.md` receives a timestamped initial entry — both inside `vault/`. Two runs a second apart differ. A5 fails on a correct implementation, and §13 threshold #5 (re-ingest ID stability, 100%) is measured by a test that can never pass.

**Recommended resolution**

Scope the assertion and make the clock injectable:

> **A5** Running ingest twice on the same file with `--reingest` produces byte-identical `vault/sections/**` and `vault/assets/**`, and allocates zero new IDs. Generated files carrying timestamps (`vault/coverage.md`, `vault/log.md`, `meta/coverage.json`) are excluded; with `--now <ISO8601>` they too are byte-identical.

Add `--now` to §6.1. It is also what makes A7 (`--dry-run`) and the D3 determinism tests reproducible in CI.

### 2.2 Group B: missing mechanisms

#### GAP-06 — No block lineage for split and merge  *(owner decision, see §6.1)*

**A-ref:** §7.2 V04, §8.4, §15.1 · **Affects:** §13 thresholds #7 and #9, the entire Problem B workflow

**What A says**

> **V04** error — No ID present in `--base` has silently vanished (unless `--allow-delete`)
> **§8.4** Change detection is by **ID**, never by position.
> **§15.1** `allowed_changes: "reorder, split, merge, rewrite prose"`

**Why it fails**

Splitting and merging blocks is explicitly permitted — it is most of what "restructure a section" means in practice. But the design has no way to express *this block became those two*:

1. Merging two paragraphs retires one ID. V04 fires an error. The only escape is `--allow-delete`, which switches off deletion protection for **the entire run**, including the accidental deletions V04 exists to catch. The safety rail is all-or-nothing at exactly the moment it matters.
2. Splitting a paragraph produces a block with no anchor (V11), which `--assign-ids` gives a fresh ID. Nothing records where it came from.
3. Downstream, §8.4 keys the customer-facing Excel by ID. A merge appears as `deleted` + `modified`; a split appears as `modified` + `new`. The Excel deliverable — the thing the customer reads — misrepresents an editorial improvement as content deletion.

So the primary Problem B operation fights V04, defeats `--allow-delete`'s purpose, and produces a misleading §8 deliverable. This is the largest single gap in the document.

**Recommended resolution**

Introduce explicit lineage. It is small: two anchor attributes, two registry statuses, one V04 clause, two Excel values.

- **Anchor attributes** — `supersedes:<ID>[,<ID>…]` on a block that absorbed others; `split_from:<ID>` on each block carved out of an existing one. Written by the agent as part of the edit, so lineage is stated at the point of the change, in the file, reviewable in the diff.
- **`meta/ids.json` statuses** — extend `status` beyond `active`/`deleted` with `merged` (plus `merged_into: <ID>`) and `split` (plus `split_into: [<ID>…]`). `specctl validate --assign-ids` records them.
- **V04 becomes** — *error if an ID present in `--base` is absent from the working tree **and** no surviving block claims it via `supersedes`/`split_from`, unless `--allow-delete`.* Add **V04a** (warn): a lineage claim naming an ID that does not exist in `--base`.
- **§8.2 `Change`** gains `merged` and `split`. `Old content` is resolved through the lineage chain: for `merged`, the concatenated old text of the superseded blocks; for `split`, the old text of the parent, repeated on each child with a note.

`--allow-delete` then returns to meaning what it says: content was genuinely removed, and a human said so.

**Alternative, if the pilot budget cannot absorb this** — forbid split and merge in `restructure-section` (§15.1 `allowed_changes` becomes `"reorder, rewrite prose"`), and state the restriction in `B-limitations-roadmap.md` as a new limitation with its own trigger condition. Cheaper, and it makes the improvement skill materially weaker. Owner's call.

#### GAP-07 — Re-ingest key is built on heading numbers, which churn

**A-ref:** §6.5 · **Affects:** §6.6 tests A5 and A6, §13 threshold #5

**What A says**

> `key` = `<heading path>|<type>|<ordinal within section>|<text hash>`
> On `--reingest`, match candidates in this order: (1) exact `key`; (2) same heading path + type + text hash; (3) same heading path + type + ordinal with text similarity ≥ 0.85; otherwise allocate a new ID and mark the old one `deleted`.

**Why it fails**

Two problems, both fatal to threshold #5 (100% ID stability).

1. **"Heading path" is undefined, and the obvious reading is unstable.** §5.3 shows `path: ["3", "3.2"]` — heading *numbers*. Insert one new section at 3.2 and everything below renumbers: every key under it changes, so match (1) fails, and matches (2) and (3) both key on "same heading path" and fail too. Every block in the affected subtree is marked `deleted` and re-allocated. On an automotive SYS spec, inserting a section is routine. The first real re-ingest destroys the ID registry.
2. **Matching is described per-candidate, so IDs can swap.** Step (3) accepts the first candidate above 0.85 similarity. Specs are full of near-identical boilerplate paragraphs ("The system shall log the event."). Two such paragraphs in one section can be matched to each other's IDs, silently transposing history and, through §8.2, the rationale shown to the customer.

**Recommended resolution**

- **Key on IDs, not numbers:**

  > `key` = `<ancestor section IDs, root-first, slash-separated>|<type>|<ordinal within section>|<text hash>`

  Ancestor IDs are immutable by §5.2, so inserting or renumbering a section changes no key. Add `path_ids` to the section schema alongside the human-readable `path`.
- **Match as a global assignment, not first-match:** compute all candidate pairs within a section, sort by (tier, similarity) descending, and consume greedily so each old ID and each new block is used at most once, breaking remaining ties by document order. State the tie-break, because A5 requires determinism.
- Keep the 0.85 threshold and the tier order; only the key and the assignment strategy change.

#### GAP-08 — Nothing regenerates derived front matter

**A-ref:** §9 vs. §5.3 · **Affects:** §13 threshold #6, agent navigation (§10.1), §8 export

**What A says**

> `specctl index  # regenerate index.md, backlinks.md, coverage.md`

and §5.3 front matter containing `number`, `title`, `level`, `parent`, `order`, `path`, `breadcrumb`, `refs_out`, `blocks`.

**Why it fails**

Every one of those keys is *derived* — from the heading line, from the document tree, or from the body's wikilinks. None survives editing:

- Rename a heading and the section's own `title`, and **every descendant section's `breadcrumb`**, are wrong. `breadcrumb` is what §10.1 tells the agent to navigate by, so the agent is then navigating by stale data with no warning.
- Add or remove a wikilink and `refs_out` is wrong. Nothing validates it; `backlinks.md` is regenerated from the body, so the two disagree silently.
- `blocks` is covered by V09, but only as a warn, and only for that one key.

`specctl index` regenerates the four vault-level files and nothing inside the section files. So A has no owner for roughly half of its own normative front matter.

**Recommended resolution**

- Add a command that owns derived front matter:

  > `specctl fmt [PATHS...] [--check]` — recompute `number`, `title`, `level`, `parent`, `order`, `path`, `path_ids`, `breadcrumb`, `refs_out`, `blocks` from the file bodies and the document tree; normalise F9 formatting (see GAP-24); add required `^id` markers (F4, see GAP-03). `--check` reports without writing and exits 1 on any difference.

  Authored keys (`id`, `doc`, `source`, `ingest_version`, `generated`, `bookmarks`) are never touched.
- Add **V15** (warn, auto-fixable): derived front matter disagrees with the file body or the document tree. V09 becomes a special case of it.
- Add to §10.1 CLAUDE.md: *never hand-edit derived front matter; edit the heading line and run `specctl fmt`.*
- Add `specctl fmt` to the §10.3 workflow between steps 2 and 3, and to the §11 runbook next to `specctl index`.

#### GAP-09 — `eval/` and `references/` are used but absent from the layout

**A-ref:** §5.1 vs. §10.2, §12 · **Affects:** §13 threshold #8, the W2-D6 gate

**What A says**

§5.1 lists `CLAUDE.md`, `.claude/`, `source/`, `vault/`, `meta/`, `exports/`, `tests/`. But §10.2 has skill `write-eval-questions` producing `eval/questions.yaml`, and `restructure-section` which "must reference `references/target-structure.md`" — the latter being the W2-D6 gate, described in §12 as **"Gate: no example, no improvement skills"**.

**Why it fails**

§5.1 is inside the section A marks NORMATIVE and tells the implementer not to deviate from. Two directories the plan depends on are not in it, so their location, and whether they are committed, is left to invention. `eval/questions.yaml` is the evidence base for threshold #8 (golden-set answers ≥ 80%); `references/target-structure.md` gates a third of the schedule.

**Recommended resolution**

Add to the §5.1 tree, and to the commit list beneath it:

```
├── references/
│   └── target-structure.md         # OWNER-AUTHORED — the W2 D6 gate (§12)
├── eval/
│   ├── questions.yaml              # golden set (§10.2, §13 #8)
│   └── runs/                       # dated result files, committed
```

State that `references/` is owner-authored and never generated, and that `eval/` is committed so before/after runs are comparable.

#### GAP-10 — Preamble and levels above `split_level` are undefined

**A-ref:** §5.3, §6.1, §6.2 step 7 · **Affects:** §13 threshold #2, §11 runbook day 1

**What A says**

> A section file contains **one heading block and all content until the next heading of the same or higher level**.
> `--split-level N  heading level that starts a new file (default 2)`

**Why it fails**

Two unanswered questions, both of which a real SYS spec hits on page 1:

1. **Does a level-1 heading start a file?** "Heading level that starts a new file (default 2)" reads as *level 2 and only level 2*. Then a level-1 heading and any prose directly under it belong to no file. If the intent is "levels 1 through N", the rule does not say so.
2. **Where does content before the first heading go?** Cover page, document control block, scope statement, and above all the **revision history table** — which in an ASPICE SYS spec is contractual content, not decoration. There is no file for it, so it is either dropped (violating D3 and depressing the §13 #2 fidelity number) or invented into some location the spec never names.

**Recommended resolution**

> Headings at levels `1..split_level` each start a new section file. Content appearing before the first heading is collected into a synthetic front-matter section that takes the first allocated ID, with `number: ""`, `title` taken from the document title property (fallback `"Front matter"`), `level: 0`, `generated: false`. It is an ordinary editable section in every other respect.

#### GAP-11 — "Never silently drop" is implied everywhere, stated nowhere

**A-ref:** §13 #1 vs. §6.4 · **Affects:** D3, §13 thresholds #1 and #2

**What A says**

> §13 #1 — Blocks with valid unique IDs: **100%**
> §6.4 `issues` — `{ "severity": "error", "code": "table_parse_failed", "paragraph": 1044 }`

**Why it fails**

A table that failed to parse is recorded as an issue, but A never says what is *written into the vault* in its place. If nothing is written, content is gone — which is precisely the outcome D3 exists to prevent ("the spec is contractual; a hallucinated sentence is unacceptable" — an omitted requirement is worse). If something is written, its type, lock state and ID are unspecified, and threshold #1's "100%" is being measured against a block population that excludes the failures.

The invariant is visible in a dozen places in A — "Conversion failures are logged, never silently dropped" (§5.4), "Always write raw OOXML beside it" (§6.2) — but is never stated as a rule, so it is not testable.

**Recommended resolution**

Add to §5.4 as a lead-in rule:

> **Total-capture invariant.** Every construct in the source document produces at least one block with an ID in the vault. When a construct cannot be represented in its intended form, it degrades — never disappears — to a `raw` block with `locked:true` and `fallback:true`, carrying the verbatim OOXML in `assets/<ID>.xml` and the extractable plain text inline, accompanied by an `issues` entry naming the reason. Coverage counts a degraded block as captured-with-fallback, never as captured or as skipped.

Add an acceptance test: **A8** — a fixture with a deliberately malformed table produces a `raw locked fallback` block with an ID, an `issues` entry, and no loss of the cell text from the fidelity measurement.

---

## 3. S2 — Undefined algorithms

#### GAP-12 — `text_fidelity.ratio` is a net figure and cannot prove its claim  *(owner decision, see §6.3)*

**A-ref:** §6.4 · **Affects:** §13 threshold #2, the W1-D1 go/no-go

**What A says**

> `text_fidelity.ratio` compares normalized text extracted independently from OOXML with the text emitted into the vault. This is the primary automated proof that nothing was silently dropped.

with `"source_chars": 412839, "emitted_chars": 411902, "ratio": 0.9977`.

**Why it fails**

It is a ratio of two totals, so additions mask deletions. The extractor *legitimately* adds text on every page: rendered heading numbers (F5), literal list numbers (§5.4), figure captions, wikilink display text. And §5.4 emits text-box content **twice** — once inside the rendered fallback's caption, once as a `raw` block "so it is searchable". A vault that dropped 1% of paragraphs and added 1% of numbering scores 1.0000. The ratio can legitimately exceed 1, at which point the number is not interpretable at all.

Beyond that, "normalized" and the scope of "source text" are undefined: headers and footers, footnotes, text-box content, TOC field results, and `w:del` runs (GAP-20) each move the denominator by percent-scale amounts. §13 threshold #2 is stated to three decimal places against an undefined quantity.

**Recommended resolution**

Replace the metric with a directional one and report additions separately:

```json
"text_fidelity": {
  "scope": ["body", "footnotes", "textboxes"],
  "source_segments": 3184,
  "segments_covered": 3179,
  "coverage": 0.9984,
  "uncovered": [{"paragraph": 1044, "chars": 218, "reason": "table_parse_failed"}],
  "added_chars": 4127,
  "added_breakdown": {"heading_numbers": 1204, "list_numbers": 2611, "captions": 312}
}
```

- **`coverage`** = fraction of normalized source segments (one per source paragraph or table cell) found in the emitted text. Directional: additions cannot raise it, and every miss is enumerated with its paragraph index, so a failure is actionable rather than a number.
- **Normalization**, normatively: NFKC, collapse all whitespace runs to one space, strip leading/trailing space, drop zero-width characters, casefold. Nothing else — no punctuation stripping, since units and ranges matter (GAP-13).
- **Scope**, normatively: body, footnotes and text boxes are in; headers, footers and TOC field results are out and counted as `skipped` (GAP-22). Source segments are computed against the accepted revision state (GAP-20), so a discarded `w:del` run is never counted as uncovered.
- §13 threshold #2 becomes `text_fidelity.coverage ≥ 0.99`, with `uncovered` reviewed by hand — which is what §11's "review, fix leftovers by hand" already assumes.

Owner confirms before W1-D1, because this is the measurement the Markdown-as-store decision (D1, and B §6 decision 1) is made on.

#### GAP-13 — Numeric-change detection has no tokenizer and no pairing rule

**A-ref:** §7.2 V10, §7.3 · **Affects:** §13 threshold #7, §8.3, §14's primary control

**What A says**

> **V10** warn — always reported prominently — Any numeric value or unit changed inside a block (report old → new, per block)
> `V10  warn   SYS-000121  number changed: "50 ms" -> "80 ms"`

and §14 names it the response to "Agent silently changes values".

**Why it fails**

V10 is the design's main defence against the failure mode §2.2 calls Problem B's risk, and it is one sentence. Undefined:

- **What is a number.** `0–100` (one range or two numbers?), `3.2` in "section 3.2", `SYS-000120`, `1,000` vs `1.000`, `50ms` vs `50 ms`, `1e-3`, `0x1F`, `±5%`, "two" spelled out.
- **What is a unit.** No vocabulary. Is `%` a unit? `ms` vs `msec`? A signal name ending in a digit?
- **How old pairs with new.** `"50 ms" -> "80 ms"` presumes alignment. After a restructure that splits one paragraph into three and reorders them, there is no alignment — but V10 must still fire, because that is exactly the edit under which a value could be slipped through.

An implementer will invent something; whatever they invent will either flood the reviewer with false positives on section numbers and IDs, or align wrongly and report `"50 ms" -> "100 %"`.

**Recommended resolution**

- **Token grammar**, normative: a numeric token is `[+−±]? digits ( [.,] digits )* ( [eE][+−]?digits )?` optionally followed by a unit, where the unit is one whitespace-or-nothing then a token from the unit vocabulary. A range `A–B` (en dash or hyphen between two numeric tokens) is two tokens plus a `range` flag. **Excluded:** tokens matching the ID pattern `[A-Z][A-Z0-9]{1,7}-\d{6}`, tokens inside a wikilink target, tokens on a heading line, and tokens matching a section-number pattern `\d+(\.\d+)+` when preceded by "section", "clause", "§" or "Figure"/"Table".
- **Unit vocabulary** in `specctl/validate/units.txt`: SI units and prefixes, `%`, time/frequency/voltage/current/temperature/pressure units, plus a project-extensible list. Unknown trailing tokens are not treated as units; the number is still compared.
- **Comparison**: per block, build the **multiset** of `(normalized value, unit)` pairs for base and working text, and report the symmetric difference — `removed:` and `added:` lists. Only when exactly one pair is removed and one added does V10 print the `old -> new` arrow form. This is always computable, is invariant under reordering and rewriting, and never misaligns.
- §8.3's `Numeric change` column consumes the same structure.

Extend acceptance test **B2** with a split-and-reorder fixture where the multiset is unchanged (must be silent) and one where a value moved between blocks (must report in both).

#### GAP-14 — Shape rendering has no element-to-region mechanism

**A-ref:** §6.2 step 6 · **Affects:** the W1 D3–D4 timebox, §13 threshold #4 by proximity

**What A says**

> **Render fallbacks.** If `--render-shapes`, convert the docx to PDF via LibreOffice once, then crop/export the page region for each unrenderable element; if cropping is unreliable, export the whole page image and reference it. Always write raw OOXML beside it.

**Why it fails**

Nothing maps an OOXML element to a page region. A PDF produced by LibreOffice carries no element identity, and the extractor is parsing `document.xml` directly, so it knows an element's anchor in the *flow* but not its coordinates on a *rendered page* — the two are related only by running a full layout engine. The step also never says how to know which page a given element landed on. This is the single most expensive sentence in A: it sits inside the W1 D3–D4 timebox and §14 already identifies "extractor consumes the whole budget" as the top risk.

**Recommended resolution**

- **Primary path:** `soffice --convert-to html` instead of PDF. LibreOffice writes each drawing, text box, SmartArt and OLE object as a separate image file beside the HTML, in document order. Match them to the block stream by order of appearance among rendered objects — an index-to-index mapping the extractor already has from step 2, with no layout reasoning.
- **Fallback, unchanged from A's intent:** whole-page PNG plus `assets/<ID>.xml` plus the `raw` text block. Record `shapes.raw_only` in coverage as §6.4 already does.
- **Timebox it as a W1-D1 spike** alongside the fidelity gate, since it is a binary question — does LibreOffice emit one image per drawing on the real file, yes or no — answerable in an hour, and §14's accepted response ("store them as raw OOXML + rendered image, flag `locked`, note the limitation") is already written.

#### GAP-15 — OMML to LaTeX path is unreachable as described

**A-ref:** §5.4, §15.3 · **Affects:** coverage `formulas`, §13 threshold #2

**What A says**

> | Equation (OMML) | `$...$` or `$$...$$` if conversion succeeds, else image fallback |

with §15.3 listing `pandoc` as an "optional external binary (equations)".

**Why it fails**

Pandoc converts OMML when it reads a whole `.docx`. The pipeline in §6.2 parses OOXML directly and never hands a document to pandoc, so there is no point at which pandoc sees the equation. Feeding it one equation means synthesising a minimal `.docx` per formula — workable but slow and entirely unstated. With ~12 formulas (§6.4's example) an implementer will improvise, and improvised OMML handling is silently lossy.

**Recommended resolution**

> OMML is converted in-process: apply the `OMML2MML.XSL` stylesheet (ships with Office, vendored into `specctl/ingest/xsl/`) to obtain MathML, then MathML to LaTeX via a pure-Python converter. On failure, fall back to the rendered image path of GAP-14 and record `formulas.image`. Pandoc is not used; remove it from §15.3.

Both outcomes are already counted by §6.4's `formulas: {total, latex, image}`.

#### GAP-16 — One `--fail-under` scalar for three different thresholds

**A-ref:** §6.1 vs. §13 · **Affects:** the W1-D1 gate, CI

**What A says**

> `--fail-under PCT  exit non-zero if link or table coverage < PCT (default 0)`

while §13 sets links ≥ 95%, tables ≥ 90%, fidelity ≥ 0.99, and threshold #1 at 100%.

**Why it fails**

One scalar cannot express three different thresholds. Set it to 95 and every run fails on tables; set it to 90 and link regressions pass unnoticed. Fidelity, the most important of the three, is not covered by the flag at all.

**Recommended resolution**

Replace with per-metric gates defaulting to the §13 values:

```
--fail-under-links PCT       default 95
--fail-under-tables PCT      default 90
--fail-under-fidelity RATIO  default 0.99
--no-gates                   disable all of the above (day-1 exploration)
```

All four overridable from `specctl.toml` (GAP-26). Exit code 2 on any breach, with the breached metric named. Note that the default is now *on*, inverting A's `default 0` — the day-1 exploratory run uses `--no-gates` explicitly.

#### GAP-17 — Excel `Rationale` needs per-block blame that is never specified

**A-ref:** §8.2 · **Affects:** §8.5 acceptance, export runtime

**What A says**

> | Rationale | Commit rationale of the last commit touching that block |

**Why it fails**

"Touching that block" means per-block attribution across a file whose line numbers shift with every edit — `git log -L` over a moving range, re-run for each of ~1200 blocks, against a commit whose rationale describes the *section* and may cover twenty blocks at once. Cost is quadratic-ish and the answer is not more precise than the section it came from. A specifies neither the mechanism nor the precision.

**Recommended resolution**

Source it from data already recorded rather than recomputing it:

> `Rationale` and `Commit` are resolved from `vault/log.md`, which records timestamp, SHA, section ID and rationale per edit (§9.2). For a block, take the most recent `log.md` row whose section ID matches the block's owning section and whose commit is an ancestor of `--ref`. Attribution is therefore **section-level**; state this in the sheet header note.

Blocks changed outside the logged workflow (direct hand edits) get the SHA of the last commit touching the file and an empty rationale — which is itself a useful signal that the workflow was bypassed.

#### GAP-18 — `--base` defaults to `HEAD`, which silences the validator on a branch

**A-ref:** §7.1 vs. §10.3 · **Affects:** V04, V05, V10, V12 — every comparison rule

**What A says**

> `--base REF  git ref to compare against (default: HEAD)`

while every invocation in §10.3 and §11 passes `--base main`.

**Why it fails**

On an edit branch, `HEAD` is the branch tip — the agent's own committed work. After step 7 of §10.3 (`git commit`), a bare `specctl validate` compares the working tree against the edit that was just made and finds nothing: V04, V05, V10 and V12 all report clean on a commit that changed a locked figure and three values. The safe default is the one nobody types, and the correct one has to be remembered every time — the same failure mode B §3 flags as L13.

**Recommended resolution**

> `--base REF` — git ref to compare against. Default: `merge-base(HEAD, <default branch>)`, i.e. the point the current branch diverged. On the default branch itself, defaults to `HEAD`. The resolved ref is always printed in the summary line.

§7.3's summary already prints `base=HEAD`; making the resolved SHA explicit there means a misconfigured comparison is visible in the output the agent is required to report verbatim (§15.1 step 5).

#### GAP-19 — Global block order is required by Excel and never defined

**A-ref:** §5.3 vs. §8.2 · **Affects:** §8.5 test C3

**What A says**

> §5.3 front matter: `order: 14`
> §8.2: | Order | Global document order index |

**Why it fails**

Front matter carries one `order` per *section* file (the example's section has 9 blocks and `order: 14`, so it is plainly a section index). §8.2 needs a *global block* index. Nothing defines how blocks are ordered, and test C3 ("a moved block … shows the new order") cannot be written against an undefined quantity.

**Recommended resolution**

> `order` in section front matter is the section's zero-based index in document order. Block order within a file is the order of anchors in the file. The export's `Order` column is the block's global index, computed as the position of `(section.order, block index in file)` in the sorted sequence over the whole vault. It is derived at export time and never stored.

#### GAP-20 — Tracked changes: `w:del` text will be emitted as current

**A-ref:** §5.4 · **Affects:** D3, §13 threshold #2

**What A says**

> | Tracked change / comment | Ignored, but counted in coverage as `skipped` |

**Why it fails**

"Ignored" is ambiguous in the one way that matters. A straightforward walk over `document.xml` collecting `w:t` elements picks up text inside `w:del` — content the author *deleted* — and emits it into the vault as current requirement text, while `w:ins` content is also emitted, so the vault contains both sides of every pending revision with no marker distinguishing them. A customer spec delivered mid-review routinely carries unaccepted revisions. This is silent content *fabrication* in a contractual document: the exact scenario D3 is written to prevent, arrived at by parsing rather than by hallucination.

The parallel case: `w:t` inside `w:delText` and comment ranges (`w:commentRangeStart`).

**Recommended resolution**

> Revision markup is resolved to the **accepted** state: content inside `w:ins` is emitted as normal body text; content inside `w:del`/`w:delText` is discarded. Comments (`w:comment`, `w:commentReference`) and comment ranges are discarded, their anchor text retained. Coverage records `revisions: {ins_accepted, del_discarded, comments_discarded}` and, when any count is non-zero, emits a `warn` issue `source_has_unresolved_revisions` — the source file should be reviewed before it is treated as a baseline.

Add acceptance test **A9** on a fixture carrying one insertion and one deletion.

#### GAP-21 — `w:sdt` content controls vanish without error

**A-ref:** §6.2 step 2 · **Affects:** D3, §13 threshold #2

**Why it fails**

Structured document tags wrap content in `w:sdt` / `w:sdtContent`. They are common in customer-templated specs — document-control fields, drop-down status cells, repeating requirement blocks. A block-stream walker that iterates `w:body/w:p` and `w:body/w:tbl` sees the `w:sdt` element, does not recognise it, and skips the paragraphs nested inside it. No error, no issue entry, no trace in coverage beyond a fidelity number nobody can attribute (GAP-12). A never mentions `w:sdt`.

**Recommended resolution**

> The block stream walker descends into `w:sdt`/`w:sdtContent` transparently, treating nested paragraphs and tables as if they appeared at the `w:sdt`'s position. The same applies to `mc:AlternateContent` (prefer `mc:Choice`, fall back to `mc:Fallback`) and to `w:smartTag`. Any unrecognised element containing `w:p` or `w:tbl` descendants is descended into and recorded once as `unknown_container` in coverage.

That last clause is the general defence: an unknown wrapper degrades to captured-with-a-note rather than to silence.

#### GAP-22 — TOC field, cover page, revision history, headers/footers undecided

**A-ref:** §6.2, §6.4 · **Affects:** §13 thresholds #2 and #3

**Why it fails**

Four constructs guaranteed to be in an ASPICE SYS spec, none addressed:

- **TOC field.** A Word TOC expands into dozens of paragraphs of hyperlinks to `_Toc…` bookmarks. Ingested naively, they become vault content duplicating `index.md`, and — worse — they inflate `links.word_links_found` by a hundred or more, so §13 threshold #3 (≥ 95% resolved) is computed mostly over links nobody cares about, masking real unresolved references.
- **Headers and footers.** Separate parts (`header1.xml`). In or out of the fidelity denominator? Undefined, and they are repeated per section, so getting it wrong moves the number measurably.
- **Cover page and revision history.** See GAP-10 — no file exists to hold them.

**Recommended resolution**

> - TOC field results (`w:fldSimple`/`w:instrText` containing `TOC`, and paragraphs styled `TOC \d+`) are skipped, counted as `skipped.toc`, and excluded from both the link counts and the fidelity scope.
> - Headers and footers are skipped, counted as `skipped.header_footer`, excluded from the fidelity scope.
> - Cover page and revision history are ordinary content, captured by the front-matter section of GAP-10.
> - Coverage gains a `skipped` object enumerating every skip code with its count and character total, so what was deliberately dropped is visible next to what was captured.

---

## 4. S3 — Minor

#### GAP-23 — `--no-git` is undocumented; ingest and the runbook both commit

**A-ref:** §6.1 vs. §6.2 step 12, §11

§6.2 step 12 reads "Git: if the repo is clean, commit and tag `SYS-baseline-v0` (skip if `--no-git`)" — but `--no-git` is not in the §6.1 option list, and §11's runbook then does `git add -A && git commit && git tag SYS-baseline-v0` by hand, so following both produces an empty commit and a duplicate-tag error.

**Resolution:** make ingest never touch git; delete step 12 and the flag; keep the runbook as the single place git is driven. (If auto-commit is preferred instead, add `--no-git` to §6.1 and delete the git lines from §11 — but one of the two must go.)

#### GAP-24 — No validator rule enforces F9 formatting

**A-ref:** §5.3 F9 vs. §7.2

F9 mandates UTF-8, LF, one blank line between blocks, no trailing whitespace. No V-rule checks any of it, so a vault can drift out of the contract and still validate clean — and the drift shows up as diff noise in exactly the human review step (§10.3 step 5) the design relies on.

**Resolution:** **V16** (warn, auto-fixable) for F9 violations, fixed by `specctl fmt` (GAP-08); `specctl fmt --check` in the pre-commit hook B §3 L13 proposes.

#### GAP-25 — Runbook writes a commit message into `.git/`

**A-ref:** §11

`git commit -F .git/COMMIT_MSG` puts a working file inside the git directory, where it collides with git's own `COMMIT_EDITMSG` conventions and is invisible to the agent's own tooling.

**Resolution:** write to a temp file outside the repo, or configure `commit.template`. Since §15 says "copy these shapes literally", this one matters more than its size suggests.

#### GAP-26 — No config file; options repeat across commands

**A-ref:** §6.1, §7.1, §8.1

`--doc-key`, `--split-level`, the gate thresholds (GAP-16), the default branch (GAP-18) and the export paths are re-supplied on every invocation, so the runbook's correctness depends on retyping them consistently.

**Resolution:** `specctl.toml` at the repo root with `[project]` (doc_key, split_level, default_branch), `[gates]` (§13 thresholds) and `[export]`. CLI flags override; the resolved configuration prints in `--verbose`.

#### GAP-27 — `Model:` trailer assumes the agent knows its own model ID

**A-ref:** §10.4

`Model: claude-<model-id>` in the commit trailer. An agent cannot always report its own model ID reliably, and a guessed one in a contractual audit trail is worse than an absent one.

**Resolution:** make the trailer optional, or `Model: <filled at review>`. The §8.2 `Rationale` chain (GAP-17) does not depend on it.

#### GAP-28 — The A1 fixture cannot be authored with `python-docx`

**A-ref:** §6.6 A1, §15.3

A1 requires a fixture containing a text box, an equation and (per §5.4) SmartArt and OLE. `python-docx` cannot author any of those; they need raw XML injection or a hand-made file. Left unsaid, the implementer builds what the library allows and silently drops the constructs the test exists to cover.

**Resolution:** hand-author `tests/fixtures/constructs.docx` in Word, commit it, and document what it contains and why in `tests/fixtures/README.md`. Generate the simpler fixtures (headings, lists, simple tables, cross-references) programmatically so they stay editable. Add the degraded-table fixture (A8, GAP-11) and the revisions fixture (A9, GAP-20) to the same file or beside it.

#### GAP-29 — Word counts break on CJK, which survives the translation

**A-ref:** §9.1, §7.2 V14

`index.md` carries a word count and V14 fires above 1500 words. Whitespace-splitting counts a 200-character Japanese run as one word. NG5 says no Japanese support, but the source is a *translation* of a Japanese document: signal names, figure labels, table headers and untranslated notes routinely survive it.

**Resolution:** define the count — Latin tokens by whitespace, plus CJK codepoints divided by 2.5, summed. One line in §9.1; it keeps V14 meaningful and prevents an oversized section from hiding.

#### GAP-30 — `ingest_version` has no bump or migration semantics

**A-ref:** §5.3, §6.4

The key exists in both front matter and coverage with no statement of when it increments or what a consumer does on a mismatch — so it cannot serve the purpose it was added for.

**Resolution:** state that it increments when the serialization contract (§5.3, §5.4) changes in a way that makes an older vault non-conforming; `specctl validate` reports an error naming the required migration when a file's `ingest_version` is below the tool's.

#### GAP-31 — Moving a block between sections and creating a section are impossible

**A-ref:** §10.3 vs. §2.4

§10.3 step 2 restricts the agent to "vault/sections/SYS-000120.md only". Two consequences are neither supported nor listed as non-goals:

- **Moving a block to a better-fitting section** touches two files, so it is forbidden — yet it is an obvious restructuring outcome.
- **Creating a new section** requires an ID *before* the file can be named `<section-id>.md`, and §5.2 only says `--assign-ids` allocates IDs for new blocks. Who creates and names the file is unstated.

**Resolution:** the cheap option is to declare both out of scope in §2.4 (NG10: no cross-section moves; NG11: no new sections in this phase) and note them in `B-limitations-roadmap.md` with trigger conditions. The fuller option is to extend `--assign-ids` to allocate the heading ID, create the file, and update `parent`/`order` on its neighbours — which is also the GAP-06 lineage machinery applied at section granularity. Either is fine; silence is not, because the agent will hit this in the first restructure.

---

## 5. Impact on §13 acceptance thresholds

Thresholds that cannot be met, or cannot be measured, while the listed gaps stay open:

| §13 | Threshold | Blocked by |
| --- | --- | --- |
| #1 | Blocks with valid unique IDs — 100% | GAP-11 (failures have no defined block, so the population is undefined) |
| #2 | `text_fidelity.ratio` ≥ 0.99 | GAP-12 (metric cannot prove its claim), GAP-20, GAP-21, GAP-22 (uncounted loss and undefined scope), GAP-10 (preamble has nowhere to go) |
| #3 | Word internal links resolved ≥ 95% | GAP-04 (non-heading targets become dead links counted as resolved), GAP-22 (TOC inflates the denominator) |
| #4 | Tables preserved ≥ 90% | GAP-11 (a failed table's fallback is undefined, so "preserved" is undefined) |
| #5 | Re-ingest ID stability — 100% | GAP-07 (keys churn on renumber), GAP-05 (the test that measures it cannot pass) |
| #6 | Sections improved end to end ≥ 3 | GAP-06 (split/merge fights V04), GAP-31 (no cross-section moves), GAP-08 (front matter goes stale) |
| #7 | Validator detection on fixtures — 100% | GAP-13 (V10 undefined), GAP-06 (V04 unusable during normal editing), GAP-18 (default base silences comparisons) |
| #9 | Excel change columns correct | GAP-06 (split/merge mis-reported as deletion), GAP-17 (rationale source), GAP-19 (order undefined) |

Thresholds #8 (golden-set accuracy) and the §12 schedule are affected only indirectly, via GAP-09 (`eval/` and `references/` have no home).

---

## 6. Owner decisions

Three findings are policy, not engineering. They are listed here rather than resolved above.

### 6.1 Block lineage (GAP-06)

Adopting lineage adds anchor attributes, two registry statuses, a V04 clause and two Excel values — a real addition to the W2-D9 validator scope. Declining it means `restructure-section` may not split or merge blocks, which makes the pilot's central improvement skill materially weaker, and that restriction belongs in B with a trigger condition. The register recommends adopting; the decision is the owner's because it moves schedule.

### 6.2 Confidential content and the cloud model

A §2.5 states "Local only" and D5 selects Claude Code as the agent and editor. Those two are in tension and A never resolves it: Claude Code sends the spec content it reads to a hosted model. The source is a customer's contractual system specification. B raises local LLM only as a cost/security *option* (L11), triggered "when there is a cost or security constraint" — not as a question already answered.

Nothing here suggests the arrangement is wrong; it may well be covered by the customer agreement. But A is the document a coding agent and a reviewer work from, and it should say so explicitly. **Recommended:** add one line to §2.5 recording the customer's position on cloud model processing of spec content, and its date.

### 6.3 Fidelity metric definition (GAP-12)

Replacing the ratio with directional coverage changes §13 threshold #2 and the W1-D1 go/no-go criterion — the gate that decides whether Markdown is a sufficient store at all (B §6, decision 1). The owner should confirm the new definition **before D1**, since the measurement is run that day and the decision is hard to revisit afterwards.

---

## 7. Suggested sequencing

If the register is accepted, the resolutions land naturally in three groups:

1. **Before any code** — GAP-01–GAP-05 (§5 contract), GAP-07 (ids key), GAP-09–GAP-11 (layout, preamble, invariant), GAP-12 and GAP-16 (the D1 gate and its thresholds). These change what the implementer builds on day one.
2. **Before the W1 D3–D4 extractor** — GAP-14, GAP-15, GAP-19–GAP-22 (the parsing decisions), GAP-28 (fixtures). GAP-14 is a D1 spike, not a D3 decision.
3. **Before the W2 D9 validator and D10 export** — GAP-06 (owner decision first), GAP-08, GAP-13, GAP-17, GAP-18, GAP-24. GAP-23, GAP-25–GAP-27, GAP-29–GAP-31 are editorial and can ride along.

Nothing in this register requires rework of a resolution in an earlier group.
