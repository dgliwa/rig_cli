from __future__ import annotations

from typing import Literal

from rich.console import Console

console = Console()

_ConfirmResult = Literal["confirm", "retry", "skip", "quit"]


def prompt_cba_channel(device: str, midi_channel: int, midi_sent: bool = False) -> _ConfirmResult:
    """Guide user through CBA power-on MIDI channel learn process."""
    console.print(f"\n[bold]Chase Bliss Setup — {device}[/bold]")
    console.print()
    if midi_sent:
        console.print(f"[green]✓[/green] PC#0 sent on channel {midi_channel}")
        console.print("Now quickly hold BOTH footswitches to save the channel assignment")
    else:
        console.print("Establish MIDI Channel (one-time):")
        console.print("  1. Disconnect power from the pedal")
        console.print("  2. Hold BOTH footswitches")
        console.print("  3. While holding, reconnect power (pedal enters learn mode)")
        console.print(f"  4. I will send PC#0 on channel {midi_channel} to lock the channel")
    while True:
        label = "done — channel saved" if midi_sent else f"ready — send PC on ch {midi_channel}"
        response = input(f"  [c] {label}  [r] show again  [s] skip  [q] quit: ").strip().lower()
        if response in ("c", "confirm", "done"):
            console.print(f"  [green]✓[/green] {device}: channel {midi_channel} established")
            return "confirm"
        if response in ("r", "retry"):
            return "retry"
        if response in ("s", "skip"):
            console.print(f"  [yellow]⚠[/yellow] {device}: channel setup skipped")
            return "skip"
        if response in ("q", "quit"):
            return "quit"
        console.print("[yellow]Invalid choice. Enter c, r, s, or q[/yellow]")


def prompt_cba_build_preset(
    device: str, preset_name: str, preset_number: int | None, midi_channel: int
) -> _ConfirmResult:
    """Guide user through saving a preset on a CBA pedal (hold footswitches)."""
    pc_info = f"PC#{preset_number}" if preset_number is not None else "preset"
    console.print(f"\n[bold]Chase Bliss Preset Build — {device}[/bold]")
    console.print()
    console.print(f"Parameters sent for '{preset_name}' on channel {midi_channel}.")
    console.print()
    console.print("Hold BOTH footswitches to enter save mode, then confirm below.")
    console.print(f"[dim]On confirm, {pc_info} will be sent to write to that slot.[/dim]")
    while True:
        response = (
            input("  [c] done — preset saved  [r] retry  [s] skip  [q] quit: ").strip().lower()
        )
        if response in ("c", "done"):
            console.print(f"  [green]✓[/green] {device}: '{preset_name}' saved")
            return "confirm"
        if response in ("r", "retry"):
            return "retry"
        if response in ("s", "skip"):
            console.print(f"  [yellow]⚠[/yellow] {device}: preset '{preset_name}' skipped")
            return "skip"
        if response in ("q", "quit"):
            return "quit"
        console.print("[yellow]Invalid choice. Enter c, r, s, or q[/yellow]")


def prompt_cba_register(device: str, scene_refs: list[str]) -> _ConfirmResult:
    """Confirm that CBA presets have been built for all referencing scenes."""
    console.print(f"\n[bold]Chase Bliss Scene Registration — {device}[/bold]")
    console.print()
    console.print("The following scenes reference this pedal:")
    for ref in scene_refs:
        console.print(f"  • {ref}")
    console.print()
    console.print("Presets are built on the device. Confirm registration?")
    while True:
        response = input("  [c] confirm  [s] skip  [q] quit: ").strip().lower()
        if response in ("c", "confirm"):
            console.print(f"  [green]✓[/green] {device}: registered to {len(scene_refs)} scene(s)")
            return "confirm"
        if response in ("s", "skip"):
            console.print(f"  [yellow]⚠[/yellow] {device}: registration skipped")
            return "skip"
        if response in ("q", "quit"):
            return "quit"
        console.print("[yellow]Invalid choice. Enter c, s, or q[/yellow]")
