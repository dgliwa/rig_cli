from __future__ import annotations

import logging
from typing import Literal

from rich.console import Console

from rig.config.errors import ConfigError
from rig.engine.plan import Plan
from rig.engine.state import read_state, write_state
from rig.midi.adapter import MidiManager
from rig.models.rig import RigConfig

logger = logging.getLogger(__name__)
console = Console()

_ConfirmResult = Literal["confirm", "retry", "skip", "quit"]


def _prompt_device(
    device: str,
    preset_name: str,
    preset_number: int | None,
    midi_channel: int | None,
    midi_connected: bool = False,
) -> _ConfirmResult:
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


def _prompt_cba_channel(device: str, midi_channel: int, midi_sent: bool = False) -> _ConfirmResult:
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
        label = "done — channel saved" if midi_sent else "ready — send PC on ch {midi_channel}"
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


def _prompt_cba_build_preset(
    device: str, preset_name: str, preset_number: int | None, midi_channel: int
) -> _ConfirmResult:
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


def _prompt_cba_register(device: str, scene_refs: list[str]) -> _ConfirmResult:
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


def _merge_device_state(state: dict, device: str, **fields) -> dict:
    """Update device state fields without clobbering existing values."""
    entry = state.setdefault("devices", {}).setdefault(device, {})
    entry.update(fields)
    return state


def _prompt_midi_connect(
    device: str,
    midi_channel: int,
    midi: MidiManager,
    device_port: str | None,
) -> tuple[_ConfirmResult, str | None]:
    """Prompt the user to pick a MIDI output port for *device*.

    Returns (result, port_name_or_None).
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


def _collect_midi_devices(plan: Plan, rig: RigConfig) -> set[str]:
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


def apply_plan(
    plan: Plan,
    rig: RigConfig | None = None,
    config_path: str | None = None,
    dry_run: bool = False,
    scene: str | None = None,
    midi: MidiManager | None = None,
):
    if plan.status == "clean":
        logger.info("No changes needed — state matches config")
        console.print("[green]✓[/green] No changes needed. State matches config.")
        return

    logger.debug("Reading current state")
    state = {}
    if config_path:
        state = read_state(config_path)
    state_modified = False

    # --- Phase -1: MIDI connection per unique device ---
    midi_devices = _collect_midi_devices(plan, rig) if midi else set()
    connected_devices: set[str] = set()

    if midi_devices and not dry_run:
        logger.info("MIDI connection phase: %d device(s)", len(midi_devices))
        console.print("\n[bold]MIDI Connection Phase[/bold]")

    for device_id in sorted(midi_devices):
        if device_id in connected_devices:
            continue
        if midi.is_connected(device_id):
            connected_devices.add(device_id)
            continue

        # Look up pedal info
        pedal = rig.pedals.get(device_id) if rig else None
        ch = (pedal.config.midi_channel or 1) if pedal else 1
        cached_port = state.get("devices", {}).get(device_id, {}).get("midi_port")

        if dry_run:
            console.print(
                f"  [cyan]🔌[/cyan] {device_id}: connect MIDI (ch {ch})[dim] (dry-run)[/dim]"
            )
            connected_devices.add(device_id)
            continue

        result, port_name = _prompt_midi_connect(device_id, ch, midi, cached_port)
        if result == "quit":
            console.print("[red]Apply cancelled by user[/red]")
            return
        if result == "confirm" and port_name:
            _merge_device_state(state, device_id, midi_port=port_name)
            state_modified = True
            connected_devices.add(device_id)
        # If skipped → device not in connected_devices, falls back to manual prompts

    # --- Phase 0: CBA device setup ---
    if plan.cba_setup:
        logger.info("CBA setup phase: %d action(s)", len(plan.cba_setup))
        console.print("\n[bold]Chase Bliss Setup Phase[/bold]")

    for action in plan.cba_setup:
        if action.type == "establish_channel":
            if dry_run:
                logger.debug(
                    "Dry-run: CB establish channel %d on %s", action.midi_channel, action.device
                )
                console.print(
                    f"  [cyan]🔧[/cyan] {action.device}: establish MIDI channel {action.midi_channel}[dim] (dry-run)[/dim]"
                )
                continue

            midi_sent = action.device in connected_devices
            if midi_sent:
                try:
                    midi.send_program_change(action.device, 0, action.midi_channel)
                    logger.info("Sent PC#0 on ch %d to %s", action.midi_channel, action.device)
                except Exception as e:
                    logger.error("Failed to send to %s: %s", action.device, e)
                    console.print(f"  [red]✗[/red] MIDI send failed: {e}")
                    midi_sent = False

            result = _prompt_cba_channel(action.device, action.midi_channel, midi_sent=midi_sent)
            if result == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                return
            if result == "confirm":
                _merge_device_state(
                    state, action.device, channel_established=True, midi_channel=action.midi_channel
                )
                state_modified = True

        elif action.type == "build_preset":
            if dry_run:
                logger.debug(
                    "Dry-run: CB build preset '%s' on %s", action.preset_name, action.device
                )
                console.print(
                    f"  [cyan]🔧[/cyan] {action.device}: build preset #{action.preset_number} '{action.preset_name}'[dim] (dry-run)[/dim]"
                )
                continue

            if action.device in connected_devices and action.preset_number is not None:
                try:
                    midi.send_program_change(
                        action.device, action.preset_number, action.midi_channel
                    )
                    logger.info(
                        "Sent PC#%d on ch %d to %s",
                        action.preset_number,
                        action.midi_channel,
                        action.device,
                    )
                except Exception as e:
                    logger.error("Failed to send to %s: %s", action.device, e)
                    console.print(f"  [red]✗[/red] MIDI send failed: {e}")

            result = _prompt_cba_build_preset(
                action.device, action.preset_name, action.preset_number, action.midi_channel
            )
            if result == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                return
            if result == "confirm":
                _merge_device_state(state, action.device, last_preset=action.preset_name)
                state.setdefault("devices", {}).setdefault(action.device, {}).setdefault(
                    "presets_saved", {}
                )[action.preset_id] = True
                state_modified = True

        elif action.type == "register_scenes":
            if dry_run:
                logger.debug("Dry-run: CB register %s scenes", action.device)
                console.print(
                    f"  [cyan]🔧[/cyan] {action.device}: register presets to scenes[dim] (dry-run)[/dim]"
                )
                continue
            result = _prompt_cba_register(action.device, action.scene_refs)
            if result == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                return
            if result == "confirm":
                _merge_device_state(state, action.device, registration_done=True)
                state_modified = True

    # --- Phase 1: Scene apply ---
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
                    logger.debug(
                        "Dry-run: would prompt analog '%s' → '%s'",
                        action.device,
                        action.preset_name,
                    )
                    console.print(
                        f"  [yellow]⚠[/yellow] {action.device}: would prompt to set '{action.preset_name}'"
                    )
                    continue
                result = _prompt_analog(action.device, action.preset_name)
                if result == "quit":
                    console.print("[red]Apply cancelled by user[/red]")
                    return
                if result == "confirm":
                    _merge_device_state(state, action.device, last_preset=action.preset_name)
                    state_modified = True
                continue

            if dry_run:
                pc_info = f" PC#{action.preset_number}" if action.preset_number else ""
                ch_info = f" (ch {action.midi_channel})" if action.midi_channel else ""
                logger.debug(
                    "Dry-run: %s%s '%s'%s", action.device, pc_info, action.preset_name, ch_info
                )
                console.print(
                    f"  [cyan]→[/cyan] {action.device}{pc_info} '{action.preset_name}'[dim] (dry-run)[/dim]"
                )
                continue

            midi_connected = action.device in connected_devices

            # Send via MIDI when connected
            if (
                midi_connected
                and action.preset_number is not None
                and action.midi_channel is not None
            ):
                try:
                    midi.send_program_change(
                        action.device, action.preset_number, action.midi_channel
                    )
                    logger.info(
                        "Sent PC#%d on ch %d to %s",
                        action.preset_number,
                        action.midi_channel,
                        action.device,
                    )
                except Exception as e:
                    logger.error("Failed to send to %s: %s", action.device, e)
                    console.print(f"  [red]✗[/red] MIDI send failed: {e}")
                    midi_connected = False

            while True:
                result = _prompt_device(
                    action.device,
                    action.preset_name,
                    action.preset_number,
                    action.midi_channel,
                    midi_connected=midi_connected,
                )
                if result == "confirm":
                    logger.info(
                        "Device '%s' configured to preset '%s'", action.device, action.preset_name
                    )
                    console.print(
                        f"  [green]✓[/green] {action.device}: '{action.preset_name}' configured"
                    )
                    _merge_device_state(state, action.device, last_preset=action.preset_name)
                    state_modified = True
                    break
                if result == "retry":
                    # Re-send on retry when MIDI is connected
                    if (
                        midi_connected
                        and action.preset_number is not None
                        and action.midi_channel is not None
                    ):
                        try:
                            midi.send_program_change(
                                action.device, action.preset_number, action.midi_channel
                            )
                        except Exception:
                            pass
                    continue
                if result == "skip":
                    logger.warning("Device '%s' skipped by user", action.device)
                    console.print(f"  [yellow]⚠[/yellow] {action.device}: skipped")
                    break
                if result == "quit":
                    console.print("[red]Apply cancelled by user[/red]")
                    return

        state.setdefault("scenes", {})[sp.scene_name] = {}
        state_modified = True

    if config_path and not dry_run and state_modified:
        logger.info("Saving state to .rig/state.json")
        write_state(config_path, state)
        console.print("[green]✓[/green] State saved to .rig/state.json")
