"""rig edit command — interactive preset editor."""

from __future__ import annotations

from pathlib import Path

import typer

from rig.cli._shared import _CONFIG_OPTION, _VERBOSE_OPTION, app, console
from rig.config.errors import ConfigError
from rig.config.loader import load_rig
from rig.config.yaml_writer import write_preset
from rig.engine.plugin import EditContext, EditorProtocol
from rig.engine.ports import RichConfirmationIO
from rig.log_setup import setup_logging


@app.command()
def edit(
    device_id: str = typer.Argument(..., help="Device ID to edit"),
    preset_id: str = typer.Argument(..., help="Preset ID to edit"),
    config: str = _CONFIG_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change"),
    verbose: int = _VERBOSE_OPTION,
) -> None:
    """Edit a preset interactively and write back to rig.yaml."""
    setup_logging(verbose)

    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if device_id not in rig.devices:
        console.print(f"[red]✗[/red] Device '{device_id}' not found in rig config")
        raise typer.Exit(1)

    device = rig.devices[device_id]

    if not any(p.id == preset_id for p in device.presets):
        console.print(f"[red]✗[/red] Preset '{preset_id}' not found on device '{device_id}'")
        raise typer.Exit(1)

    if not isinstance(device, EditorProtocol):
        console.print(f"Device '{device_id}' does not support editing.")
        return

    ctx = EditContext(
        config_path=Path(config) / "rig.yaml",
        dry_run=dry_run,
        confirmation_io=RichConfirmationIO(),
        rig=rig,
    )

    updated_values = device.edit(preset_id, ctx)

    response = ctx.confirmation_io.prompt("Save changes? [y/N] ")
    if response.lower() in ("y", "yes"):
        write_preset(ctx.config_path, device_id, preset_id, updated_values, dry_run=dry_run)
        console.print("[green]✓[/green] Preset saved.")
    else:
        console.print("Changes discarded.")
