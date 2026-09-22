"""The CLI surface: global flags, exit codes (§9.3, §9.4), and the clock (§9.5).

Exit codes are checked as real process exits, because `main()` is where a `SpecctlError`
becomes a code and that mapping is the part downstream tooling — the pre-commit hook of
§20 — actually depends on.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specctl import __version__
from specctl.clock import parse_now
from specctl.exits import ExitCode, SpecctlError

REPO = Path(__file__).resolve().parent.parent


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "specctl.cli", *args],
        cwd=cwd or REPO, capture_output=True, text=True,
    )


# ---------------------------------------------------------------- global flags

def test_version_prints_and_exits_zero() -> None:
    result = run("--version")
    assert result.returncode == ExitCode.OK
    assert result.stdout.strip() == f"specctl {__version__}"


def test_no_arguments_shows_help() -> None:
    result = run()
    assert "Usage" in result.stdout + result.stderr


def test_verbose_prints_resolved_configuration_and_its_sources() -> None:
    """§9.2: `--verbose` MUST print the resolved configuration and each value's source."""
    result = run("--verbose", "fmt")
    assert "resolved configuration" in result.stderr
    assert "specctl.toml" in result.stderr
    assert "doc_key" in result.stderr and "SYS" in result.stderr


def test_verbose_goes_to_stderr_not_stdout() -> None:
    """Progress on stdout would corrupt `--format json` for a caller that pipes it."""
    result = run("--verbose", "fmt")
    assert "resolved configuration" not in result.stdout


def test_verbose_reports_a_fixed_clock() -> None:
    result = run("--verbose", "--now", "2026-09-21T10:00:00+07:00", "fmt")
    assert "clock: fixed 2026-09-21T10:00:00+07:00" in result.stderr


# ---------------------------------------------------------------- exit codes

@pytest.mark.parametrize("args", [
    ("--format", "yaml", "fmt"),
    ("--now", "not-a-date", "fmt"),
    ("--now", "2026-09-21T10:00:00", "fmt"),   # naive: no offset
])
def test_bad_global_flags_exit_usage(args: tuple[str, ...]) -> None:
    result = run(*args)
    assert result.returncode == ExitCode.USAGE, result.stderr


def test_unknown_option_exits_usage_not_clicks_own_code() -> None:
    """The parser's own exit code is 2, which §9.4 reserves for "errors present"."""
    result = run("--nope", "fmt")
    assert result.returncode == ExitCode.USAGE


def test_unknown_command_exits_usage() -> None:
    assert run("nope").returncode == ExitCode.USAGE


def test_missing_required_argument_exits_usage() -> None:
    assert run("ingest").returncode == ExitCode.USAGE


# ---------------------------------------------------------------- command surface

@pytest.mark.parametrize("args,feature", [
    (("ingest", "x.docx"), "F06–F11"),
    (("fmt",), "F14"),
    (("validate",), "F16–F20"),
    (("assign-ids",), "F21"),
    (("split-section", "f.md"), "F21"),
    (("registry", "sync"), "F21"),
    (("index",), "F13"),
    (("log", "why"), "F24"),
    (("export", "xlsx"), "F25"),
])
def test_every_command_exists_and_names_the_feature_that_will_build_it(
    args: tuple[str, ...], feature: str
) -> None:
    """Every command in §9.1 is reachable. None of them pretends to work."""
    result = run(*args)
    assert result.returncode == ExitCode.USAGE
    assert "not implemented yet" in result.stderr
    assert feature in result.stderr


def test_help_lists_every_command_from_the_spec() -> None:
    text = run("--help").stdout
    for command in ("ingest", "fmt", "validate", "assign-ids", "split-section",
                    "registry", "index", "log", "export"):
        assert command in text, f"{command} missing from --help"


# ---------------------------------------------------------------- the clock

def test_fixed_clock_returns_the_same_value_every_call() -> None:
    clock = parse_now("2026-09-21T10:00:00+07:00")
    assert clock.is_fixed
    assert clock.now() == clock.now()
    assert clock.stamp() == "2026-09-21T10:00:00+07:00"


def test_live_clock_is_not_fixed() -> None:
    assert parse_now(None).is_fixed is False


@pytest.mark.parametrize("bad", ["not-a-date", "2026-13-45T00:00:00+07:00", ""])
def test_unparseable_now_is_a_usage_error(bad: str) -> None:
    with pytest.raises(SpecctlError) as exc:
        parse_now(bad)
    assert exc.value.code is ExitCode.USAGE


def test_naive_now_is_rejected() -> None:
    """Without an offset the output would depend on the machine's timezone — which is
    exactly what `--now` exists to remove (§9.5 determinism)."""
    with pytest.raises(SpecctlError, match="must include a UTC offset"):
        parse_now("2026-09-21T10:00:00")


# ---------------------------------------------------------------- exit code table

def test_exit_codes_match_the_spec_table() -> None:
    """§9.4 defines exactly these five. A sixth would be a code nobody documented."""
    assert [(e.name, int(e)) for e in ExitCode] == [
        ("OK", 0), ("WARNINGS", 1), ("ERRORS", 2), ("INPUT", 3), ("USAGE", 4)
    ]


# ---------------------------------------------------------------- shared context

def test_callback_hands_every_command_a_populated_context(tmp_path: Path) -> None:
    """The plumbing F03 onward depends on: resolved config, clock and flags on ctx.obj.

    Registering a probe command on the real app exercises the real callback, so this
    breaks here rather than inside the first command that needs it.
    """
    from specctl.cli import Context, app

    seen: dict[str, object] = {}

    @app.command("probe-context", hidden=True)
    def probe(ctx: typer.Context) -> None:
        seen["obj"] = ctx.obj

    try:
        result = CliRunner().invoke(
            app, ["--now", "2026-09-21T10:00:00+07:00", "--format", "json", "probe-context"]
        )
        assert result.exit_code == 0, result.output
        context = seen["obj"]
        assert isinstance(context, Context)
        assert context.clock.stamp() == "2026-09-21T10:00:00+07:00"
        assert context.output_format == "json"
        assert context.verbose is False
        assert context.config.doc_key == "SYS"  # the repository's own specctl.toml
    finally:
        app.registered_commands = [
            c for c in app.registered_commands if c.name != "probe-context"
        ]


def test_verbose_output_is_reproducible(tmp_path: Path) -> None:
    """§9.5 determinism, applied to the only real output the scaffold produces.

    Uses the tree-hash harness rather than a string compare, so the first real command
    inherits a path that is already exercised.
    """
    from .support.determinism import assert_deterministic

    (tmp_path / "specctl.toml").write_text(
        '[project]\ndoc_key = "SYS"\n[gates]\nfidelity = 0.99\n', encoding="utf-8"
    )

    def write(out: Path) -> None:
        result = run("--verbose", "--now", "2026-09-21T10:00:00+07:00", "fmt", cwd=tmp_path)
        assert result.returncode == ExitCode.USAGE
        (out / "stderr.txt").write_text(result.stderr, encoding="utf-8")

    assert_deterministic(write, tmp_path / "runs", label="--verbose output")
