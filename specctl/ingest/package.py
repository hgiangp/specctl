"""Opening a .docx and handing out its parts (§10.2 step 1).

A .docx is a ZIP of XML parts wired together by relationship files. This module does that
unwrapping and nothing else: no interpretation of content lives here, so that the walker
above it has exactly one way to reach a part and there is one place that decides what a
readable package is.

`python-docx` is deliberately not used (§18.3). Its object model hides the very elements
§10.5 has to see — `w:sdt`, `mc:AlternateContent`, `w:ins`, `w:del` — so building on it
would create the silent-loss path the walker exists to close. The tree is read with
`lxml`, once, and every component sees the same nodes.
"""

from __future__ import annotations

import posixpath
import zipfile
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Mapping

from lxml import etree

from ..exits import ExitCode, SpecctlError

#: Every prefix the walker, the numbering resolver and the media extractor need. One
#: table, bound into every XPath, so a component cannot quietly use a different URI for
#: the same prefix and match nothing.
NS: Mapping[str, str] = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}

_REL_BASE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

#: Relationship types, by the short name the rest of the package uses.
REL_TYPES: Mapping[str, str] = {
    "header": f"{_REL_BASE}/header",
    "footer": f"{_REL_BASE}/footer",
    "footnotes": f"{_REL_BASE}/footnotes",
    "endnotes": f"{_REL_BASE}/endnotes",
    "comments": f"{_REL_BASE}/comments",
    "numbering": f"{_REL_BASE}/numbering",
    "styles": f"{_REL_BASE}/styles",
    "image": f"{_REL_BASE}/image",
    "hyperlink": f"{_REL_BASE}/hyperlink",
    "oleObject": f"{_REL_BASE}/oleObject",
}

DOCUMENT_PART = "word/document.xml"

#: Conventional names, used only when a package carries no relationship part. Word always
#: writes one; packages built by hand for a test often do not, and refusing those would
#: make the fixtures harder to write without making the reader safer.
_CONVENTIONAL = {
    "footnotes": ("word/footnotes.xml",),
    "endnotes": ("word/endnotes.xml",),
    "comments": ("word/comments.xml",),
    "numbering": ("word/numbering.xml",),
    "styles": ("word/styles.xml",),
}


def qn(qualified: str) -> str:
    """`"w:p"` → `"{http://…}p"` — the form lxml compares tags in."""
    prefix, _, local = qualified.partition(":")
    return f"{{{NS[prefix]}}}{local}"


@dataclass(frozen=True)
class Relationship:
    """One entry of a `_rels` part."""

    rel_id: str
    type: str
    target: str
    external: bool = False

    def resolve(self, source_part: str) -> str:
        """The package-absolute name of the target, for an internal relationship."""
        if self.external:
            return self.target
        base = posixpath.dirname(source_part)
        return posixpath.normpath(posixpath.join(base, self.target))


class Package:
    """A read-only view of a .docx.

    Every part is read once, at open time, into memory. The real document is a few
    megabytes, the walker makes several passes over it, and holding the bytes means no
    component can be surprised by a file that changed underneath it mid-run — §9.5 asks
    for byte-identical output from identical input, and re-reading a moving file is one
    of the ways that stops being true.
    """

    def __init__(self, path: Path, members: Mapping[str, bytes]) -> None:
        self.path = Path(path)
        self._members: dict[str, bytes] = dict(members)

    # -- opening ------------------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> "Package":
        """Read the package, or fail with exit code 3 (§9.4 — unrecoverable input)."""
        path = Path(path)
        if not path.is_file():
            raise SpecctlError(f"{path} does not exist", ExitCode.INPUT)
        try:
            with zipfile.ZipFile(path) as archive:
                broken = archive.testzip()
                if broken is not None:
                    raise SpecctlError(
                        f"{path} is a corrupt zip — member {broken!r} fails its CRC. "
                        "If it was committed through a text filter, check that "
                        ".gitattributes marks *.docx as binary",
                        ExitCode.INPUT,
                    )
                members = {name: archive.read(name) for name in archive.namelist()}
        except zipfile.BadZipFile as exc:
            raise SpecctlError(f"{path} is not a .docx package: {exc}", ExitCode.INPUT) from exc
        except OSError as exc:
            raise SpecctlError(f"{path} could not be read: {exc}", ExitCode.INPUT) from exc

        if DOCUMENT_PART not in members:
            raise SpecctlError(
                f"{path} has no {DOCUMENT_PART} — it is a zip, but not a Word document",
                ExitCode.INPUT,
            )
        return cls(path, members)

    # -- parts --------------------------------------------------------------

    @property
    def names(self) -> tuple[str, ...]:
        """Every member, sorted. Sorted because callers iterate it and §9.5 forbids
        output that depends on the order a zip happens to list its entries in."""
        return tuple(sorted(self._members))

    def has(self, name: str) -> bool:
        return name in self._members

    def read(self, name: str) -> bytes:
        try:
            return self._members[name]
        except KeyError:
            raise SpecctlError(f"{self.path} has no part {name}", ExitCode.INPUT) from None

    def xml(self, name: str) -> etree._Element:
        """Parse a part. A malformed part is an input error, never a traceback."""
        try:
            return etree.fromstring(self.read(name))
        except etree.XMLSyntaxError as exc:
            raise SpecctlError(
                f"{self.path}: part {name} is not well-formed XML: {exc}", ExitCode.INPUT
            ) from exc

    # -- the parts by name --------------------------------------------------

    @cached_property
    def document(self) -> etree._Element:
        return self.xml(DOCUMENT_PART)

    @cached_property
    def body(self) -> etree._Element:
        body = self.document.find(qn("w:body"))
        if body is None:
            raise SpecctlError(
                f"{self.path}: {DOCUMENT_PART} has no w:body", ExitCode.INPUT
            )
        return body

    def part_names(self, kind: str) -> tuple[str, ...]:
        """Every part of one relationship type, in package order.

        Sorted, so that `header2.xml` never precedes `header1.xml` because a zip listed
        it first: the skip accounting of W5 walks these and its totals must not move
        between runs.
        """
        rel_type = REL_TYPES[kind]
        found = {
            rel.resolve(DOCUMENT_PART)
            for rel in self.relationships.values()
            if rel.type == rel_type and not rel.external
        }
        if not found:
            found = {n for n in _CONVENTIONAL.get(kind, ()) if n in self._members}
        return tuple(sorted(n for n in found if n in self._members))

    def optional_root(self, kind: str) -> etree._Element | None:
        """The single part of a kind there is at most one of, or `None`."""
        names = self.part_names(kind)
        return self.xml(names[0]) if names else None

    @cached_property
    def footnotes(self) -> etree._Element | None:
        return self.optional_root("footnotes")

    @cached_property
    def endnotes(self) -> etree._Element | None:
        return self.optional_root("endnotes")

    @cached_property
    def comments(self) -> etree._Element | None:
        return self.optional_root("comments")

    @cached_property
    def numbering(self) -> etree._Element | None:
        return self.optional_root("numbering")

    @cached_property
    def styles(self) -> etree._Element | None:
        return self.optional_root("styles")

    @property
    def header_names(self) -> tuple[str, ...]:
        return self.part_names("header")

    @property
    def footer_names(self) -> tuple[str, ...]:
        return self.part_names("footer")

    # -- relationships and media -------------------------------------------

    @cached_property
    def relationships(self) -> Mapping[str, Relationship]:
        """`word/_rels/document.xml.rels`, by relationship id. Empty when absent."""
        return self.relationships_of(DOCUMENT_PART)

    def relationships_of(self, part: str) -> Mapping[str, Relationship]:
        rels_name = posixpath.join(
            posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels"
        )
        if rels_name not in self._members:
            return {}
        root = self.xml(rels_name)
        out: dict[str, Relationship] = {}
        for element in root.iter(f"{{{NS['pr']}}}Relationship"):
            rel_id = element.get("Id")
            target = element.get("Target")
            rel_type = element.get("Type")
            if not (rel_id and target and rel_type):
                continue
            out[rel_id] = Relationship(
                rel_id=rel_id,
                type=rel_type,
                target=target,
                external=(element.get("TargetMode") == "External"),
            )
        return out

    @property
    def media(self) -> tuple[str, ...]:
        return tuple(n for n in self.names if n.startswith("word/media/"))

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"<Package {self.path.name} parts={len(self._members)}>"
