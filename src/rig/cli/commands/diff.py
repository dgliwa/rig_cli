from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from rig.cli._shared import (
    _CONFIG_OPTION,
    _FORMAT_OPTION,
    _VERBOSE_OPTION,
    _emit_json,
    app,
    console,
)
from rig.config.errors import ConfigError
from rig.config.loader import load_rig
from rig.engine.diff import compute_diff, format_diff
from rig.log_setup import setup_logging

logger = logging.getLogger(__name__)


@app.command()
def diff(
    config: str = _CONFIG_OPTION,
    output_format: str = _FORMAT_OPTION,
    verbose: int = _VERBOSE_OPTION,
):
    """Show differences between config and last-known state."""
    setup_logging(verbose)
    logger.info("Computing diff for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    config_path = str(Path(config).resolve())
    changes = compute_diff(rig, root_path=config_path)
    if output_format == "json":
        _emit_json(json.dumps(changes, indent=2))
        return
    output = format_diff(changes)
    console.print(output)
