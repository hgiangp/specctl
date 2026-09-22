#!/usr/bin/env python3
"""Measure what a .docx contains, and how much of it a converter keeps.

This is the **W1 D1 spike** of §21.1 and the decision point of F11: does a Markdown vault
hold enough of this document to be trusted as the source of truth? Run it on the real file
before building anything on top of it.

    python scripts/spike_coverage.py source/SYS.docx
    python scripts/spike_coverage.py source/SYS.docx --pandoc
    python scripts/spike_coverage.py source/SYS.docx --pandoc --json report.json

It is a **spike tool, not the implementation.** F11 supersedes it with the real, tested
metric of §10.12 wired into `coverage.json` and the gates. What it gives you now is an
early number on the real document, and a concrete list of what a converter drops.

Reading the output
------------------
`coverage` answers one question: what fraction of the source text can be found in the
converted output? It is directional. Text a converter *adds* — rendered numbers, captions
— cannot raise it, because a net ratio scores 1.00 on output that lost 1% and added 1%.

Segments shorter than 12 characters are matched at a token boundary only. Without that,
a cell reading "B" matches the "b" in "the table below" and coverage rises with the size
of the document rather than with what was captured.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lxml import etree  # noqa: E402

from specctl.textutil import normalize  # noqa: E402
from tests.support import docx as D  # noqa: E402
from tests.support import pandoc  # noqa: E402

W = D.NS["w"]
MIN_LONG_SEGMENT = 12  # §10.12 F8


# --------------------------------------------------------------------------- source side

def _in_deletion(node) -> bool:
    """A paragraph inside `w:del` is not current content (§10.12 F3, §10.5 W1)."""
    for ancestor in node.iterancestors():
        if ancestor.tag == f"{{{W}}}del":
            return True
    return False


def _in_toc(node) -> bool:
    """TOC results are out of the fidelity scope and accounted separately (§8.3)."""
    style = node.find(f"{{{W}}}pPr/{{{W}}}pStyle")
    if style is not None:
        value = style.get(f"{{{W}}}val") or ""
        if value.startswith("TOC"):
            return True
    return False


def source_segments(root) -> list[str]:
    """One normalized string per paragraph in scope — body, footnotes, text boxes.

    Read straight from OOXML and therefore independent of any writer, which is what lets
    the same metric judge our reader and pandoc alike (§10.12 step 1).
    """
    segments: list[str] = []
    for paragraph in root.iter(f"{{{W}}}p"):
        if _in_deletion(paragraph) or _in_toc(paragraph):
            continue
        # w:t only: w:delText is deleted text and must never count as present.
        text = normalize("".join(t.text or "" for t in paragraph.iter(f"{{{W}}}t")))
        if text:
            segments.append(text)
    return segments


def covered(segment: str, haystack: str) -> bool:
    if len(segment) >= MIN_LONG_SEGMENT:
        return segment in haystack
    pattern = r"(?<![0-9a-z])" + re.escape(segment) + r"(?![0-9a-z])"
    return re.search(pattern, haystack) is not None


# --------------------------------------------------------------------------- inventory

CONSTRUCTS: tuple[tuple[str, str], ...] = (
    ("paragraphs",            "//w:body//w:p"),
    ("tables",                "//w:tbl"),
    ("  with merged cells",   "//w:tbl[.//w:gridSpan or .//w:vMerge]"),
    ("numbered paragraphs",   "//w:numPr"),
    ("headings (outline)",    "//w:outlineLvl"),
    ("headings (style)",      "//w:pStyle[starts-with(@w:val, 'Heading')]"),
    ("images",                "//a:blip | //v:imagedata"),
    ("text boxes",            "//w:txbxContent"),
    ("content controls",      "//w:sdt"),
    ("equations (OMML)",      "//m:oMath | //m:oMathPara"),
    ("tracked insertions",    "//w:ins"),
    ("tracked deletions",     "//w:del"),
    ("comments",              "//w:commentReference | //w:commentRangeStart"),
    ("footnote references",   "//w:footnoteReference"),
    ("bookmarks",             "//w:bookmarkStart"),
    ("internal hyperlinks",   "//w:hyperlink[@w:anchor]"),
    ("REF fields",            "//w:instrText[contains(text(), 'REF')]"),
    ("TOC fields",            "//w:instrText[contains(text(), 'TOC')]"),
    ("AlternateContent",      "//mc:AlternateContent"),
)


def inventory(path: Path) -> dict[str, int]:
    root = D.parse_part(path)
    counts: dict[str, int] = {}
    for label, expression in CONSTRUCTS:
        counts[label] = len(root.xpath(expression, namespaces=D.NS))
    return counts


# --------------------------------------------------------------------------- report

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("docx", type=Path)
    parser.add_argument("--pandoc", action="store_true",
                        help="also measure what pandoc keeps, as a cross-check")
    parser.add_argument("--json", type=Path, help="write the report as JSON")
    parser.add_argument("--show", type=int, default=20,
                        help="how many lost segments to print (default 20)")
    args = parser.parse_args()

    if not D.is_docx(args.docx):
        print(f"error: {args.docx} is not a readable .docx package", file=sys.stderr)
        return 3

    root = D.parse_part(args.docx)
    counts = inventory(args.docx)
    segments = source_segments(root)
    short = [s for s in segments if len(s) < MIN_LONG_SEGMENT]

    report: dict = {
        "source": str(args.docx),
        "parts": D.part_names(args.docx),
        "counts": counts,
        "segments": {"total": len(segments), "short": len(short)},
    }

    print(f"\n{args.docx}")
    print("=" * 72)
    print("\nWhat the document contains")
    print("-" * 72)
    for label, value in counts.items():
        marker = "" if value else "   (none)"
        print(f"  {label:24} {value:>6}{marker}")
    print(f"\n  {'text segments in scope':24} {len(segments):>6}")
    print(f"  {'  of those, short (<12)':24} {len(short):>6}")

    optional_parts = [p for p in report["parts"] if p.startswith("word/")]
    print(f"\n  package parts: {len(optional_parts)}")
    for part in optional_parts[:12]:
        print(f"    {part}")

    if args.pandoc:
        print("\nCross-check: what pandoc keeps")
        print("-" * 72)
        if not pandoc.available():
            print("  pandoc is not installed — skipping")
            report["pandoc"] = {"available": False}
        else:
            result = pandoc.convert(args.docx)
            haystack = normalize(result.text)
            lost = [s for s in segments if not covered(s, haystack)]
            ratio = (len(segments) - len(lost)) / len(segments) if segments else 1.0
            print(f"  version          {pandoc.version()}")
            print(f"  exit code        {result.returncode}")
            print(f"  coverage         {ratio:.4f}   ({len(segments) - len(lost)}"
                  f"/{len(segments)} segments)")
            print(f"  gate (ACC-2)     0.99 -> {'PASS' if ratio >= 0.99 else 'FAIL'}")
            if result.stderr:
                print(f"  stderr           {result.stderr[:200]}")
            if lost:
                print(f"\n  {len(lost)} segment(s) pandoc dropped, first {args.show}:")
                for segment in lost[: args.show]:
                    print(f"    - {segment[:100]!r}")
                if len(lost) > args.show:
                    print(f"    ... and {len(lost) - args.show} more")
            report["pandoc"] = {
                "available": True,
                "version": pandoc.version(),
                "returncode": result.returncode,
                "coverage": ratio,
                "lost": lost,
            }

    print("\nWhat this does and does not tell you")
    print("-" * 72)
    print("  It measures TEXT only. A converter can keep every character and still lose")
    print("  the structure that makes it addressable: table shape, list numbering, the")
    print("  cross-reference edges of §10.4. Those are counted above, not scored here.")
    print("  A converter that drops silently gives you a number and no recovery path;")
    print("  §6.4 requires knowing WHICH construct degraded, so it can be kept as raw.\n")

    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        print(f"  JSON written to {args.json}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
