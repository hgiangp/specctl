"""ID format (§5.1–§5.3). The ID is the only stable handle in the system."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from specctl import ids


@pytest.mark.parametrize("value", ["SYS-000120", "S1-000001", "ABCDEFGH-999999", "A1-000000"])
def test_well_formed_ids_are_accepted(value: str) -> None:
    assert ids.is_id(value)


@pytest.mark.parametrize("value", [
    "sys-000120",        # lowercase is the `^id` spelling, not the canonical one
    "SYS-00120",         # five digits
    "SYS-0001200",       # seven digits
    "S-000120",          # key too short
    "ABCDEFGHI-000120",  # key too long
    "1YS-000120",        # key must start with a letter
    "SYS_000120",
    "SYS-000120 ",
    "",
])
def test_malformed_ids_are_rejected(value: str) -> None:
    assert not ids.is_id(value)


def test_make_and_split_are_inverses() -> None:
    assert ids.make_id("SYS", 120) == "SYS-000120"
    assert ids.split_id("SYS-000120") == ("SYS", 120)


@given(st.from_regex(r"\A[A-Z][A-Z0-9]{1,7}\Z"), st.integers(min_value=0, max_value=999_999))
@settings(max_examples=200, deadline=None)
def test_round_trip_over_every_key_and_counter(doc_key: str, counter: int) -> None:
    block_id = ids.make_id(doc_key, counter)
    assert ids.is_id(block_id)
    assert ids.split_id(block_id) == (doc_key, counter)


def test_the_counter_is_padded_to_exactly_six_digits() -> None:
    assert ids.make_id("SYS", 1) == "SYS-000001"
    assert ids.make_id("SYS", 999_999) == "SYS-999999"


def test_a_counter_that_does_not_fit_is_an_error() -> None:
    """IDs are never reused (§5.2), so the counter only grows — running out is a real
    condition and must not wrap silently into another block's address."""
    with pytest.raises(ValueError, match="does not fit"):
        ids.make_id("SYS", 1_000_000)


def test_a_lowercase_document_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="not a document key"):
        ids.make_id("sys", 1)


def test_the_lowercase_spelling_round_trips() -> None:
    """§5.1 — used only in `^id` markers (FMT-04) and wikilink fragments (FMT-07)."""
    assert ids.to_lower("SYS-000120") == "sys-000120"
    assert ids.from_lower("sys-000120") == "SYS-000120"


@pytest.mark.parametrize("value", ["SYS-000120", "not-an-id", "sys-00012"])
def test_from_lower_rejects_anything_that_is_not_the_lowercase_form(value: str) -> None:
    with pytest.raises(ValueError):
        ids.from_lower(value)


def test_sort_key_orders_by_key_then_counter_numerically() -> None:
    """A total order (§9.5). Plain string sorting works only while every counter has the
    same width; this keeps holding if that ever changes."""
    unsorted = ["SYS-000120", "ABC-000002", "SYS-000012", "ABC-000010"]
    assert sorted(unsorted, key=ids.sort_key) == [
        "ABC-000002", "ABC-000010", "SYS-000012", "SYS-000120",
    ]
