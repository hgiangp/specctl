#!/usr/bin/env python3
"""The F05 sign-off gate: run the OOXML reader against the hand-authored fixtures and
show what it recovered, next to what the file actually contains.

    python scripts/verify_f05.py                      # the three fixtures
    python scripts/verify_f05.py --redact             # counts and positions, no text
    python scripts/verify_f05.py --record             # write the SHA-256 manifest
    python scripts/verify_f05.py path/to/other.docx   # any document

**Why this exists when the tests are already green.** A passing suite says the reader did
what the tests asked. It cannot say the tests asked for everything that is in the file —
and F05's whole claim is a negative one: *nothing was lost*. Nobody can confirm a negative
from a row of dots. So this prints the evidence in the shape the claim is made in: every
construct the file contains, every counter, every issue, and every source segment the
reader did not recover, named.

It writes nothing unless `--record` is passed, and it opens no socket. Read it as the
report you sign, not as a second test suite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from specctl.ingest.walk import walk_document                      # noqa: E402
from specctl.textutil import normalize                             # noqa: E402
from tests.support import docx as D                                # noqa: E402
from tests.support import pandoc                                   # noqa: E402
from tests.support.fixtures import (                               # noqa: E402
    BY_NAME, HAND_AUTHORED, is_substituted, resolve,
)

MANIFEST = ROOT / "tests" / "fixtures" / "manifest.json"
MIN_LONG_SEGMENT = 12          # §10.12 F8
W = D.NS["w"]

GREEN, RED, YELLOW, DIM, BOLD, OFF = (
    "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
)


# --------------------------------------------------------------------------- source side

def _toc_paragraphs(root) -> set:
    """Paragraphs a TOC produced — out of the fidelity scope per §10.12 F2.

    Read from the XML rather than asked of the walker: a gate that takes the reader's word
    for what is in scope agrees with it by construction and proves nothing.
    """
    out: set = set()
    depth: list[bool] = []
    for p in root.iter(f"{{{W}}}p"):
        was_open, opened = any(depth), False
        for node in p.iter():
            if node.tag == f"{{{W}}}fldChar":
                kind = node.get(f"{{{W}}}fldCharType")
                if kind == "begin":
                    depth.append(False)
                elif kind == "end" and depth:
                    depth.pop()
            elif node.tag == f"{{{W}}}instrText" and depth:
                if (node.text or "").strip().upper().startswith("TOC"):
                    depth[-1] = True
            elif node.tag == f"{{{W}}}fldSimple":
                if (node.get(f"{{{W}}}instr") or "").strip().upper().startswith("TOC"):
                    opened = True
            opened = opened or any(depth)
        style = p.find(f"{{{W}}}pPr/{{{W}}}pStyle")
        styled = style is not None and re.match(
            r"^TOC\s*\d+$", style.get(f"{{{W}}}val") or "", re.IGNORECASE
        )
        if was_open or opened or styled:
            out.add(p)
    return out


def _own_text(paragraph) -> str:
    """A paragraph's text without the text box hanging inside it (§10.12 F4, D v2.3 #15)."""
    parts = []
    for node in paragraph.iter(f"{{{W}}}t"):
        nested = False
        for ancestor in node.iterancestors():
            if ancestor is paragraph:
                break
            if ancestor.tag == f"{{{W}}}txbxContent":
                nested = True
                break
        if not nested:
            parts.append(node.text or "")
    return "".join(parts)


def source_segments(path: Path) -> list[tuple[int, str]]:
    """One `(paragraph index, normalized text)` per in-scope paragraph, from OOXML alone."""
    root = D.parse_part(path)
    skip = _toc_paragraphs(root)
    mc_fallback = f"{{{D.NS['mc']}}}Fallback"
    out: list[tuple[int, str]] = []
    for index, p in enumerate(root.iter(f"{{{W}}}p")):
        if p in skip:
            continue
        ancestors = list(p.iterancestors())
        if any(a.tag == f"{{{W}}}del" for a in ancestors):
            continue
        if any(a.tag == mc_fallback for a in ancestors):
            continue
        text = normalize(_own_text(p))
        if text:
            out.append((index, text))
    return out


def covered(segment: str, haystack: str) -> bool:
    """§10.12 F8 — a short segment must match at a token boundary, not by accident."""
    if len(segment) >= MIN_LONG_SEGMENT:
        return segment in haystack
    return re.search(
        r"(?<![0-9a-z])" + re.escape(segment) + r"(?![0-9a-z])", haystack
    ) is not None


# --------------------------------------------------------------------------- reporting

@dataclass
class Result:
    name: str
    failures: list[str]
    warnings: list[str]
    substituted: bool = False

    @property
    def ok(self) -> bool:
        return not self.failures


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def show(label: str, value: object, *, indent: int = 2) -> None:
    print(" " * indent + f"{label:<30}" + str(value))


def verify(path: Path, *, redact: bool, min_coverage: float,
           manifest: dict[str, str], stands_for: str | None = None) -> Result:
    failures: list[str] = []
    warnings: list[str] = []
    name = path.name

    def quote(text: str) -> str:
        return f"{len(text)} chars" if redact else repr(text[:100])

    label = name if stands_for is None else f"{name}  {DIM}(standing in for {stands_for}){OFF}"
    print(f"\n{BOLD}== {OFF}{BOLD}{label}{OFF}")
    if stands_for is not None:
        warnings.append(
            f"{stands_for} was read as {name}: a fixture built from raw OOXML proves the "
            "reader handles the OOXML we imagined, not the OOXML Word writes"
        )
    digest = sha256(path)
    show("sha256", digest[:16] + "…")
    show("size", f"{path.stat().st_size:,} bytes")

    recorded = manifest.get(name)
    if recorded and recorded != digest:
        failures.append(
            f"{name} differs from the recorded manifest — the sign-off was made against "
            f"other bytes (recorded {recorded[:16]}…, found {digest[:16]}…)"
        )
        show("manifest", f"{RED}MISMATCH{OFF}")
    elif recorded:
        show("manifest", f"{GREEN}matches{OFF}")
    else:
        show("manifest", f"{DIM}not recorded — run with --record{OFF}")

    # -- what the file promises to contain (§18.3) --------------------------
    fixture = BY_NAME.get(name)
    if fixture is not None:
        missing = fixture.missing_requirements()
        show("required constructs",
             f"{len(fixture.requirements) - len(missing)}/{len(fixture.requirements)} present")
        for req in missing:
            failures.append(f"{name} is missing '{req.label}' — {req.hint}")

    # -- what the reader recovered ------------------------------------------
    stream = walk_document(path)
    kinds: dict[str, int] = {}
    for item in stream.items:
        kinds[item.kind] = kinds.get(item.kind, 0) + 1
    embedded: dict[str, int] = {}
    for obj in stream.embedded():
        embedded[obj.kind] = embedded.get(obj.kind, 0) + 1

    show("blocks", ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())) or "none")
    show("embedded objects",
         ", ".join(f"{k}={v}" for k, v in sorted(embedded.items())) or "none")
    show("revisions (W1)",
         f"kept {stream.revisions.ins_accepted}, "
         f"discarded {stream.revisions.del_discarded}, "
         f"comments {stream.revisions.comments_discarded}")
    for code, skip in sorted(stream.skipped.items()):
        show(f"skipped.{code} (W4/W5)", f"{skip.paragraphs} paragraphs, {skip.chars} chars")

    # -- deleted text must not have survived (W1) ---------------------------
    deleted = {
        normalize(t.text or "")
        for t in D.xpath(path, "//w:delText")
        if normalize(t.text or "")
    }
    recovered = normalize("\n".join(stream.texts()))
    resurrected = [d for d in deleted if covered(d, recovered)]
    if deleted:
        show("tracked deletions", f"{len(deleted)} in file, {len(resurrected)} resurrected")
    for text in resurrected:
        failures.append(
            f"{name}: deleted text surfaced as a live requirement — {quote(text)}"
        )

    # -- directional coverage (§10.12) --------------------------------------
    segments = source_segments(path)
    uncovered = [(i, s) for i, s in segments if not covered(s, recovered)]
    ratio = (len(segments) - len(uncovered)) / len(segments) if segments else 1.0
    colour = GREEN if ratio >= min_coverage else RED
    show("source segments", len(segments))
    show("coverage", f"{colour}{ratio:.4f}{OFF}  (gate {min_coverage:.2f})")
    if ratio < min_coverage:
        failures.append(f"{name}: coverage {ratio:.4f} is below {min_coverage:.2f}")
    for index, text in uncovered:
        print(f"    {RED}uncovered{OFF} paragraph {index}: {quote(text)}")

    # -- issues raised -------------------------------------------------------
    if stream.issues:
        show("issues", len(stream.issues))
        for issue in stream.issues:
            mark = RED if issue.severity == "error" else (
                YELLOW if issue.severity == "warn" else DIM)
            print(f"    {mark}{issue.severity:<5}{OFF} {issue.code} "
                  f"@p{issue.paragraph} {DIM}{issue.detail[:80]}{OFF}")
        for issue in stream.issues:
            if issue.severity == "error":
                failures.append(f"{name}: error issue {issue.code} @p{issue.paragraph}")
    else:
        show("issues", "none")

    # -- the independent arbiter --------------------------------------------
    if pandoc.available():
        theirs = normalize(pandoc.convert(path).text)
        missed = [(i, s) for i, s in segments
                  if covered(s, theirs) and not covered(s, recovered)]
        show("pandoc oracle",
             f"{GREEN}clean{OFF}" if not missed
             else f"{RED}{len(missed)} segment(s) pandoc found, we did not{OFF}")
        for index, text in missed:
            failures.append(
                f"{name}: pandoc recovered paragraph {index} and we did not — {quote(text)}"
            )
    else:
        warnings.append("pandoc is not installed — the independent cross-check did not run")
        show("pandoc oracle", f"{YELLOW}skipped (not installed){OFF}")

    # -- determinism (§9.5) --------------------------------------------------
    again = walk_document(path)
    if again.texts() != stream.texts() or \
       [i.to_mapping() for i in again.issues] != [i.to_mapping() for i in stream.issues]:
        failures.append(f"{name}: two reads of the same file disagree — not deterministic")
        show("determinism", f"{RED}DIFFERS{OFF}")
    else:
        show("determinism", f"{GREEN}two reads agree{OFF}")

    return Result(name, failures, warnings, substituted=stands_for is not None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path,
                        help="documents to check; default is the three fixtures")
    parser.add_argument("--redact", action="store_true",
                        help="print lengths and positions instead of text")
    parser.add_argument("--record", action="store_true",
                        help="write tests/fixtures/manifest.json — the only path that writes")
    parser.add_argument("--min-coverage", type=float, default=1.0,
                        help="coverage gate (default 1.0; ACC-2 on the real document is 0.99)")
    args = parser.parse_args()

    manifest: dict[str, str] = {}
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text()).get("sha256", {})

    targets: list[tuple[Path, str | None]] = []
    if args.paths:
        targets = [(p, None) for p in args.paths]
    else:
        unresolved = []
        for fixture in HAND_AUTHORED:
            resolved = resolve(fixture.name)
            if resolved is None:
                unresolved.append(fixture.name)
                continue
            targets.append(
                (resolved.path, fixture.name if is_substituted(fixture.name) else None)
            )
        if unresolved:
            print(f"{RED}No fixture, and no stand-in, for: "
                  f"{', '.join(unresolved)}{OFF}")
            print("Rebuild the stand-ins with `python scripts/build_fixtures.py`, or put "
                  "the Word files in tests/fixtures/.")
            return 3

    results = [verify(p, redact=args.redact, min_coverage=args.min_coverage,
                      manifest=manifest, stands_for=stands_for)
               for p, stands_for in targets]

    print(f"\n{BOLD}== F05 gate{OFF}")
    for result in results:
        mark = f"{GREEN}PASS{OFF}" if result.ok else f"{RED}FAIL{OFF}"
        suffix = f"  {YELLOW}(stand-in — does not sign F05 off){OFF}" if result.substituted else ""
        print(f"  {mark}  {result.name}{suffix}")
    for result in results:
        for warning in result.warnings:
            print(f"  {YELLOW}warn{OFF}  {warning}")
        for failure in result.failures:
            print(f"  {RED}fail{OFF}  {failure}")

    ok = all(r.ok for r in results)
    substituted = [r.name for r in results if r.substituted]
    if substituted and not args.paths:
        print(f"\n  {YELLOW}F05 is NOT signed off.{OFF} {len(substituted)} of "
              f"{len(results)} case(s) were read from a built stand-in. A stand-in is "
              "well-formed\n  OOXML that lxml accepts; only Word writes the OOXML the "
              "customer's document is made of,\n  and the difference is exactly where a "
              "reader loses content without saying so.")

    if args.record:
        if not ok:
            print(f"\n{RED}Refusing to record a manifest for a failing run.{OFF}")
            return 2
        if substituted:
            print(f"\n{RED}Refusing to record a manifest for stand-ins.{OFF} "
                  "It exists to pin the hand-authored bytes.")
            return 2
        MANIFEST.write_text(json.dumps(
            {"comment": "SHA-256 of the hand-authored .docx fixtures, which are not "
                        "committed (F04). Recorded by scripts/verify_f05.py --record so "
                        "a later run can tell it is reading the bytes that were signed off.",
             "sha256": {p.name: sha256(p) for p, _ in targets}},
            indent=2, sort_keys=True) + "\n")
        print(f"\n{GREEN}Recorded{OFF} {MANIFEST.relative_to(ROOT)}")

    print()
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
