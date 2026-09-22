#!/usr/bin/env python3
"""Regenerate the built `.docx` fixtures in `tests/fixtures/` from raw OOXML.

    python scripts/build_fixtures.py            # write them
    python scripts/build_fixtures.py --check    # verify the committed files match

The fixtures are committed as binaries, which normally means nobody can review them. These
can be reviewed by rebuilding: the builders in `tests/support/docx.py` are pure functions
of constants, so the package a build produces today is the package that was committed.
`--check` is what `test_fixtures.py` runs — a committed fixture that no longer matches its
builder has been edited by hand, and a hand-edited binary is exactly the thing a test
cannot see into.

Only the **built** fixtures are touched. `constructs.docx`, `revisions.docx` and
`containers.docx` are hand-authored in Word and this script never writes them; see
`tests/fixtures/README.md`.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.support.fixtures import BUILT, FIXTURE_DIR, stale_parts  # noqa: E402


def check() -> list[str]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for fixture in BUILT:
            if not fixture.exists():
                problems.append(f"{fixture.name}: not committed")
                continue
            stale = stale_parts(fixture, Path(tmp))
            if stale:
                problems.append(f"{fixture.name}: parts differ -> {', '.join(stale)}")
            else:
                print(f"ok       {fixture.name}")
    return problems


def write() -> None:
    for fixture in BUILT:
        fixture.build(FIXTURE_DIR / fixture.name)
        print(f"wrote    tests/fixtures/{fixture.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="do not write; exit non-zero if a committed fixture differs from its builder",
    )
    args = parser.parse_args(argv)

    if not args.check:
        write()
        return 0

    problems = check()
    if problems:
        print("\nstale fixtures:", file=sys.stderr)
        for line in problems:
            print(f"  - {line}", file=sys.stderr)
        print("\nRun `python scripts/build_fixtures.py` to regenerate them.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
