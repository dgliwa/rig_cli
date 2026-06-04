from __future__ import annotations

import json
import logging

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
from rig.log_setup import setup_logging

logger = logging.getLogger(__name__)


@app.command()
def validate(
    config: str = _CONFIG_OPTION,
    output_format: str = _FORMAT_OPTION,
    verbose: int = _VERBOSE_OPTION,
):
    """Validate the rig configuration."""
    setup_logging(verbose)
    logger.info("Validating config at: %s", config)
    try:
        rig = load_rig(config)
        if output_format == "json":
            console.print(
                json.dumps(
                    {"status": "valid", "pedals": len(rig.pedals), "scenes": len(rig.scenes)},
                    indent=2,
                )
            )
        else:
            console.print(
                f"[green]✓[/green] {rig.name} — {len(rig.pedals)} pedals, {len(rig.scenes)} scenes"
            )
            console.print("[green]✓[/green] All cross-references valid")
    except ConfigError as e:
        if output_format == "json":
            _emit_json(json.dumps({"status": "error", "error": str(e)}))
        else:
            console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)
