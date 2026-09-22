"""Hash a directory tree, so "byte-identical" is checkable rather than asserted.

§9.5 requires that, given the same inputs, configuration and `--now`, every command
produce byte-identical output. Several named tests depend on this being mechanical:

* T-ING-05 — two `--reingest --now X` runs produce identical `vault/sections/**`
* T-FMT-02 — `fmt` is idempotent
* T-VAL-12 — `validate`, and every `--check`, leave the working tree untouched

Directories are part of the manifest, so an output that differs only by an empty
directory is still caught. The manifest is sorted, giving the total order §9.5 demands.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

Manifest = dict[str, str]

DEFAULT_EXCLUDE: tuple[str, ...] = ("__pycache__", ".pytest_cache", ".git", ".mypy_cache")


def _excluded(rel: Path, exclude: tuple[str, ...]) -> bool:
    return any(part in exclude for part in rel.parts)


def hash_tree(root: Path, *, exclude: tuple[str, ...] = DEFAULT_EXCLUDE) -> Manifest:
    """Map every path under `root` to a digest of its content.

    Values are `sha256:<hex>` for a file, `dir` for a directory, `link:<target>` for a
    symlink. A symlink is recorded by target rather than followed, so that a tree which
    merely points somewhere else is not reported as identical.
    """
    root = Path(root)
    manifest: Manifest = {}
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root)
        if _excluded(rel, exclude):
            continue
        key = rel.as_posix()
        if path.is_symlink():
            manifest[key] = f"link:{path.readlink().as_posix()}"
        elif path.is_dir():
            manifest[key] = "dir"
        else:
            manifest[key] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def tree_digest(root: Path, *, exclude: tuple[str, ...] = DEFAULT_EXCLUDE) -> str:
    """One digest over the whole tree, for a cheap equality check."""
    manifest = hash_tree(root, exclude=exclude)
    blob = "\n".join(f"{k}\t{v}" for k, v in sorted(manifest.items()))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def diff_manifests(a: Manifest, b: Manifest) -> list[str]:
    """Human-readable differences, so a failure says *what* differed."""
    out: list[str] = []
    for key in sorted(set(a) - set(b)):
        out.append(f"only in first:  {key}")
    for key in sorted(set(b) - set(a)):
        out.append(f"only in second: {key}")
    for key in sorted(set(a) & set(b)):
        if a[key] != b[key]:
            out.append(f"differs:        {key}  {a[key]} != {b[key]}")
    return out


def assert_same_tree(first: Path, second: Path, *, label: str = "output") -> None:
    """Fail with the list of differing paths, not just a mismatched digest."""
    differences = diff_manifests(hash_tree(first), hash_tree(second))
    if differences:
        detail = "\n  ".join(differences)
        raise AssertionError(f"{label} is not byte-identical across runs:\n  {detail}")


def assert_deterministic(write, root: Path, *, label: str = "output") -> None:
    """Run `write(out_dir)` twice into sibling directories and compare the results.

    `write` receives a fresh, existing directory each time and must put its output there.
    """
    first = root / "run-1"
    second = root / "run-2"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    write(first)
    write(second)
    assert_same_tree(first, second, label=label)
