"""Configuration resolution (§9.2, DEC-13).

Settings resolve in this order, first match wins:

    command-line flag  →  environment variable  →  ./specctl.toml  →  built-in default

Every resolved value remembers **where it came from**, because `--verbose` MUST print the
fully resolved configuration and the source of each value (§9.2). A runbook diverges
silently when nobody can see which value was actually in effect.

Environment variable names
--------------------------
§9.2 says `SPECCTL_<NAME>`. `<NAME>` is this module's **flat setting name**, uppercased —
one rule, no ambiguity between sections. `gates.links` is reached by `SPECCTL_GATE_LINKS`,
never by `SPECCTL_LINKS` and never by `SPECCTL_GATES_LINKS`. The flat name is also what
`Config` exposes as an attribute and what `--verbose` prints, so there is a single spelling
of every setting throughout the tool.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .exits import ExitCode, SpecctlError

CONFIG_FILENAME = "specctl.toml"


@dataclass(frozen=True)
class Setting:
    """One knob: its flat name, where it lives in TOML, its type and its default."""

    name: str
    section: str
    key: str
    kind: str  # "str" | "int" | "float" | "bool" | "list[str]"
    default: Any
    help: str

    @property
    def env(self) -> str:
        return f"SPECCTL_{self.name.upper()}"

    @property
    def toml_path(self) -> str:
        return f"{self.section}.{self.key}"


SETTINGS: tuple[Setting, ...] = (
    Setting("doc_key", "project", "doc_key", "str", "",
            "Document key, the ID prefix. Matches [A-Z][A-Z0-9]{1,7} (§5.1)"),
    Setting("split_level", "project", "split_level", "int", 2,
            "Heading level at which a new section file starts (§6.1)"),
    Setting("default_branch", "project", "default_branch", "str", "main",
            "Branch that `validate` takes its merge-base against (§12.2)"),
    Setting("source", "project", "source", "str", "source/SYS.docx",
            "The .docx. Never written to by any command (§9.5)"),
    Setting("vault", "project", "vault", "str", "vault",
            "Vault directory (§4)"),
    Setting("gate_links", "gates", "links", "float", 95.0,
            "Percent of internal links that must resolve (ACC-3)"),
    Setting("gate_tables", "gates", "tables", "float", 90.0,
            "Percent of tables that must survive as pipe or HTML (ACC-4)"),
    Setting("gate_fidelity", "gates", "fidelity", "float", 0.99,
            "Fraction of source text that must be found in the vault (ACC-2)"),
    Setting("large_section_words", "validate", "large_section_words", "int", 1500,
            "Word count above which V14 flags a section as a split candidate"),
    Setting("decimal_comma", "validate", "decimal_comma", "bool", False,
            "True when the source writes decimals as \"1,5\" (§12.6)"),
    Setting("extra_units", "validate", "extra_units", "list[str]", (),
            "Project-specific unit symbols, added to Appendix C"),
    Setting("export_out", "export", "out", "str", "exports/SYS.xlsx",
            "Default path for `export xlsx` (§13.5)"),
    Setting("export_compare_to", "export", "compare_to", "str", "",
            "Default baseline ref for `export xlsx --compare-to`"),
)

_BY_NAME = {s.name: s for s in SETTINGS}
_BY_TOML: dict[tuple[str, str], Setting] = {(s.section, s.key): s for s in SETTINGS}
_SECTIONS = {s.section for s in SETTINGS}

_TRUE = {"true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


@dataclass(frozen=True)
class Value:
    """A resolved setting and the provenance `--verbose` prints."""

    setting: Setting
    value: Any
    source: str


def _coerce(setting: Setting, raw: Any, origin: str) -> Any:
    """Convert `raw` to the setting's declared type, or raise a configuration error."""

    def bad(detail: str) -> SpecctlError:
        return SpecctlError(
            f"{origin}: {setting.name} expects {setting.kind}, {detail}", ExitCode.USAGE
        )

    kind = setting.kind
    if kind == "str":
        if not isinstance(raw, str):
            raise bad(f"got {type(raw).__name__} {raw!r}")
        return raw
    if kind == "bool":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            low = raw.strip().lower()
            if low in _TRUE:
                return True
            if low in _FALSE:
                return False
        raise bad(f"got {raw!r} (use one of {sorted(_TRUE | _FALSE)})")
    if kind == "int":
        # bool is a subclass of int; `split_level = true` is a mistake, not a 1.
        if isinstance(raw, bool):
            raise bad(f"got boolean {raw!r}")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            try:
                return int(raw.strip())
            except ValueError:
                raise bad(f"got {raw!r}") from None
        raise bad(f"got {type(raw).__name__} {raw!r}")
    if kind == "float":
        if isinstance(raw, bool):
            raise bad(f"got boolean {raw!r}")
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            try:
                return float(raw.strip())
            except ValueError:
                raise bad(f"got {raw!r}") from None
        raise bad(f"got {type(raw).__name__} {raw!r}")
    if kind == "list[str]":
        if isinstance(raw, str):
            # An environment variable carries a list as a comma-separated string.
            return tuple(part.strip() for part in raw.split(",") if part.strip())
        if isinstance(raw, (list, tuple)):
            for item in raw:
                if not isinstance(item, str):
                    raise bad(f"got a list containing {type(item).__name__} {item!r}")
            return tuple(raw)
        raise bad(f"got {type(raw).__name__} {raw!r}")
    raise AssertionError(f"unknown setting kind {kind!r}")  # pragma: no cover


def _read_toml(path: Path) -> dict[str, Any]:
    """Load and shape-check specctl.toml.

    Unknown sections and keys are **errors**, not ignored. A silently ignored typo is
    how a runbook and the tool it documents drift apart — the failure DEC-13 exists to
    prevent.
    """
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SpecctlError(f"cannot read {path}: {exc}", ExitCode.USAGE) from exc
    except tomllib.TOMLDecodeError as exc:
        raise SpecctlError(f"{path} is not valid TOML: {exc}", ExitCode.USAGE) from exc

    flat: dict[str, Any] = {}
    for section, body in data.items():
        if section not in _SECTIONS:
            raise SpecctlError(
                f"{path}: unknown section [{section}] "
                f"(known: {', '.join(sorted(_SECTIONS))})",
                ExitCode.USAGE,
            )
        if not isinstance(body, dict):
            raise SpecctlError(
                f"{path}: [{section}] must be a table, got {type(body).__name__}",
                ExitCode.USAGE,
            )
        for key, raw in body.items():
            setting = _BY_TOML.get((section, key))
            if setting is None:
                known = ", ".join(
                    sorted(k for (s, k) in _BY_TOML if s == section)
                )
                raise SpecctlError(
                    f"{path}: unknown key {key!r} in [{section}] (known: {known})",
                    ExitCode.USAGE,
                )
            flat[setting.name] = raw
    return flat


class Config:
    """Resolved settings, each with its provenance.

    Access by flat name: `cfg.doc_key`, `cfg.gate_fidelity`. Unknown names raise
    `AttributeError` rather than returning `None`, so a typo fails at the call site.
    """

    def __init__(self, values: dict[str, Value], config_path: Path | None) -> None:
        self._values = values
        self.config_path = config_path

    def __getattr__(self, name: str) -> Any:
        try:
            return self._values[name].value
        except KeyError:
            raise AttributeError(f"no such setting: {name!r}") from None

    def source_of(self, name: str) -> str:
        if name not in self._values:
            raise KeyError(f"no such setting: {name!r}")
        return self._values[name].source

    def provenance(self) -> list[Value]:
        """Every setting in declaration order — a total order, per §9.5 determinism."""
        return [self._values[s.name] for s in SETTINGS]

    def dump(self) -> str:
        """The table `--verbose` prints (§9.2)."""
        rows = [(v.setting.name, _render(v.value), v.source) for v in self.provenance()]
        w_name = max(len(r[0]) for r in rows)
        w_val = max(len(r[1]) for r in rows)
        origin = str(self.config_path) if self.config_path else "(no specctl.toml found)"
        lines = [f"resolved configuration  [config file: {origin}]"]
        lines += [f"  {n:<{w_name}}  {v:<{w_val}}  {s}" for n, v, s in rows]
        return "\n".join(lines)


def _render(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple):
        return "[" + ", ".join(value) + "]"
    return str(value)


def find_config(start: Path) -> Path | None:
    """Locate `./specctl.toml`.

    §9.2 says `./specctl.toml` — the current directory, not an upward search. An upward
    search would make the effective configuration depend on where the operator happened
    to stand, which is the opposite of declaring it once.
    """
    candidate = start / CONFIG_FILENAME
    return candidate if candidate.is_file() else None


def load_config(
    overrides: Mapping[str, Any] | None = None,
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Config:
    """Resolve every setting, recording where each value came from.

    `overrides` holds command-line flags; a `None` value means "flag not given" and is
    skipped, so callers can pass their parsed options straight through.
    """
    overrides = {k: v for k, v in (overrides or {}).items() if v is not None}
    unknown = set(overrides) - set(_BY_NAME)
    if unknown:
        raise SpecctlError(
            f"unknown setting overridden: {', '.join(sorted(unknown))}", ExitCode.USAGE
        )

    cwd = Path.cwd() if cwd is None else cwd
    env = os.environ if env is None else env

    config_path = find_config(cwd)
    from_file = _read_toml(config_path) if config_path else {}

    values: dict[str, Value] = {}
    for setting in SETTINGS:
        if setting.name in overrides:
            raw, source = overrides[setting.name], "flag"
        elif setting.env in env:
            raw, source = env[setting.env], f"env:{setting.env}"
        elif setting.name in from_file:
            raw, source = from_file[setting.name], str(config_path)
        else:
            raw, source = setting.default, "default"
        values[setting.name] = Value(setting, _coerce(setting, raw, source), source)
    return Config(values, config_path)
