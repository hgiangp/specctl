"""The three text functions, with exactly one definition each (§6.6).

Four consumers compare text: fidelity measurement (§10.12), the ID registry's
`text_hash` and similarity matching (§10.10), the numeric diff (§12.6), and the Excel
`Content` column (§13.5). If each wrote its own comparison, four places would disagree
about whether two strings are the same and nobody could say which was right. So they all
call these.

`normalize_ws` is case-preserving and `normalize` is not. Use `normalize_ws` wherever case
carries meaning — unit symbols do: `mV` and `MV` differ by nine orders of magnitude, which
is why the numeric diff uses `normalize_ws` and never `normalize` (§12.6 N3).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from .model import Block

# --------------------------------------------------------------------------- normalize

#: §6.6 step 2 — zero-width characters and the soft hyphen. These survive a copy-paste
#: out of Word and would otherwise make two identical-looking strings compare unequal.
_INVISIBLE = "\u200b\u200c\u200d\ufeff\u00ad"
_INVISIBLE_RE = re.compile(f"[{_INVISIBLE}]")

#: Every Unicode whitespace character, including U+00A0 which Word emits freely.
_WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)


def normalize_ws(s: str) -> str:
    """§6.6 — NFKC, drop invisibles, collapse whitespace runs to one space, strip.

    Case-preserving.
    """
    s = unicodedata.normalize("NFKC", s)
    s = _INVISIBLE_RE.sub("", s)
    s = _WHITESPACE_RE.sub(" ", s)
    return s.strip()


def normalize(s: str) -> str:
    """§6.6 — `casefold(normalize_ws(s))`. Use only where case does not carry meaning."""
    return normalize_ws(s).casefold()


# --------------------------------------------------------------------------- word count

#: §6.6 — the CJK ranges. The English translation still carries CJK in signal names and
#: figure labels (NG5 note), so the word count has to handle them.
_CJK_RANGES: tuple[tuple[int, int], ...] = (
    (0x3040, 0x30FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF), (0xFF66, 0xFF9F),
)

#: The divisor of §6.6, as exact integer arithmetic: ceil(n / 2.5) == ceil(2n / 5).
#: Written this way so the count never depends on binary floating point — the V14
#: threshold has to mean the same thing in every section.
_CJK_NUMERATOR = 2
_CJK_DENOMINATOR = 5


def is_cjk(char: str) -> bool:
    point = ord(char)
    return any(low <= point <= high for low, high in _CJK_RANGES)


def words(s: str) -> int:
    """§6.6 — whitespace tokens carrying a non-CJK letter or digit, plus CJK/2.5."""
    cjk_chars = 0
    token_count = 0
    for token in s.split():
        has_latin_alnum = False
        for char in token:
            if is_cjk(char):
                cjk_chars += 1
            elif char.isalnum():
                has_latin_alnum = True
        if has_latin_alnum:
            token_count += 1
    cjk_words = -(-cjk_chars * _CJK_NUMERATOR // _CJK_DENOMINATOR)  # ceil, integers only
    return token_count + cjk_words


# --------------------------------------------------------------------------- markdown

#: §6.6 (as amended) — the characters the writer escapes inside cell and inline content.
_ESCAPABLE = "|*_[]<>`\\"
#: `re.escape` per character: a bare "]" would close the character class early, which
#: silently reduced this to "|*_[" and left every other escape in place.
_UNESCAPE_RE = re.compile(r"\\([" + "".join(re.escape(c) for c in _ESCAPABLE) + r"])")


def unescape_markdown(s: str) -> str:
    r"""Remove the writer's escapes: `\|` → `|`, `\\` → `\` (§6.6, final step).

    The writer escapes a literal `|` inside a pipe-table cell. Without this, the source
    segment ``A|B`` never matches the emitted ``A\|B``, and a paragraph that was captured
    perfectly is reported as lost (§10.12).
    """
    return _UNESCAPE_RE.sub(r"\1", s)


#: `[[TARGET|display]]` or `[[TARGET]]` (FMT-07, §6.5).
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")

#: `[display](url)` and `![alt](path)`. An unescaped `[` only.
_MDLINK_RE = re.compile(r"(?<!\\)!?\[([^\]]*)\]\([^)]*\)")

#: Emphasis and inline-code markers, when not backslash-escaped. Longest first, so that
#: `**bold**` is consumed before `*italic*` can split it.
_EMPHASIS_RE = re.compile(r"(?<!\\)(\*\*\*|___|\*\*|__|\*|_|`)")


def strip_wikilinks(s: str) -> str:
    """Reduce each wikilink to its display text (§6.6 `paragraph` row).

    `[[SYS-000245|5.1 Signal thresholds]]` → `5.1 Signal thresholds`.
    `[[SYS-000245]]` → `SYS-000245`, which is what the reader sees.
    """
    return _WIKILINK_RE.sub(lambda m: m.group(2) if m.group(2) is not None else m.group(1), s)


def strip_markdown_links(s: str) -> str:
    """Reduce `[display](url)` to its display text.

    §6.6 names only wikilinks, but the same reasoning applies and fidelity depends on it:
    the source paragraph in Word contains the link's display text and not its URL, so
    leaving the URL in the emitted text makes every paragraph with an external link
    (§6.5) fail to match.
    """
    return _MDLINK_RE.sub(lambda m: m.group(1), s)


def strip_emphasis(s: str) -> str:
    """Remove bold, italic and inline-code markers, leaving escaped ones for the
    unescape step (§6.6 `paragraph` row)."""
    return _EMPHASIS_RE.sub("", s)


def inline_plain(s: str) -> str:
    """Inline markup → plain reading text, then unescape. The order matters: unescaping
    first would turn `\\*` into `*` and the emphasis pass would then eat it."""
    s = strip_wikilinks(s)
    s = strip_markdown_links(s)
    s = strip_emphasis(s)
    return unescape_markdown(s)


# --------------------------------------------------------------------------- to_plain_text

_FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
_CAPTION_RE = re.compile(r"^\s*\*(?P<caption>.+)\*\s*$")
_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\([^)]*\)")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$")
_TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
_CELL_RE = re.compile(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", re.I | re.S)
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<rest>.*)$")
_NUMBER_RE = re.compile(r"^(?P<number>[0-9]+(?:\.[0-9]+)*\.?|[A-Z](?:\.[0-9]+)*\.?)\s+(?P<title>.+)$")


def split_heading_line(line: str) -> tuple[int, str, str]:
    """`## 3.2 Braking control` → (2, "3.2", "Braking control") (FMT-05).

    The rendered number comes from Word (§10.3) and sits on the heading line; body text
    MUST NOT contain section numbering. A heading with no number yields `""`.
    """
    match = _HEADING_RE.match(line.rstrip())
    if not match:
        raise ValueError(f"not an ATX heading line: {line!r}")
    level = len(match.group("hashes"))
    rest = match.group("rest").strip()
    numbered = _NUMBER_RE.match(rest)
    if numbered:
        return level, numbered.group("number"), numbered.group("title").strip()
    return level, "", rest


def _pipe_table_plain(lines: Iterable[str]) -> str:
    """§6.6 — one line per data row, cells joined by `" | "`, separator row excluded."""
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _TABLE_SEPARATOR_RE.match(stripped) and set(stripped) <= set("|-: \t"):
            continue
        cells = _split_pipe_row(stripped)
        out.append(" | ".join(inline_plain(c).strip() for c in cells))
    return "\n".join(out)


def _split_pipe_row(row: str) -> list[str]:
    r"""Split on unescaped `|`, dropping the leading and trailing delimiter."""
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in row:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            current.append(char)
            escaped = True
        elif char == "|":
            cells.append("".join(current))
            current = []
        else:
            current.append(char)
    cells.append("".join(current))
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return cells


def _html_table_plain(text: str) -> str:
    """§6.6 — one line per `<tr>`, `<br>` becomes a space, tags stripped."""
    out: list[str] = []
    for row in _TR_RE.findall(text):
        cells = _CELL_RE.findall(row)
        rendered = [
            normalize_ws(_TAG_RE.sub("", _BR_RE.sub(" ", cell))) for cell in cells
        ]
        out.append(" | ".join(rendered))
    return "\n".join(out)


def _figure_plain(lines: tuple[str, ...]) -> str:
    """§6.6 — `[FIGURE] <caption>`. Prefer the italic caption line, fall back to alt text."""
    caption = ""
    for line in lines:
        match = _CAPTION_RE.match(line)
        if match:
            caption = match.group("caption").strip()
            break
    if not caption:
        for line in lines:
            image = _IMAGE_RE.search(line)
            if image:
                caption = image.group("alt").strip()
                break
    return f"[FIGURE] {caption}".rstrip()


def _code_plain(lines: tuple[str, ...]) -> str:
    """§6.6 — the code text without the fence lines. Never unescaped: code is verbatim."""
    body = list(lines)
    if body and _FENCE_RE.match(body[0]):
        body = body[1:]
    if body and _FENCE_RE.match(body[-1]):
        body = body[:-1]
    return "\n".join(body)


def to_plain_text(block: Block) -> str:
    """§6.6 — one comparison string per block, by type.

    Every branch unescapes Markdown as its final step, except `code`, whose content is
    verbatim by definition and carries no writer escapes.
    """
    kind = block.type
    lines = block.lines

    if kind == "heading":
        if not lines:
            return ""
        try:
            _, number, title = split_heading_line(lines[0])
        except ValueError:
            return unescape_markdown(inline_plain(lines[0].strip()))
        return unescape_markdown(f"{number} {title}".strip())

    if kind in ("paragraph", "list", "raw"):
        return "\n".join(inline_plain(line) for line in lines).strip()

    if kind == "table":
        if block.anchor.get("format") == "html":
            return _html_table_plain(block.text)
        return _pipe_table_plain(lines)

    if kind == "figure":
        return unescape_markdown(_figure_plain(lines))

    if kind == "formula":
        if block.anchor.get("format") == "image":
            alt = ""
            for line in lines:
                image = _IMAGE_RE.search(line)
                if image:
                    alt = image.group("alt").strip()
                    break
            return f"[FORMULA] {alt}".rstrip()
        stripped = block.text.strip()
        for delim in ("$$", "$"):
            if stripped.startswith(delim) and stripped.endswith(delim) and len(stripped) > 2 * len(delim):
                stripped = stripped[len(delim):-len(delim)]
                break
        return stripped.strip()

    if kind == "code":
        return _code_plain(lines)

    raise ValueError(f"unknown block type: {kind!r}")  # pragma: no cover


# --------------------------------------------------------------------------- wikilinks

#: A wikilink target exactly as `refs_out` records it: `SYS-000245` or
#: `SYS-000301#^sys-000302`, i.e. everything before the `|` (§6.5).
_WIKILINK_TARGET_RE = re.compile(r"\[\[(?P<target>[^\]|]+)(?:\|[^\]]*)?\]\]")


def wikilink_targets(text: str) -> tuple[str, ...]:
    """Every wikilink target in `text`, in order of appearance, duplicates kept.

    `refs_out` deduplicates and sorts (§6.5); callers that need the raw sequence — a
    backlink scan, for instance — get it here.
    """
    return tuple(m.group("target").strip() for m in _WIKILINK_TARGET_RE.finditer(text))
