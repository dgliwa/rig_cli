from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from rig.config.loader import load_rig
from rig.config.errors import ConfigError

app = typer.Typer(name="rig")
console = Console()

_CONFIG_OPTION = typer.Option(
    ".", "--config", "-c", help="Path to the rig config directory",
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
def plan(config: str = _CONFIG_OPTION):
    """Preview changes needed to reach desired state."""
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    console.print(f"[bold]Rig:[/bold] {rig.name}")
    console.print(f"[bold]Scenes:[/bold] {', '.join(rig.scenes.keys())}")
    console.print("[yellow]plan: full diff engine coming in next feature[/yellow]")


@app.command()
def apply(config: str = _CONFIG_OPTION):
    """Apply changes to reach desired state."""
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)
    console.print(f"[bold]Rig:[/bold] {rig.name}")
    console.print("[yellow]apply: interactive sequencer coming in next feature[/yellow]")


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


if __name__ == "__main__":
    app()
