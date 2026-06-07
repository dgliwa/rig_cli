from __future__ import annotations

from typing import Literal

from rich.console import Console

console = Console()

_ConfirmResult = Literal["confirm", "retry", "skip", "quit"]


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
