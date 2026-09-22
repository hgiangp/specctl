"""Build and inspect .docx packages from raw OOXML.

A .docx is a ZIP of XML parts. Writing them directly serves two jobs Word cannot:

* **deliberately malformed input** — Word always writes valid OOXML, so a table that
  cannot be serialized in either form (§10.6) has to be built by hand. It is what
  proves the degrade path of §6.4 actually degrades rather than crashing;
* **regression cases found later** — when the real document exposes a walker bug, the
  minimal reproduction is written here, in code that diffs, instead of as another
  binary nobody can review.

Hand-authored fixtures remain the primary input (see `tests/fixtures/README.md`): Word
emits the same OOXML the customer's file does, and a committed binary is byte-stable.

The inspection half exists because **Word does not always save what you think**. It
resolves fields, drops empty content controls, and silently accepts tracked changes on
some save paths. Checking the raw XML tells you a fixture is wrong *here*, instead of
letting F05 blame the walker for a construct that was never in the file.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "v": "urn:schemas-microsoft-com:vml",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}

_W = NS["w"]

CONTENT_TYPE = {
    "document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
    "numbering": "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml",
    "footnotes": "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml",
    "comments": "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
    "header": "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
    "footer": "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml",
    "styles": "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml",
}

_XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

_NS_DECL = " ".join(
    f'xmlns:{prefix}="{uri}"'
    for prefix, uri in NS.items()
    if prefix not in ("ct", "pr")
)


# --------------------------------------------------------------------------- building

@dataclass
class DocxPackage:
    """The parts of a package, ready to zip."""

    body: str
    parts: dict[str, str] = field(default_factory=dict)
    relationships: list[tuple[str, str, str]] = field(default_factory=list)
    binaries: dict[str, bytes] = field(default_factory=dict)

    def document_xml(self) -> str:
        return (
            _XML_DECL
            + f"<w:document {_NS_DECL}><w:body>{self.body}</w:body></w:document>"
        )

    def content_types_xml(self) -> str:
        overrides = ['<Override PartName="/word/document.xml" '
                     f'ContentType="{CONTENT_TYPE["document"]}"/>']
        for name in sorted(self.parts):
            kind = Path(name).stem.rstrip("0123456789")
            content_type = CONTENT_TYPE.get(kind)
            if content_type:
                overrides.append(
                    f'<Override PartName="/word/{name}" ContentType="{content_type}"/>'
                )
        defaults = [
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Default Extension="png" ContentType="image/png"/>',
        ]
        return (
            _XML_DECL
            + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            + "".join(defaults) + "".join(overrides) + "</Types>"
        )

    def root_rels_xml(self) -> str:
        return (
            _XML_DECL
            + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>'
        )

    def document_rels_xml(self) -> str:
        entries = "".join(
            f'<Relationship Id="{rel_id}" Type="{rel_type}" Target="{target}"/>'
            for rel_id, rel_type, target in self.relationships
        )
        return (
            _XML_DECL
            + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + entries + "</Relationships>"
        )

    def write(self, path: Path) -> Path:
        """Zip the package. Fixed timestamps, so two builds are byte-identical (§9.5)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        members: list[tuple[str, bytes]] = [
            ("[Content_Types].xml", self.content_types_xml().encode("utf-8")),
            ("_rels/.rels", self.root_rels_xml().encode("utf-8")),
            ("word/document.xml", self.document_xml().encode("utf-8")),
        ]
        if self.relationships:
            members.append(
                ("word/_rels/document.xml.rels", self.document_rels_xml().encode("utf-8"))
            )
        for name, text in sorted(self.parts.items()):
            members.append((f"word/{name}", (_XML_DECL + text).encode("utf-8")))
        for name, blob in sorted(self.binaries.items()):
            members.append((f"word/{name}", blob))

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, blob in members:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, blob)
        return path


def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def run(text: str, *, bold: bool = False, italic: bool = False) -> str:
    props = ""
    if bold or italic:
        props = "<w:rPr>" + ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + "</w:rPr>"
    # xml:space keeps leading and trailing spaces, which normalize_ws then collapses.
    return f'<w:r>{props}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def paragraph(
    text: str = "",
    *,
    style: str | None = None,
    outline_level: int | None = None,
    num_id: int | None = None,
    ilvl: int = 0,
    runs: str | None = None,
) -> str:
    """One `w:p`. `runs` replaces the text with raw run XML when a construct needs it."""
    props: list[str] = []
    if style:
        props.append(f'<w:pStyle w:val="{style}"/>')
    if outline_level is not None:
        props.append(f'<w:outlineLvl w:val="{outline_level}"/>')
    if num_id is not None:
        props.append(
            f'<w:numPr><w:ilvl w:val="{ilvl}"/><w:numId w:val="{num_id}"/></w:numPr>'
        )
    prop_xml = f"<w:pPr>{''.join(props)}</w:pPr>" if props else ""
    body = runs if runs is not None else (run(text) if text else "")
    return f"<w:p>{prop_xml}{body}</w:p>"


def heading(level: int, text: str, *, num_id: int | None = None) -> str:
    return paragraph(
        text, style=f"Heading{level}", outline_level=level - 1, num_id=num_id
    )


def cell(text: str, *, grid_span: int | None = None, v_merge: str | None = None,
         content: str | None = None) -> str:
    props: list[str] = []
    if grid_span is not None:
        props.append(f'<w:gridSpan w:val="{grid_span}"/>')
    if v_merge is not None:
        props.append(f'<w:vMerge w:val="{v_merge}"/>')
    prop_xml = f"<w:tcPr>{''.join(props)}</w:tcPr>" if props else ""
    inner = content if content is not None else paragraph(text)
    return f"<w:tc>{prop_xml}{inner}</w:tc>"


def table(rows: Sequence[str], *, columns: int) -> str:
    grid = "".join(f'<w:gridCol w:w="2000"/>' for _ in range(columns))
    return f"<w:tbl><w:tblGrid>{grid}</w:tblGrid>{''.join(rows)}</w:tbl>"


def row(*cells: str) -> str:
    return f"<w:tr>{''.join(cells)}</w:tr>"


def bookmark(name: str, *, bookmark_id: int = 1) -> str:
    return (
        f'<w:bookmarkStart w:id="{bookmark_id}" w:name="{name}"/>'
        f'<w:bookmarkEnd w:id="{bookmark_id}"/>'
    )


def ref_field(target: str, display: str) -> str:
    """A `REF` field with its rendered result, as Word stores a cross-reference (§10.4)."""
    return (
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve"> REF {target} \\h </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        f"{run(display)}"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    )


def toc_field(entries: Iterable[str]) -> str:
    """A TOC field and its expanded result — skipped in full by W4 (§10.5)."""
    body = [
        "<w:p>"
        '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
        '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        "</w:p>"
    ]
    for index, entry in enumerate(entries, start=1):
        body.append(
            paragraph(
                style="TOC1",
                runs=bookmark(f"_Toc9000{index}", bookmark_id=900 + index) + run(entry),
            )
        )
    body.append('<w:p><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
    return "".join(body)


def content_control(inner: str) -> str:
    """A `w:sdt`. The walker must descend through it transparently (§10.5)."""
    return (
        "<w:sdt><w:sdtPr><w:alias w:val='block'/></w:sdtPr>"
        f"<w:sdtContent>{inner}</w:sdtContent></w:sdt>"
    )


def tracked_insertion(text: str, *, author: str = "Reviewer", rev_id: int = 1) -> str:
    """`w:ins` — current content, MUST be emitted (W1)."""
    return (
        f'<w:ins w:id="{rev_id}" w:author="{author}" w:date="2026-01-01T00:00:00Z">'
        f"{paragraph(text)}</w:ins>"
    )


def tracked_deletion(text: str, *, author: str = "Reviewer", rev_id: int = 2) -> str:
    """`w:del` with `w:delText` — NOT current content, MUST be discarded (W1).

    A walker that merely collects `w:t` descendants misses that `w:delText` is a
    different element and emits deleted text as a live requirement.
    """
    return (
        f'<w:del w:id="{rev_id}" w:author="{author}" w:date="2026-01-01T00:00:00Z">'
        f'<w:p><w:r><w:delText xml:space="preserve">{esc(text)}</w:delText></w:r></w:p>'
        "</w:del>"
    )


def text_box(text: str) -> str:
    """A shape with a text box, inside `mc:AlternateContent` as Word writes it (§10.7)."""
    return (
        "<w:p><w:r><mc:AlternateContent>"
        '<mc:Choice Requires="wps"><w:drawing><wp:inline>'
        "<a:graphic><a:graphicData><wps:wsp><wps:txbx><w:txbxContent>"
        f"{paragraph(text)}"
        "</w:txbxContent></wps:txbx></wps:wsp></a:graphicData></a:graphic>"
        "</wp:inline></w:drawing></mc:Choice>"
        "<mc:Fallback><w:pict><v:shape><v:textbox><w:txbxContent>"
        f"{paragraph(text)}"
        "</w:txbxContent></v:textbox></v:shape></w:pict></mc:Fallback>"
        "</mc:AlternateContent></w:r></w:p>"
    )


def equation(latex_ish: str = "x") -> str:
    """An inline OMML equation (§10.8)."""
    return (
        "<w:p><m:oMath><m:r><m:t>" + esc(latex_ish) + "</m:t></m:r></m:oMath></w:p>"
    )


def image_paragraph(rel_id: str = "rIdImg") -> str:
    return (
        "<w:p><w:r><w:drawing><wp:inline><a:graphic><a:graphicData>"
        f'<a:blip r:embed="{rel_id}"/>'
        "</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
    )


def footnote_reference(footnote_id: int = 2) -> str:
    return f'<w:p><w:r><w:footnoteReference w:id="{footnote_id}"/></w:r></w:p>'


# --------------------------------------------------------------------------- fixtures

def malformed_table_document() -> DocxPackage:
    """A table that cannot be serialized as a pipe table **or** as HTML (§10.6).

    Word cannot author this, which is why it is built here. Two independent breaks:

    * the grid declares three columns, while the first row's `gridSpan` values total
      five — no consistent column count exists, so `rowspan`/`colspan` cannot be
      computed;
    * a `vMerge` continuation appears with no `restart` above it, so the vertical merge
      has no origin row to attach to.

    The total-capture invariant (§6.4) says this must still produce a `raw locked
    fallback` block carrying the cell text, never an error that drops the table.
    """
    rows = [
        row(cell("A", grid_span=3), cell("B", grid_span=2)),
        row(cell("C", v_merge="continue"), cell("D")),
        row(),  # a row with no cells at all
    ]
    body = (
        heading(1, "Degraded table")
        + paragraph("The table below cannot be represented in either form.")
        + table(rows, columns=3)
        + paragraph("Text after the table, which must survive.")
    )
    return DocxPackage(body=body)


# --------------------------------------------------------------------------- inspecting

def part_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return sorted(archive.namelist())


def read_part(path: Path, name: str) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read(name)


def parse_part(path: Path, name: str = "word/document.xml"):
    return etree.fromstring(read_part(path, name))


def xpath(path: Path, expression: str, *, part: str = "word/document.xml") -> list:
    """Run an XPath over a part, with every OOXML prefix already bound."""
    return parse_part(path, part).xpath(expression, namespaces=NS)


def count(path: Path, expression: str, *, part: str = "word/document.xml") -> int:
    return len(xpath(path, expression, part=part))


def has(path: Path, expression: str, *, part: str = "word/document.xml") -> bool:
    return count(path, expression, part=part) > 0


def is_docx(path: Path) -> bool:
    """A readable ZIP carrying a main document part."""
    if not Path(path).is_file():
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                return False
            return "word/document.xml" in archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


# --------------------------------------------------------------------------- F05 builders

REL_BASE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _wrapped_part(tag: str, body: str) -> str:
    return f"<w:{tag} {_NS_DECL}>{body}</w:{tag}>"


def header_part(*paragraphs: str) -> str:
    """A `word/headerN.xml` part. Skipped whole and accounted by W5 (§10.5)."""
    return _wrapped_part("hdr", "".join(paragraphs))


def footer_part(*paragraphs: str) -> str:
    return _wrapped_part("ftr", "".join(paragraphs))


def footnotes_part(notes: Mapping[int, str], *, with_separators: bool = True) -> str:
    """A `word/footnotes.xml`. Word puts the separator furniture at ids -1 and 0, which
    W5 accounts and skips — a fixture without them would not test that."""
    body: list[str] = []
    if with_separators:
        body.append(
            f'<w:footnote w:type="separator" w:id="-1">{paragraph(runs="<w:r><w:separator/></w:r>")}</w:footnote>'
        )
        body.append(
            f'<w:footnote w:type="continuationSeparator" w:id="0">'
            f'{paragraph(runs="<w:r><w:continuationSeparator/></w:r>")}</w:footnote>'
        )
    for note_id, text in sorted(notes.items()):
        body.append(f'<w:footnote w:id="{note_id}">{paragraph(text)}</w:footnote>')
    return _wrapped_part("footnotes", "".join(body))


def comments_part(comments: Mapping[int, str]) -> str:
    body = "".join(
        f'<w:comment w:id="{cid}" w:author="Reviewer" w:date="2026-01-01T00:00:00Z">'
        f"{paragraph(text)}</w:comment>"
        for cid, text in sorted(comments.items())
    )
    return _wrapped_part("comments", body)


def comment_anchor(text: str, *, comment_id: int = 1) -> str:
    """Runs carrying a comment: the text stays, the anchor is dropped and counted (W3)."""
    return (
        f'<w:commentRangeStart w:id="{comment_id}"/>'
        + run(text)
        + f'<w:commentRangeEnd w:id="{comment_id}"/>'
        + f'<w:r><w:commentReference w:id="{comment_id}"/></w:r>'
    )


def smart_tag(inner: str, *, element: str = "place") -> str:
    """A `w:smartTag` — packaging the walker steps straight through (§10.5)."""
    return f'<w:smartTag w:uri="urn:test" w:element="{element}">{inner}</w:smartTag>'


def unknown_container(inner: str, *, tag: str = "x:未知") -> str:
    """An element no rule names, holding real paragraphs — the W6 case.

    W6 is the rule that makes the walker safe against a construct nobody anticipated:
    descend anyway, and leave a note. A fixture for it cannot use a real OOXML element,
    because then it would not be unknown.
    """
    return f'<{tag} xmlns:x="urn:test">{inner}</{tag}>'


def fld_simple_toc(result: str) -> str:
    """The simple-field spelling of a TOC (W4 names both forms)."""
    return (
        '<w:p><w:fldSimple w:instr=" TOC \\o &quot;1-3&quot; \\h ">'
        + run(result)
        + "</w:fldSimple></w:p>"
    )


def ole_object(text: str = "") -> str:
    """A `w:object` — the OLE case of §10.7, which has no extractable bitmap."""
    inner = run(text) if text else ""
    return (
        "<w:p><w:r><w:object>"
        '<v:shape><v:imagedata r:id="rIdOle"/></v:shape>'
        '<o:OLEObject xmlns:o="urn:schemas-microsoft-com:office:office" '
        f'Type="Embed" ProgID="Excel.Sheet.12" r:id="rIdOle"/>{inner}'
        "</w:object></w:r></w:p>"
    )


def add_part(package: "DocxPackage", name: str, xml: str, rel_type: str) -> "DocxPackage":
    """Attach a part and the relationship that points at it, as Word writes both."""
    package.parts[name] = xml
    rel_id = f"rId{len(package.relationships) + 100}"
    package.relationships.append((rel_id, f"{REL_BASE}/{rel_type}", name))
    return package
