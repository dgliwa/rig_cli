from __future__ import annotations

import sys

import typer
from rich.console import Console

app = typer.Typer(name="rig")
console = Console()

_CONFIG_OPTION = typer.Option(
    ".",
    "--config",
    "-c",
    help="Path to the rig config directory",
)
_FORMAT_OPTION = typer.Option(
    "text",
    "--format",
    "-f",
    help="Output format: text or json",
)
_SCENE_OPTION = typer.Option(
    None,
    "--scene",
    "-s",
    help="Plan a single scene",
)
_VERBOSE_OPTION = typer.Option(
    0,
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity: -v INFO, -vv DEBUG",
)


def _emit_json(data: str) -> None:
    """Write JSON to raw stdout, bypassing Rich wrapping."""
    sys.stdout.write(data + "\n")
    sys.stdout.flush()
