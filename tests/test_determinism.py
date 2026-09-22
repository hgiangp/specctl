"""The determinism harness must detect non-determinism, not just bless sameness.

A harness that always passes is the most expensive kind of test: it costs nothing to
run and it removes the incentive to look. So each check here comes in a pair — one tree
that must compare equal, and one that must be caught.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .support.determinism import (
    assert_deterministic,
    assert_same_tree,
    diff_manifests,
    hash_tree,
    tree_digest,
)


def test_identical_trees_compare_equal(tmp_path: Path) -> None:
    for name in ("a", "b"):
        root = tmp_path / name
        (root / "sections").mkdir(parents=True)
        (root / "sections" / "SYS-000120.md").write_text("x\n", encoding="utf-8")
    assert_same_tree(tmp_path / "a", tmp_path / "b")
    assert tree_digest(tmp_path / "a") == tree_digest(tmp_path / "b")


def test_changed_content_is_caught(tmp_path: Path) -> None:
    for name, body in (("a", "50 ms\n"), ("b", "80 ms\n")):
        root = tmp_path / name
        root.mkdir()
        (root / "f.md").write_text(body, encoding="utf-8")
    with pytest.raises(AssertionError, match="differs"):
        assert_same_tree(tmp_path / "a", tmp_path / "b")


def test_added_and_removed_files_are_caught(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "f.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "b" / "f.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "b" / "extra.md").write_text("y\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="only in second"):
        assert_same_tree(tmp_path / "a", tmp_path / "b")


def test_empty_directory_difference_is_caught(tmp_path: Path) -> None:
    """A vault that differs only by an empty assets/ directory is still not identical."""
    (tmp_path / "a").mkdir()
    (tmp_path / "b" / "assets").mkdir(parents=True)
    with pytest.raises(AssertionError, match="only in second: assets"):
        assert_same_tree(tmp_path / "a", tmp_path / "b")


def test_symlinks_are_recorded_by_target_not_followed(tmp_path: Path) -> None:
    for name, target in (("a", "one.md"), ("b", "two.md")):
        root = tmp_path / name
        root.mkdir()
        (root / "one.md").write_text("same\n", encoding="utf-8")
        (root / "two.md").write_text("same\n", encoding="utf-8")
        (root / "link.md").symlink_to(target)
    manifest = hash_tree(tmp_path / "a")
    assert manifest["link.md"] == "link:one.md"
    with pytest.raises(AssertionError, match="differs"):
        assert_same_tree(tmp_path / "a", tmp_path / "b")


def test_pycache_is_excluded(tmp_path: Path) -> None:
    """Build artefacts are not output; they must not make two good runs look different."""
    for name in ("a", "b"):
        root = tmp_path / name / "__pycache__"
        root.mkdir(parents=True)
        (root / f"mod.{name}.pyc").write_bytes(name.encode())
    assert_same_tree(tmp_path / "a", tmp_path / "b")


def test_assert_deterministic_passes_on_a_fixed_writer(tmp_path: Path) -> None:
    def write(out: Path) -> None:
        (out / "report.md").write_text("coverage: 0.9984\n", encoding="utf-8")

    assert_deterministic(write, tmp_path)


def test_assert_deterministic_catches_a_drifting_writer(tmp_path: Path) -> None:
    """The case that matters: an unfixed clock, a random tmp name, a set iteration order."""
    calls = {"n": 0}

    def write(out: Path) -> None:
        calls["n"] += 1
        (out / "report.md").write_text(
            f"generated_at: 2026-09-21T10:00:0{calls['n']}+07:00\n", encoding="utf-8"
        )

    with pytest.raises(AssertionError, match="not byte-identical"):
        assert_deterministic(write, tmp_path)


def test_diff_manifests_reports_every_kind_of_difference() -> None:
    a = {"keep": "sha256:1", "gone": "dir", "changed": "sha256:1"}
    b = {"keep": "sha256:1", "added": "dir", "changed": "sha256:2"}
    assert diff_manifests(a, b) == [
        "only in first:  gone",
        "only in second: added",
        "differs:        changed  sha256:1 != sha256:2",
    ]
