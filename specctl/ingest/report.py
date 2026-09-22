"""What a read of the source says about itself: issues, skips, revision counts (§8).

`coverage.json` is assembled in F11, but the values it reports are produced here, by the
components that actually observe them. Keeping the carriers in one module means the walker
cannot invent an issue code the report does not know about, and the report cannot silently
grow a skip bucket that nothing accounts for.

Two shapes matter:

* an **issue** is something a human may need to act on, and is always addressable — it
  carries the source paragraph index, so a low number is a list of places rather than a
  verdict (§10.12 F5);
* a **skip** is a deliberate omission, and is counted in paragraphs *and* characters, so
  that what was dropped on purpose sits next to what was captured (§8.3).

A skip is never an issue and an issue is never a skip. Conflating them is how "not
handled yet" turns into "gone", which is Failure 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

Severity = Literal["error", "warn", "info"]

#: Appendix B — the complete issue registry, with the severity each code is raised at.
#: A code outside this table is a bug, not a new kind of finding: `Issue` refuses it.
ISSUE_CODES: dict[str, Severity] = {
    "unresolved_ref": "warn",
    "textual_ref_candidate": "info",
    "numbering_unresolved": "warn",
    "table_parse_failed": "error",
    "formula_conversion_failed": "warn",
    "shape_unrenderable": "warn",
    "style_dropped": "info",
    "unknown_container": "info",
    "source_has_unresolved_revisions": "warn",
    "index_too_large": "warn",
}

#: §8.3 — fixed. Skipping anything else needs a code here first, which is the point:
#: the set of things dropped on purpose is closed and visible.
SKIP_CODES: tuple[str, ...] = ("toc", "header_footer")

_SEVERITY_RANK = {"error": 0, "warn": 1, "info": 2}


@dataclass(frozen=True, order=False)
class Issue:
    """One entry of `coverage.json` `issues` (§8.4)."""

    code: str
    paragraph: int
    detail: str = ""
    severity: Severity = ""  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.code not in ISSUE_CODES:
            raise ValueError(
                f"{self.code!r} is not an issue code in Appendix B; "
                f"known codes are {', '.join(sorted(ISSUE_CODES))}"
            )
        if not self.severity:
            object.__setattr__(self, "severity", ISSUE_CODES[self.code])

    @property
    def sort_key(self) -> tuple[int, int, str, str]:
        """§8.4 sorts by paragraph. The rest of the key only breaks ties, so that two
        issues on one paragraph never depend on the order they were appended in — a
        total order is what §9.5 means by deterministic."""
        return (self.paragraph, _SEVERITY_RANK[self.severity], self.code, self.detail)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "paragraph": self.paragraph,
            "detail": self.detail,
        }


def sorted_issues(issues: Iterable[Issue]) -> tuple[Issue, ...]:
    return tuple(sorted(issues, key=lambda i: i.sort_key))


@dataclass(frozen=True)
class Skip:
    """A deliberate omission, in paragraphs and characters (§8.3)."""

    paragraphs: int = 0
    chars: int = 0

    def plus(self, paragraphs: int, chars: int) -> "Skip":
        return Skip(self.paragraphs + paragraphs, self.chars + chars)

    def to_mapping(self) -> dict[str, int]:
        return {"paragraphs": self.paragraphs, "chars": self.chars}


@dataclass(frozen=True)
class Revisions:
    """§10.5 W1 — what the tracked-change handling did, in numbers.

    Both directions are counted. A run that only reported what it kept would say nothing
    about the deleted paragraph it correctly threw away, and W2 needs the total to decide
    whether the source is fit to be a baseline at all.
    """

    ins_accepted: int = 0
    del_discarded: int = 0
    comments_discarded: int = 0

    @property
    def total(self) -> int:
        return self.ins_accepted + self.del_discarded

    def to_mapping(self) -> dict[str, int]:
        return {
            "ins_accepted": self.ins_accepted,
            "del_discarded": self.del_discarded,
            "comments_discarded": self.comments_discarded,
        }


@dataclass
class Counter:
    """The mutable accumulator the walker writes into; frozen shapes come out of it."""

    ins_accepted: int = 0
    del_discarded: int = 0
    comments_discarded: int = 0
    skips: dict[str, Skip] = field(default_factory=lambda: {c: Skip() for c in SKIP_CODES})
    issues: list[Issue] = field(default_factory=list)

    def skip(self, code: str, *, paragraphs: int, chars: int) -> None:
        if code not in SKIP_CODES:
            raise ValueError(f"{code!r} is not a skip code in §8.3")
        self.skips[code] = self.skips[code].plus(paragraphs, chars)

    def issue(self, code: str, paragraph: int, detail: str = "") -> None:
        self.issues.append(Issue(code=code, paragraph=paragraph, detail=detail))

    def revisions(self) -> Revisions:
        return Revisions(self.ins_accepted, self.del_discarded, self.comments_discarded)
