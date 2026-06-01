from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from rig.config.loader import load_rig
from rig.config.errors import ConfigError
from rig.engine.plan import compute_plan
from rig.engine.apply import apply_plan
from rig.engine.diff import compute_diff, format_diff
from rig.generators.mc6_presets import generate_mc6, write_mc6_config
from rig.ingest.hx_stomp import ingest_hx_file
from rig.ingest.mc6_config import ingest_mc6_config
from rig.ingest.scene import create_scene, add_device_to_scene, set_device_in_scene, IngestError
from rig.log_setup import setup_logging

logger = logging.getLogger(__name__)

app = typer.Typer(name="rig")
console = Console()

_CONFIG_OPTION = typer.Option(
    ".", "--config", "-c", help="Path to the rig config directory",
)
_FORMAT_OPTION = typer.Option(
    "text", "--format", "-f", help="Output format: text or json",
)
_SCENE_OPTION = typer.Option(
    None, "--scene", "-s", help="Plan a single scene",
)
_VERBOSE_OPTION = typer.Option(
    0, "--verbose", "-v", count=True,
    help="Increase verbosity: -v INFO, -vv DEBUG",
)


@app.command()
def validate(config: str = _CONFIG_OPTION, format: str = _FORMAT_OPTION, verbose: int = _VERBOSE_OPTION):
    """Validate the rig configuration."""
    setup_logging(verbose)
    logger.info("Validating config at: %s", config)
    try:
        rig = load_rig(config)
        if format == "json":
            import json
            console.print(json.dumps({"status": "valid", "pedals": len(rig.pedals), "scenes": len(rig.scenes)}, indent=2))
        else:
            console.print(f"[green]✓[/green] {rig.name} — {len(rig.pedals)} pedals, {len(rig.scenes)} scenes")
            console.print("[green]✓[/green] All cross-references valid")
    except ConfigError as e:
        if format == "json":
            import json
            console.print(json.dumps({"status": "error", "error": str(e)}))
        else:
            console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


@app.command()
def plan(config: str = _CONFIG_OPTION, scene: str | None = _SCENE_OPTION, format: str = _FORMAT_OPTION, verbose: int = _VERBOSE_OPTION):
    """Preview changes needed to reach desired state."""
    setup_logging(verbose)
    logger.info("Planning changes for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    plan = compute_plan(rig, root_path=Path(config).resolve() if config else None)

    if format == "json":
        import json
        console.print(plan.model_dump_json(indent=2))
        return

    scene_names = [scene] if scene else plan.scenes.keys()

    for name in scene_names:
        sp = plan.scenes.get(name)
        if sp is None:
            console.print(f"[yellow]Scene '{name}' not found[/yellow]")
            continue

        status_icon = {"new": "[cyan]+   ", "changed": "[yellow]~   ", "unchanged": "[green]    "}[sp.status]
        console.print(f"\n{status_icon}[bold]{sp.scene_name}[/bold] ({sp.status})")

        for action in sp.device_actions:
            if action.device_type == "analog":
                console.print(f"  [yellow]⚠[/yellow] {action.device}: set to '{action.preset_name}' (manual)")
            elif action.status == "configure":
                pc_info = f" PC#{action.preset_number}" if action.preset_number else ""
                ch_info = f" (ch {action.midi_channel})" if action.midi_channel else ""
                console.print(f"  [cyan]→[/cyan] {action.device}:{pc_info} '{action.preset_name}'{ch_info}")
                for bd in action.block_diffs:
                    if bd.status == "added":
                        console.print(f"    [green]+[/green] block: {bd.name}")
            elif action.status == "verify":
                console.print(f"  [green]✓[/green] {action.device}: '{action.preset_name}' (already set)")

    if plan.cba_setup:
        console.print("\n[bold]CBA Setup Required:[/bold]")
        for action in plan.cba_setup:
            if action.type == "establish_channel":
                console.print(f"  [cyan]🔧[/cyan] {action.device}: establish MIDI channel {action.midi_channel}")
            elif action.type == "build_preset":
                console.print(f"  [cyan]🔧[/cyan] {action.device}: build preset #{action.preset_number} '{action.preset_name}'")
            elif action.type == "register_scenes":
                console.print(f"  [cyan]🔧[/cyan] {action.device}: register presets to scenes")

    if not scene_names:
        console.print("[yellow]No scenes found[/yellow]")

    unknown = config and Path(config).exists()
    if unknown:
        console.print(f"\n[dim]State source: .rig/state.json[/dim]")


@app.command()
def apply(config: str = _CONFIG_OPTION, dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"), scene: str | None = _SCENE_OPTION, verbose: int = _VERBOSE_OPTION):
    """Apply changes — walks through each device with MIDI prompts."""
    setup_logging(verbose)
    logger.info("Applying plan for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    config_path = str(Path(config).resolve())
    plan = compute_plan(rig, root_path=config_path)
    apply_plan(plan, rig=rig, config_path=config_path, dry_run=dry_run, scene=scene)


@app.command()
def status(config: str = _CONFIG_OPTION, format: str = _FORMAT_OPTION, verbose: int = _VERBOSE_OPTION):
    """Show current rig state."""
    setup_logging(verbose)
    logger.info("Showing status for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if format == "json":
        import json
        info = {
            "name": rig.name,
            "pedals": {pid: {"type": p.type.value, "midi_channel": p.midi_channel} for pid, p in rig.pedals.items()},
            "scenes": list(rig.scenes.keys()),
        }
        console.print(json.dumps(info, indent=2))
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
            str(pedal.midi_channel or "-"),
            str(preset_count),
        )
    console.print(table)


@app.command()
def diff(config: str = _CONFIG_OPTION, format: str = _FORMAT_OPTION, verbose: int = _VERBOSE_OPTION):
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
    if format == "json":
        import json
        console.print(json.dumps(changes, indent=2))
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




in_app = typer.Typer(help="Import presets from other formats")
app.add_typer(in_app, name="ingest")


@in_app.command()
def hx(path: str = typer.Argument(..., help="Path to .hlx file"),
      output: str = typer.Option(".", "--output", "-o", help="Output directory"),
      verbose: int = _VERBOSE_OPTION):
    """Ingest HX Stomp .hlx preset files."""
    setup_logging(verbose)
    logger.info("Ingesting HX file: %s", path)
    try:
        presets = ingest_hx_file(path)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if not presets:
        console.print("[yellow]No presets found in file[/yellow]")
        return

    out_dir = Path(output) / "pedals" / "hx-stomp" / "presets"
    out_dir.mkdir(parents=True, exist_ok=True)

    import yaml
    for preset in presets:
        preset_path = out_dir / f"{preset['id']}.yaml"
        with open(preset_path, "w") as f:
            yaml.dump(preset, f, default_flow_style=False, sort_keys=False)
        console.print(f"  [green]✓[/green] {preset_path}")

    console.print(f"[green]Ingested {len(presets)} preset(s)")


@in_app.command()
def mc6(path: str = typer.Argument(..., help="Path to MC6 JSON config"),
        output: str = typer.Option(".", "--output", "-o", help="Output directory"),
        verbose: int = _VERBOSE_OPTION):
    """Ingest Morningstar MC6 config as scene definitions."""
    setup_logging(verbose)
    logger.info("Ingesting MC6 config: %s", path)
    try:
        scenes = ingest_mc6_config(path)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    if not scenes:
        console.print("[yellow]No scenes found in config[/yellow]")
        return

    out_dir = Path(output) / "scenes"
    out_dir.mkdir(parents=True, exist_ok=True)

    import yaml
    for scene in scenes:
        scene_path = out_dir / f"{scene['name']}.yaml"
        with open(scene_path, "w") as f:
            yaml.dump(scene, f, default_flow_style=False, sort_keys=False)
        console.print(f"  [green]✓[/green] {scene_path}")

    console.print(f"[green]Ingested {len(scenes)} scene(s)")


scene_app = typer.Typer(help="Manage scene definitions (create/add/set)")
in_app.add_typer(scene_app, name="scene")


@scene_app.command()
def create(
    name: str = typer.Argument(..., help="Scene name"),
    device: str = typer.Option(..., "--device", "-d", help="Pedal ID"),
    preset: str = typer.Option(..., "--preset", "-p", help="Preset ID"),
    description: str = typer.Option(None, "--description", help="Scene description"),
    config: str = _CONFIG_OPTION,
):
    """Create a new scene with a single device-preset mapping."""
    try:
        path = create_scene(config, name, device, preset, description)
        console.print(f"[green]✓[/green] Created scene {path}")
    except IngestError as e:
        console.print(f"[red]✗[/red] {e.message}")
        raise typer.Exit(1)


@scene_app.command()
def add(
    name: str = typer.Argument(..., help="Scene name"),
    device: str = typer.Option(..., "--device", "-d", help="Pedal ID"),
    preset: str = typer.Option(..., "--preset", "-p", help="Preset ID"),
    config: str = _CONFIG_OPTION,
):
    """Add a device-preset mapping to an existing scene."""
    try:
        path = add_device_to_scene(config, name, device, preset)
        console.print(f"[green]✓[/green] Updated scene {path}")
    except IngestError as e:
        console.print(f"[red]✗[/red] {e.message}")
        raise typer.Exit(1)


@scene_app.command(name="set")
def set_(
    name: str = typer.Argument(..., help="Scene name"),
    device: str = typer.Option(..., "--device", "-d", help="Pedal ID"),
    preset: str = typer.Option(..., "--preset", "-p", help="Preset ID"),
    config: str = _CONFIG_OPTION,
):
    """Overwrite a device's preset in an existing scene."""
    try:
        path = set_device_in_scene(config, name, device, preset)
        console.print(f"[green]✓[/green] Updated scene {path}")
    except IngestError as e:
        console.print(f"[red]✗[/red] {e.message}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
