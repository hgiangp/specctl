"""Opening a .docx (§10.2 step 1).

Small surface, but it decides what "readable" means, and it is the one place a bad
input can still be turned into a clear message instead of a traceback. §9.4 gives that
its own exit code — `3`, unrecoverable input — precisely so a corrupt source is never
confused with a failing gate.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from specctl.exits import ExitCode, SpecctlError
from specctl.ingest.package import DOCUMENT_PART, Package, Relationship, qn

from .support import docx as D


def _package(tmp_path: Path, **kwargs) -> Package:
    built = D.DocxPackage(body=D.paragraph("Hello."), **kwargs)
    return Package.open(built.write(tmp_path / "doc.docx"))


# --------------------------------------------------------------------------- opening

def test_a_built_package_opens_and_exposes_its_body(tmp_path: Path) -> None:
    package = _package(tmp_path)
    assert package.body.tag == qn("w:body")
    assert DOCUMENT_PART in package.names


def test_a_missing_file_is_an_input_error_not_a_traceback(tmp_path: Path) -> None:
    with pytest.raises(SpecctlError) as caught:
        Package.open(tmp_path / "nope.docx")
    assert caught.value.code is ExitCode.INPUT


def test_a_zip_without_a_document_part_is_refused(tmp_path: Path) -> None:
    """A .docx is a zip, but not every zip is a .docx."""
    path = tmp_path / "not-really.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("hello.txt", "not a document")

    with pytest.raises(SpecctlError) as caught:
        Package.open(path)
    assert caught.value.code is ExitCode.INPUT
    assert "word/document.xml" in str(caught.value)


def test_a_file_that_is_not_a_zip_at_all_is_refused(tmp_path: Path) -> None:
    """The shape a .docx takes when git normalized its line endings (§18.3)."""
    path = tmp_path / "corrupt.docx"
    path.write_bytes(b"PK\x03\x04 and then nothing that parses")

    with pytest.raises(SpecctlError) as caught:
        Package.open(path)
    assert caught.value.code is ExitCode.INPUT


def test_a_malformed_part_is_an_input_error(tmp_path: Path) -> None:
    built = D.DocxPackage(body=D.paragraph("Hello."))
    path = built.write(tmp_path / "doc.docx")
    # Rewrite the package with a truncated document part.
    with zipfile.ZipFile(path) as archive:
        members = {n: archive.read(n) for n in archive.namelist()}
    members[DOCUMENT_PART] = b"<w:document><w:body><w:p>"
    with zipfile.ZipFile(path, "w") as archive:
        for name, blob in members.items():
            archive.writestr(name, blob)

    package = Package.open(path)
    with pytest.raises(SpecctlError) as caught:
        _ = package.body
    assert caught.value.code is ExitCode.INPUT


# --------------------------------------------------------------------------- parts

def test_header_and_footer_parts_are_found_through_relationships(tmp_path: Path) -> None:
    built = D.DocxPackage(body=D.paragraph("Body."))
    D.add_part(built, "header1.xml", D.header_part(D.paragraph("Confidential")), "header")
    D.add_part(built, "footer1.xml", D.footer_part(D.paragraph("Page 1")), "footer")
    package = Package.open(built.write(tmp_path / "doc.docx"))

    assert package.header_names == ("word/header1.xml",)
    assert package.footer_names == ("word/footer1.xml",)


def test_parts_are_found_by_convention_when_a_package_has_no_rels(tmp_path: Path) -> None:
    """Word always writes a relationship part; a fixture built by hand often does not.

    Refusing those would make fixtures harder to write without making the reader any
    safer, so the conventional names are a fallback — never a substitute when the
    relationships are there to be read.
    """
    built = D.DocxPackage(
        body=D.paragraph("Body."),
        parts={"footnotes.xml": D.footnotes_part({2: "A footnote."})},
    )
    package = Package.open(built.write(tmp_path / "doc.docx"))

    assert package.relationships == {}
    assert package.footnotes is not None


def test_part_names_are_sorted_so_two_runs_agree(tmp_path: Path) -> None:
    """§9.5 — nothing may depend on the order a zip happens to list its entries in."""
    built = D.DocxPackage(body=D.paragraph("Body."))
    for n in (3, 1, 2):
        D.add_part(built, f"header{n}.xml", D.header_part(D.paragraph(f"H{n}")), "header")
    package = Package.open(built.write(tmp_path / "doc.docx"))

    assert package.header_names == (
        "word/header1.xml", "word/header2.xml", "word/header3.xml",
    )


def test_an_external_relationship_keeps_its_target_untouched() -> None:
    internal = Relationship("rId1", "t", "header1.xml")
    external = Relationship("rId2", "t", "https://example.invalid/x", external=True)

    assert internal.resolve(DOCUMENT_PART) == "word/header1.xml"
    assert external.resolve(DOCUMENT_PART) == "https://example.invalid/x"


def test_parts_are_read_once_so_a_second_pass_sees_the_same_bytes(tmp_path: Path) -> None:
    """The walker makes several passes. Re-reading a file that moved underneath it is
    one of the ways byte-identical output quietly stops being true (§9.5)."""
    built = D.DocxPackage(body=D.paragraph("Original."))
    path = built.write(tmp_path / "doc.docx")
    package = Package.open(path)

    D.DocxPackage(body=D.paragraph("Replaced.")).write(path)

    assert "Original." in package.read(DOCUMENT_PART).decode("utf-8")
