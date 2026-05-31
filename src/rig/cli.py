from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from rig.config.loader import load_rig
from rig.config.errors import ConfigError
from rig.engine.plan import compute_plan
from rig.engine.apply import apply_plan
from rig.generators.mc6_presets import generate_mc6, write_mc6_config

app = typer.Typer(name="rig")
console = Console()

_CONFIG_OPTION = typer.Option(
    ".", "--config", "-c", help="Path to the rig config directory",
)
_SCENE_OPTION = typer.Option(
    None, "--scene", "-s", help="Plan a single scene",
)


@app.command()
def validate(config: str = _CONFIG_OPTION):
    """Validate the rig configuration."""
    try:
        rig = load_rig(config)
        console.print(f"[green]✓[/green] {rig.name} — {len(rig.pedals)} pedals, {len(rig.scenes)} scenes")
        console.print("[green]✓[/green] All cross-references valid")
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


@app.command()
def plan(config: str = _CONFIG_OPTION, scene: str | None = _SCENE_OPTION):
    """Preview changes needed to reach desired state."""
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    plan = compute_plan(rig, root_path=Path(config).resolve() if config else None)

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

    if not scene_names:
        console.print("[yellow]No scenes found[/yellow]")

    unknown = config and Path(config).exists()
    if unknown:
        console.print(f"\n[dim]State source: .rig/state.json[/dim]")


@app.command()
def apply(config: str = _CONFIG_OPTION, dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"), scene: str | None = _SCENE_OPTION):
    """Apply changes — walks through each device with MIDI prompts."""
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    config_path = str(Path(config).resolve())
    plan = compute_plan(rig, root_path=config_path)
    apply_plan(plan, config_path=config_path, dry_run=dry_run, scene=scene)


@app.command()
def status(config: str = _CONFIG_OPTION):
    """Show current rig state."""
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

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
def diff(config: str = _CONFIG_OPTION):
    """Show differences between config versions."""
    typer.echo("diff: not yet implemented")


gen_app = typer.Typer(help="Generate artifacts from config")
app.add_typer(gen_app, name="generate")


@gen_app.command()
def mc6(config: str = _CONFIG_OPTION):
    """Generate MC6 bank configs from scene definitions."""
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
