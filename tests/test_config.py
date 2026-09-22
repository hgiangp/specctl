"""Configuration resolution (§9.2).

The order — flag, environment, file, default — is the whole contract, and `--verbose`
has to be able to say which one won. These tests pin both.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specctl.config import SETTINGS, load_config
from specctl.exits import ExitCode, SpecctlError

TOML = """
[project]
doc_key = "SYS"
split_level = 3

[gates]
fidelity = 0.995

[validate]
decimal_comma = true
extra_units = ["Nm/s", "deg/s"]
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "specctl.toml").write_text(TOML, encoding="utf-8")
    return tmp_path


def test_defaults_apply_with_no_file_and_no_env(tmp_path: Path) -> None:
    cfg = load_config(cwd=tmp_path, env={})
    assert cfg.split_level == 2
    assert cfg.default_branch == "main"
    assert cfg.gate_fidelity == 0.99
    assert cfg.source_of("split_level") == "default"
    assert cfg.config_path is None


def test_file_beats_default(project: Path) -> None:
    cfg = load_config(cwd=project, env={})
    assert cfg.doc_key == "SYS"
    assert cfg.split_level == 3
    assert cfg.gate_fidelity == 0.995
    assert cfg.decimal_comma is True
    assert cfg.extra_units == ("Nm/s", "deg/s")
    assert cfg.source_of("split_level").endswith("specctl.toml")


def test_env_beats_file(project: Path) -> None:
    cfg = load_config(cwd=project, env={"SPECCTL_SPLIT_LEVEL": "4"})
    assert cfg.split_level == 4
    assert cfg.source_of("split_level") == "env:SPECCTL_SPLIT_LEVEL"
    assert cfg.doc_key == "SYS"  # untouched keys still come from the file


def test_flag_beats_env(project: Path) -> None:
    cfg = load_config({"split_level": 5}, cwd=project, env={"SPECCTL_SPLIT_LEVEL": "4"})
    assert cfg.split_level == 5
    assert cfg.source_of("split_level") == "flag"


def test_full_precedence_chain_in_one_run(project: Path) -> None:
    """One value from each of the four sources, in one resolution."""
    cfg = load_config(
        {"vault": "other-vault"},
        cwd=project,
        env={"SPECCTL_SPLIT_LEVEL": "4"},
    )
    assert (cfg.vault, cfg.source_of("vault")) == ("other-vault", "flag")
    assert (cfg.split_level, cfg.source_of("split_level")) == (4, "env:SPECCTL_SPLIT_LEVEL")
    assert cfg.doc_key == "SYS" and cfg.source_of("doc_key").endswith("specctl.toml")
    assert (cfg.default_branch, cfg.source_of("default_branch")) == ("main", "default")


def test_a_none_flag_means_not_given(project: Path) -> None:
    """Callers pass parsed options straight through; `None` must not shadow the file."""
    cfg = load_config({"split_level": None}, cwd=project, env={})
    assert cfg.split_level == 3


def test_every_setting_has_an_env_name_and_they_are_unique() -> None:
    names = [s.env for s in SETTINGS]
    assert len(set(names)) == len(names)
    assert all(n.startswith("SPECCTL_") for n in names)


def test_env_list_is_comma_separated(tmp_path: Path) -> None:
    cfg = load_config(cwd=tmp_path, env={"SPECCTL_EXTRA_UNITS": "Nm/s, deg/s , "})
    assert cfg.extra_units == ("Nm/s", "deg/s")


@pytest.mark.parametrize("raw,expected", [
    ("true", True), ("1", True), ("yes", True), ("ON", True),
    ("false", False), ("0", False), ("no", False), ("Off", False),
])
def test_bool_spellings(tmp_path: Path, raw: str, expected: bool) -> None:
    cfg = load_config(cwd=tmp_path, env={"SPECCTL_DECIMAL_COMMA": raw})
    assert cfg.decimal_comma is expected


def test_provenance_is_in_declaration_order(project: Path) -> None:
    """A total order, per §9.5 — so `--verbose` output is itself reproducible."""
    cfg = load_config(cwd=project, env={})
    assert [v.setting.name for v in cfg.provenance()] == [s.name for s in SETTINGS]


def test_dump_names_the_file_and_every_source(project: Path) -> None:
    cfg = load_config(cwd=project, env={"SPECCTL_VAULT": "v2"})
    text = cfg.dump()
    assert "specctl.toml" in text
    assert "env:SPECCTL_VAULT" in text
    for setting in SETTINGS:
        assert setting.name in text


# ---------------------------------------------------------------- error cases

def test_unknown_section_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "specctl.toml").write_text("[nope]\nx = 1\n", encoding="utf-8")
    with pytest.raises(SpecctlError, match="unknown section") as exc:
        load_config(cwd=tmp_path, env={})
    assert exc.value.code is ExitCode.USAGE


def test_unknown_key_is_an_error_not_a_silent_ignore(tmp_path: Path) -> None:
    """A typo that is ignored is how a runbook and its tool drift apart (DEC-13)."""
    (tmp_path / "specctl.toml").write_text(
        '[project]\ndoc_kye = "SYS"\n', encoding="utf-8"
    )
    with pytest.raises(SpecctlError, match="unknown key 'doc_kye'"):
        load_config(cwd=tmp_path, env={})


def test_malformed_toml_is_a_configuration_error(tmp_path: Path) -> None:
    (tmp_path / "specctl.toml").write_text("[project\n", encoding="utf-8")
    with pytest.raises(SpecctlError, match="not valid TOML") as exc:
        load_config(cwd=tmp_path, env={})
    assert exc.value.code is ExitCode.USAGE


def test_wrong_type_in_file_is_reported_with_the_source(tmp_path: Path) -> None:
    (tmp_path / "specctl.toml").write_text(
        '[project]\nsplit_level = "deep"\n', encoding="utf-8"
    )
    with pytest.raises(SpecctlError, match=r"specctl\.toml: split_level expects int"):
        load_config(cwd=tmp_path, env={})


def test_boolean_is_not_accepted_as_an_int(tmp_path: Path) -> None:
    """`split_level = true` is a mistake, not a 1 — bool subclasses int in Python."""
    (tmp_path / "specctl.toml").write_text(
        "[project]\nsplit_level = true\n", encoding="utf-8"
    )
    with pytest.raises(SpecctlError, match="got boolean"):
        load_config(cwd=tmp_path, env={})


def test_unparseable_env_value_names_the_variable(tmp_path: Path) -> None:
    with pytest.raises(SpecctlError, match="env:SPECCTL_GATE_FIDELITY"):
        load_config(cwd=tmp_path, env={"SPECCTL_GATE_FIDELITY": "very high"})


def test_bad_bool_lists_the_accepted_spellings(tmp_path: Path) -> None:
    with pytest.raises(SpecctlError, match="use one of"):
        load_config(cwd=tmp_path, env={"SPECCTL_DECIMAL_COMMA": "maybe"})


def test_overriding_an_unknown_setting_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(SpecctlError, match="unknown setting overridden: nonesuch"):
        load_config({"nonesuch": 1}, cwd=tmp_path, env={})


def test_unknown_attribute_raises_rather_than_returning_none(tmp_path: Path) -> None:
    cfg = load_config(cwd=tmp_path, env={})
    with pytest.raises(AttributeError, match="no such setting"):
        _ = cfg.nonesuch


def test_config_is_not_searched_upward(tmp_path: Path) -> None:
    """§9.2 says `./specctl.toml`. An upward search would make the effective
    configuration depend on where the operator happened to stand."""
    (tmp_path / "specctl.toml").write_text('[project]\ndoc_key = "UP"\n', encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    cfg = load_config(cwd=nested, env={})
    assert cfg.doc_key == ""
    assert cfg.config_path is None
