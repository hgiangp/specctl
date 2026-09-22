"""Run pandoc, when it is available, as a **cross-check** — never in the conversion path.

Pandoc carries years of accumulated .docx edge-case handling, and that knowledge is worth
having. What it cannot do is tell you when it failed: it drops what it cannot represent,
silently, and exits 0. The total-capture invariant (§6.4) needs a converter that *knows*
it degraded, so it can emit a `raw locked fallback` block with the OOXML and an issue.

So pandoc is used here the one way that costs nothing: as a **test oracle**. Text pandoc
found that our reader did not is a bug in our reader, surfaced immediately instead of on
the real document. Nothing in `specctl/` imports this module, and the tests that use it
skip when pandoc is absent.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PandocResult:
    text: str
    stderr: str
    returncode: int


def available() -> bool:
    return shutil.which("pandoc") is not None


def version() -> str | None:
    if not available():
        return None
    out = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
    return out.stdout.splitlines()[0].strip() if out.stdout else None


def convert(path: Path, *, to: str = "plain", track_changes: str = "accept") -> PandocResult:
    """Convert a .docx. `track_changes=accept` matches §10.5 W1 — keep `w:ins`, drop `w:del`."""
    if not available():
        raise RuntimeError("pandoc is not installed")
    out = subprocess.run(
        ["pandoc", "-f", "docx", "-t", to, f"--track-changes={track_changes}", str(path)],
        capture_output=True, text=True,
    )
    return PandocResult(text=out.stdout, stderr=out.stderr.strip(), returncode=out.returncode)
