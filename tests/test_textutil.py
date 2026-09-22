"""The three text functions (§6.6).

Four consumers compare text through these. A disagreement here shows up as a fidelity
number that is wrong, a registry that loses a block's history, a numeric diff that misses
a changed value, or an Excel cell that does not match the vault — all of them silent.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from specctl.model import Anchor, Block
from specctl.textutil import (
    inline_plain,
    is_cjk,
    normalize,
    normalize_ws,
    split_heading_line,
    to_plain_text,
    unescape_markdown,
    wikilink_targets,
    words,
)


def block(kind: str, *lines: str, **attrs: str) -> Block:
    return Block(anchor=Anchor("SYS-000121", kind, attrs), lines=lines)


# ------------------------------------------------------------------ normalize_ws

def test_nfkc_folds_compatibility_forms() -> None:
    """Word emits full-width forms freely; NFKC makes them compare equal (§6.6 step 1)."""
    assert normalize_ws("ｍＶ") == "mV"
    assert normalize_ws("１２３") == "123"


@pytest.mark.parametrize("invisible,name", [
    ("​", "zero-width space"),
    ("‌", "zero-width non-joiner"),
    ("‍", "zero-width joiner"),
    ("﻿", "zero-width no-break space"),
    ("­", "soft hyphen"),
])
def test_invisible_characters_are_removed(invisible: str, name: str) -> None:
    """§6.6 step 2. These survive a copy-paste out of Word and would otherwise make two
    identical-looking strings compare unequal."""
    assert normalize_ws(f"50{invisible} ms") == "50 ms", name
    assert normalize_ws(f"brake{invisible}force") == "brakeforce", name


@pytest.mark.parametrize("whitespace", [" ", "\t", "\r", "\n", " ", "　"])
def test_every_whitespace_run_collapses_to_one_space(whitespace: str) -> None:
    """§6.6 step 3 — including U+00A0, which Word uses for non-breaking spaces."""
    assert normalize_ws(f"a{whitespace}{whitespace}b") == "a b"


def test_leading_and_trailing_space_is_stripped() -> None:
    assert normalize_ws("    50 ms \t ") == "50 ms"


def test_normalize_ws_preserves_case_and_normalize_does_not() -> None:
    """The reason there are two functions: `mV` and `MV` differ by nine orders of
    magnitude, so the numeric diff must never casefold (§12.6 N3)."""
    assert normalize_ws("mV") == "mV"
    assert normalize_ws("mV") != normalize_ws("MV")
    assert normalize("mV") == normalize("MV") == "mv"


@given(st.text(max_size=80))
@settings(max_examples=200, deadline=None)
def test_normalize_ws_is_idempotent(value: str) -> None:
    once = normalize_ws(value)
    assert normalize_ws(once) == once


@given(st.text(max_size=80))
@settings(max_examples=200, deadline=None)
def test_normalize_is_normalize_ws_casefolded(value: str) -> None:
    assert normalize(value) == normalize_ws(value).casefold()


# ------------------------------------------------------------------ words

def test_latin_tokens_need_a_letter_or_digit() -> None:
    assert words("The system shall apply 50 ms") == 6
    assert words("— – · |") == 0  # punctuation-only tokens do not count
    assert words("") == 0


@pytest.mark.parametrize("char", ["あ", "ブ", "一", "龥", "豈", "ｰ"])
def test_the_documented_cjk_ranges_are_recognised(char: str) -> None:
    assert is_cjk(char)


@pytest.mark.parametrize("char", ["a", "Z", "0", "é", "Ж", "　"])
def test_non_cjk_characters_are_not(char: str) -> None:
    assert not is_cjk(char)


@pytest.mark.parametrize("count", list(range(0, 13)))
def test_cjk_characters_count_as_ceil_over_two_and_a_half(count: int) -> None:
    """§6.6. Computed with integers so the V14 threshold cannot shift with the platform's
    floating point."""
    assert words("一" * count) == math.ceil(count / 2.5)


def test_mixed_script_adds_the_two_terms() -> None:
    """3 Latin tokens + 4 katakana characters -> 3 + ceil(4/2.5) = 5."""
    assert words("Signal ブレーキ 50 ms") == 5


def test_a_cjk_only_token_contributes_no_token_count() -> None:
    assert words("日本語") == 2  # ceil(3/2.5), no Latin token


@given(st.text(max_size=60))
@settings(max_examples=200, deadline=None)
def test_word_count_is_never_negative_and_is_deterministic(value: str) -> None:
    first = words(value)
    assert first >= 0
    assert words(value) == first


# ------------------------------------------------------------------ unescape

@pytest.mark.parametrize("raw,plain", [
    (r"A\|B", "A|B"),
    (r"a\*b", "a*b"),
    (r"u\_v", "u_v"),
    (r"p\[q\]", "p[q]"),
    (r"lt\<gt\>", "lt<gt>"),
    (r"c\`d", "c`d"),
    ("x\\\\y", "x\\y"),
    (r"no\qescape", r"no\qescape"),
])
def test_writer_escapes_are_removed(raw: str, plain: str) -> None:
    """§6.6 final step. Without this, a table cell holding a literal `|` is emitted as
    `\\|`, never matches the source segment, and a captured paragraph is reported lost."""
    assert unescape_markdown(raw) == plain


def test_escaped_emphasis_survives_the_emphasis_pass() -> None:
    r"""Order matters: unescaping first would turn `\*` into `*`, and the emphasis pass
    would then eat it."""
    assert inline_plain(r"a \* b **bold**") == "a * b bold"


# ------------------------------------------------------------------ links

def test_wikilinks_reduce_to_display_text() -> None:
    assert inline_plain("see [[SYS-000245|5.1 Signal thresholds]]") == "see 5.1 Signal thresholds"
    assert inline_plain("see [[SYS-000245]]") == "see SYS-000245"


def test_block_level_wikilinks_keep_their_display_text() -> None:
    assert inline_plain("[[SYS-000301#^sys-000302|the ramp limit]]") == "the ramp limit"


def test_markdown_links_reduce_to_display_text() -> None:
    """Not named in §6.6, but fidelity needs it: the Word paragraph contains the display
    text and not the URL, so leaving the URL in makes every externally linked paragraph
    fail to match (§6.5)."""
    assert inline_plain("see [the standard](https://example.test/a_b)") == "see the standard"


def test_wikilink_targets_are_extracted_as_written() -> None:
    text = "[[SYS-000245|x]] and [[SYS-000301#^sys-000302]] and [[SYS-000245]]"
    assert wikilink_targets(text) == ("SYS-000245", "SYS-000301#^sys-000302", "SYS-000245")


# ------------------------------------------------------------------ heading lines

@pytest.mark.parametrize("line,expected", [
    ("## 3.2 Braking control", (2, "3.2", "Braking control")),
    ("# 3 Braking system", (1, "3", "Braking system")),
    ("###### 1.2.3.4 Deep", (6, "1.2.3.4", "Deep")),
    ("## Revision history", (2, "", "Revision history")),
    ("## A.1 Annex item", (2, "A.1", "Annex item")),
])
def test_heading_lines_split_into_level_number_and_title(line: str, expected: tuple) -> None:
    assert split_heading_line(line) == expected


def test_a_non_heading_line_is_rejected() -> None:
    with pytest.raises(ValueError, match="not an ATX heading"):
        split_heading_line("just text")


# ------------------------------------------------------------------ to_plain_text

def test_heading_plain_text_is_number_then_title() -> None:
    assert to_plain_text(block("heading", "## 3.2 Braking control")) == "3.2 Braking control"


def test_paragraph_strips_emphasis_and_links() -> None:
    result = to_plain_text(block(
        "paragraph",
        "Apply **50 ms** of torque per [[SYS-000245|5.1 Thresholds]] and `code`.",
    ))
    assert result == "Apply 50 ms of torque per 5.1 Thresholds and code."


def test_list_keeps_its_markers_and_indentation() -> None:
    """§6.6 — one line per item, each prefixed with its literal marker."""
    result = to_plain_text(block("list", "- first", "  - nested", "- second", ordered="false"))
    assert result == "- first\n  - nested\n- second"


def test_pipe_table_excludes_the_separator_row_and_joins_cells() -> None:
    result = to_plain_text(block(
        "table",
        "| Signal | Unit | Range |",
        "|---|---|---|",
        "| BrakePedalPos | % | 0-100 |",
        format="pipe",
    ))
    assert result == "Signal | Unit | Range\nBrakePedalPos | % | 0-100"


def test_pipe_table_cell_holding_an_escaped_pipe_is_one_cell() -> None:
    """The failure §6.6's unescape rule exists for: `A\\|B` is one cell reading `A|B`."""
    result = to_plain_text(block("table", "| Signal |", "|---|", r"| A\|B |", format="pipe"))
    assert result == "Signal\nA|B"


def test_html_table_flattens_rows_and_replaces_line_breaks() -> None:
    result = to_plain_text(block(
        "table",
        "<table>",
        "<tr><th>Signal</th><th>Unit</th></tr>",
        '<tr><td rowspan="2">Brake<br/>Pedal</td><td>%</td></tr>',
        "</table>",
        format="html",
    ))
    assert result == "Signal | Unit\nBrake Pedal | %"


def test_figure_uses_its_caption() -> None:
    result = to_plain_text(block(
        "figure",
        "![Figure 3-2: Braking state machine](../assets/SYS-000123.png)",
        "*Figure 3-2: Braking state machine*",
        locked="true", asset="SYS-000123.png",
    ))
    assert result == "[FIGURE] Figure 3-2: Braking state machine"


def test_figure_falls_back_to_alt_text_when_there_is_no_caption() -> None:
    result = to_plain_text(block(
        "figure", "![State machine](../assets/x.png)", locked="true", asset="x.png"
    ))
    assert result == "[FIGURE] State machine"


@pytest.mark.parametrize("raw,expected", [
    ("$x^2 + y^2$", "x^2 + y^2"),
    ("$$\\frac{a}{b}$$", "\\frac{a}{b}"),
])
def test_latex_formula_drops_its_delimiters(raw: str, expected: str) -> None:
    assert to_plain_text(block("formula", raw, format="latex")) == expected


def test_image_formula_reports_its_alt_text() -> None:
    result = to_plain_text(block(
        "formula", "![v = a t](../assets/x.png)", format="image", asset="x.png"
    ))
    assert result == "[FORMULA] v = a t"


def test_code_drops_the_fences_and_stays_verbatim() -> None:
    r"""Code carries no writer escapes, so `\|` inside code must survive untouched."""
    result = to_plain_text(block("code", "```c", r"int a = 1; /* \| */", "```", lang="c"))
    assert result == r"int a = 1; /* \| */"


def test_raw_block_yields_its_extracted_text() -> None:
    """§6.6 — the plain text, **not** the OOXML, which lives in assets/<ID>.xml."""
    result = to_plain_text(block(
        "raw", "Torque limit 400 Nm/s",
        locked="true", fallback="true", asset="x.xml", reason="shape_unrenderable",
    ))
    assert result == "Torque limit 400 Nm/s"
