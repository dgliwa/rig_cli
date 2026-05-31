from __future__ import annotations
import logging
from typing import Literal

from rich.console import Console

from rig.engine.plan import Plan
from rig.engine.state import read_state, write_state
from rig.config.errors import ConfigError


logger = logging.getLogger(__name__)
console = Console()

_ConfirmResult = Literal["confirm", "retry", "skip", "quit"]


def _prompt_device(device: str, preset_name: str, preset_number: int | None, midi_channel: int | None) -> _ConfirmResult:
    pc_info = f" PC#{preset_number}" if preset_number else ""
    ch_info = f" (ch {midi_channel})" if midi_channel else ""
    console.print(f"\n[bold]Step:[/bold] {device}{pc_info} '{preset_name}'{ch_info}")
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


def _prompt_analog(device: str, preset_name: str) -> _ConfirmResult:
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


def apply_plan(plan: Plan, config_path: str | None = None, dry_run: bool = False, scene: str | None = None):
    if plan.status == "clean":
        logger.info("No changes needed — state matches config")
        console.print("[green]✓[/green] No changes needed. State matches config.")
        return

    logger.debug("Reading current state")
    state = {}
    if config_path:
        state = read_state(config_path)

    scene_names = [scene] if scene else list(plan.scenes.keys())
    logger.info("Applying plan with %d scene(s)", len(scene_names))

    for name in scene_names:
        sp = plan.scenes.get(name)
        if sp is None:
            logger.warning("Scene '%s' not found in plan", name)
            console.print(f"[yellow]Scene '{name}' not found[/yellow]")
            continue
        if sp.status == "unchanged":
            logger.debug("Scene '%s': no changes needed", name)
            console.print(f"[green]  ✓[/green] {sp.scene_name}: no changes needed")
            continue

        logger.info("Applying scene '%s' (status: %s)", sp.scene_name, sp.status)
        console.print(f"\n[bold]Scene: {sp.scene_name}[/bold] ({sp.status})")

        for action in sp.device_actions:
            if action.status == "no_change":
                continue

            if action.device_type == "analog":
                if dry_run:
                    logger.debug("Dry-run: would prompt analog '%s' → '%s'", action.device, action.preset_name)
                    console.print(f"  [yellow]⚠[/yellow] {action.device}: would prompt to set '{action.preset_name}'")
                    continue
                result = _prompt_analog(action.device, action.preset_name)
                if result == "quit":
                    console.print("[red]Apply cancelled by user[/red]")
                    return
                if result == "confirm":
                    state.setdefault("devices", {})[action.device] = {"last_preset": action.preset_name}
                continue

            if dry_run:
                pc_info = f" PC#{action.preset_number}" if action.preset_number else ""
                ch_info = f" (ch {action.midi_channel})" if action.midi_channel else ""
                logger.debug("Dry-run: %s%s '%s'%s", action.device, pc_info, action.preset_name, ch_info)
                console.print(f"  [cyan]→[/cyan] {action.device}{pc_info} '{action.preset_name}'[dim] (dry-run)[/dim]")
                continue

            while True:
                result = _prompt_device(action.device, action.preset_name, action.preset_number, action.midi_channel)
                if result == "confirm":
                    logger.info("Device '%s' configured to preset '%s'", action.device, action.preset_name)
                    console.print(f"  [green]✓[/green] {action.device}: '{action.preset_name}' configured")
                    state.setdefault("devices", {})[action.device] = {"last_preset": action.preset_name}
                    break
                if result == "retry":
                    continue
                if result == "skip":
                    logger.warning("Device '%s' skipped by user", action.device)
                    console.print(f"  [yellow]⚠[/yellow] {action.device}: skipped")
                    break
                if result == "quit":
                    console.print("[red]Apply cancelled by user[/red]")
                    return

        state.setdefault("scenes", {})[sp.scene_name] = {}

    if config_path and not dry_run:
        logger.info("Saving state to .rig/state.json")
        write_state(config_path, state)
        console.print(f"[green]✓[/green] State saved to .rig/state.json")
