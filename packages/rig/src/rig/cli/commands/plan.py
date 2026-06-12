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
from rig.models.device import DeviceType

logger = logging.getLogger(__name__)

_SHOW_UNCHANGED_OPTION = typer.Option(
    False,
    "--show-unchanged",
    help="Include unchanged scenes in output",
)


@app.command()
def plan(
    config: str = _CONFIG_OPTION,
    scene: str | None = _SCENE_OPTION,
    output_format: str = _FORMAT_OPTION,
    verbose: int = _VERBOSE_OPTION,
    show_unchanged: bool = _SHOW_UNCHANGED_OPTION,
):
    """Preview changes needed to reach desired state."""
    setup_logging(verbose)
    logger.info("Planning changes for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    config_path = Path(config).resolve()
    state_path = config_path / ".rig" / "state.json"
    cold_start = not state_path.exists()

    try:
        result = compute_plan(rig, root_path=str(config_path))
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if output_format == "json":
        _emit_json(result.model_dump_json(indent=2))
        return

    if cold_start:
        console.print(
            "[yellow]⚠ Cold start — no state file found. Treating all scenes as new.[/yellow]"
        )

    # --- Scenes section ---
    scene_names = [scene] if scene else list(result.scenes.keys())

    if scene_names:
        console.print("\n[bold]Scenes:[/bold]")

    configure_count = 0
    manual_count = 0
    already_set_count = 0

    for name in scene_names:
        sp = result.scenes.get(name)
        # TODO: scene plans should have their own logging output class
        if sp is None:
            console.print(f"[yellow]Scene '{name}' not found[/yellow]")
            continue

        if sp.status == "unchanged" and not show_unchanged:
            continue

        if sp.status == "new":
            status_icon = "[cyan]+[/cyan]"
        elif sp.status == "changed":
            status_icon = "[yellow]~[/yellow]"
        else:
            status_icon = "[green]✓[/green]"

        console.print(f"\n  {status_icon} [bold]{sp.scene_name}[/bold] ({sp.status})")

        for action in sp.device_actions:
            if action.device_type == DeviceType.ANALOG:
                manual_count += 1
                console.print(
                    f"    [yellow]⚠[/yellow] {action.device}: set to '{action.preset_name}' (manual)"
                )
            elif action.status == "configure":
                configure_count += 1
                pc_info = f" PC#{action.preset_number}" if action.preset_number else ""
                ch_info = f" (ch {action.midi_channel})" if action.midi_channel else ""
                console.print(
                    f"    [cyan]~[/cyan] {action.device}:{pc_info} '{action.preset_name}'{ch_info}"
                )
            elif action.status == "verify":
                already_set_count += 1
                console.print(
                    f"    [green]✓[/green] {action.device}: '{action.preset_name}' (already set)"
                )

    if not scene_names:
        console.print("[yellow]No scenes found[/yellow]")

    # --- Warnings section ---
    if result.missing_refs:
        console.print("\n[bold red]Warnings — Missing References:[/bold red]")
        for ref in result.missing_refs:
            console.print(f"  [red]✗[/red] {ref}")

    if result.unused_presets:
        console.print("\n[bold yellow]Warnings — Unused Presets:[/bold yellow]")
        for preset in result.unused_presets:
            console.print(f"  [yellow]⚠[/yellow] {preset}")

    # --- Summary line ---
    if result.status == "clean" and not result.missing_refs:
        console.print(
            f"\n[green]Plan: No changes — {already_set_count} already set, {manual_count} manual[/green]"
        )
    else:
        console.print(
            f"\n[yellow]Plan: {configure_count} to configure, {manual_count} manual, {already_set_count} already set[/yellow]"
        )

    if result.status == "changes_detected" or result.missing_refs:
        raise typer.Exit(2)
