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

REL_BASE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

REL_TYPE = {
    kind: f"{REL_BASE}/{kind}"
    for kind in ("numbering", "footnotes", "comments", "header", "footer", "image", "styles")
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
    mark_revision: str | None = None,
) -> str:
    """One `w:p`. `runs` replaces the text with raw run XML when a construct needs it.

    `mark_revision` is raw XML for the paragraph mark's own `w:rPr` — how Word records
    that the paragraph *mark* was inserted or deleted, which is what makes a whole
    paragraph, rather than a run inside it, a tracked change.

    The properties are emitted in schema order (`pStyle`, `numPr`, `outlineLvl`, `rPr`).
    Order is not decoration here: the fixtures exist to look like what Word writes, and a
    walker tuned to a shape Word never emits is a walker that works only on the fixtures.
    """
    props: list[str] = []
    if style:
        props.append(f'<w:pStyle w:val="{style}"/>')
    if num_id is not None:
        props.append(
            f'<w:numPr><w:ilvl w:val="{ilvl}"/><w:numId w:val="{num_id}"/></w:numPr>'
        )
    if outline_level is not None:
        props.append(f'<w:outlineLvl w:val="{outline_level}"/>')
    if mark_revision is not None:
        props.append(f"<w:rPr>{mark_revision}</w:rPr>")
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


def _revision_attrs(rev_id: int, author: str) -> str:
    return f'w:id="{rev_id}" w:author="{esc(author)}" w:date="2026-01-01T00:00:00Z"'


def tracked_insertion(text: str, *, author: str = "Reviewer", rev_id: int = 1) -> str:
    """A whole paragraph inserted with Track Changes on — current content, MUST be
    emitted (W1).

    Written the way Word writes it: `w:ins` is a **run-level** element inside the
    paragraph, and the inserted paragraph *mark* is recorded separately in `w:pPr/w:rPr`.
    Wrapping a `w:p` in a `w:ins` instead produces a file that parses but that Word never
    emits — and readers do drop it, so a walker built against that shape would pass the
    fixtures and lose inserted requirements on the real document.
    """
    return paragraph(
        mark_revision=f"<w:ins {_revision_attrs(rev_id, author)}/>",
        runs=f"<w:ins {_revision_attrs(rev_id + 1, author)}>{run(text)}</w:ins>",
    )


def tracked_deletion(text: str, *, author: str = "Reviewer", rev_id: int = 3) -> str:
    """A whole paragraph deleted with Track Changes on — NOT current content, MUST be
    discarded (W1).

    A walker that merely collects `w:t` descendants misses that `w:delText` is a
    different element and emits deleted text as a live requirement. Same run-level shape
    as `tracked_insertion`, for the same reason.
    """
    deleted_run = (
        f'<w:r><w:delText xml:space="preserve">{esc(text)}</w:delText></w:r>'
    )
    return paragraph(
        mark_revision=f"<w:del {_revision_attrs(rev_id, author)}/>",
        runs=f"<w:del {_revision_attrs(rev_id + 1, author)}>{deleted_run}</w:del>",
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


# --------------------------------------------------------------------- separate parts

# A 1x1 opaque PNG, written out literally rather than compressed at build time: the
# fixtures are committed, so every byte of them has to be the same on every machine.
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\xdachhh\x00"
    b"\x00\x03\x04\x01\x81u.\x01\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
)


def numbering_part(*, decimal_num_id: int = 1, bullet_num_id: int = 2) -> str:
    """`word/numbering.xml` with one decimal list and one bullet list.

    F06 recomputes list numbers from these definitions, because the number Word shows is
    not in the text of the file. Two `numId`s, because a numbered list and a bulleted
    list are two different ones.
    """
    def abstract(abstract_id: int, fmt: str, text: str) -> str:
        return (
            f'<w:abstractNum w:abstractNumId="{abstract_id}"><w:lvl w:ilvl="0">'
            '<w:start w:val="1"/>'
            f'<w:numFmt w:val="{fmt}"/><w:lvlText w:val="{text}"/>'
            '<w:lvlJc w:val="left"/></w:lvl></w:abstractNum>'
        )

    return (
        f"<w:numbering {_NS_DECL}>"
        + abstract(0, "decimal", "%1.")
        + abstract(1, "bullet", "\u2022")
        + f'<w:num w:numId="{decimal_num_id}"><w:abstractNumId w:val="0"/></w:num>'
        + f'<w:num w:numId="{bullet_num_id}"><w:abstractNumId w:val="1"/></w:num>'
        + "</w:numbering>"
    )


def section_properties(*, header_rel: str | None = None, footer_rel: str | None = None) -> str:
    """The trailing `w:sectPr`, which is what actually attaches a header and a footer."""
    references = ""
    if header_rel:
        references += f'<w:headerReference w:type="default" r:id="{header_rel}"/>'
    if footer_rel:
        references += f'<w:footerReference w:type="default" r:id="{footer_rel}"/>'
    return (
        f"<w:sectPr>{references}"
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417" '
        'w:header="708" w:footer="708" w:gutter="0"/>'
        "</w:sectPr>"
    )


# --------------------------------------------------------------------------- fixtures

def construct_document() -> DocxPackage:
    """Every construct §6.4 has a representation for, in one package.

    Stands in for the hand-authored `constructs.docx` until Word-authored fixtures land
    (see `tests/fixtures/README.md`). The prose carries real quantities and units, so the
    same file is usable later as input to the numeric diff of §12.
    """
    numbered = "".join(
        paragraph(text, num_id=1)
        for text in (
            "The system shall sample the pedal signal every 10 ms.",
            "The system shall report a fault within 200 ms of detection.",
        )
    )
    bulleted = "".join(
        paragraph(text, num_id=2)
        for text in (
            "Nominal supply voltage is 12 V.",
            "Threshold hysteresis is 250 mV, measured at the connector.",
        )
    )
    simple = table(
        [
            row(cell("Signal"), cell("Range"), cell("Unit")),
            row(cell("PedalPos"), cell("0 to 100"), cell("percent")),
            row(cell("BrakePressure"), cell("0 to 250"), cell("bar")),
        ],
        columns=3,
    )
    merged = table(
        [
            row(cell("Operating conditions", grid_span=2), cell("Limit")),
            row(cell("Temperature", v_merge="restart"), cell("Minimum"), cell("-40 degC")),
            row(cell("", v_merge="continue"), cell("Maximum"), cell("85 degC")),
        ],
        columns=3,
    )
    body = (
        heading(1, "Scope")
        + paragraph(
            "This document specifies the braking subsystem interface and its timing."
        )
        + heading(2, "Timing requirements")
        + numbered
        + heading(3, "Electrical thresholds")
        + bulleted
        + simple
        + merged
        + image_paragraph()
        + paragraph("Figure 1 shows the signal chain from pedal to actuator.")
        + text_box(
            "Note in a text box: the actuator is disabled below 9 V of supply voltage."
        )
        + equation("E = mc^2")
        + paragraph(runs=bookmark("_Ref_thresholds") + run("Signal thresholds are listed here."))
        + paragraph(
            runs=run("Braking force is applied once the pedal exceeds the threshold in ")
            + ref_field("_Ref_thresholds", "section 1.3")
            + run(".")
        )
        + footnote_reference(2)
        + section_properties()
    )
    return DocxPackage(
        body=body,
        parts={
            "numbering.xml": numbering_part(),
            "footnotes.xml": footnotes_part(
                {2: "Measured at 25 degC unless stated otherwise."}
            ),
        },
        relationships=[
            ("rIdNum", REL_TYPE["numbering"], "numbering.xml"),
            ("rIdFootnotes", REL_TYPE["footnotes"], "footnotes.xml"),
            ("rIdImg", REL_TYPE["image"], "media/image1.png"),
        ],
        binaries={"media/image1.png": PNG_1X1},
    )


def revisions_document() -> DocxPackage:
    """One tracked insertion, one tracked deletion, one comment — saved unaccepted.

    Stands in for the hand-authored `revisions.docx`. The deletion is the point: `w:delText`
    is a different element from `w:t`, so a walker that collects `w:t` descendants emits
    deleted text as a live requirement (§10.5 W1). That is content fabricated by parsing
    rather than by hallucination, and no AI is involved in it at all.
    """
    body = (
        heading(1, "Revision handling")
        + paragraph("This paragraph is untouched and must be emitted exactly once.")
        + tracked_insertion(
            "The watchdog shall reset the controller after 100 ms without a heartbeat."
        )
        + tracked_deletion(
            "The watchdog shall reset the controller after 500 ms without a heartbeat."
        )
        + paragraph(
            runs=comment_anchor(
                "The supply rail shall remain within 11 V to 15 V during cranking.",
                comment_id=1,
            )
        )
        + section_properties()
    )
    return DocxPackage(
        body=body,
        parts={"comments.xml": comments_part({1: "Confirm the cranking range with the OEM."})},
        relationships=[("rIdComments", REL_TYPE["comments"], "comments.xml")],
    )


def containers_document() -> DocxPackage:
    """Wrappers to see through, and content to skip.

    Stands in for the hand-authored `containers.docx`. The content control is a wrapper —
    the walker descends through it (W6); the TOC field, the header and the footer are
    skipped **with counts** (W4, W5), so what was dropped on purpose sits next to what
    was kept.
    """
    body = (
        toc_field(["1 Scope", "2 Requirements", "3 Interfaces"])
        + heading(1, "Scope")
        + content_control(
            paragraph(
                "This paragraph sits inside a rich text content control and is ordinary "
                "requirement text."
            )
        )
        + heading(1, "Requirements")
        + content_control(
            paragraph("The diagnostic session shall time out after 5 s of inactivity.")
            + paragraph("Timeout is measured from the last accepted request.")
        )
        + paragraph("A plain paragraph after the content controls, to prove nothing is eaten.")
        + section_properties(header_rel="rIdHeader", footer_rel="rIdFooter")
    )
    return DocxPackage(
        body=body,
        parts={
            "header1.xml": header_part(paragraph("SYS specification - confidential")),
            "footer1.xml": footer_part(paragraph("Page 1 of 3")),
        },
        relationships=[
            ("rIdHeader", REL_TYPE["header"], "header1.xml"),
            ("rIdFooter", REL_TYPE["footer"], "footer1.xml"),
        ],
    )


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


def parts_of(path: Path) -> dict[str, bytes]:
    """Every part of a package, by name.

    Used to compare a committed fixture with a fresh build. Parts are compared rather than
    whole-file bytes because the zip container's compressed bytes can differ between zlib
    builds, while the parts inside it are what the fixture actually *is*.
    """
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


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
