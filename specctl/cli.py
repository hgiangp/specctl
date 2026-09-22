"""The `specctl` command line (§9.1–§9.4).

This module owns three things and nothing else: parsing global flags, resolving
configuration, and turning a `SpecctlError` into a stderr line plus an exit code.
No command logic lives here.

Commands that are not built yet exit `USAGE` with the feature that will build them
named in the message. §9.4 defines five exit codes and no sixth, so a scaffold stub
reports a usage error rather than inventing a code the spec does not have.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from . import __version__
from .clock import Clock, parse_now
from .config import Config, load_config
from .exits import ExitCode, SpecctlError

app = typer.Typer(
    name="specctl",
    help="Turn a Word system requirements spec into a Markdown vault with stable block IDs.",
    add_completion=False,
    no_args_is_help=True,
)
registry_app = typer.Typer(help="The ID registry (§7).", no_args_is_help=True)
export_app = typer.Typer(help="Exporters (§13.5).", no_args_is_help=True)
app.add_typer(registry_app, name="registry")
app.add_typer(export_app, name="export")


@dataclass
class Context:
    """What every command gets: resolved configuration, a clock, and verbosity."""

    config: Config
    clock: Clock
    verbose: bool
    output_format: str


def _version(value: bool) -> None:
    if value:
        typer.echo(f"specctl {__version__}")
        raise typer.Exit(ExitCode.OK)


def _todo(feature: str, command: str) -> NoReturn:
    """A command the scaffold does not implement yet."""
    raise SpecctlError(
        f"`specctl {command}` is not implemented yet — it is feature {feature} "
        f"(see docs/F-features.md)",
        ExitCode.USAGE,
    )


@app.callback()
def main_callback(
    ctx: typer.Context,
    now: Annotated[
        str | None,
        typer.Option("--now", metavar="ISO8601",
                     help="Fix the clock. Every timestamp written in the run uses it. "
                          "Required for reproducible tests (§9.3)."),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option("--format", metavar="text|json",
                     help="Output format where the command produces a report."),
    ] = "text",
    verbose: Annotated[
        bool,
        typer.Option("--verbose",
                     help="Print the resolved configuration and per-step progress to stderr."),
    ] = False,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True,
                     help="Print the specctl version and exit 0."),
    ] = False,
) -> None:
    """Resolve the global flags once, for every command."""
    if output_format not in ("text", "json"):
        raise SpecctlError(
            f"--format must be 'text' or 'json', got {output_format!r}", ExitCode.USAGE
        )
    config = load_config()
    context = Context(
        config=config, clock=parse_now(now), verbose=verbose, output_format=output_format
    )
    ctx.obj = context
    if verbose:
        print(config.dump(), file=sys.stderr)
        print(
            f"clock: {'fixed ' + context.clock.stamp() if context.clock.is_fixed else 'live'}",
            file=sys.stderr,
        )


@app.command()
def ingest(
    ctx: typer.Context,
    source: Annotated[Path, typer.Argument(help="The .docx to read.")],
    doc_key: Annotated[str | None, typer.Option("--doc-key", help="ID prefix (§5.1).")] = None,
    out: Annotated[Path | None, typer.Option("--out", help="Vault directory.")] = None,
) -> None:
    """Convert the .docx into the Markdown vault (§10)."""
    _todo("F05–F11", "ingest")


@app.command()
def fmt(
    ctx: typer.Context,
    paths: Annotated[list[Path] | None, typer.Argument(help="Section files; default all.")] = None,
    check: Annotated[bool, typer.Option("--check", help="Report without writing.")] = False,
) -> None:
    """Recompute everything derived (§11)."""
    _todo("F14", "fmt")


@app.command()
def validate(
    ctx: typer.Context,
    paths: Annotated[list[Path] | None, typer.Argument(help="Section files; default all.")] = None,
    base: Annotated[str | None, typer.Option("--base", help="Ref to compare against (§12.2).")] = None,
    allow_delete: Annotated[bool, typer.Option("--allow-delete")] = False,
) -> None:
    """Check IDs, lineage, locked blocks and numbers. Writes nothing (§12)."""
    _todo("F16–F20", "validate")


@app.command("assign-ids")
def assign_ids(
    ctx: typer.Context,
    paths: Annotated[list[Path] | None, typer.Argument()] = None,
    label: Annotated[str | None, typer.Option("--label", help="Baseline label for first_seen.")] = None,
) -> None:
    """Allocate IDs to anchorless blocks, changing nothing else (§12.4)."""
    _todo("F21", "assign-ids")


@app.command("split-section")
def split_section(
    ctx: typer.Context,
    file: Annotated[Path, typer.Argument(help="The section file to split.")],
    at: Annotated[str, typer.Option("--at", help="Heading block ID to carve out.")] = "",
) -> None:
    """Move a heading and its content into a new section file (§12.9)."""
    _todo("F21", "split-section")


@registry_app.command("sync")
def registry_sync(
    ctx: typer.Context,
    base: Annotated[str | None, typer.Option("--base")] = None,
    label: Annotated[str | None, typer.Option("--label")] = None,
) -> None:
    """Write terminal statuses into meta/ids.json. Runs after the commit (§12.10)."""
    _todo("F21", "registry sync")


@app.command()
def index(
    ctx: typer.Context,
    check: Annotated[bool, typer.Option("--check")] = False,
) -> None:
    """Regenerate index.md, backlinks.md and coverage.md (§13.1)."""
    _todo("F13", "index")


@app.command()
def log(
    ctx: typer.Context,
    message: Annotated[str, typer.Argument(help="The rationale.")],
    section: Annotated[str | None, typer.Option("--section")] = None,
    skill: Annotated[str | None, typer.Option("--skill")] = None,
    model: Annotated[str | None, typer.Option("--model")] = None,
) -> None:
    """Append one row to the append-only change log (§13.4)."""
    _todo("F24", "log")


@export_app.command("xlsx")
def export_xlsx(
    ctx: typer.Context,
    out: Annotated[Path | None, typer.Option("--out")] = None,
    ref: Annotated[str, typer.Option("--ref")] = "HEAD",
    compare_to: Annotated[str | None, typer.Option("--compare-to")] = None,
) -> None:
    """Export the vault to Excel with change columns (§13.5)."""
    _todo("F25", "export xlsx")


def main() -> NoReturn:
    """Console entry point: the single place an error becomes an exit code.

    `standalone_mode=False` stops typer from exiting on its own, so that every path
    out of here maps onto §9.4 and nothing maps onto a code §9.4 does not define.
    Typer's parser raises usage errors with its own `exit_code` of 2, which §9.4 gives
    a different meaning to — they are re-mapped onto `USAGE`.
    """
    from typer._click.exceptions import ClickException

    try:
        app(standalone_mode=False)
    except SpecctlError as exc:
        print(f"specctl: {exc}", file=sys.stderr)
        raise SystemExit(int(exc.code))
    except typer.Exit as exc:
        raise SystemExit(int(exc.exit_code))
    except ClickException as exc:
        exc.show()
        raise SystemExit(int(ExitCode.USAGE))
    except KeyboardInterrupt:
        print("specctl: interrupted", file=sys.stderr)
        raise SystemExit(int(ExitCode.USAGE))
    raise SystemExit(int(ExitCode.OK))


if __name__ == "__main__":  # pragma: no cover
    main()
