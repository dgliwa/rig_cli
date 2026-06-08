from __future__ import annotations

import logging
from pathlib import Path

import typer

from rig.cli._shared import _CONFIG_OPTION, _VERBOSE_OPTION, console, gen_app
from rig.config.errors import ConfigError
from rig.config.loader import load_rig
from rig.log_setup import setup_logging

logger = logging.getLogger(__name__)


@gen_app.command()
def mc6(config: str = _CONFIG_OPTION, verbose: int = _VERBOSE_OPTION):
    """Generate MC6 bank configs from scene definitions."""
    setup_logging(verbose)
    logger.info("Generating MC6 config from: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    try:
        from rig_morningstar.generator import generate_mc6, write_mc6_config
    except ImportError:
        console.print("[red]✗[/red] rig-morningstar is not installed. Run: uv add rig-morningstar")
        raise typer.Exit(1)

    data = generate_mc6(rig)
    if not data:
        console.print(
            "[yellow]No MC6 configuration found — ensure a controller device with banks is defined in the rig config[/yellow]"
        )
        return

    out_dir = write_mc6_config(data, output_path=str(Path(config).resolve() / "generated" / "mc6"))
    console.print(f"[green]✓[/green] MC6 config written to {out_dir}")
