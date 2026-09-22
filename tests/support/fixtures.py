"""The fixture registry: which .docx files the suite needs, and what must be inside them.

§18.3 names the fixtures. This module says what each one must *contain*, as checks against
the raw OOXML, because **Word does not always save what you think**:

* accepting tracked changes before saving removes the `w:del` the fixture exists for;
* deleting a content control's contents makes Word drop the `w:sdt` wrapper;
* "Update field" on a TOC can leave the result without the field codes;
* pasting a picture as a link stores no image part at all.

Each of those produces a fixture that opens fine in Word and is useless as a test. Without
these checks the failure surfaces in F05 as "the walker loses text", and the walker gets
blamed for a construct that was never in the file.

**Two files per case, on purpose.** Each hand-authored fixture has a *built stand-in*
carrying the same constructs, produced from raw OOXML by `tests.support.docx`. The
stand-in is what keeps F05 unblocked while the Word files are outstanding; the Word file
is what proves the walker handles the OOXML Word actually emits, which is the OOXML the
customer's document is made of. They are checked against **one** requirement list, defined
once below, so the pair cannot drift apart: whatever the Word file must contain, the
stand-in must contain too, and `require()` switches to the Word file the moment it lands.

A stand-in is not a substitute for delivery. `test_fixtures.py` keeps reporting the
outstanding Word files for exactly that reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

import pytest

from . import docx

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"

#: The hard cases F04 exists to isolate. Each one must be carried by a fixture that is
#: actually present, not merely named — `test_fixtures.py` checks that.
HARD_CASES: tuple[str, ...] = (
    "tracked deletion",
    "content control",
    "merged-cell table",
    "text box",
    "table of contents",
    "equation",
    "cross-reference",
)


@dataclass(frozen=True)
class Requirement:
    """One construct a fixture must contain, and how to tell."""

    label: str
    hint: str
    xpath: str | None = None
    part: str = "word/document.xml"
    min_count: int = 1
    custom: Callable[[Path], bool] | None = None
    case: str | None = None  # which of HARD_CASES this construct proves, if any

    def satisfied_by(self, path: Path) -> bool:
        if self.custom is not None:
            return self.custom(path)
        assert self.xpath is not None
        try:
            return docx.count(path, self.xpath, part=self.part) >= self.min_count
        except KeyError:
            return False  # the part itself is absent


def _has_part(name: str) -> Callable[[Path], bool]:
    return lambda path: name in docx.part_names(path)


def _distinct_heading_levels(path: Path) -> bool:
    """Three distinct heading levels, by style name or by outline level (§10.3)."""
    styles = {
        e.get(f"{{{docx.NS['w']}}}val")
        for e in docx.xpath(path, "//w:pStyle[starts-with(@w:val, 'Heading')]")
    }
    outlines = {
        e.get(f"{{{docx.NS['w']}}}val") for e in docx.xpath(path, "//w:outlineLvl")
    }
    return len(styles) >= 3 or len(outlines) >= 3


def _two_list_kinds(path: Path) -> bool:
    """A numbered list and a bulleted list are two different `numId`s (§10.3)."""
    num_ids = {
        e.get(f"{{{docx.NS['w']}}}val") for e in docx.xpath(path, "//w:numPr/w:numId")
    }
    return len(num_ids) >= 2


def _simple_table(path: Path) -> bool:
    """At least one table with no merged cells — the pipe-table branch of §10.6."""
    return docx.count(path, "//w:tbl[not(.//w:gridSpan) and not(.//w:vMerge)]") >= 1


def _internal_cross_reference(path: Path) -> bool:
    """A bookmark plus something pointing at it: a REF field or an anchored hyperlink."""
    if not docx.has(path, "//w:bookmarkStart"):
        return False
    return (
        docx.has(path, "//w:instrText[contains(text(), 'REF')]")
        or docx.has(path, "//w:hyperlink[@w:anchor]")
    )


def _run_level_revisions(path: Path) -> bool:
    """Tracked changes wrapping **runs**, which is the shape Word writes (§10.5 W1).

    `w:ins` and `w:del` are run-level elements living inside `w:p`; a whole inserted or
    deleted paragraph is marked by a `w:ins`/`w:del` on the paragraph mark in
    `w:pPr/w:rPr`. A file that wraps a `w:p` inside a `w:ins` instead parses fine and is
    silently dropped by real readers — so a fixture in that shape would let a walker pass
    here and lose inserted requirements on the customer's document.
    """
    return docx.has(path, "//w:p/w:ins/w:r") and docx.has(path, "//w:p/w:del/w:r")


def _toc_field(path: Path) -> bool:
    """A TOC field, either as a complex field or as `w:fldSimple` (W4)."""
    return (
        docx.has(path, "//w:instrText[contains(text(), 'TOC')]")
        or docx.has(path, "//w:fldSimple[contains(@w:instr, 'TOC')]")
        or docx.has(path, "//w:pStyle[starts-with(@w:val, 'TOC')]")
    )


# --------------------------------------------------------------- requirement sets
#
# Defined once and shared by a hand-authored fixture and its built stand-in. One list,
# two files: the stand-in cannot quietly cover less than the Word file is required to.

CONSTRUCT_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement("three heading levels",
                "Apply Heading 1, Heading 2 and Heading 3 to three paragraphs.",
                custom=_distinct_heading_levels),
    Requirement("a numbered list and a bulleted list",
                "Two lists with different numbering — Word gives each its own numId.",
                custom=_two_list_kinds),
    Requirement("a table with no merged cells",
                "Insert a plain 3x2 table and do not merge anything in it.",
                custom=_simple_table),
    Requirement("a table with merged cells",
                "Insert a second table and merge two cells (gridSpan or vMerge).",
                xpath="//w:tbl[.//w:gridSpan or .//w:vMerge]",
                case="merged-cell table"),
    Requirement("an embedded image",
                "Insert > Picture, and embed it — do NOT 'link to file', "
                "which stores no image part.",
                xpath="//a:blip | //v:imagedata"),
    Requirement("an image part in the package",
                "Follows from an embedded image. If this is missing the picture was "
                "linked, not embedded, and there is no image to carry over.",
                custom=lambda path: any(
                    n.startswith("word/media/") for n in docx.part_names(path)
                )),
    Requirement("a text box",
                "Insert > Text Box with some text in it. The text must be "
                "searchable, so §6.4 emits it twice and §10.12 F4 counts it once.",
                xpath="//w:txbxContent",
                case="text box"),
    Requirement("an equation",
                "Insert > Equation (an OMML one, not a picture of one).",
                xpath="//m:oMath",
                case="equation"),
    Requirement("an internal cross-reference",
                "Insert > Cross-reference to a heading or bookmark in the same "
                "document. This is the edge §10.4 reads and converters drop.",
                custom=_internal_cross_reference,
                case="cross-reference"),
    Requirement("a footnote",
                "References > Insert Footnote.",
                xpath="//w:footnoteReference"),
    Requirement("a footnotes part",
                "Follows from the footnote; if this is missing the footnote text "
                "itself was not saved.",
                custom=_has_part("word/footnotes.xml")),
)

REVISION_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement("a tracked insertion",
                "Turn on Track Changes and type a sentence. It is CURRENT content "
                "and must be emitted.",
                xpath="//w:ins"),
    Requirement("a tracked deletion",
                "With Track Changes on, delete a sentence. Do NOT accept the "
                "changes before saving, or the w:del disappears and the fixture "
                "stops testing anything.",
                xpath="//w:del",
                case="tracked deletion"),
    Requirement("deleted text inside the deletion",
                "w:delText is a different element from w:t — a walker that "
                "collects w:t descendants emits deleted text as a live "
                "requirement. This is what makes that detectable.",
                xpath="//w:delText",
                case="tracked deletion"),
    Requirement("tracked changes that wrap runs, not paragraphs",
                "Word writes w:ins and w:del inside w:p around runs, and marks a whole "
                "inserted or deleted paragraph in w:pPr/w:rPr. A w:p wrapped in a w:ins "
                "parses but is dropped by real readers, so the fixture would prove "
                "nothing about the shape the customer's file is in.",
                custom=_run_level_revisions),
    Requirement("a comment",
                "Review > New Comment on some text. The text stays, the comment "
                "is discarded and counted (W3).",
                xpath="//w:commentReference | //w:commentRangeStart"),
    Requirement("a comments part",
                "Follows from the comment.",
                custom=_has_part("word/comments.xml")),
)

CONTAINER_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement("a content control",
                "Developer > Rich Text Content Control around a paragraph. Keep "
                "text inside it: Word drops an empty one on save.",
                xpath="//w:sdt",
                case="content control"),
    Requirement("a paragraph inside the content control",
                "The point of the fixture: the walker must descend into w:sdt "
                "and emit what is inside.",
                xpath="//w:sdt//w:sdtContent//w:p",
                case="content control"),
    Requirement("a table of contents field",
                "References > Table of Contents. Keep the field codes — a TOC "
                "pasted as plain text is not a TOC field.",
                custom=_toc_field,
                case="table of contents"),
    Requirement("a header part",
                "Insert > Header, with some text.",
                custom=_has_part("word/header1.xml")),
    Requirement("a footer part",
                "Insert > Footer, with some text.",
                custom=_has_part("word/footer1.xml")),
)

DEGRADED_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement("a table", "Built by tests.support.docx.malformed_table_document.",
                xpath="//w:tbl"),
    Requirement("an inconsistent column count",
                "gridSpan totals disagree with the declared grid, so no "
                "rowspan/colspan assignment exists.",
                xpath="//w:gridSpan"),
    Requirement("a vMerge continuation with no origin",
                "A vertical merge with no restart row above it.",
                xpath='//w:vMerge[@w:val="continue"]'),
    Requirement("text after the table",
                "Proves the degrade does not swallow what follows it.",
                xpath="//w:tbl/following-sibling::w:p//w:t"),
)


@dataclass(frozen=True)
class Fixture:
    """One file in `tests/fixtures/`."""

    name: str
    origin: str  # "word" | "built"
    purpose: str
    covers: str
    requirements: Sequence[Requirement] = field(default_factory=tuple)
    builder: Callable[[], docx.DocxPackage] | None = None
    stands_in_for: str | None = None  # the hand-authored fixture this one substitutes for

    @property
    def path(self) -> Path:
        return FIXTURE_DIR / self.name

    def exists(self) -> bool:
        return self.path.is_file()

    def missing_requirements(self) -> list[Requirement]:
        return [r for r in self.requirements if not r.satisfied_by(self.path)]

    def build(self, destination: Path) -> Path:
        if self.builder is None:
            raise ValueError(f"{self.name} is hand-authored in Word; it cannot be built")
        return self.builder().write(destination)


REGISTRY: tuple[Fixture, ...] = (
    Fixture(
        name="constructs.docx",
        origin="word",
        purpose="Every construct §6.4 has a representation for, in one document.",
        covers="T-ING-01, T-ING-02, §6.3, §6.4",
        requirements=CONSTRUCT_REQUIREMENTS,
    ),
    Fixture(
        name="revisions.docx",
        origin="word",
        purpose="Tracked changes, the most dangerous silent-data-loss path (§10.5 W1).",
        covers="T-ING-11, §10.5 W1-W2",
        requirements=REVISION_REQUIREMENTS,
    ),
    Fixture(
        name="containers.docx",
        origin="word",
        purpose="Wrappers the walker must see through, and content it must skip (§10.5).",
        covers="T-ING-12, §10.5 W4-W6, §8.3",
        requirements=CONTAINER_REQUIREMENTS,
    ),
    Fixture(
        name="built_constructs.docx",
        origin="built",
        purpose="Built stand-in for constructs.docx, so F05 is testable before Word lands.",
        covers="T-ING-01, T-ING-02, §6.3, §6.4",
        requirements=CONSTRUCT_REQUIREMENTS,
        builder=docx.construct_document,
        stands_in_for="constructs.docx",
    ),
    Fixture(
        name="built_revisions.docx",
        origin="built",
        purpose="Built stand-in for revisions.docx.",
        covers="T-ING-11, §10.5 W1-W2",
        requirements=REVISION_REQUIREMENTS,
        builder=docx.revisions_document,
        stands_in_for="revisions.docx",
    ),
    Fixture(
        name="built_containers.docx",
        origin="built",
        purpose="Built stand-in for containers.docx.",
        covers="T-ING-12, §10.5 W4-W6, §8.3",
        requirements=CONTAINER_REQUIREMENTS,
        builder=docx.containers_document,
        stands_in_for="containers.docx",
    ),
    Fixture(
        name="degraded.docx",
        origin="built",
        purpose="A table representable in neither form, to prove the degrade path works.",
        covers="T-ING-10, §6.4 invariant, §10.6",
        requirements=DEGRADED_REQUIREMENTS,
        builder=docx.malformed_table_document,
    ),
)

BY_NAME = {f.name: f for f in REGISTRY}
HAND_AUTHORED = tuple(f for f in REGISTRY if f.origin == "word")
BUILT = tuple(f for f in REGISTRY if f.origin == "built")
STAND_INS = {f.stands_in_for: f for f in REGISTRY if f.stands_in_for}


def resolve(name: str) -> Fixture | None:
    """The fixture a test should actually read for `name`, or None if there is none.

    The hand-authored file wins whenever it is present, so delivering the Word files
    switches every test over to them without a line of test code changing.
    """
    fixture = BY_NAME[name]
    if fixture.exists():
        return fixture
    stand_in = STAND_INS.get(name)
    if stand_in is not None and stand_in.exists():
        return stand_in
    return None


def is_substituted(name: str) -> bool:
    """True when `name` is being served by its built stand-in rather than the real thing."""
    resolved = resolve(name)
    return resolved is not None and resolved.name != name


def require(name: str) -> Path:
    """The path to a fixture, skipping the test with an actionable reason if absent."""
    resolved = resolve(name)
    if resolved is None:
        fixture = BY_NAME[name]
        stand_in = STAND_INS.get(name)
        detail = (
            f" Its stand-in {stand_in.name} is missing too — run "
            "`python scripts/build_fixtures.py` to rebuild it."
            if stand_in is not None
            else ""
        )
        pytest.skip(
            f"fixture {name} is not in tests/fixtures/ yet. "
            f"{fixture.purpose} See tests/fixtures/README.md for what it must contain."
            + detail
        )
    if not docx.is_docx(resolved.path):
        pytest.fail(
            f"tests/fixtures/{resolved.name} is not a readable .docx package. "
            "If it was committed through a text filter its zip is corrupt — "
            "check that .gitattributes marks *.docx as binary."
        )
    return resolved.path


def stale_parts(fixture: Fixture, workdir: Path) -> list[str]:
    """Parts where the committed fixture disagrees with a fresh build of it.

    A committed binary is normally unreviewable. These are reviewable by rebuilding: the
    builders are pure functions of constants, so what a build produces now is what was
    committed. A disagreement means the file was edited by hand — and a hand-edited binary
    is precisely what a test cannot see into.
    """
    if fixture.builder is None or not fixture.exists():
        return []
    fresh = docx.parts_of(fixture.build(workdir / fixture.name))
    committed = docx.parts_of(fixture.path)
    return sorted(
        name for name in set(fresh) | set(committed)
        if fresh.get(name) != committed.get(name)
    )


def ensure_built(tmp_path: Path, name: str = "degraded.docx") -> Path:
    """The path to a built fixture, writing it into `tmp_path` if it is not committed."""
    fixture = BY_NAME[name]
    if fixture.exists():
        return fixture.path
    return fixture.build(tmp_path / fixture.name)
