from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from rig.config.errors import ConfigError
from rig.config.loader import load_rig
from rig.engine.apply import apply_plan
from rig.engine.diff import compute_diff, format_diff
from rig.engine.plan import compute_plan
from rig.generators.mc6_presets import generate_mc6, write_mc6_config
from rig.log_setup import setup_logging
from rig.midi.adapter import MidiManager


# JSON output helper — uses raw sys.stdout to bypass Rich wrapping.
def _emit_json(data: str) -> None:
    sys.stdout.write(data + "\n")
    sys.stdout.flush()


logger = logging.getLogger(__name__)

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

    plan = compute_plan(rig, root_path=Path(config).resolve() if config else None)

    if output_format == "json":
        _emit_json(plan.model_dump_json(indent=2))
        return

    scene_names = [scene] if scene else plan.scenes.keys()

    for name in scene_names:
        sp = plan.scenes.get(name)
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

    if plan.cba_setup:
        console.print("\n[bold]CBA Setup Required:[/bold]")
        for action in plan.cba_setup:
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


@app.command()
def apply(
    config: str = _CONFIG_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    scene: str | None = _SCENE_OPTION,
    verbose: int = _VERBOSE_OPTION,
):
    """Apply changes — walks through each device with MIDI prompts."""
    setup_logging(verbose)
    logger.info("Applying plan for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    midi = MidiManager()
    config_path = str(Path(config).resolve())
    plan = compute_plan(rig, root_path=config_path)
    try:
        apply_plan(plan, rig=rig, config_path=config_path, dry_run=dry_run, scene=scene, midi=midi)
    finally:
        midi.disconnect_all()


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


gen_app = typer.Typer(help="Generate artifacts from config")
app.add_typer(gen_app, name="generate")


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

    data = generate_mc6(rig)
    if not data:
        console.print("[yellow]No MC6 configuration found (mc6.yaml missing or empty)[/yellow]")
        return

    out_dir = write_mc6_config(data, output_path=str(Path(config).resolve() / "generated" / "mc6"))
    console.print(f"[green]✓[/green] MC6 config written to {out_dir}")


if __name__ == "__main__":
    app()
