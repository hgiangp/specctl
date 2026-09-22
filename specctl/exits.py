"""Exit codes and the one error type that carries them (§9.4)."""

from __future__ import annotations

import enum


class ExitCode(enum.IntEnum):
    """The complete set. §9.4 defines these five and no others."""

    OK = 0
    """Success, no findings above `info`."""

    WARNINGS = 1
    """Warnings only."""

    ERRORS = 2
    """Errors present, or a coverage gate breached."""

    INPUT = 3
    """Unrecoverable input error — the source could not be parsed."""

    USAGE = 4
    """Usage or configuration error."""


class SpecctlError(Exception):
    """An error that knows which exit code it means.

    Raised anywhere below the CLI; `specctl.cli` turns it into a stderr line and
    that exit code. Nothing else in the package calls `sys.exit`.
    """

    def __init__(self, message: str, code: ExitCode = ExitCode.USAGE) -> None:
        super().__init__(message)
        self.code = code
