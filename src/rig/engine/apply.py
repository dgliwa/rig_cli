from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel
from rich.console import Console

from rig.engine.plan import Plan, _detect_cba_setup
from rig.engine.state import DeviceState, RigState, read_state, write_state
from rig.interaction import (
    collect_midi_devices,
    prompt_analog,
    prompt_cba_build_preset,
    prompt_cba_channel,
    prompt_cba_register,
    prompt_device,
    prompt_midi_connect,
)
from rig.midi.adapter import MidiManager
from rig.midi.mc6 import SWITCH_INDEX, clear_preset_messages, update_preset_name, update_preset_pc
from rig.models.rig import Rig

logger = logging.getLogger(__name__)
console = Console()


class DeviceApplyResult(BaseModel):
    """Result of applying one device action."""

    device: str
    status: Literal["confirmed", "skipped", "error"]
    preset: str | None = None
    error: str | None = None


class SceneApplyResult(BaseModel):
    """Result of applying one scene."""

    scene: str
    status: Literal["new", "changed", "unchanged"]
    devices: list[DeviceApplyResult] = []


class ApplyResult(BaseModel):
    """Overall result of an apply run."""

    status: Literal["completed", "cancelled", "no_changes"]
    cba_setup: list[DeviceApplyResult] = []
    scenes: list[SceneApplyResult] = []


def _update_device_state(state: RigState, device: str, **fields) -> None:
    """Update a device's state fields in-place."""
    current = state.devices.get(device, DeviceState())
    state.devices[device] = current.model_copy(update=fields)


def apply_plan(
    plan: Plan,
    rig: Rig | None = None,
    config_path: str | None = None,
    dry_run: bool = False,
    scene: str | None = None,
    midi: MidiManager | None = None,
) -> ApplyResult:
    if plan.status == "clean":
        logger.info("No changes needed — state matches config")
        console.print("[green]✓[/green] No changes needed. State matches config.")
        return ApplyResult(status="no_changes")

    logger.debug("Reading current state")
    state = RigState()
    if config_path:
        state = read_state(config_path)
    state_modified = False

    cba_results: list[DeviceApplyResult] = []
    scene_results: list[SceneApplyResult] = []

    # --- Phase -1: MIDI connection per unique device ---
    midi_devices = collect_midi_devices(plan, rig) if midi else set()
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
        cached_port = state.devices.get(device_id, DeviceState()).midi_port

        if dry_run:
            console.print(
                f"  [cyan]🔌[/cyan] {device_id}: connect MIDI (ch {ch})[dim] (dry-run)[/dim]"
            )
            connected_devices.add(device_id)
            continue

        res, port_name = prompt_midi_connect(device_id, ch, midi, cached_port)
        if res == "quit":
            console.print("[red]Apply cancelled by user[/red]")
            return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)
        if res == "confirm" and port_name:
            _update_device_state(state, device_id, midi_port=port_name)
            state_modified = True
            connected_devices.add(device_id)
        # If skipped → device not in connected_devices, falls back to manual prompts

    # --- Phase 0: CBA device setup ---
    if plan.cba_setup:
        logger.info("CBA setup phase: %d action(s)", len(plan.cba_setup))
        console.print("\n[bold]Chase Bliss Setup Phase[/bold]")

    cba_pending = list(plan.cba_setup)
    cba_seen: set[tuple] = set()

    def _enqueue_new_cba_actions() -> None:
        if rig is None:
            return
        for a in _detect_cba_setup(rig, state):
            key = (a.device, a.type, a.preset_id)
            if key not in cba_seen:
                cba_pending.append(a)

    while cba_pending:
        action = cba_pending.pop(0)
        action_key = (action.device, action.type, action.preset_id)
        if action_key in cba_seen:
            continue
        cba_seen.add(action_key)

        if action.type == "establish_channel":
            if dry_run:
                logger.debug(
                    "Dry-run: CB establish channel %d on %s", action.midi_channel, action.device
                )
                console.print(
                    f"  [cyan]🔧[/cyan] {action.device}: establish MIDI channel {action.midi_channel}[dim] (dry-run)[/dim]"
                )
                continue

            # Step 1: guide user to power-cycle + hold footswitches to enter learn mode
            while True:
                res = prompt_cba_channel(action.device, action.midi_channel, midi_sent=False)
                if res != "retry":
                    break
            if res == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)
            if res == "skip":
                cba_results.append(
                    DeviceApplyResult(device=action.device, status="skipped", preset=None)
                )
                continue

            # Step 2: pedal is in learn mode — send PC#0 to lock the channel
            midi_sent = False
            if action.device in connected_devices:
                try:
                    midi.send_program_change(action.device, 0, action.midi_channel)
                    logger.info("Sent PC#0 on ch %d to %s", action.midi_channel, action.device)
                    midi_sent = True
                except Exception as e:
                    logger.error("Failed to send to %s: %s", action.device, e)
                    console.print(f"  [red]✗[/red] MIDI send failed: {e}")

            if midi_sent:
                # Step 3: pedal received PC#0 — prompt user to hold footswitches to save
                while True:
                    res = prompt_cba_channel(action.device, action.midi_channel, midi_sent=True)
                    if res == "retry":
                        try:
                            midi.send_program_change(action.device, 0, action.midi_channel)
                        except Exception as e:
                            console.print(f"  [red]✗[/red] MIDI resend failed: {e}")
                    else:
                        break
                if res == "quit":
                    console.print("[red]Apply cancelled by user[/red]")
                    return ApplyResult(
                        status="cancelled", cba_setup=cba_results, scenes=scene_results
                    )

            if res == "confirm":
                _update_device_state(
                    state, action.device, channel_established=True, midi_channel=action.midi_channel
                )
                state_modified = True
                _enqueue_new_cba_actions()
            cba_results.append(
                DeviceApplyResult(
                    device=action.device,
                    status="confirmed" if res == "confirm" else "skipped",
                    preset=None,
                )
            )

        elif action.type == "build_preset":
            if dry_run:
                logger.debug(
                    "Dry-run: CB build preset '%s' on %s", action.preset_name, action.device
                )
                cc_count = len(action.cc_params)
                console.print(
                    f"  [cyan]🔧[/cyan] {action.device}: build preset #{action.preset_number} '{action.preset_name}' ({cc_count} CC params)[dim] (dry-run)[/dim]"
                )
                continue

            def _send_ccs() -> int:
                sent = 0
                if action.device in connected_devices and action.cc_params:
                    for param in action.cc_params:
                        try:
                            midi.send_control_change(
                                action.device, param["cc"], param["value"], action.midi_channel
                            )
                            sent += 1
                        except Exception as e:
                            logger.error("Failed CC %d on %s: %s", param["cc"], action.device, e)
                            console.print(f"  [red]✗[/red] CC send failed (CC {param['cc']}): {e}")
                return sent

            cc_sent = _send_ccs()
            if cc_sent:
                logger.info("Sent %d CC params to %s", cc_sent, action.device)
                console.print(
                    f"  [green]✓[/green] {cc_sent}/{len(action.cc_params)} CC params sent"
                )

            while True:
                res = prompt_cba_build_preset(
                    action.device, action.preset_name, action.preset_number, action.midi_channel
                )
                if res == "retry":
                    cc_sent = _send_ccs()
                    if cc_sent:
                        console.print(f"  [green]✓[/green] Resent {cc_sent} CC params")
                    continue
                break

            if res == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)
            if res == "confirm":
                if action.device in connected_devices and action.preset_number is not None:
                    try:
                        midi.send_program_change(
                            action.device, action.preset_number, action.midi_channel
                        )
                        logger.info(
                            "Sent PC#%d on ch %d to %s to save preset",
                            action.preset_number,
                            action.midi_channel,
                            action.device,
                        )
                    except Exception as e:
                        logger.error("Failed PC send to %s: %s", action.device, e)
                        console.print(f"  [red]✗[/red] PC send failed: {e}")
                _update_device_state(state, action.device, last_preset=action.preset_name)
                ds = state.devices.get(action.device, DeviceState())
                ps = dict(ds.presets_saved)
                ps[action.preset_id] = True
                state.devices[action.device] = ds.model_copy(update={"presets_saved": ps})
                state_modified = True
                _enqueue_new_cba_actions()

        elif action.type == "register_scenes":
            if dry_run:
                logger.debug("Dry-run: CB register %s scenes", action.device)
                console.print(
                    f"  [cyan]🔧[/cyan] {action.device}: register presets to scenes[dim] (dry-run)[/dim]"
                )
                continue
            res = prompt_cba_register(action.device, action.scene_refs)
            if res == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)
            if res == "confirm":
                _update_device_state(state, action.device, registration_done=True)
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
                res = prompt_analog(action.device, action.preset_name)
                if res == "quit":
                    console.print("[red]Apply cancelled by user[/red]")
                    return ApplyResult(
                        status="cancelled", cba_setup=cba_results, scenes=scene_results
                    )
                if res == "confirm":
                    _update_device_state(state, action.device, last_preset=action.preset_name)
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
                result = prompt_device(
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
                    _update_device_state(state, action.device, last_preset=action.preset_name)
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
                    return ApplyResult(
                        status="cancelled", cba_setup=cba_results, scenes=scene_results
                    )

        state.scenes[sp.scene_name] = {}
        state_modified = True

    # --- Phase 2: MC6 programming ---
    mc6_banks = (rig.mc6.get("banks", []) if rig else []) if not scene else []
    if mc6_banks and midi:
        console.print("\n[bold]MC6 Programming Phase[/bold]")
        mc6_port = state.devices.get("mc6", DeviceState()).midi_port

        if dry_run:
            for bank in mc6_banks:
                for switch_label, switch_data in bank.get("switches", {}).items():
                    scene_name = switch_data.get("scene", "")
                    console.print(
                        f"  [cyan]🎛[/cyan] Bank {bank['bank']} / {switch_label}: '{scene_name}'[dim] (dry-run)[/dim]"
                    )
        else:
            res, port_name = prompt_midi_connect("mc6", 1, midi, mc6_port)
            if res == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)

            if res == "confirm" and port_name:
                _update_device_state(state, "mc6", midi_port=port_name)
                state_modified = True

                for bank in mc6_banks:
                    bank_num = bank["bank"]
                    console.print(
                        f"\n  Navigate the MC6 to [bold]Bank {bank_num}[/bold], then press Enter..."
                    )
                    input()

                    for switch_label, switch_data in bank.get("switches", {}).items():
                        scene_name = switch_data.get("scene", "")
                        preset_idx = SWITCH_INDEX.get(switch_label)
                        if preset_idx is None:
                            logger.warning("Unknown MC6 switch label '%s'", switch_label)
                            continue

                        try:
                            for msg in clear_preset_messages(preset_idx):
                                midi.send_sysex("mc6", msg)
                            midi.send_sysex("mc6", update_preset_name(preset_idx, scene_name))

                            scene_obj = rig.scenes.get(scene_name) if rig else None
                            if scene_obj:
                                msg_slot = 0
                                for pedal_id, preset_id in scene_obj.presets.items():
                                    pedal = rig.pedals.get(pedal_id)
                                    if pedal is None or pedal.config.midi_channel is None:
                                        continue
                                    pc = pedal.get_scene_pc_command(preset_id, rig)
                                    if pc:
                                        midi.send_sysex(
                                            "mc6",
                                            update_preset_pc(
                                                preset_idx,
                                                msg_slot,
                                                pc["value"],
                                                pc["channel"],
                                            ),
                                        )
                                        msg_slot += 1

                            console.print(
                                f"  [green]✓[/green] Switch {switch_label}: '{scene_name}' programmed"
                            )
                        except Exception as e:
                            logger.error("MC6 SysEx failed for switch %s: %s", switch_label, e)
                            console.print(f"  [red]✗[/red] Switch {switch_label}: {e}")

    if config_path and not dry_run and state_modified:
        logger.info("Saving state to .rig/state.json")
        write_state(config_path, state)
        console.print("[green]✓[/green] State saved to .rig/state.json")

    return ApplyResult(status="completed", cba_setup=cba_results, scenes=scene_results)
