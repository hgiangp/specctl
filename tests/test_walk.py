"""The block-stream walker (§10.5) — the one place data is lost silently.

Every test here is a claim about something that does **not** happen: a paragraph that
does not vanish inside a wrapper, deleted text that does not come back as a requirement,
a table of contents that does not become a hundred requirements, a text box that is not
counted twice. Those are the four shapes of Failure 1, and a reader can be wrong in any
of them while running cleanly and producing plausible output.

So the assertions are mostly negative, and the positive ones are paired with a negative:
"the insertion is emitted" is only half a test — the other half is "the deletion is not",
and a third is "both were counted", because a silent drop and an accounted skip look the
same from the outside if nobody counts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specctl.ingest.package import Package
from specctl.ingest.report import ISSUE_CODES
from specctl.ingest.walk import BlockStream, walk_document, walk_text

from .support import docx as D
from .support.fixtures import require


def build(tmp_path: Path, body: str, *, name: str = "doc.docx", **kwargs) -> Path:
    return D.DocxPackage(body=body, **kwargs).write(tmp_path / name)


def stream(tmp_path: Path, body: str, **kwargs) -> BlockStream:
    return walk_document(build(tmp_path, body, **kwargs))


def texts(result: BlockStream) -> str:
    """Everything the walk recovered, as one searchable string."""
    return "\n".join(result.texts())


# =========================================================================== W1

def test_a_tracked_insertion_is_emitted_and_a_tracked_deletion_is_not(tmp_path: Path) -> None:
    """T-ING-11, the most dangerous case in the whole reader.

    A walker that collects `w:t` descendants emits the deleted paragraph as a live
    requirement. That is content fabricated by *parsing* rather than by hallucination,
    and in a contractual document it is indistinguishable from the real thing.
    """
    result = stream(
        tmp_path,
        D.paragraph("Untouched requirement.")
        + D.tracked_insertion("Inserted requirement, currently in force.")
        + D.tracked_deletion("Deleted requirement, no longer in force."),
    )

    body = texts(result)
    assert "Inserted requirement, currently in force." in body
    assert "Deleted requirement" not in body


def test_both_sides_of_a_revision_are_counted(tmp_path: Path) -> None:
    """The other half of T-ING-11. A run that reported only what it kept would say
    nothing about the paragraph it correctly threw away."""
    result = stream(
        tmp_path,
        D.tracked_insertion("Inserted.") + D.tracked_deletion("Deleted."),
    )

    assert result.revisions.ins_accepted == 1
    assert result.revisions.del_discarded == 1


def test_run_level_revisions_inside_one_paragraph_are_handled_too(tmp_path: Path) -> None:
    """The form Word actually writes: a sentence edited in place, not a whole paragraph
    wrapped. Both spellings have to work or the fixture proves nothing about the file."""
    body = (
        '<w:p><w:r><w:t xml:space="preserve">Before. </w:t></w:r>'
        '<w:ins w:id="1" w:author="R" w:date="2026-01-01T00:00:00Z">'
        '<w:r><w:t xml:space="preserve">Inserted sentence. </w:t></w:r></w:ins>'
        '<w:del w:id="2" w:author="R" w:date="2026-01-01T00:00:00Z">'
        "<w:r><w:delText>Deleted sentence.</w:delText></w:r></w:del>"
        "<w:r><w:t>After.</w:t></w:r></w:p>"
    )
    result = stream(tmp_path, body)

    assert result.items[0].text == "Before. Inserted sentence. After."
    assert result.revisions.ins_accepted == 1
    assert result.revisions.del_discarded == 1


def test_del_text_never_reaches_the_stream_under_any_wrapper(tmp_path: Path) -> None:
    """`w:delText` is a different element from `w:t` — which is exactly why a reader
    that queries for `w:t` looks correct and a reader that queries for text is not."""
    body = (
        D.content_control(D.tracked_deletion("Deleted inside a content control."))
        + D.table(
            [D.row(D.cell("", content=D.tracked_deletion("Deleted inside a cell.")))],
            columns=1,
        )
    )
    result = stream(tmp_path, body)

    assert "Deleted inside" not in texts(result)


def test_an_insertion_inside_a_deletion_is_discarded_with_it(tmp_path: Path) -> None:
    """Reinstated then removed again: the deletion is the outer state, so the whole
    subtree goes. Walking into `w:del` to find the `w:ins` would resurrect it."""
    body = (
        '<w:del w:id="1" w:author="R" w:date="2026-01-01T00:00:00Z">'
        '<w:p><w:ins w:id="2" w:author="R" w:date="2026-01-01T00:00:00Z">'
        "<w:r><w:delText>Reinstated then removed.</w:delText></w:r></w:ins></w:p>"
        "</w:del>"
    )
    result = stream(tmp_path, body)

    assert "Reinstated" not in texts(result)
    assert result.revisions.del_discarded == 1
    assert result.revisions.ins_accepted == 0, "the nested insertion is not current content"


# =========================================================================== W2

def test_a_source_carrying_revisions_raises_the_baseline_warning(tmp_path: Path) -> None:
    """W2 — the source should be reviewed before it is treated as a baseline. Handling
    tracked changes correctly is not the same as the document being ready."""
    result = stream(tmp_path, D.tracked_deletion("Deleted."))
    found = result.issues_with("source_has_unresolved_revisions")

    assert len(found) == 1
    assert found[0].severity == "warn"


def test_a_clean_source_raises_no_revision_warning(tmp_path: Path) -> None:
    """The half that keeps the warning worth reading. A check that fires on every
    document is a check nobody looks at."""
    result = stream(tmp_path, D.paragraph("A clean requirement."))

    assert result.issues_with("source_has_unresolved_revisions") == ()


# =========================================================================== W3

def test_a_comment_is_discarded_and_the_text_it_annotates_is_kept(tmp_path: Path) -> None:
    result = stream(
        tmp_path,
        D.paragraph(runs=D.comment_anchor("Braking force within 50 ms.")),
        parts={"comments.xml": D.comments_part({1: "Is this still right?"})},
    )

    assert "Braking force within 50 ms." in texts(result)
    assert "Is this still right?" not in texts(result)
    assert result.revisions.comments_discarded == 1


# =========================================================================== W4

def test_a_toc_field_is_skipped_whole_and_accounted(tmp_path: Path) -> None:
    """T-ING-12. A TOC expands to one paragraph per heading; emitting them would turn
    the table of contents into a hundred requirements that nobody wrote."""
    result = stream(
        tmp_path,
        D.paragraph("Before the contents.")
        + D.toc_field(["1 Scope 3", "2 Requirements 7", "3 Braking 11"])
        + D.heading(1, "Scope"),
    )

    body = texts(result)
    assert "Requirements 7" not in body
    assert "Before the contents." in body
    assert "Scope" in body, "the real heading after the field survives"
    assert result.skipped["toc"].paragraphs == 5   # open, three entries, close
    assert result.skipped["toc"].chars > 0


def test_the_simple_field_spelling_of_a_toc_is_skipped_too(tmp_path: Path) -> None:
    """W4 names `w:fldSimple` as well. One spelling handled is the other one lost."""
    result = stream(
        tmp_path, D.fld_simple_toc("1 Scope 3") + D.paragraph("Real content.")
    )

    assert "1 Scope 3" not in texts(result)
    assert "Real content." in texts(result)
    assert result.skipped["toc"].paragraphs == 1


def test_a_toc_styled_paragraph_is_skipped_even_with_no_field(tmp_path: Path) -> None:
    result = stream(tmp_path, D.paragraph("2 Requirements 7", style="TOC1"))

    assert result.items == ()
    assert result.skipped["toc"].paragraphs == 1


def test_the_table_of_contents_heading_itself_is_not_skipped(tmp_path: Path) -> None:
    """`TOCHeading` styles the words "Table of Contents", which is a heading the
    document genuinely contains. Skipping by prefix would drop it."""
    result = stream(tmp_path, D.paragraph("Table of Contents", style="TOCHeading"))

    assert "Table of Contents" in texts(result)
    assert result.skipped["toc"].paragraphs == 0


def test_a_field_that_spans_paragraphs_closes_again_afterwards(tmp_path: Path) -> None:
    """The state has to survive between items, and it has to *stop*. A walker that
    never pops the field skips the entire rest of the document — silently."""
    result = stream(
        tmp_path,
        D.toc_field(["1 Scope 3"])
        + D.paragraph("First requirement after the contents.")
        + D.paragraph("Second requirement after the contents."),
    )

    assert [i.text for i in result.items] == [
        "First requirement after the contents.",
        "Second requirement after the contents.",
    ]


def test_a_non_toc_field_keeps_its_rendered_result(tmp_path: Path) -> None:
    """A cross-reference is a field too. Skipping every field would lose the text of
    every "see section 3.2" in the document (§10.4)."""
    result = stream(
        tmp_path,
        D.paragraph(runs=D.bookmark("_Ref55001") + D.run("Signal thresholds"))
        + D.paragraph(runs=D.ref_field("_Ref55001", "5.1 Signal thresholds")),
    )

    body = texts(result)
    assert "5.1 Signal thresholds" in body
    assert "REF _Ref55001" not in body, "the field instruction is not content"
    assert result.skipped["toc"].paragraphs == 0


# =========================================================================== W5

def test_headers_and_footers_are_skipped_and_accounted(tmp_path: Path) -> None:
    built = D.DocxPackage(body=D.paragraph("Body text."))
    D.add_part(built, "header1.xml",
               D.header_part(D.paragraph("Confidential — do not distribute")), "header")
    D.add_part(built, "footer1.xml", D.footer_part(D.paragraph("Page 1 of 9")), "footer")
    result = walk_document(built.write(tmp_path / "doc.docx"))

    assert "Confidential" not in texts(result)
    assert "Page 1 of 9" not in texts(result)
    assert result.skipped["header_footer"].paragraphs == 2
    assert result.skipped["header_footer"].chars == len("Confidential — do not distribute") + len("Page 1 of 9")


def test_footnote_text_is_content_and_its_separators_are_not(tmp_path: Path) -> None:
    """Footnotes are in the fidelity scope (§10.12 F2); the separator furniture Word
    writes alongside them is not, and is accounted rather than dropped."""
    result = stream(
        tmp_path,
        D.paragraph(runs=D.run("Braking force.") + '<w:r><w:footnoteReference w:id="2"/></w:r>'),
        parts={"footnotes.xml": D.footnotes_part({2: "Measured at the wheel."})},
    )

    assert "Measured at the wheel." in texts(result)
    assert [i.part for i in result.items] == ["document", "footnotes"]
    assert result.skipped["header_footer"].paragraphs == 2   # separator, continuation


# =========================================================================== W6

def test_an_unrecognised_container_is_descended_into_and_reported(tmp_path: Path) -> None:
    """The rule that makes the walker safe against a construct nobody anticipated.

    Descending is what keeps the content; the issue is what stops "we handled it" from
    being a guess. Dropping it would be Failure 1 in its purest form: an element the
    author of this code had never seen, quietly discarded.
    """
    result = stream(
        tmp_path,
        D.unknown_container(D.paragraph("Requirement inside something unknown.")),
    )

    assert "Requirement inside something unknown." in texts(result)
    found = result.issues_with("unknown_container")
    assert len(found) == 1 and found[0].severity == "info"


def test_an_unknown_leaf_carrying_text_is_captured_rather_than_dropped(tmp_path: Path) -> None:
    """W6 names paragraphs and tables, but the invariant is about content, not element
    names. Loose text under an unknown element is still text that was in the file."""
    result = stream(
        tmp_path,
        '<x:odd xmlns:x="urn:test"><w:r><w:t>Loose text with no paragraph.</w:t></w:r></x:odd>',
    )

    assert "Loose text with no paragraph." in texts(result)
    assert result.issues_with("unknown_container") != ()


def test_an_unknown_element_with_nothing_in_it_is_not_reported(tmp_path: Path) -> None:
    """Otherwise every `w:proofErr` and `w:sectPr` in the document files an issue, and
    the list stops being something anyone reads."""
    result = stream(tmp_path, D.paragraph("Text.") + "<w:sectPr><w:type w:val='nextPage'/></w:sectPr>")

    assert result.issues_with("unknown_container") == ()


# =========================================================================== wrappers

def test_a_content_control_is_transparent(tmp_path: Path) -> None:
    """T-ING-12. `w:sdt` is packaging: the paragraph inside it is an ordinary paragraph,
    and a reader that only looks at direct children of `w:body` loses it whole."""
    result = stream(
        tmp_path, D.content_control(D.paragraph("Requirement inside a content control."))
    )

    assert [i.text for i in result.items] == ["Requirement inside a content control."]
    assert result.issues_with("unknown_container") == ()


def test_nested_wrappers_are_all_transparent(tmp_path: Path) -> None:
    """Word nests these freely — a content control inside a smart tag inside a tracked
    insertion is not exotic. Handling one level is handling none."""
    result = stream(
        tmp_path,
        D.content_control(
            D.smart_tag(
                '<w:ins w:id="7" w:author="R" w:date="2026-01-01T00:00:00Z">'
                + D.paragraph("Deeply wrapped requirement.")
                + "</w:ins>"
            )
        ),
    )

    assert [i.text for i in result.items] == ["Deeply wrapped requirement."]
    assert result.revisions.ins_accepted == 1


def test_alternate_content_yields_one_branch_not_both(tmp_path: Path) -> None:
    """A text box is written twice — DrawingML in `mc:Choice`, VML in `mc:Fallback`.

    Taking both would double the text, and §10.12 F4 says text emitted twice counts
    once. Coverage that counts the same sentence twice measures the writer, not the
    document.
    """
    result = stream(tmp_path, D.text_box("Requirement inside a text box."))
    recovered = [t for t in result.texts() if "text box" in t]

    assert recovered == ["Requirement inside a text box."]


# =========================================================================== objects

def test_text_box_content_is_recovered_as_an_embedded_object(tmp_path: Path) -> None:
    """Automotive specs put requirements in text boxes. Ordinary converters lose them
    entirely — `tests/test_pandoc_oracle.py` records pandoc doing exactly that."""
    result = stream(tmp_path, D.text_box("Requirement inside a text box."))
    boxes = [e for e in result.embedded() if e.kind == "textbox"]

    assert len(boxes) == 1
    assert boxes[0].text == "Requirement inside a text box."


def test_a_text_box_does_not_also_appear_as_page_paragraphs(tmp_path: Path) -> None:
    """Its insides belong to the object, so F10 can keep it whole and F11 can count it
    once. Emitting them as page content would look like better coverage and be worse."""
    result = stream(tmp_path, D.text_box("Requirement inside a text box."))

    assert [i.text for i in result.items] == [""]
    assert result.items[0].embedded[0].kind == "textbox"


def test_an_equation_is_kept_as_a_formula_object(tmp_path: Path) -> None:
    result = stream(tmp_path, D.equation("a+b"))
    formulas = [e for e in result.embedded() if e.kind == "formula"]

    assert len(formulas) == 1
    assert formulas[0].text == "a+b"


def test_an_embedded_image_is_seen_even_though_it_has_no_text(tmp_path: Path) -> None:
    """§10.7 needs the object; there is nothing to read out of it. Silence here is
    correct — but the object still has to arrive, or the figure is lost."""
    result = stream(tmp_path, D.image_paragraph())
    images = [e for e in result.embedded() if e.kind == "image"]

    assert len(images) == 1 and images[0].text == ""


def test_an_ole_object_arrives_as_an_object(tmp_path: Path) -> None:
    result = stream(tmp_path, D.ole_object("Embedded spreadsheet"))

    assert [e.kind for e in result.embedded()] == ["object"]


# =========================================================================== tables

def test_a_table_is_one_item_carrying_its_cell_text(tmp_path: Path) -> None:
    """How it is *represented* is F09's decision. What F05 owes is that no cell text is
    missing before that decision is made."""
    result = stream(
        tmp_path,
        D.table(
            [D.row(D.cell("Signal"), D.cell("Threshold")),
             D.row(D.cell("Brake pedal"), D.cell("50 ms"))],
            columns=2,
        ),
    )

    assert len(result.items) == 1 and result.items[0].is_table
    assert result.items[0].cell_texts == ("Signal", "Threshold", "Brake pedal", "50 ms")


def test_a_merged_cell_table_loses_no_text_either(tmp_path: Path) -> None:
    """The merged-cell case is most of the tables in an automotive spec, and it is the
    one a pipe-table-only reader flattens."""
    result = stream(
        tmp_path,
        D.table(
            [D.row(D.cell("Spans two", grid_span=2)),
             D.row(D.cell("Left"), D.cell("Right"))],
            columns=2,
        ),
    )

    assert result.items[0].cell_texts == ("Spans two", "Left", "Right")


def test_cell_paragraphs_are_not_emitted_separately_from_their_table(tmp_path: Path) -> None:
    result = stream(
        tmp_path, D.table([D.row(D.cell("A"), D.cell("B"))], columns=2)
    )

    assert [i.kind for i in result.items] == ["table"]


def test_a_content_control_inside_a_cell_still_yields_its_text(tmp_path: Path) -> None:
    result = stream(
        tmp_path,
        D.table(
            [D.row(D.cell("", content=D.content_control(D.paragraph("Wrapped cell."))))],
            columns=1,
        ),
    )

    assert "Wrapped cell." in texts(result)


# =========================================================================== addressing

def test_paragraph_indices_are_document_order_and_start_at_zero(tmp_path: Path) -> None:
    """Every issue is filed against one of these, so they have to mean a real place in
    the source — an unactionable finding is what §10.12 F5 exists to prevent."""
    result = stream(
        tmp_path,
        D.paragraph("One.") + D.paragraph("Two.") + D.paragraph("Three."),
    )

    assert [i.paragraph for i in result.items] == [0, 1, 2]


def test_a_skipped_paragraph_still_consumes_its_index(tmp_path: Path) -> None:
    """The index addresses the *source*. Renumbering around what was dropped would make
    every issue point one paragraph earlier than the thing it is about."""
    result = stream(
        tmp_path,
        D.paragraph("Kept.")
        + D.paragraph("2 Requirements 7", style="TOC1")
        + D.paragraph("Also kept."),
    )

    assert [i.paragraph for i in result.items] == [0, 2]


def test_a_table_takes_the_index_of_its_first_cell_paragraph(tmp_path: Path) -> None:
    result = stream(
        tmp_path,
        D.paragraph("Before.")
        + D.table([D.row(D.cell("A"), D.cell("B"))], columns=2)
        + D.paragraph("After."),
    )

    assert [(i.kind, i.paragraph) for i in result.items] == [
        ("paragraph", 0), ("table", 1), ("paragraph", 3),
    ]


def test_issues_are_sorted_by_paragraph(tmp_path: Path) -> None:
    """§8.4. Two issues on one paragraph must not depend on the order they happened to
    be appended in, or the report is not byte-stable (§9.5)."""
    result = stream(
        tmp_path,
        D.paragraph("A.")
        + D.unknown_container(D.paragraph("B."))
        + D.unknown_container(D.paragraph("C.")),
    )
    positions = [i.paragraph for i in result.issues]

    assert positions == sorted(positions)


def test_every_issue_code_the_walker_raises_is_in_appendix_b(tmp_path: Path) -> None:
    """A code outside the registry is a finding no report knows how to render."""
    result = stream(
        tmp_path,
        D.unknown_container(D.paragraph("B.")) + D.tracked_deletion("Gone."),
    )

    assert {i.code for i in result.issues} <= set(ISSUE_CODES)


# =========================================================================== invariants

def test_two_walks_of_the_same_file_agree_exactly(tmp_path: Path) -> None:
    """§9.5. Nothing here may depend on dict ordering, zip ordering or object identity —
    and the paragraph index is built from `id()`, which is exactly the kind of thing
    that works until a garbage collection happens at the wrong moment."""
    path = build(
        tmp_path,
        D.heading(1, "Braking")
        + D.paragraph("Apply within 50 ms.")
        + D.table([D.row(D.cell("A"), D.cell("B"))], columns=2)
        + D.text_box("In a box.")
        + D.toc_field(["1 Braking 3"]),
    )
    first, second = walk_document(path), walk_document(path)

    assert first.texts() == second.texts()
    assert [(i.kind, i.paragraph) for i in first.items] == \
           [(i.kind, i.paragraph) for i in second.items]
    assert [i.to_mapping() for i in first.issues] == [i.to_mapping() for i in second.issues]
    assert first.skipped == second.skipped


def test_the_walk_writes_nothing_to_the_source(tmp_path: Path) -> None:
    """Non-negotiable principle 3: the .docx is the final point of comparison."""
    path = build(tmp_path, D.paragraph("Requirement."))
    before = path.read_bytes()

    walk_document(path)

    assert path.read_bytes() == before


def test_an_empty_document_is_an_empty_stream_not_a_crash(tmp_path: Path) -> None:
    result = stream(tmp_path, "")

    assert result.items == ()
    assert result.issues == ()
    assert result.revisions.total == 0


def test_walk_text_is_the_flattened_view_the_oracle_compares(tmp_path: Path) -> None:
    path = build(tmp_path, D.paragraph("One.") + D.text_box("Two."))

    assert walk_text(path) == ("One.", "Two.")


def test_walk_package_and_walk_document_agree(tmp_path: Path) -> None:
    path = build(tmp_path, D.paragraph("One."))
    from specctl.ingest.walk import walk_package

    assert walk_package(Package.open(path)).texts() == walk_document(path).texts()


# =========================================================================== fixtures

def test_the_degraded_table_fixture_keeps_its_cell_text_and_what_follows(tmp_path: Path) -> None:
    """T-ING-10's input, at the walker stage. The degrade itself is F10; what F05 owes
    is that the cells arrive at all, and that the table does not swallow the paragraph
    after it."""
    from .support.fixtures import ensure_built

    result = walk_document(ensure_built(tmp_path))
    body = texts(result)

    for cell_text in ("A", "B", "C", "D"):
        assert cell_text in body
    assert "Text after the table, which must survive." in body


@pytest.mark.parametrize("fixture", ["constructs.docx", "revisions.docx", "containers.docx"])
def test_the_hand_authored_fixtures_walk_without_losing_their_constructs(fixture: str) -> None:
    """F05 is done when it runs on all seven hard cases of F04 — and these are the files
    Word wrote, which is the only OOXML that proves anything about the customer's."""
    result = walk_document(require(fixture))

    assert result.items, "a fixture with content produced an empty stream"
    assert {i.code for i in result.issues} <= set(ISSUE_CODES)


def test_the_revisions_fixture_emits_the_insertion_and_drops_the_deletion() -> None:
    """T-ING-11 on the file Word actually wrote, which is the only version that counts:
    a fixture built in code proves the walker handles the OOXML we imagined."""
    path = require("revisions.docx")
    result = walk_document(path)

    deleted = {
        (t.text or "").strip()
        for t in D.xpath(path, "//w:delText")
        if (t.text or "").strip()
    }
    assert deleted, "the fixture carries no w:delText — see tests/fixtures/README.md"

    body = texts(result)
    for gone in deleted:
        assert gone not in body, f"deleted text surfaced as a live requirement: {gone!r}"

    assert result.revisions.ins_accepted > 0
    assert result.revisions.del_discarded > 0
    assert result.issues_with("source_has_unresolved_revisions") != ()


def test_the_containers_fixture_keeps_the_sdt_and_skips_the_toc() -> None:
    """T-ING-12 on Word's own output: content controls seen through, TOC accounted."""
    path = require("containers.docx")
    result = walk_document(path)

    inside_sdt = {
        (t.text or "").strip()
        for t in D.xpath(path, "//w:sdt//w:sdtContent//w:p//w:t")
        if (t.text or "").strip()
    }
    assert inside_sdt, "the fixture's content control is empty — Word dropped it on save"

    body = texts(result)
    for kept in inside_sdt:
        assert kept in body, f"text inside a content control was lost: {kept!r}"

    assert result.skipped["toc"].paragraphs > 0
    assert result.skipped["header_footer"].paragraphs > 0


def test_the_constructs_fixture_yields_every_construct_it_promises() -> None:
    """T-ING-01 at the walker stage: the table, the text box, the equation and the image
    all arrive. What they are turned into is F09, F10 and F08."""
    result = walk_document(require("constructs.docx"))
    kinds = {e.kind for e in result.embedded()}

    assert result.of_kind("table"), "no table reached the stream"
    assert "textbox" in kinds, "text box content was lost — see §10.7"
    assert "formula" in kinds, "the equation was lost — see §10.8"
    assert "image" in kinds, "the embedded image was lost — see §10.7"


def test_no_socket_is_opened_while_reading_a_document(tmp_path: Path) -> None:
    """T-ING-15, §9.5, and non-negotiable principle 1 — stated once by name.

    The suite-wide guard in `conftest.py` already covers every test in this file, so this
    asserts nothing the others do not. It exists so the claim "there is no AI in the
    conversion path" has a test with that name attached to it, rather than being a
    property that happens to hold.
    """
    from .support.netguard import blocked_network

    path = build(tmp_path, D.heading(1, "Braking") + D.paragraph("Within 50 ms."))
    with blocked_network():
        result = walk_document(path)

    assert texts(result)


def test_an_object_standing_where_a_paragraph_would_is_not_dropped(tmp_path: Path) -> None:
    """An image carries no text, so anything that decides by text loses the figure.

    "Nothing to read inside it" and "nothing there" are different facts, and collapsing
    them is Failure 1 — F10 needs the object to extract it, and a figure that never
    reaches the stream cannot be degraded, reported or counted.
    """
    drawing = (
        '<w:drawing><wp:inline><a:graphic><a:graphicData>'
        '<a:blip r:embed="rId9"/>'
        "</a:graphicData></a:graphic></wp:inline></w:drawing>"
    )
    result = stream(tmp_path, D.paragraph("Before.") + drawing)

    assert [e.kind for e in result.embedded()] == ["image"]
