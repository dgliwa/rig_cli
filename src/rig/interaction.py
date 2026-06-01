"""User-facing prompts and interaction helpers for rig apply.

These functions handle all ``input()`` and ``console.print()`` calls
so that ``rig.engine.apply`` can focus on orchestration logic.
"""

from __future__ import annotations

import logging
from typing import Literal

from rich.console import Console

from rig.config.errors import ConfigError
from rig.engine.plan import Plan
from rig.midi.adapter import MidiManager
from rig.models.rig import RigConfig

logger = logging.getLogger(__name__)
console = Console()

_ConfirmResult = Literal["confirm", "retry", "skip", "quit"]


def prompt_device(
    device: str,
    preset_name: str,
    preset_number: int | None,
    midi_channel: int | None,
    midi_connected: bool = False,
) -> _ConfirmResult:
    """Ask user to confirm/retry/skip/quit a device configuration step."""
    pc_info = f" PC#{preset_number}" if preset_number else ""
    ch_info = f" (ch {midi_channel})" if midi_channel else ""
    console.print(f"\n[bold]Step:[/bold] {device}{pc_info} '{preset_name}'{ch_info}")
    if midi_connected:
        console.print(f"[green]✓[/green] Sent via MIDI — did {device} respond?")
    else:
        console.print(f"[dim]→ Connect MIDI to {device}[/dim]")
    while True:
        response = input("  [c] confirm  [r] retry  [s] skip  [q] quit: ").strip().lower()
        if response in ("c", "confirm"):
            return "confirm"
        if response in ("r", "retry"):
            return "retry"
        if response in ("s", "skip"):
            return "skip"
        if response in ("q", "quit"):
            return "quit"
        console.print("[yellow]Invalid choice. Enter c, r, s, or q[/yellow]")


def prompt_analog(device: str, preset_name: str) -> _ConfirmResult:
    """Ask user to confirm/retry/skip/quit an analog pedal adjustment."""
    console.print(f"\n[bold]Analog:[/bold] {device} → set to '{preset_name}'")
    console.print("[yellow]  ⚠ Adjust knobs/switches manually[/yellow]")
    while True:
        response = input("  [c] done  [s] skip  [q] quit: ").strip().lower()
        if response in ("c", "done"):
            return "confirm"
        if response in ("s", "skip"):
            return "skip"
        if response in ("q", "quit"):
            return "quit"
        console.print("[yellow]Invalid choice. Enter c, s, or q[/yellow]")


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
    pc_info = f" PC#{preset_number}" if preset_number else ""
    console.print(f"\n[bold]Chase Bliss Preset Build — {device}[/bold]")
    console.print()
    console.print(f"Sent {pc_info} on channel {midi_channel} — '{preset_name}' loaded")
    console.print()
    console.print("Now hold BOTH footswitches to save as preset")
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


def prompt_midi_connect(
    device: str,
    midi_channel: int,
    midi: MidiManager,
    device_port: str | None,
) -> tuple[_ConfirmResult, str | None]:
    """Let user pick a MIDI output port for *device*.

    Returns ``(result, port_name_or_None)``.
    """
    # If a port name is cached in state and still available, reconnect silently.
    if device_port and device_port in midi.list_output_ports():
        try:
            midi.connect(device_port, device)
            logger.info("Reconnected '%s' to cached port '%s'", device, device_port)
            return ("confirm", device_port)
        except Exception:
            logger.warning("Cached port '%s' for '%s' failed to reopen", device_port, device)

    console.print(f"\n[bold]MIDI Connection — {device}[/bold]")
    console.print(
        f"Plug MIDI cable connected to [cyan]{device}[/cyan] (MIDI channel {midi_channel})"
    )

    while True:
        ports = midi.list_output_ports()
        if not ports:
            console.print("\n[yellow]No MIDI output ports detected.[/yellow]")
            console.print("Make sure your MIDI interface is connected.")
            response = input("  [r] refresh  [s] skip  [q] quit: ").strip().lower()
            if response in ("r", "refresh"):
                continue
            if response in ("s", "skip"):
                return ("skip", None)
            if response in ("q", "quit"):
                return ("quit", None)
            console.print("[yellow]Enter r, s, or q[/yellow]")
            continue

        console.print("\nAvailable MIDI outputs:")
        for i, name in enumerate(ports, 1):
            marker = " (cached)" if name == device_port else ""
            console.print(f"  {i}. {name}{marker}")

        prompt = f"Select port (1-{len(ports)}) or [s]kip [q]uit: "
        response = input(f"  {prompt}").strip().lower()

        if response in ("s", "skip"):
            return ("skip", None)
        if response in ("q", "quit"):
            return ("quit", None)

        try:
            idx = int(response) - 1
            if idx < 0 or idx >= len(ports):
                console.print(f"[yellow]Enter a number between 1 and {len(ports)}[/yellow]")
                continue
            port_name = ports[idx]
            midi.connect(port_name, device)
            console.print(f"  [green]✓[/green] Connected to '{port_name}'")
            return ("confirm", port_name)
        except ValueError:
            console.print("[yellow]Enter a number, s, or q[/yellow]")
        except (ConfigError, Exception) as e:
            console.print(f"[red]✗[/red] Could not open '{ports[idx]}': {e}")
            console.print("Try a different port or check the connection.")
            continue


def collect_midi_devices(plan: Plan, rig: RigConfig) -> set[str]:
    """Return the set of device IDs that need MIDI connections."""
    devices: set[str] = set()
    for sp in plan.scenes.values():
        for action in sp.device_actions:
            if (
                action.device_type in ("digital", "modeler", "controller")
                and action.status == "configure"
            ):
                if action.midi_channel is not None:
                    devices.add(action.device)
    for action in plan.cba_setup:
        if action.type in ("establish_channel", "build_preset"):
            devices.add(action.device)
    return devices
