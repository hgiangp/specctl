"""Pandoc as a test oracle — never as part of the conversion path.

Pandoc carries years of .docx edge-case handling. Borrowing it as an *oracle* costs
nothing and catches real bugs: **text pandoc finds that our reader does not is a bug in
our reader**, surfaced on a fixture instead of on the customer's document.

What pandoc cannot do is be the converter. It drops what it cannot represent, silently,
and exits 0 — while §6.4 requires a converter that knows it degraded, so the construct
survives as a `raw locked fallback` block with its OOXML and a named reason. A number
with no recovery path is not the same thing as a preserved document.

Every test here skips when pandoc is not installed, so it is never a build dependency.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specctl.textutil import normalize

from .support import docx as D
from .support import pandoc

pytestmark = pytest.mark.skipif(not pandoc.available(), reason="pandoc is not installed")

MIN_LONG_SEGMENT = 12  # §10.12 F8


def source_segments(path: Path) -> list[str]:
    """Paragraph text in the accepted-revision state, read straight from OOXML.

    Writer-independent by construction (§10.12 step 1), which is what lets one metric
    judge our reader and pandoc on equal terms.
    """
    w = D.NS["w"]
    out: list[str] = []
    for paragraph in D.parse_part(path).iter(f"{{{w}}}p"):
        if any(a.tag == f"{{{w}}}del" for a in paragraph.iterancestors()):
            continue
        text = normalize("".join(t.text or "" for t in paragraph.iter(f"{{{w}}}t")))
        if text:
            out.append(text)
    return out


def covered(segment: str, haystack: str) -> bool:
    """§10.12 F8 — a short segment must match at a token boundary, not by accident."""
    if len(segment) >= MIN_LONG_SEGMENT:
        return segment in haystack
    return re.search(r"(?<![0-9a-z])" + re.escape(segment) + r"(?![0-9a-z])", haystack) is not None


def pandoc_coverage(path: Path) -> tuple[float, list[str]]:
    segments = source_segments(path)
    haystack = normalize(pandoc.convert(path).text)
    lost = [s for s in segments if not covered(s, haystack)]
    ratio = (len(segments) - len(lost)) / len(segments) if segments else 1.0
    return ratio, lost


# ------------------------------------------------------------------ the oracle

@pytest.mark.parametrize("fixture", ["constructs.docx", "revisions.docx", "containers.docx"])
def test_our_reader_finds_everything_pandoc_finds(fixture: str) -> None:
    """The whole point of keeping pandoc around.

    When F05 lands this compares the two readers segment by segment. Anything pandoc
    recovered and we did not is a walker bug, reported with the text it lost.
    """
    from .support.fixtures import require

    path = require(fixture)
    pytest.importorskip(
        "specctl.ingest.walk",
        reason="F05 (the OOXML walker) is not implemented yet — this is its oracle",
    )
    from specctl.ingest.walk import walk_text  # type: ignore[attr-defined]

    ours = normalize("\n".join(walk_text(path)))
    theirs = normalize(pandoc.convert(path).text)
    missed = [
        s for s in source_segments(path)
        if covered(s, theirs) and not covered(s, ours)
    ]
    assert not missed, (
        f"pandoc recovered {len(missed)} segment(s) our walker did not:\n"
        + "\n".join(f"  - {s[:100]!r}" for s in missed)
    )


# ------------------------------------------------------------------ recorded baseline

def test_pandoc_loses_text_box_content(tmp_path: Path) -> None:
    """Recorded, because it is why pandoc cannot be the converter.

    A text box holds requirement text in automotive specs. §6.4 emits it twice — once
    rendered, once as a searchable `raw` block — and §10.12 F4 counts it once. Pandoc
    emits it zero times, in both the VML and the DrawingML form, and says nothing.

    If this test ever fails, pandoc has improved: re-run the comparison rather than
    deleting the test.
    """
    vml = (
        '<w:p><w:r><w:pict><v:shape><v:textbox><w:txbxContent>'
        '<w:p><w:r><w:t>VML textbox sentence long enough to match.</w:t></w:r></w:p>'
        "</w:txbxContent></v:textbox></v:shape></w:pict></w:r></w:p>"
    )
    path = D.DocxPackage(
        body=D.paragraph("Ordinary paragraph that survives.")
        + vml
        + D.text_box("DrawingML textbox sentence long enough to match.")
    ).write(tmp_path / "textbox.docx")

    ratio, lost = pandoc_coverage(path)
    assert ratio < 1.0, "pandoc no longer loses text boxes — re-evaluate the decision"
    assert any("textbox sentence" in s for s in lost)


def test_pandoc_loses_cells_of_a_table_it_cannot_represent(tmp_path: Path) -> None:
    """The failure mode the whole design exists to prevent, demonstrated.

    Pandoc prints a plausible-looking table containing only the first cell, drops the
    rest, and exits 0. Nothing in its output says a cell went missing. §6.4 requires the
    opposite: degrade to `raw`, keep the text, name the reason.
    """
    path = D.malformed_table_document().write(tmp_path / "degraded.docx")
    result = pandoc.convert(path)
    assert result.returncode == 0, "the silence is the point: no error is raised"

    ratio, lost = pandoc_coverage(path)
    assert ratio < 1.0
    assert {"b", "c", "d"} <= {s.lower() for s in lost}, (
        f"expected the merged-away cells to vanish, lost={lost}"
    )


def test_pandoc_drops_a_custom_list_number_prefix(tmp_path: Path) -> None:
    """`lvlText = "REQ-%1."` with `start = 5` should render as `REQ-5.` (§10.3).

    Pandoc gets the start value right and drops the prefix, so a requirement identified
    as REQ-5 loses its identifier while the text around it looks untouched.
    """
    ns = " ".join(f'xmlns:{p}="{u}"' for p, u in D.NS.items() if p not in ("ct", "pr"))
    numbering = (
        f"<w:numbering {ns}><w:abstractNum w:abstractNumId=\"0\"><w:lvl w:ilvl=\"0\">"
        '<w:start w:val="5"/><w:numFmt w:val="decimal"/><w:lvlText w:val="REQ-%1."/>'
        '</w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
        "</w:numbering>"
    )
    path = D.DocxPackage(
        body=D.paragraph("Apply torque within 50 ms.", num_id=1),
        parts={"numbering.xml": numbering},
    ).write(tmp_path / "numbering.docx")

    text = pandoc.convert(path, to="markdown").text
    assert "REQ-5" not in text, "pandoc now renders lvlText — re-evaluate"
    assert "5." in text  # the start value survives; the prefix does not


def test_pandoc_keeps_bookmarks_and_anchored_links(tmp_path: Path) -> None:
    """The fair other side: pandoc does preserve these, and a hand-written reader that
    loses them would be worse. Recorded so the comparison stays honest."""
    path = D.DocxPackage(
        body=D.paragraph(runs=D.bookmark("_Ref55001") + D.run("Target paragraph."))
        + D.paragraph(
            runs='<w:hyperlink w:anchor="_Ref55001">' + D.run("see target") + "</w:hyperlink>"
        )
    ).write(tmp_path / "links.docx")

    markdown = pandoc.convert(path, to="markdown").text
    assert "_Ref55001" in markdown
    assert "(#_Ref55001)" in markdown


def test_pandoc_handles_word_style_tracked_changes(tmp_path: Path) -> None:
    """Also fair: run-level and paragraph-mark tracked changes are handled correctly,
    which is the form Word actually writes (§10.5 W1)."""
    body = (
        '<w:p><w:r><w:t xml:space="preserve">Before. </w:t></w:r>'
        '<w:ins w:id="1" w:author="R" w:date="2026-01-01T00:00:00Z">'
        '<w:r><w:t xml:space="preserve">Inserted sentence here. </w:t></w:r></w:ins>'
        '<w:del w:id="2" w:author="R" w:date="2026-01-01T00:00:00Z">'
        "<w:r><w:delText>Deleted sentence here.</w:delText></w:r></w:del>"
        "<w:r><w:t>After.</w:t></w:r></w:p>"
    )
    path = D.DocxPackage(body=body).write(tmp_path / "revisions.docx")
    text = pandoc.convert(path).text
    assert "Inserted sentence here." in text
    assert "Deleted sentence here." not in text
