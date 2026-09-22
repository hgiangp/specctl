"""Round-trip: the highest-leverage test in the project.

Every command that writes into the vault goes through `parse_section` and
`serialize_section`. If that loop is not closed, a command can corrupt a file — drop a
blank line, reorder an attribute, lose a `^id` marker — and nothing downstream notices,
because the file still parses. That is silent data loss (failure mode 1) arrived at from
the inside.

Two properties, checked over generated input:

* **structural** — `parse(serialize(section)) == section`
* **canonical** — `serialize(parse(serialize(section))) == serialize(section)`, so the
  canonical form is a fixed point and `fmt` is idempotent (T-FMT-02)
"""

from __future__ import annotations

import pytest
import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from specctl.model import ATTR_ORDER, Anchor, Block
from specctl.sectionfile import (
    ParseError,
    emit_scalar,
    parse_anchor,
    parse_section,
    serialize_section,
)

from .support.generators import TEXT_ALPHABET, sections

SLOW = settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)

# The worked example of Appendix D, verbatim, with the `origin` key of F01 decision 6.
APPENDIX_D = '''---
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
'''


# ------------------------------------------------------------------ the worked example

def test_appendix_d_round_trips_byte_for_byte() -> None:
    """Appendix D says to copy this shape literally, so the writer must reproduce it."""
    assert serialize_section(parse_section(APPENDIX_D)) == APPENDIX_D


def test_appendix_d_parses_into_the_documented_blocks() -> None:
    section = parse_section(APPENDIX_D)
    assert [(b.block_id, b.type) for b in section.blocks] == [
        ("SYS-000120", "heading"),
        ("SYS-000121", "paragraph"),
        ("SYS-000122", "table"),
        ("SYS-000123", "figure"),
    ]
    assert section.block("SYS-000121").blockref is True
    assert section.block("SYS-000123").locked is True
    assert section.heading.lines == ("## 3.2 Braking control",)


# ------------------------------------------------------------------ properties

@given(sections())
@SLOW
def test_parse_of_serialize_is_the_identity(section) -> None:
    assert parse_section(serialize_section(section)) == section


@given(sections())
@SLOW
def test_canonical_form_is_a_fixed_point(section) -> None:
    """`fmt` re-serializes what it reads, so serializing twice must change nothing."""
    once = serialize_section(section)
    assert serialize_section(parse_section(once)) == once


@given(sections())
@SLOW
def test_every_serialized_file_ends_with_exactly_one_newline(section) -> None:
    text = serialize_section(section)
    assert text.endswith("\n") and not text.endswith("\n\n")  # FMT-06


@given(sections())
@SLOW
def test_blocks_are_separated_by_exactly_one_blank_line(section) -> None:
    """FMT-06, stated structurally rather than as "no three newlines anywhere".

    Two consecutive blank lines *inside* a fenced code block are legal content, so the
    textual form of the rule would reject files the format admits. What FMT-06 constrains
    is the gap between one block and the next.
    """
    from specctl.sectionfile import serialize_block

    text = serialize_section(section)
    rendered = [serialize_block(b) for b in section.blocks]
    for first, second in zip(rendered, rendered[1:]):
        assert f"{first}\n\n{second}" in text


def test_the_gap_between_blocks_is_one_blank_line() -> None:
    """The same rule as a worked case, so the property test cannot drift into vacuity."""
    text = serialize_section(parse_section(APPENDIX_D))
    assert "type:heading -->\n\n<!-- id:SYS-000121" in text
    assert "^sys-000121\n\n<!-- id:SYS-000122" in text


@given(sections())
@SLOW
def test_no_trailing_whitespace_is_written(section) -> None:
    for line in serialize_section(section).split("\n"):
        assert line == line.rstrip(), repr(line)  # FMT-09


# ------------------------------------------------------------------ anchors

@given(sections())
@SLOW
def test_attributes_are_written_in_canonical_order(section) -> None:
    """FMT-12 — one spelling per anchor, so a reordering never shows up as a diff."""
    for block in section.blocks:
        keys = [k for k, _ in block.anchor.ordered_attrs()]
        ranks = [ATTR_ORDER.index(k) for k in keys if k in ATTR_ORDER]
        assert ranks == sorted(ranks), keys


def test_anchor_render_matches_the_spec_examples() -> None:
    """The five anchors printed in §6.3, which together pin the attribute order."""
    cases = [
        (Anchor("SYS-000121", "paragraph"), "<!-- id:SYS-000121 type:paragraph -->"),
        (Anchor("SYS-000122", "table", {"format": "pipe"}),
         "<!-- id:SYS-000122 type:table format:pipe -->"),
        (Anchor("SYS-000123", "figure", {"locked": "true", "asset": "SYS-000123.png"}),
         "<!-- id:SYS-000123 type:figure locked:true asset:SYS-000123.png -->"),
        (Anchor("SYS-000151", "raw", {"locked": "true", "fallback": "true",
                                      "asset": "SYS-000151.xml",
                                      "reason": "shape_unrenderable"}),
         "<!-- id:SYS-000151 type:raw locked:true fallback:true "
         "asset:SYS-000151.xml reason:shape_unrenderable -->"),
        (Anchor("SYS-000121", "paragraph", {"supersedes": "SYS-000122"}),
         "<!-- id:SYS-000121 type:paragraph supersedes:SYS-000122 -->"),
        (Anchor("SYS-001205", "paragraph", {"split_from": "SYS-000130"}),
         "<!-- id:SYS-001205 type:paragraph split_from:SYS-000130 -->"),
    ]
    for anchor, expected in cases:
        assert anchor.render() == expected


def test_attribute_order_is_normalized_on_render() -> None:
    """Whatever order a file used, one order comes out (FMT-12)."""
    scrambled = Anchor("SYS-000151", "raw", {
        "reason": "shape_unrenderable", "asset": "x.xml",
        "fallback": "true", "locked": "true",
    })
    assert scrambled.render() == (
        "<!-- id:SYS-000151 type:raw locked:true fallback:true "
        "asset:x.xml reason:shape_unrenderable -->"
    )


@pytest.mark.parametrize("body,reason", [
    ("type:paragraph id:SYS-000121", "must start with id:"),
    ("id:SYS-000121", "at least id and type"),
    ("id:SYS-000121 locked:true", "second attribute must be type:"),
    ("id:sys-000121 type:paragraph", "well-formed block ID"),
    ("id:SYS-121 type:paragraph", "well-formed block ID"),
    ("id:SYS-000121 type:paragraph nonsense", "malformed anchor attribute"),
    ("id:SYS-000121 type:paragraph locked:true locked:false", "duplicate anchor attribute"),
])
def test_malformed_anchors_are_rejected_with_a_reason(body: str, reason: str) -> None:
    with pytest.raises(ParseError, match=reason):
        parse_anchor(body)


def test_unknown_attribute_is_preserved_rather_than_dropped() -> None:
    """V02 reports it; until then it must stay visible in the file. Dropping it would be
    the validator and the writer disagreeing about what the file says."""
    anchor = parse_anchor("id:SYS-000121 type:paragraph nonce:7")
    assert "nonce:7" in anchor.render()


# ------------------------------------------------------------------ block delimiting

def test_a_fenced_code_block_keeps_its_internal_blank_lines() -> None:
    """Blocks are delimited by anchors, not blank lines. Splitting on blank lines would
    truncate this block's content and still produce a file that parses."""
    text = (
        APPENDIX_D.split("\n\n## ")[0]
        + "\n\n## 3.2 Braking control <!-- id:SYS-000120 type:heading -->\n\n"
        + "<!-- id:SYS-000124 type:code lang:c -->\n"
        + "```c\nint a;\n\nint b;\n```\n\n"
        + "<!-- id:SYS-000125 type:paragraph -->\nAfter.\n"
    )
    section = parse_section(text)
    code = section.block("SYS-000124")
    assert code.lines == ("```c", "int a;", "", "int b;", "```")
    assert section.block_ids()[-1] == "SYS-000125"
    assert serialize_section(section) == text


def test_blockref_belonging_to_another_block_stays_as_content() -> None:
    """A `^id` marker is only this block's marker when it names this block (FMT-04)."""
    section = parse_section(
        "---\n" + APPENDIX_D.split("---\n")[1] + "---\n\n"
        "## 3.2 Braking control <!-- id:SYS-000120 type:heading -->\n\n"
        "<!-- id:SYS-000121 type:paragraph -->\nText.\n^sys-000999\n"
    )
    block = section.block("SYS-000121")
    assert block.blockref is False
    assert block.lines == ("Text.", "^sys-000999")


# ------------------------------------------------------------------ parse errors

@pytest.mark.parametrize("text,reason", [
    ("no front matter\n", "must start with a '---'"),
    ("---\nid: SYS-000120\n", "never closed"),
    ("---\n- a\n- b\n---\n", "must be a mapping"),
    ("---\nid: [unclosed\n---\n", "not valid YAML"),
])
def test_broken_front_matter_is_a_parse_error_with_a_line(text: str, reason: str) -> None:
    with pytest.raises(ParseError, match=reason) as exc:
        parse_section(text, path="SYS-000120.md")
    assert exc.value.line == 1
    assert exc.value.path == "SYS-000120.md"


def test_byte_order_mark_is_rejected() -> None:
    with pytest.raises(ParseError, match="byte-order mark"):
        parse_section("﻿" + APPENDIX_D)  # FMT-09


def test_unknown_front_matter_key_is_rejected() -> None:
    """FMT-01 — keys outside the schema are an error (V01)."""
    broken = APPENDIX_D.replace("origin: ingest", "origin: ingest\nnonce: 7")
    with pytest.raises(ParseError, match="outside the schema: nonce"):
        parse_section(broken)


def test_missing_front_matter_key_is_rejected() -> None:
    broken = APPENDIX_D.replace("words: 61\n", "")
    with pytest.raises(ParseError, match="missing required keys: words"):
        parse_section(broken)


def test_a_file_whose_first_block_is_not_a_heading_is_rejected() -> None:
    broken = APPENDIX_D.replace(
        "## 3.2 Braking control <!-- id:SYS-000120 type:heading -->",
        "<!-- id:SYS-000120 type:paragraph -->\nNot a heading.",
    )
    with pytest.raises(ParseError, match="first block must be its heading"):
        parse_section(broken)


def test_content_before_the_first_anchor_is_rejected() -> None:
    """Text with no anchor has no ID, so it has no address — the failure §5 prevents."""
    broken = APPENDIX_D.replace(
        "## 3.2 Braking control <!-- id:SYS-000120 type:heading -->",
        "Orphan text.\n\n## 3.2 Braking control <!-- id:SYS-000120 type:heading -->",
    )
    with pytest.raises(ParseError, match="content before the first anchor"):
        parse_section(broken)


# ------------------------------------------------------------------ YAML scalars

@given(st.text(TEXT_ALPHABET, max_size=60))
@SLOW
def test_emitted_scalars_read_back_as_the_same_string(value: str) -> None:
    """The quoting rule is what stops `number: 3.2` becoming a float (§10.11)."""
    assert yaml.safe_load(f"k: {emit_scalar(value)}\n")["k"] == value


@pytest.mark.parametrize("value", ["3.2", "3", "true", "false", "null", "yes", "no",
                                   "on", "off", "0x1F", "1e5", "-1", ".5", "", " x",
                                   "x ", "a: b", "a #b", "[x]", "{x}", "*x", "&x",
                                   "SYS > 3 Braking system"])
def test_ambiguous_scalars_are_quoted(value: str) -> None:
    rendered = emit_scalar(value)
    assert rendered.startswith('"'), (value, rendered)
    assert yaml.safe_load(f"k: {rendered}\n")["k"] == value


@pytest.mark.parametrize("value", ["SYS", "SYS-000120", "Braking control", "ingest",
                                   "authored", "Signal name 2"])
def test_unambiguous_scalars_are_left_plain(value: str) -> None:
    """Matching §6.2's worked front matter, which quotes only what needs it."""
    assert emit_scalar(value) == value
