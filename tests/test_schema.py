"""The shipped schemas (Appendix A), checked against the specification's own examples.

A schema that accepts everything is indistinguishable from no schema, so every case here
comes with the matching rejection.
"""

from __future__ import annotations

import copy
import json

import pytest

from specctl import schema as sc
from specctl.model import INGEST_VERSION

# §7's worked registry, verbatim.
REGISTRY = {
    "version": 1,
    "doc_key": "SYS",
    "next": 1205,
    "blocks": {
        "SYS-000121": {
            "key": "SYS-000100/SYS-000120|paragraph|3|9f2a1c8b", "status": "active",
            "type": "paragraph", "section": "SYS-000120", "text_hash": "9f2a1c8b",
            "first_seen": "v0", "last_seen": "v1",
        },
        "SYS-000122": {
            "key": "SYS-000100/SYS-000120|paragraph|4|1de99042", "status": "merged",
            "merged_into": "SYS-000121", "type": "paragraph", "section": "SYS-000120",
            "text_hash": "1de99042", "first_seen": "v0", "last_seen": "v1",
        },
        "SYS-000130": {
            "key": "SYS-000100/SYS-000120|paragraph|5|77c0aa31", "status": "split",
            "split_into": ["SYS-001205", "SYS-001206"], "type": "paragraph",
            "section": "SYS-000120", "text_hash": "77c0aa31",
            "first_seen": "v0", "last_seen": "v1",
        },
    },
}

GENERATED = {
    "generated": True, "doc": "SYS", "kind": "index",
    "generated_at": "2026-09-21T10:00:00+07:00",
    "generator": "specctl index 0.1.0", "ingest_version": INGEST_VERSION,
}


def without(mapping: dict, *path: str) -> dict:
    out = copy.deepcopy(mapping)
    target = out
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return out


@pytest.mark.parametrize("name", sorted(sc.SCHEMAS))
def test_every_shipped_schema_is_itself_valid(name: str) -> None:
    sc.validator(name)  # calls check_schema


def test_an_unknown_schema_name_is_an_error() -> None:
    with pytest.raises(KeyError, match="no such schema"):
        sc.load_schema("nonesuch")


# ------------------------------------------------------------------ A.3 registry

def test_the_spec_registry_example_validates() -> None:
    sc.validate("ids", REGISTRY)


def test_merged_requires_merged_into() -> None:
    assert not sc.is_valid("ids", without(REGISTRY, "blocks", "SYS-000122", "merged_into"))


def test_split_requires_split_into() -> None:
    assert not sc.is_valid("ids", without(REGISTRY, "blocks", "SYS-000130", "split_into"))


def test_an_active_entry_may_not_carry_lineage() -> None:
    """A terminal status means "not in the vault" (F01 decision 1). An `active` entry
    with `merged_into` is the contradictory state that decision removed."""
    broken = copy.deepcopy(REGISTRY)
    broken["blocks"]["SYS-000121"]["merged_into"] = "SYS-000999"
    assert not sc.is_valid("ids", broken)


def test_a_split_must_name_at_least_two_parts() -> None:
    """Splitting into one part is not a split; it would retire an ID for nothing."""
    broken = copy.deepcopy(REGISTRY)
    broken["blocks"]["SYS-000130"]["split_into"] = ["SYS-001205"]
    assert not sc.is_valid("ids", broken)


@pytest.mark.parametrize("status", ["archived", "ACTIVE", "", "removed"])
def test_unknown_statuses_are_rejected(status: str) -> None:
    broken = copy.deepcopy(REGISTRY)
    broken["blocks"]["SYS-000121"]["status"] = status
    assert not sc.is_valid("ids", broken)


def test_registry_keys_must_be_block_ids() -> None:
    broken = copy.deepcopy(REGISTRY)
    broken["blocks"]["sys-000121"] = broken["blocks"].pop("SYS-000121")
    assert not sc.is_valid("ids", broken)


def test_a_short_text_hash_is_rejected() -> None:
    """§7.1 — the first 8 hex characters of SHA-256. A different width means the key
    format changed and every match key with it."""
    broken = copy.deepcopy(REGISTRY)
    broken["blocks"]["SYS-000121"]["text_hash"] = "9f2a"
    assert not sc.is_valid("ids", broken)


# ------------------------------------------------------------------ A.2 generated

def test_generated_front_matter_validates() -> None:
    sc.validate("generated", GENERATED)


@pytest.mark.parametrize("kind", ["index", "log", "backlinks", "coverage"])
def test_the_four_generated_kinds_are_accepted(kind: str) -> None:
    sc.validate("generated", {**GENERATED, "kind": kind})


def test_generated_must_be_true() -> None:
    """FMT-10 — a generated file says so, and nothing hand-edited claims to be one."""
    assert not sc.is_valid("generated", {**GENERATED, "generated": False})


def test_an_extra_key_in_a_generated_file_is_rejected() -> None:
    assert not sc.is_valid("generated", {**GENERATED, "nonce": 7})


# ------------------------------------------------------------------ A.1 section

def test_errors_are_returned_in_a_stable_order() -> None:
    """Findings go into reports, and reports must be reproducible (§9.5)."""
    instance = {"id": "bad", "doc": "bad!", "level": 99}
    first = sc.errors("section", instance)
    assert first == sc.errors("section", instance)
    assert len(first) > 1


def test_violation_lists_every_problem_not_just_the_first() -> None:
    with pytest.raises(sc.SchemaViolation) as exc:
        sc.validate("section", {"id": "bad"})
    assert len(exc.value.errors) > 1


def test_the_shipped_section_schema_matches_appendix_a1() -> None:
    """It is generated from the document, so the two cannot drift apart."""
    import pathlib
    import re

    spec = pathlib.Path("docs/D-implementation-spec.md").read_text(encoding="utf-8")
    match = re.search(
        r"\*\*A\.1 `section\.schema\.json`\*\*.*?```json\n(.*?)\n```", spec, re.S
    )
    assert match, "Appendix A.1 no longer contains a JSON block"
    assert json.loads(match.group(1)) == sc.load_schema("section")


# ------------------------------------------------------------------ parser ↔ schema

def test_what_the_parser_reads_satisfies_the_schema() -> None:
    """The two halves of the contract meet here: a file the parser accepts must produce
    front matter the schema accepts, or `validate` V01 and the reader disagree."""
    from .test_sectionfile import APPENDIX_D
    from specctl.sectionfile import parse_section

    sc.validate("section", parse_section(APPENDIX_D).front_matter.to_mapping())


def test_an_authored_section_satisfies_the_conditional_branch() -> None:
    """F01 decision 6 — `origin: authored` means `source: null` and `bookmarks: []`."""
    from .test_sectionfile import APPENDIX_D
    from specctl.sectionfile import parse_section, serialize_section

    authored = (APPENDIX_D
                .replace("origin: ingest", "origin: authored")
                .replace('source: { docx: "source/SYS.docx", paragraphs: [412, 447] }',
                         "source: null")
                .replace('bookmarks: ["_Ref123456", "_Toc99887"]', "bookmarks: []"))
    section = parse_section(authored)
    sc.validate("section", section.front_matter.to_mapping())
    assert section.front_matter.source is None
    assert serialize_section(section) == authored


def test_an_authored_section_carrying_a_source_is_rejected() -> None:
    from .test_sectionfile import APPENDIX_D
    from specctl.sectionfile import parse_section

    broken = parse_section(APPENDIX_D.replace("origin: ingest", "origin: authored"))
    assert not sc.is_valid("section", broken.front_matter.to_mapping())


def test_generated_sections_satisfy_the_schema() -> None:
    """Over generated input, so the schema and the parser agree on the whole space and
    not only on the worked example."""
    from hypothesis import HealthCheck, given, settings

    from .support.generators import sections

    @given(sections())
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    def check(section) -> None:
        sc.validate("section", section.front_matter.to_mapping())

    check()
