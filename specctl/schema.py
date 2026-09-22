"""Schema loading and validation (Appendix A).

The schemas ship inside the package and are enforced by V01 and by the writers, so that
a malformed file is caught where it is read rather than three commands later.

`section.schema.json` is generated from Appendix A.1 of the specification, so the shipped
schema and the document cannot drift apart. `coverage.schema.json` (A.4) and
`findings.schema.json` (A.5) arrive with the commands that produce them — F11 and
F16–F20 — since a schema written before its producer exists only invites churn.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Mapping

import jsonschema

SCHEMA_DIR = Path(__file__).parent / "schemas"

#: Appendix A, by file class.
SCHEMAS: Mapping[str, str] = {
    "section": "section.schema.json",
    "generated": "generated.schema.json",
    "ids": "ids.schema.json",
}


class SchemaViolation(Exception):
    """A document that does not satisfy its schema. Reported as V01."""

    def __init__(self, schema_name: str, errors: list[str]) -> None:
        joined = "; ".join(errors)
        super().__init__(f"does not satisfy the {schema_name} schema: {joined}")
        self.schema_name = schema_name
        self.errors = errors


@functools.lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    try:
        filename = SCHEMAS[name]
    except KeyError:
        raise KeyError(f"no such schema: {name!r} (have {sorted(SCHEMAS)})") from None
    return json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def validator(name: str) -> jsonschema.protocols.Validator:
    schema = load_schema(name)
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def errors(name: str, instance: Any) -> list[str]:
    """Every violation, in a stable order — messages go into reports (§9.5 determinism)."""
    found = sorted(validator(name).iter_errors(instance), key=lambda e: list(e.absolute_path))
    return [_describe(error) for error in found]


def _describe(error: jsonschema.ValidationError) -> str:
    location = "/".join(str(part) for part in error.absolute_path) or "(root)"
    return f"{location}: {error.message}"


def validate(name: str, instance: Any) -> None:
    """Raise `SchemaViolation` listing every problem, not just the first."""
    found = errors(name, instance)
    if found:
        raise SchemaViolation(name, found)


def is_valid(name: str, instance: Any) -> bool:
    return not errors(name, instance)
