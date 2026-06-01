"""Interactive prompting for ingesting manual (non-MIDI) pedals.

Usage::

    rig ingest manual
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

from rig.models.pedal import ManualConfig, PedalDefinition, PedalType

console = Console()

__all__ = ["ingest_manual_pedal"]


def _prompt_controls() -> list[dict]:
    """Prompt the user for one or more physical controls on the pedal."""
    controls: list[dict] = []
    while True:
        console.print("\n[bold]Add a control[/bold]")
        name = Prompt.ask("  Control name", default="")
        if not name:
            if not controls:
                console.print("[yellow]At least one control is required.[/yellow]")
                continue
            break

        control_type = Prompt.ask(
            "  Type",
            choices=["knob", "switch", "toggle", "dipswitch"],
            default="knob",
        )
        control: dict[str] = {"name": name, "type": control_type}

        if control_type == "knob":
            min_val = IntPrompt.ask("  Min value", default=0)
            max_val = IntPrompt.ask("  Max value", default=10)
            control["min"] = min_val
            control["max"] = max_val
            current_raw = Prompt.ask(f"  Current value ({min_val}-{max_val})", default="")
            if current_raw:
                control["value"] = int(current_raw)
        else:
            positions_raw = Prompt.ask("  Positions (comma-separated, e.g. on,off)")
            if positions_raw:
                control["positions"] = [p.strip() for p in positions_raw.split(",")]
            current_raw = Prompt.ask("  Current position", default="")
            if current_raw:
                control["value"] = current_raw

        midi_cc_raw = Prompt.ask("  MIDI CC (optional, press Enter to skip)", default="")
        if midi_cc_raw:
            control["midi_cc"] = int(midi_cc_raw)

        expr = Confirm.ask("  Expression assignable?", default=False)
        control["expression_assignable"] = expr

        controls.append(control)

        if not Confirm.ask("\nAdd another control?", default=True):
            break

    return controls


def ingest_manual_pedal(config_dir: Path) -> PedalDefinition | None:
    """Interactively prompt for a manual pedal definition and write its YAML.

    Returns the parsed ``PedalDefinition`` if successful, or ``None`` if the
    user aborts at the confirmation step.
    """
    console.print("[bold]Manual Pedal Ingest[/bold]\n")

    pedal_id = Prompt.ask("  Pedal ID (e.g. 'tumnus')")
    manufacturer = Prompt.ask("  Manufacturer")
    model = Prompt.ask("  Model")
    pedal_type = Prompt.ask(
        "  Pedal type",
        choices=[t.value for t in PedalType],
        default="analog",
    )
    notes = Prompt.ask("  Notes (optional)", default="")
    image = Prompt.ask("  Image filename (optional)", default="")

    console.print("\n[bold]Controls[/bold] — describe the knobs, switches, and toggles.")
    controls = _prompt_controls()

    config = ManualConfig(controls=controls)

    pedal = PedalDefinition(
        id=pedal_id,
        manufacturer=manufacturer,
        model=model,
        type=PedalType(pedal_type),
        config=config,
        notes=notes or None,
        image=image or None,
    )

    pedal_dir = config_dir / "pedals"
    pedal_dir.mkdir(parents=True, exist_ok=True)
    dest = pedal_dir / f"{pedal_id}.yaml"

    if dest.exists():
        console.print(f"[yellow]{dest} already exists.[/yellow]")
        if not Confirm.ask("Overwrite?", default=False):
            console.print("[red]Aborted.[/red]")
            return None

    import yaml

    dest.write_text(yaml.dump(pedal.model_dump(), default_flow_style=False, sort_keys=False))

    console.print(f"\n[green]Wrote {dest}[/green]")
    return pedal
