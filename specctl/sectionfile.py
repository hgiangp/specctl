"""Read and write a section file (§6.1, §10.11).

The parser and the serializer live in one module on purpose: they are a pair, and a
change to one that is not mirrored in the other corrupts files. The property that keeps
them honest is round-trip — `serialize(parse(text)) == text` for any file already in
canonical form, and `parse(serialize(section)) == section` for any section.

Blocks are delimited by **anchors**, never by blank lines. A fenced code block and an
HTML table both contain blank lines legitimately, so splitting on them would silently
truncate content — the failure mode this whole design exists to prevent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import yaml

from .ids import ID_RE, to_lower
from .model import (
    FRONT_MATTER_KEYS,
    Block,
    Anchor,
    FrontMatter,
    Section,
)

FENCE = "---"


class ParseError(Exception):
    """A section file that cannot be read at all.

    Carries a line number so a validator can report it as a finding at a location
    (V01/V02) instead of a stack trace.
    """

    def __init__(self, message: str, *, line: int | None = None, path: str | None = None) -> None:
        location = ""
        if path:
            location += path
        if line is not None:
            location += f":{line}"
        super().__init__(f"{location}: {message}" if location else message)
        self.line = line
        self.path = path
        self.reason = message


# --------------------------------------------------------------------------- anchors

_ANCHOR_BODY = r"<!--\s+(?P<body>id:[^>]*?)\s+-->"
#: A line that is nothing but an anchor — how every non-heading block starts (FMT-02).
ANCHOR_LINE_RE = re.compile(r"^" + _ANCHOR_BODY + r"$")
#: An ATX heading whose anchor is appended after one space (FMT-02).
HEADING_LINE_RE = re.compile(r"^(?P<heading>#{1,6}\s.*?)\s" + _ANCHOR_BODY + r"$")
#: The trailing block-reference marker (FMT-04).
BLOCKREF_RE = re.compile(r"^\^(?P<lower>[a-z][a-z0-9]{1,7}-[0-9]{6})$")

_ATTR_RE = re.compile(r"^(?P<key>[a-z][a-z0-9_]*):(?P<value>[^\s]*)$")

#: A heading line on its own, before the anchor is appended (§6.1).
HEADING_TEXT_RE = re.compile(r"^#{1,6}\s+\S")


def parse_anchor(body: str, *, line: int | None = None) -> Anchor:
    """Parse the inside of an anchor comment: `id:X type:Y key:value …` (§6.1)."""
    tokens = body.split()
    if len(tokens) < 2:
        raise ParseError(f"anchor needs at least id and type: {body!r}", line=line)

    attrs: dict[str, str] = {}
    for index, token in enumerate(tokens):
        match = _ATTR_RE.match(token)
        if not match:
            raise ParseError(f"malformed anchor attribute {token!r}", line=line)
        key, value = match.group("key"), match.group("value")
        if key in attrs:
            raise ParseError(f"duplicate anchor attribute {key!r}", line=line)
        if index == 0 and key != "id":
            raise ParseError(f"anchor must start with id:, got {key!r}", line=line)
        if index == 1 and key != "type":
            raise ParseError(f"anchor's second attribute must be type:, got {key!r}", line=line)
        attrs[key] = value

    block_id = attrs.pop("id")
    block_type = attrs.pop("type")
    if not ID_RE.match(block_id):
        raise ParseError(f"not a well-formed block ID: {block_id!r}", line=line)
    return Anchor(block_id=block_id, type=block_type, attrs=attrs)


# --------------------------------------------------------------------------- YAML out

#: A scalar is written plain only when it is unmistakably a string and needs no escaping.
#: Over-quoting is always safe in YAML; under-quoting turns `3.2` into a float, which is
#: exactly what §10.11 calls out. This set reproduces the worked front matter of §6.2
#: character for character.
_PLAIN_SAFE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]*$")

#: Values a YAML reader may take for a number, a boolean or null. Checked in addition to
#: asking PyYAML, because the vault is read by other tools too: PyYAML implements YAML 1.1
#: and returns the *string* "1e5", while a YAML 1.2 reader — Obsidian's, or any JS one —
#: returns the float 100000.0. Quoting costs nothing; being read differently by the
#: viewer than by the validator is a silent disagreement about what the spec says.
_YAML_NUMERIC_RE = re.compile(
    r"""^[-+]?(
        (\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?   # 3, 3.2, .5, 1e5, 1.2E-3
      | 0[xXbBoO][0-9a-fA-F_]+                 # 0x1F, 0b1010, 0o17
      | \d+(:\d+)+                             # 1:30 sexagesimal
    )$""",
    re.VERBOSE,
)
_YAML_KEYWORDS = frozenset({
    "true", "false", "yes", "no", "on", "off", "null", "none", "~",
    "y", "n", ".inf", "-.inf", "+.inf", ".nan",
})


def _yaml_ambiguous(value: str) -> bool:
    return value.lower() in _YAML_KEYWORDS or bool(_YAML_NUMERIC_RE.match(value))


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    return f'"{escaped}"'


def emit_scalar(value: Any) -> str:
    """One front-matter scalar, quoted only when it has to be (§10.11)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if not isinstance(value, str):
        raise TypeError(f"cannot emit {type(value).__name__} as a front-matter scalar")
    if not _PLAIN_SAFE_RE.match(value) or value != value.strip():
        return _quote(value)
    if _yaml_ambiguous(value):
        return _quote(value)
    # Unambiguously string-shaped, but YAML may still read it as something else.
    try:
        loaded = yaml.safe_load(value)
    except yaml.YAMLError:
        return _quote(value)
    return value if isinstance(loaded, str) and loaded == value else _quote(value)


def emit_sequence(values: Sequence[Any]) -> str:
    """A flow sequence. Strings are always quoted inside one, as §6.2's example writes
    them — inside brackets the quotes cost nothing and remove every ambiguity."""
    if not values:
        return "[]"
    rendered = [
        _quote(v) if isinstance(v, str) else emit_scalar(v) for v in values
    ]
    return "[" + ", ".join(rendered) + "]"


def emit_front_matter(front_matter: FrontMatter) -> str:
    """Render front matter between its `---` fences, keys in §6.2 order."""
    mapping = front_matter.to_mapping()
    lines = [FENCE]
    for key in FRONT_MATTER_KEYS:
        if key not in mapping:
            continue  # `parent` is omitted at level 1 rather than written as null
        value = mapping[key]
        if key == "source":
            if value is None:
                lines.append("source: null")
            else:
                paragraphs = emit_sequence(value["paragraphs"])
                lines.append(
                    f"source: {{ docx: {emit_scalar(value['docx'])}, "
                    f"paragraphs: {paragraphs} }}"
                )
        elif isinstance(value, list):
            lines.append(f"{key}: {emit_sequence(value)}")
        else:
            lines.append(f"{key}: {emit_scalar(value)}")
    lines.append(FENCE)
    return "\n".join(lines)


# --------------------------------------------------------------------------- serialize

def serialize_block(block: Block) -> str:
    """One block in canonical form (FMT-02, FMT-04, FMT-12)."""
    anchor = block.anchor.render()
    if block.type == "heading":
        # A heading block is exactly one ATX line (§6.3, §6.1 as amended in v2.2).
        # Refuse rather than emit a line the parser cannot read back: a file written
        # without a heading line parses as "content before the first anchor", so the
        # section would be unreadable and its content effectively lost.
        if len(block.lines) != 1 or not HEADING_TEXT_RE.match(block.lines[0]):
            raise ValueError(
                f"{block.block_id}: a heading block must be exactly one ATX line with "
                f"1-6 '#' characters, got {list(block.lines)!r}. "
                "The synthetic front-matter section is level 1 with a real '#' line "
                "(§10.9)."
            )
        return f"{block.lines[0]} {anchor}"
    rendered = [anchor, *block.lines]
    if block.blockref:
        rendered.append(f"^{to_lower(block.block_id)}")
    return "\n".join(rendered)


def serialize_section(section: Section) -> str:
    """The whole file: front matter, a blank line, then blocks one blank line apart.

    Ends with exactly one LF (FMT-06).
    """
    parts = [emit_front_matter(section.front_matter)]
    parts.extend(serialize_block(block) for block in section.blocks)
    return "\n\n".join(parts) + "\n"


# --------------------------------------------------------------------------- parse

@dataclass
class _Pending:
    anchor: Anchor
    heading_line: str | None
    lines: list[str]
    blockref: bool = False


def _split_front_matter(text: str, path: str | None) -> tuple[Mapping[str, Any], list[str], int]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != FENCE:
        raise ParseError("file must start with a '---' front-matter fence", line=1, path=path)
    for index in range(1, len(lines)):
        if lines[index].strip() == FENCE:
            body = "\n".join(lines[1:index])
            try:
                loaded = yaml.safe_load(body)
            except yaml.YAMLError as exc:
                raise ParseError(f"front matter is not valid YAML: {exc}", line=1, path=path) from exc
            if loaded is None:
                loaded = {}
            if not isinstance(loaded, dict):
                raise ParseError(
                    f"front matter must be a mapping, got {type(loaded).__name__}",
                    line=1, path=path,
                )
            return loaded, lines[index + 1:], index + 2
    raise ParseError("front matter is never closed by a '---' fence", line=1, path=path)


def parse_blocks(lines: Sequence[str], *, first_line: int = 1, path: str | None = None) -> tuple[Block, ...]:
    """Split content into blocks at anchors, not at blank lines.

    Everything between one anchor and the next is that block's content, minus a trailing
    `^id` marker and minus the blank line that separates it from the next block. A fenced
    code block keeps its internal blank lines, which is the whole reason for not
    splitting on them.
    """
    pending: list[_Pending] = []
    for offset, line in enumerate(lines):
        number = first_line + offset
        heading = HEADING_LINE_RE.match(line)
        if heading:
            anchor = parse_anchor(heading.group("body"), line=number)
            pending.append(_Pending(anchor, heading.group("heading").rstrip(), []))
            continue
        anchor_only = ANCHOR_LINE_RE.match(line)
        if anchor_only:
            anchor = parse_anchor(anchor_only.group("body"), line=number)
            pending.append(_Pending(anchor, None, []))
            continue
        if not pending:
            if line.strip():
                raise ParseError(
                    f"content before the first anchor: {line.strip()[:60]!r}",
                    line=number, path=path,
                )
            continue
        pending[-1].lines.append(line)

    blocks: list[Block] = []
    for item in pending:
        body = list(item.lines)
        while body and not body[-1].strip():
            body.pop()  # the separating blank line is not content (FMT-06)
        blockref = False
        if body:
            marker = BLOCKREF_RE.match(body[-1].strip())
            if marker and marker.group("lower") == to_lower(item.anchor.block_id):
                blockref = True
                body.pop()
                while body and not body[-1].strip():
                    body.pop()
        if item.heading_line is not None:
            body = [item.heading_line, *body]
        blocks.append(Block(anchor=item.anchor, lines=tuple(body), blockref=blockref))
    return tuple(blocks)


def parse_section(text: str, *, path: str | None = None) -> Section:
    """Read a section file. Raises `ParseError`, which a validator turns into a finding."""
    if text.startswith("\ufeff"):
        raise ParseError("file starts with a byte-order mark (FMT-09 forbids one)", line=1, path=path)
    raw_fm, rest, first_line = _split_front_matter(text, path)

    unknown = sorted(set(raw_fm) - set(FRONT_MATTER_KEYS))
    if unknown:
        raise ParseError(
            f"front matter has keys outside the schema: {', '.join(unknown)} (V01)",
            line=1, path=path,
        )
    missing = [k for k in FRONT_MATTER_KEYS if k != "parent" and k not in raw_fm]
    if missing:
        raise ParseError(
            f"front matter is missing required keys: {', '.join(missing)} (V01)",
            line=1, path=path,
        )
    try:
        front_matter = FrontMatter.from_mapping(raw_fm)
    except (KeyError, TypeError, ValueError) as exc:
        raise ParseError(f"front matter is malformed: {exc}", line=1, path=path) from exc

    blocks = parse_blocks(rest, first_line=first_line, path=path)
    if not blocks:
        raise ParseError("section file has no blocks", line=first_line, path=path)
    if blocks[0].type != "heading":
        raise ParseError(
            f"a section file's first block must be its heading, got {blocks[0].type!r} (§6.1)",
            line=first_line, path=path,
        )
    return Section(front_matter=front_matter, blocks=blocks)


def load_section(path, *, encoding: str = "utf-8") -> Section:
    """Read one section file from disk."""
    from pathlib import Path

    p = Path(path)
    return parse_section(p.read_text(encoding=encoding), path=str(p))


def dump_section(section: Section, path, *, encoding: str = "utf-8") -> None:
    """Write one section file, LF endings, no BOM (FMT-09)."""
    from pathlib import Path

    Path(path).write_text(serialize_section(section), encoding=encoding, newline="\n")
