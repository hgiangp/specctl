"""Verify the fixtures themselves, before anything is verified *with* them.

A fixture that opens in Word but does not contain the construct under test is worse than
a missing one: every test using it passes, and the walker looks correct on a path it never
exercised. So the constructs are checked against the raw OOXML, and a failure names the
construct and how to add it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .support import docx
from .support.fixtures import (
    BUILT,
    HARD_CASES,
    HAND_AUTHORED,
    REGISTRY,
    STAND_INS,
    ensure_built,
    is_substituted,
    require,
    resolve,
    stale_parts,
)


# ------------------------------------------------------------------ presence

def test_fixture_directory_exists() -> None:
    from .support.fixtures import FIXTURE_DIR

    assert FIXTURE_DIR.is_dir(), "tests/fixtures/ is missing"
    assert (FIXTURE_DIR / "README.md").is_file(), "§18.3 requires a provenance README"


def test_hand_authored_fixtures_are_either_all_present_or_all_absent() -> None:
    """Partial delivery is a mistake; nothing delivered yet is a known state.

    Half a fixture set is the dangerous case: the suite goes green on whatever happens to
    be there and silently stops covering the rest. A built stand-in is not a delivery —
    it keeps F05 testable, and this test keeps saying the Word files are still owed.
    """
    present = [f.name for f in HAND_AUTHORED if f.exists()]
    absent = [f.name for f in HAND_AUTHORED if not f.exists()]
    if present and absent:
        pytest.fail(
            "tests/fixtures/ is partially populated.\n"
            f"  present: {', '.join(present)}\n"
            f"  missing: {', '.join(absent)}\n"
            "See tests/fixtures/README.md for what each one must contain."
        )
    if not present:
        pytest.skip(
            "no hand-authored fixtures committed yet (F04); the built stand-ins are "
            "carrying the cases meanwhile. Still expected in tests/fixtures/: "
            + ", ".join(f.name for f in HAND_AUTHORED)
        )


def test_every_built_fixture_is_committed() -> None:
    """The built files are the reason F05 is testable at all; they are not optional."""
    missing = [f.name for f in BUILT if not f.exists()]
    assert not missing, (
        f"{', '.join(missing)} missing from tests/fixtures/. "
        "Run `python scripts/build_fixtures.py`."
    )


@pytest.mark.parametrize("case", HARD_CASES)
def test_every_hard_case_is_carried_by_a_fixture_that_exists(case: str) -> None:
    """F04's exit criterion, as a test rather than as a claim.

    Naming the seven hard cases in a document is not coverage; a case is covered when some
    file on disk actually contains the construct. Checking it here means the criterion
    cannot quietly stop being true when a fixture is renamed, replaced or removed.
    """
    carriers = [
        fixture.name
        for fixture in REGISTRY
        if fixture.exists()
        and any(r.case == case and r.satisfied_by(fixture.path) for r in fixture.requirements)
    ]
    assert carriers, (
        f"no fixture present in tests/fixtures/ carries the {case!r} case. "
        "See tests/fixtures/README.md."
    )


@pytest.mark.parametrize("name", sorted(STAND_INS), ids=lambda n: n)
def test_a_stand_in_is_held_to_the_same_requirements_as_the_file_it_replaces(name: str) -> None:
    """One requirement list, two files.

    If a stand-in were allowed its own shorter list it would drift into covering less than
    the Word file must, and the gap would show up as a walker bug months later.
    """
    assert BUILT and HAND_AUTHORED  # both halves of the registry are populated
    from .support.fixtures import BY_NAME

    assert STAND_INS[name].requirements is BY_NAME[name].requirements


@pytest.mark.parametrize("name", sorted(STAND_INS), ids=lambda n: n)
def test_the_hand_authored_file_wins_as_soon_as_it_lands(name: str) -> None:
    """Delivering the Word files must not need a line of test code changed."""
    from .support.fixtures import BY_NAME

    resolved = resolve(name)
    assert resolved is not None, f"neither {name} nor its stand-in is present"
    if BY_NAME[name].exists():
        assert resolved.name == name and not is_substituted(name)
    else:
        assert resolved.name == STAND_INS[name].name and is_substituted(name)
    assert require(name) == resolved.path


@pytest.mark.parametrize("fixture", BUILT, ids=lambda f: f.name)
def test_a_committed_built_fixture_still_matches_its_builder(fixture, tmp_path: Path) -> None:
    """What makes a committed binary reviewable: you can regenerate it.

    A difference here means the file was edited by hand — the one change to a fixture that
    no diff shows and no other test can see.
    """
    stale = stale_parts(fixture, tmp_path)
    assert not stale, (
        f"tests/fixtures/{fixture.name} differs from what its builder produces, in: "
        f"{', '.join(stale)}. Run `python scripts/build_fixtures.py`."
    )


# ------------------------------------------------------------------ contents

@pytest.mark.parametrize("fixture", REGISTRY, ids=lambda f: f.name)
def test_each_present_fixture_contains_what_it_promises(fixture) -> None:
    if fixture.origin == "built" and not fixture.exists():
        pytest.skip(f"{fixture.name} is built on demand; see the dedicated test")
    if not fixture.exists():
        pytest.skip(
            f"{fixture.name} not committed yet — {fixture.purpose} "
            "See tests/fixtures/README.md."
        )
    assert docx.is_docx(fixture.path), (
        f"{fixture.name} is not a readable .docx package. If it was committed through a "
        "text filter its zip is corrupt; .gitattributes marks *.docx binary to prevent it."
    )
    missing = fixture.missing_requirements()
    if missing:
        detail = "\n".join(f"  - {r.label}: {r.hint}" for r in missing)
        pytest.fail(
            f"tests/fixtures/{fixture.name} is missing {len(missing)} required "
            f"construct(s), so {fixture.covers} would not actually be covered:\n{detail}"
        )


# ------------------------------------------------------------------ the built fixture

def test_the_malformed_table_fixture_is_built_and_complete(tmp_path: Path) -> None:
    """The degrade path is always testable, committed fixture or not."""
    from .support.fixtures import BY_NAME

    path = ensure_built(tmp_path)
    assert docx.is_docx(path)
    missing = [
        r.label for r in BY_NAME["degraded.docx"].requirements if not r.satisfied_by(path)
    ]
    assert not missing, f"the malformed-table fixture lacks {missing}"


@pytest.mark.parametrize("fixture", BUILT, ids=lambda f: f.name)
def test_every_built_fixture_can_be_rebuilt_from_scratch(fixture, tmp_path: Path) -> None:
    """A built fixture that cannot be rebuilt is just a binary nobody can review."""
    path = fixture.build(tmp_path / fixture.name)
    assert docx.is_docx(path)
    missing = [r.label for r in fixture.requirements if not r.satisfied_by(path)]
    assert not missing, f"{fixture.name} rebuilt without {missing}"


@pytest.mark.parametrize("fixture", BUILT, ids=lambda f: f.name)
def test_every_built_fixture_builds_byte_identically_twice(fixture, tmp_path: Path) -> None:
    """§9.5, applied to the builder: a rebuilt fixture must not be a spurious diff."""
    first = fixture.build(tmp_path / "a" / fixture.name).read_bytes()
    second = fixture.build(tmp_path / "b" / fixture.name).read_bytes()
    assert first == second


def test_neither_table_branch_can_serialize_the_malformed_table(tmp_path: Path) -> None:
    """Why this fixture cannot be authored in Word: it is invalid by construction.

    §10.6's pipe branch needs no merges; the HTML branch needs a consistent column count.
    Both are broken here, on purpose and independently.
    """
    path = ensure_built(tmp_path)
    w = docx.NS["w"]

    declared = docx.count(path, "//w:gridCol")
    spans = [int(e.get(f"{{{w}}}val")) for e in docx.xpath(path, "(//w:tr)[1]//w:gridSpan")]
    assert declared == 3
    assert sum(spans) != declared, "the column counts must disagree for the case to exist"

    assert docx.has(path, '//w:vMerge[@w:val="continue"]')
    assert not docx.has(path, '//w:vMerge[@w:val="restart"]'), (
        "a continuation with an origin row is a *valid* merge and would serialize fine"
    )


def test_text_after_the_table_is_present(tmp_path: Path) -> None:
    """The total-capture invariant (§6.4): degrading a table must not swallow what
    follows it."""
    path = ensure_built(tmp_path)
    after = docx.xpath(path, "//w:tbl/following-sibling::w:p//w:t")
    assert [t.text for t in after] == ["Text after the table, which must survive."]


def test_two_builds_are_byte_identical(tmp_path: Path) -> None:
    """§9.5 determinism, applied to the fixture builder: zip entries carry fixed
    timestamps, so a rebuilt fixture is not a spurious diff."""
    first = docx.malformed_table_document().write(tmp_path / "a.docx").read_bytes()
    second = docx.malformed_table_document().write(tmp_path / "b.docx").read_bytes()
    assert first == second


# ------------------------------------------------------------------ the builder

def test_the_builder_produces_a_package_word_would_recognise(tmp_path: Path) -> None:
    package = docx.DocxPackage(body=docx.heading(1, "Title") + docx.paragraph("Body."))
    path = package.write(tmp_path / "simple.docx")
    names = docx.part_names(path)
    assert "[Content_Types].xml" in names
    assert "_rels/.rels" in names
    assert "word/document.xml" in names
    assert [t.text for t in docx.xpath(path, "//w:t")] == ["Title", "Body."]


def test_the_builder_can_produce_every_construct_the_walker_must_handle(tmp_path: Path) -> None:
    """So a regression found on the real document can be reproduced minimally in code."""
    body = (
        docx.heading(1, "1 Scope")
        + docx.content_control(docx.paragraph("Inside a content control."))
        + docx.tracked_insertion("Inserted text.")
        + docx.tracked_deletion("Deleted text.")
        + docx.toc_field(["1 Scope", "2 Requirements"])
        + docx.text_box("Inside a text box.")
        + docx.equation("x")
        + docx.paragraph(runs=docx.bookmark("_Ref1") + docx.run("Target."))
        + docx.paragraph(runs=docx.ref_field("_Ref1", "see 1 Scope"))
        + docx.table([docx.row(docx.cell("a"), docx.cell("b"))], columns=2)
    )
    path = docx.DocxPackage(body=body).write(tmp_path / "all.docx")
    for label, expression in [
        ("content control", "//w:sdt//w:sdtContent//w:p"),
        ("tracked insertion", "//w:ins"),
        ("tracked deletion", "//w:del//w:delText"),
        ("toc field", "//w:instrText[contains(text(), 'TOC')]"),
        ("text box", "//w:txbxContent"),
        ("equation", "//m:oMath"),
        ("bookmark", "//w:bookmarkStart"),
        ("ref field", "//w:instrText[contains(text(), 'REF')]"),
        ("table", "//w:tbl"),
    ]:
        assert docx.has(path, expression), f"builder did not emit {label}"


def test_deleted_text_uses_delText_not_t(tmp_path: Path) -> None:
    """The distinction the whole revisions fixture rests on (§10.5 W1)."""
    path = docx.DocxPackage(
        body=docx.paragraph("Live.") + docx.tracked_deletion("Gone.")
    ).write(tmp_path / "rev.docx")
    assert [t.text for t in docx.xpath(path, "//w:t")] == ["Live."]
    assert [t.text for t in docx.xpath(path, "//w:delText")] == ["Gone."]
