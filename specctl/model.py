"""The data model of a section file (§6).

Sections 4–8 of the spec are the contract every component reads and writes against, so
this module holds it once: which block types exist, which anchor attributes each one may
carry, what order they are written in, and the shape of a section's front matter.

Nothing here computes anything derived — that is `derived.py` — and nothing here touches
the filesystem — that is `sectionfile.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping

from .ids import is_id

# --------------------------------------------------------------------------- block types

#: FMT-03 — the complete set.
BLOCK_TYPES: tuple[str, ...] = (
    "heading", "paragraph", "list", "table", "figure", "formula", "code", "raw",
)

#: FMT-12, pinned by the worked anchors of §6.3: `id` and `type` first, then `locked`,
#: then the type-specific attributes in the order §6.3 lists them, then lineage.
#: One total order, so `fmt` normalizes to a single spelling and diffs stay readable.
ATTR_ORDER: tuple[str, ...] = (
    "locked",
    "ordered", "format", "lang", "fallback", "asset", "reason",
    "supersedes", "split_from",
)

#: §5.4 — lineage attributes. Permanent: `fmt` MUST NOT remove them (L4).
LINEAGE_ATTRS: frozenset[str] = frozenset({"supersedes", "split_from"})


@dataclass(frozen=True)
class TypeSpec:
    """What §6.3 says about one block type."""

    name: str
    required_attrs: tuple[str, ...]
    optional_attrs: tuple[str, ...]
    locked_by_default: bool
    blockref_allowed: bool


TYPE_SPECS: Mapping[str, TypeSpec] = {
    "heading":   TypeSpec("heading",   (),           (),                False, False),
    "paragraph": TypeSpec("paragraph", (),           (),                False, True),
    "list":      TypeSpec("list",      ("ordered",), (),                False, True),
    "table":     TypeSpec("table",     ("format",),  (),                False, True),
    "figure":    TypeSpec("figure",    ("asset",),   (),                True,  True),
    # `asset` is required only for format:image; §6.3 gives the default per format.
    "formula":   TypeSpec("formula",   ("format",),  ("asset",),        False, True),
    "code":      TypeSpec("code",      ("lang",),    (),                False, True),
    "raw":       TypeSpec("raw",       ("fallback", "asset", "reason"), (), True, True),
}

#: Attributes every type may carry (§6.3).
UNIVERSAL_ATTRS: tuple[str, ...] = ("locked", "supersedes", "split_from")


def default_locked(block_type: str, attrs: Mapping[str, str]) -> bool:
    """§6.3 — `figure` and `raw` are locked; `formula` is locked only as an image."""
    if block_type == "formula":
        return attrs.get("format") == "image"
    return TYPE_SPECS[block_type].locked_by_default


# --------------------------------------------------------------------------- anchor

@dataclass(frozen=True)
class Anchor:
    """The `<!-- id:… type:… -->` comment binding a Markdown block to its ID (FMT-02).

    `attrs` holds everything besides `id` and `type`, in whatever order it was read.
    Rendering always emits `ATTR_ORDER`, so the stored order never reaches a file.
    """

    block_id: str
    type: str
    attrs: Mapping[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "attrs", dict(self.attrs or {}))

    # -- attribute access ---------------------------------------------------

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.attrs.get(key, default)

    @property
    def locked(self) -> bool:
        """The effective value: the explicit attribute if present, else the default."""
        raw = self.attrs.get("locked")
        if raw is None:
            return default_locked(self.type, self.attrs)
        return raw == "true"

    @property
    def supersedes(self) -> tuple[str, ...]:
        raw = self.attrs.get("supersedes")
        return tuple(part for part in raw.split(",") if part) if raw else ()

    @property
    def split_from(self) -> str | None:
        return self.attrs.get("split_from")

    def lineage_targets(self) -> tuple[str, ...]:
        """Every ID this block claims, for §12.5. Order is `supersedes` then `split_from`."""
        targets = list(self.supersedes)
        if self.split_from:
            targets.append(self.split_from)
        return tuple(targets)

    def with_attrs(self, **changes: str | None) -> "Anchor":
        """A copy with attributes added, replaced (value) or removed (`None`)."""
        attrs = dict(self.attrs)
        for key, value in changes.items():
            if value is None:
                attrs.pop(key, None)
            else:
                attrs[key] = value
        return replace(self, attrs=attrs)

    # -- rendering ----------------------------------------------------------

    def ordered_attrs(self) -> tuple[tuple[str, str], ...]:
        """`attrs` in canonical order (FMT-12).

        A key outside `ATTR_ORDER` would be an invalid anchor (V02), but rendering must
        not silently drop it — an unknown attribute is reported by the validator, and
        until then it is written back where it can be seen.
        """
        known = [(k, self.attrs[k]) for k in ATTR_ORDER if k in self.attrs]
        unknown = sorted((k, v) for k, v in self.attrs.items() if k not in ATTR_ORDER)
        return tuple(known + unknown)

    def render(self) -> str:
        parts = [f"id:{self.block_id}", f"type:{self.type}"]
        parts += [f"{k}:{v}" for k, v in self.ordered_attrs()]
        return "<!-- " + " ".join(parts) + " -->"

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.render()


# --------------------------------------------------------------------------- block

@dataclass(frozen=True)
class Block:
    """One addressable unit of content.

    `lines` are the block's content lines with **no** anchor and **no** `^id` marker: for
    a heading that is the single ATX line without its trailing anchor, so that rendering
    can put the anchor back in the one place FMT-02 allows.
    """

    anchor: Anchor
    lines: tuple[str, ...] = ()
    blockref: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "lines", tuple(self.lines))

    @property
    def block_id(self) -> str:
        return self.anchor.block_id

    @property
    def type(self) -> str:
        return self.anchor.type

    @property
    def locked(self) -> bool:
        return self.anchor.locked

    @property
    def text(self) -> str:
        """The raw content, newline-joined. Not normalized — see `textutil`."""
        return "\n".join(self.lines)

    def with_lines(self, lines: Iterable[str]) -> "Block":
        return replace(self, lines=tuple(lines))


# --------------------------------------------------------------------------- front matter

@dataclass(frozen=True)
class SourceRef:
    """Where a section came from in the .docx (§6.2). `None` when `origin: authored`."""

    docx: str
    paragraphs: tuple[int, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "paragraphs", tuple(self.paragraphs))

    def to_mapping(self) -> dict[str, Any]:
        return {"docx": self.docx, "paragraphs": list(self.paragraphs)}

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "SourceRef":
        return cls(docx=raw["docx"], paragraphs=tuple(raw["paragraphs"]))


#: The serialization order of §6.2's worked example. §10.11 says "keys in the order
#: listed there"; the example is the order, and Appendix D says to copy its shape
#: literally. `parent` is omitted entirely when absent rather than written as null.
FRONT_MATTER_KEYS: tuple[str, ...] = (
    "id", "doc", "number", "title", "level", "parent", "order",
    "path", "path_ids", "breadcrumb", "bookmarks", "refs_out",
    "blocks", "words", "origin", "source", "ingest_version", "generated",
)

#: §6.2 — keys `specctl fmt` owns and recomputes (DEC-12). Everything else is authored
#: at ingest and immutable.
FMT_OWNED_KEYS: frozenset[str] = frozenset({
    "number", "title", "level", "parent", "order",
    "path", "path_ids", "breadcrumb", "refs_out", "blocks", "words",
})

#: §6.7 — the serialization contract these files are written against.
INGEST_VERSION = 1


@dataclass(frozen=True)
class FrontMatter:
    """Section front matter (§6.2, schema A.1)."""

    id: str
    doc: str
    number: str
    title: str
    level: int
    order: int
    path: tuple[str, ...]
    path_ids: tuple[str, ...]
    breadcrumb: str
    bookmarks: tuple[str, ...]
    refs_out: tuple[str, ...]
    blocks: int
    words: int
    origin: str = "ingest"
    source: SourceRef | None = None
    ingest_version: int = INGEST_VERSION
    generated: bool = False
    parent: str | None = None

    def __post_init__(self) -> None:
        for field in ("path", "path_ids", "bookmarks", "refs_out"):
            object.__setattr__(self, field, tuple(getattr(self, field)))

    def to_mapping(self) -> dict[str, Any]:
        """A plain mapping in `FRONT_MATTER_KEYS` order, ready to serialize or validate."""
        out: dict[str, Any] = {}
        for key in FRONT_MATTER_KEYS:
            if key == "parent":
                if self.parent is not None:
                    out["parent"] = self.parent
                continue
            if key == "source":
                out["source"] = self.source.to_mapping() if self.source else None
                continue
            value = getattr(self, key)
            out[key] = list(value) if isinstance(value, tuple) else value
        return out

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "FrontMatter":
        source = raw.get("source")
        return cls(
            id=raw["id"], doc=raw["doc"], number=raw["number"], title=raw["title"],
            level=raw["level"], order=raw["order"],
            path=tuple(raw["path"]), path_ids=tuple(raw["path_ids"]),
            breadcrumb=raw["breadcrumb"], bookmarks=tuple(raw["bookmarks"]),
            refs_out=tuple(raw["refs_out"]), blocks=raw["blocks"], words=raw["words"],
            origin=raw["origin"],
            source=SourceRef.from_mapping(source) if source else None,
            ingest_version=raw["ingest_version"], generated=raw["generated"],
            parent=raw.get("parent"),
        )

    def replace(self, **changes: Any) -> "FrontMatter":
        return replace(self, **changes)


# --------------------------------------------------------------------------- section

@dataclass(frozen=True)
class Section:
    """One section file: front matter plus its blocks, the heading first (§6.1)."""

    front_matter: FrontMatter
    blocks: tuple[Block, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "blocks", tuple(self.blocks))

    @property
    def id(self) -> str:
        return self.front_matter.id

    @property
    def heading(self) -> Block:
        """§6.1 — a section file contains one heading block, and it comes first."""
        return self.blocks[0]

    @property
    def body(self) -> tuple[Block, ...]:
        return self.blocks[1:]

    @property
    def filename(self) -> str:
        """§5.3 — a section file MUST be named after its heading block's ID."""
        return f"{self.id}.md"

    def block(self, block_id: str) -> Block:
        for candidate in self.blocks:
            if candidate.block_id == block_id:
                return candidate
        raise KeyError(f"{block_id} is not in section {self.id}")

    def block_ids(self) -> tuple[str, ...]:
        return tuple(b.block_id for b in self.blocks)

    def with_blocks(self, blocks: Iterable[Block]) -> "Section":
        return replace(self, blocks=tuple(blocks))

    def with_front_matter(self, front_matter: FrontMatter) -> "Section":
        return replace(self, front_matter=front_matter)


@dataclass(frozen=True)
class Document:
    """Every section in the vault, in document order — what `fmt` and `index` need (§11.3)."""

    sections: tuple[Section, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sections", tuple(self.sections))

    def by_id(self) -> dict[str, Section]:
        return {s.id: s for s in self.sections}

    def all_blocks(self) -> tuple[tuple[Section, Block], ...]:
        return tuple((s, b) for s in self.sections for b in s.blocks)

    def has_block(self, block_id: str) -> bool:
        return any(b.block_id == block_id for _, b in self.all_blocks())


def is_valid_block_id(value: str) -> bool:
    return is_id(value)
