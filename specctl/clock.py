"""The clock, so that `--now` can fix it (§9.3).

Determinism (§9.5) requires that two runs with the same inputs and the same `--now`
produce byte-identical output. Nothing in specctl may call `datetime.now()` directly:
every timestamp written in a run comes from the one `Clock` the CLI builds.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from .exits import ExitCode, SpecctlError


@dataclass(frozen=True)
class Clock:
    """A fixed or live clock. `now()` returns the same value all run when fixed."""

    fixed: _dt.datetime | None = None

    def now(self) -> _dt.datetime:
        if self.fixed is not None:
            return self.fixed
        return _dt.datetime.now(_dt.timezone.utc).astimezone()

    def stamp(self) -> str:
        """The form written into front matter and reports: ISO 8601 with an offset."""
        return self.now().isoformat(timespec="seconds")

    @property
    def is_fixed(self) -> bool:
        return self.fixed is not None


def parse_now(value: str | None) -> Clock:
    """Build a Clock from a `--now` argument.

    The value must be ISO 8601 and MUST carry a UTC offset — a naive timestamp would
    make the output depend on the machine's timezone, which is exactly what `--now`
    exists to remove.
    """
    if value is None:
        return Clock()
    try:
        parsed = _dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise SpecctlError(
            f"--now is not a valid ISO 8601 timestamp: {value!r} ({exc})",
            ExitCode.USAGE,
        ) from exc
    if parsed.tzinfo is None:
        raise SpecctlError(
            f"--now must include a UTC offset, e.g. 2026-09-21T10:00:00+07:00 (got {value!r})",
            ExitCode.USAGE,
        )
    return Clock(fixed=parsed)
