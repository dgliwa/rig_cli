from __future__ import annotations

import json
import logging

import typer
from rich.table import Table

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
def status(
    config: str = _CONFIG_OPTION,
    output_format: str = _FORMAT_OPTION,
    verbose: int = _VERBOSE_OPTION,
):
    """Show current rig state."""
    setup_logging(verbose)
    logger.info("Showing status for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if output_format == "json":
        info = {
            "name": rig.name,
            "pedals": {
                pid: {"type": p.type.value, "midi_channel": p.config.midi_channel}
                for pid, p in rig.pedals.items()
            },
            "scenes": list(rig.scenes.keys()),
        }
        _emit_json(json.dumps(info, indent=2))
        return

    table = Table(title=f"Rig: {rig.name}")
    table.add_column("Pedal", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("MIDI Ch")
    table.add_column("Presets")
    for pid, pedal in rig.pedals.items():
        preset_count = (
            len(rig.digital_presets.get(pid, []))
            + len(rig.analog_presets.get(pid, []))
            + len(rig.hx_presets.get(pid, []))
        )
        table.add_row(
            pid,
            pedal.type.value,
            str(pedal.config.midi_channel or "-"),
            str(preset_count),
        )
    console.print(table)
