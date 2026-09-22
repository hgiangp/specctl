# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Not to be confused with the `CLAUDE.md` that §14 of the implementation spec specifies. That
> one is a *deliverable* — agent conventions for reading and editing a generated vault, due
> with F15 — and belongs in the vault workspace, not here. This file is about developing
> `specctl` itself. Do not overwrite it with the §14 content.

## What this is

`specctl` turns one Word system requirements spec (automotive, ASPICE SYS.2, a contractual
document) into a Markdown vault where every block carries an immutable ID, with *measured*
evidence that no content was lost and no number changed silently.

**The specification is normative and the code follows it.** `docs/D-implementation-spec.md`
(v2.3) is the contract; module and function docstrings cite it (`§9.2`, `FMT-04`, `V10`,
`DEC-12`, `T-ING-05`) and those references are how you find the rule a line of code implements.
Grep the spec for the marker before changing behaviour it governs.

| Document | Use for |
|---|---|
| `docs/F-features.md` | Read first. The problem, the four failure modes, and the feature order F01–F31 with a **status** line each |
| `docs/D-implementation-spec.md` | The normative rule for every behaviour. Appendix D is a conforming section file to copy literally |
| `docs/G-data-contract.md` | The data-contract decisions and why each went the way it did |
| `docs/H-testing.md` | Running tests, adding `.docx` fixtures, the pandoc cross-check |
| `docs/B-limitations-roadmap.md` | What is deliberately out of scope |
| `docs/archive/` | History. Never implement from it |

Planning docs are in Vietnamese; the spec, code, docstrings and test names are in English.
Keep that split.

**§1.2, the standing rule:** if a normative rule turns out to be impossible on the real
source document, stop and report it — do not invent a variant. A genuine choice goes the way
that preserves source fidelity, and gets recorded as an issue (Appendix B). When a decision
has to change, write it up in `G-data-contract.md` and amend `D-implementation-spec.md` with a
version bump; do not leave code and spec disagreeing.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate    # Python >= 3.11 (tomllib)
pip install -e ".[dev]"

pytest                                   # whole suite, ~20s
pytest -rs                               # with the reason for every skip
pytest tests/test_sectionfile.py -v      # one file — the round-trip, the core of the project
pytest tests/test_sectionfile.py::test_appendix_d_round_trips_byte_for_byte -vv   # one test
pytest -k "round_trip or canonical"      # by name

python scripts/spike_coverage.py source/SYS.docx                     # what the real doc contains
python scripts/spike_coverage.py source/SYS.docx --pandoc --json spike.json
```

Expected baseline with pandoc installed: **394 passed, 4 skipped**; without it, **381 passed,
17 skipped**. The skips are meaningful — the 4 are the three hand-authored `.docx` fixtures that
are not committed yet, plus the check that reports them. The walker and oracle tests that used
to wait on those files now run against the committed `built_*.docx` stand-ins (F04). A
different count, or zero skips, means something is wrong.

There is no linter or formatter configured; `pytest` (`-q --strict-markers`, `testpaths=tests`)
is the whole gate. `pip install -e` also puts a `specctl` entry point on PATH; `specctl --verbose
<command>` prints every resolved setting and where it came from.

F01–F05 have landed. The OOXML reader works and is tested, but **every CLI command still
deliberately exits 4 (`USAGE`)** naming the feature that will build it: `ingest` needs F06–F11
before it can write a vault. That is correct behaviour, not a bug.

## Architecture

```
source/SYS.docx  --ingest-->  vault/sections/SYS-000120.md  --agent edits-->  fmt --> validate
                              vault/assets, index.md, log.md,                          |
                              backlinks.md, coverage.md, meta/ids.json          human reviews diff
                                                                                       |
                                                                              commit --> export xlsx
```

`docs/D-implementation-spec.md` §3.1 has the full picture and §4 the repository layout that
`ingest` produces. Everything outside the Python package — Claude Code, git, VS Code diff,
Obsidian, LibreOffice — is used as is.

### Module layering

Dependencies point one way. `exits`, `ids`, `clock` are leaves; `model` depends only on `ids`;
`textutil`, `sectionfile` and `derived` sit on `model`; `cli` sits on everything.

| Module | Owns | Must not |
|---|---|---|
| `exits.py` | The five exit codes (§9.4) and `SpecctlError`, which carries one | — |
| `ids.py` | The block-ID format (`SYS-000120`), its lowercase spelling, and `sort_key` | Let any consumer carry its own regex |
| `clock.py` | The one clock. `--now` fixes it (§9.3) | — nothing in `specctl/` may call `datetime.now()` |
| `model.py` | The §6 data model: block types, anchor attribute order, front-matter shape | Compute anything derived, or touch the filesystem |
| `textutil.py` | The three text functions (§6.6) — `normalize_ws`, `to_plain_text`, `words` | Grow a second definition of "the same text" |
| `sectionfile.py` | Parsing **and** serializing a section file, as a pair | Split the pair across modules |
| `derived.py` | Everything derived: `parent`, `order`, `path`, `breadcrumb`, `blocks`, `words`, `refs_out` | Be reimplemented inside a command |
| `config.py` | Resolution: flag → env → `./specctl.toml` → default, each value remembering its source | Search upward for the config file |
| `ingest/package.py` | Opening a `.docx`: zip members, parts, relationships. Exit `3` on unreadable input | Interpret content |
| `ingest/report.py` | Issue codes (Appendix B), skip accounting (§8.3), revision counts | Let a component invent a code the report cannot render |
| `ingest/walk.py` | The block stream: §10.5 W1–W6, in document order | Decide representation — that is F06–F12, reading the stream |
| `cli.py` | Global flags, config resolution, and turning a `SpecctlError` into an exit code | Hold command logic; nothing else calls `sys.exit` |
| `schema.py` + `schemas/*.json` | Appendix A JSON Schemas, enforced where files are read | — |

Four consumers compare text (fidelity §10.12, the registry's `text_hash` §10.10, the numeric
diff §12.6, the Excel `Content` column §13.5) and they all call `textutil`. `normalize_ws` is
case-preserving and `normalize` is not: unit comparison must use `normalize_ws`, because `mV`
and `MV` differ by nine orders of magnitude (§12.6 N3).

Derived front matter is computed in `derived.py` and nowhere else — the ingest writer, `fmt`
and `index` all need it, and written three times it would be wrong three different ways
(DEC-12).

### Section file format, in two rules that matter most

* **Blocks are delimited by anchors, never by blank lines.** A fenced code block and an HTML
  table both contain blank lines legitimately; splitting on them truncates content while the
  file still parses. This is the failure mode the whole design exists to prevent.
* **Round-trip is the highest-leverage property in the repo.** `serialize(parse(text)) == text`
  for canonical input and `parse(serialize(section)) == section` for any section, checked over
  hypothesis-generated files plus the Appendix D example byte for byte. Any change to the
  parser needs the mirror change in the serializer.

Front-matter scalars are emitted by `sectionfile.emit_scalar`, which over-quotes on purpose:
the vault is read by Obsidian and other YAML 1.2 readers as well as by PyYAML's 1.1, and
`1e5` is a string to one and a float to the other.

## Invariants any change must preserve

These are §9.5 plus the seven non-negotiables of `F-features.md` §6. Each is tested, not just
asserted — breaking one is a failing test, and that is the point.

1. **No network, no LLM in the conversion path** (DEC-03). `tests/support/netguard.py` is
   `autouse` for the whole suite via `tests/conftest.py`, so a dependency added later reaches
   the network exactly once before a test goes red.
2. **Determinism.** Same inputs, config and `--now` → byte-identical output. Every sort key must
   be *total*: no reliance on dict or filesystem order. `tests/support/determinism.py` hashes a
   tree, and is itself tested to *catch* a drifting writer.
3. **`source/` is never written to.** It is the final point of reference.
4. **IDs are never reused** (§5.2). The counter only grows.
5. **`validate`, and any command with `--check`, write nothing** — not the vault, not `meta/`,
   not a temp file inside the repo. They run repeatedly and from a pre-commit hook.
6. **Derived data is owned by tooling.** Hand-edit the heading line, then run `fmt`.
7. **Atomic writes.** `ingest` builds in a temp directory and moves it into place; other
   commands write to a sibling temp file and rename. A failed run leaves no half-written vault.
8. **Five exit codes, no sixth** (§9.4). A stub reports `USAGE`; typer's own exit 2 is remapped.

## Tests

* Test names are sentences (`test_a_fenced_code_block_keeps_its_internal_blank_lines`). Keep
  that — the name is the claim being made.
* `tests/support/generators.py` holds hypothesis strategies that build **conforming** section
  files; the format's own constraints live in the strategies, so a generated counterexample is
  a real bug rather than an unrepresentable input.
* `tests/support/docx.py` builds and inspects `.docx` packages from raw OOXML. It covers what
  Word cannot do — deliberately malformed input (to prove the §6.4 degrade path degrades
  instead of crashing), minimal regressions found later on the real document — and it builds
  the three **stand-in** fixtures that keep F05 testable while the hand-authored files are
  outstanding.
* `tests/support/fixtures.py` is the registry of what each fixture must *contain*, checked
  against the raw XML — because Word does not always save what you think (accepting tracked
  changes drops the `w:del`; emptying a content control drops the `w:sdt`). A hand-authored
  fixture and its stand-in share **one** requirement list, so the stand-in cannot cover less
  than the real file must, and `require(name)` resolves to the hand-authored file the moment it
  lands. A missing hand-authored set skips; **half a set is red**, since that is the state where
  the suite goes green on whatever happens to be present and silently stops covering the rest.
  Adding a fixture: see `docs/H-testing.md` §3 and `tests/fixtures/README.md`, and leave
  `*.docx binary` in `.gitattributes` alone — a `.docx` is a ZIP, and line-ending normalization
  corrupts it invisibly.
* **Built fixtures are committed and must be regenerable.** `python scripts/build_fixtures.py
  --check` compares each committed package part by part against a fresh build; a hand-edited
  `.docx` is the one change no diff shows. What a built fixture cannot settle is whether a
  construct is in the shape *Word* emits — `lxml` reads anything well-formed. That question goes
  to pandoc, and it has already returned a real defect (see §10.5 W1 in spec D).
* **pandoc is a test oracle, never a converter.** Nothing in `specctl/` may import
  `tests/support/pandoc.py`. It drops what it cannot represent silently and exits 0, which is
  exactly what §6.4 forbids; what it is good for is arbitrating — text pandoc finds that our
  reader does not is our bug. A recorded-baseline test going red means pandoc improved: re-run
  the comparison and re-judge the decision, do not delete the test.

## Configuration

One flat name per setting, declared once in `config.py::SETTINGS`, and that name is the
attribute (`cfg.gate_fidelity`), the TOML mapping target (`[gates] fidelity`), the env var
(`SPECCTL_GATE_FIDELITY`) and what `--verbose` prints. Add a setting there and it exists
everywhere at once. A typo in `specctl.toml` is an error, not a shrug, and the config file is
`./specctl.toml` only — an upward search would make behaviour depend on where the operator
stood, which is the opposite of declaring it once (DEC-13).

## The block stream (F05), and what reads it

`walk.py` emits a stream of `StreamItem`s — one per `w:p` or `w:tbl`, in document order, each
with its text already recovered in the accepted-revision state and its embedded objects
(images, text boxes, equations, OLE) carried alongside. It emits no Markdown. Numbering (F06),
segmentation (F07), ID allocation (F08), table representation (F09) and the degrade path (F10)
all read the stream and decide separately. That split is what makes the loss question
answerable on its own: text that reached the stream cannot be lost later without a named
reason.

Three things there are easy to get wrong and are each pinned by a test:

* **Field state survives between paragraphs.** A TOC opens in one paragraph and closes dozens
  later. Judging only the paragraph in hand keeps the whole table of contents as requirements;
  forgetting to pop the field skips the rest of the document *silently*.
* **A skipped paragraph still consumes its index.** Indices address the source, so renumbering
  around a skip makes every issue point one paragraph off.
* **The paragraph index is built from `id()` of lxml elements, so every indexed element is kept
  alive.** lxml frees a proxy when the last reference goes and hands the same address to the
  next one; an `id()` map then starts matching the wrong paragraphs, with no symptom.

**`python-docx` is deliberately not a dependency** (D §1.6, decision 12): its object model hides
`w:sdt`, `mc:AlternateContent`, `w:ins` and `w:del` — exactly what §10.5 must see. Walk the XML
with `lxml`.

## Next

F06 (heading and list numbering, §10.3) and F07 (section segmentation, §10.9), both reading the
block stream.

Still worth doing, though it no longer blocks: put the three hand-authored `.docx` fixtures in
`tests/fixtures/` (F04, owner input). The stand-ins run the walker and the pandoc oracle today,
but a fixture built from raw OOXML only proves the reader handles the OOXML *we imagined*. Some
constructs — SmartArt, OLE objects, a real content control — only Word produces at all.
