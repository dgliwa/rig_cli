from __future__ import annotations

import logging
from pathlib import Path

import typer

from rig.cli._shared import (
    _CONFIG_OPTION,
    _FORMAT_OPTION,
    _SCENE_OPTION,
    _VERBOSE_OPTION,
    _emit_json,
    app,
    console,
)
from rig.config.errors import ConfigError
from rig.config.loader import load_rig
from rig.engine.plan import compute_plan
from rig.log_setup import setup_logging

logger = logging.getLogger(__name__)


@app.command()
def plan(
    config: str = _CONFIG_OPTION,
    scene: str | None = _SCENE_OPTION,
    output_format: str = _FORMAT_OPTION,
    verbose: int = _VERBOSE_OPTION,
):
    """Preview changes needed to reach desired state."""
    setup_logging(verbose)
    logger.info("Planning changes for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    result = compute_plan(rig, root_path=Path(config).resolve() if config else None)

    if output_format == "json":
        _emit_json(result.model_dump_json(indent=2))
        return

    scene_names = [scene] if scene else result.scenes.keys()

    for name in scene_names:
        sp = result.scenes.get(name)
        if sp is None:
            console.print(f"[yellow]Scene '{name}' not found[/yellow]")
            continue

        status_icon = {"new": "[cyan]+   ", "changed": "[yellow]~   ", "unchanged": "[green]    "}[
            sp.status
        ]
        console.print(f"\n{status_icon}[bold]{sp.scene_name}[/bold] ({sp.status})")

        for action in sp.device_actions:
            if action.device_type == "analog":
                console.print(
                    f"  [yellow]⚠[/yellow] {action.device}: set to '{action.preset_name}' (manual)"
                )
            elif action.status == "configure":
                pc_info = f" PC#{action.preset_number}" if action.preset_number else ""
                ch_info = f" (ch {action.midi_channel})" if action.midi_channel else ""
                console.print(
                    f"  [cyan]→[/cyan] {action.device}:{pc_info} '{action.preset_name}'{ch_info}"
                )
            elif action.status == "verify":
                console.print(
                    f"  [green]✓[/green] {action.device}: '{action.preset_name}' (already set)"
                )

    if result.cba_setup:
        console.print("\n[bold]CBA Setup Required:[/bold]")
        for action in result.cba_setup:
            if action.type == "establish_channel":
                console.print(
                    f"  [cyan]🔧[/cyan] {action.device}: establish MIDI channel {action.midi_channel}"
                )
            elif action.type == "build_preset":
                console.print(
                    f"  [cyan]🔧[/cyan] {action.device}: build preset #{action.preset_number} '{action.preset_name}'"
                )
            elif action.type == "register_scenes":
                console.print(f"  [cyan]🔧[/cyan] {action.device}: register presets to scenes")

    if not scene_names:
        console.print("[yellow]No scenes found[/yellow]")

    config_exists = config and Path(config).exists()
    if config_exists:
        console.print("\n[dim]State source: .rig/state.json[/dim]")
