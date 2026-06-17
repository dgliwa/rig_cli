from __future__ import annotations

import logging
from typing import Literal

from rich.console import Console

from rig.config.errors import ConfigError
from rig.midi.adapter import MidiManager

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
        if midi_channel is None:
            console.print(f"[dim]→ Set {device} manually (knobs/switches)[/dim]")
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
