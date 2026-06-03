from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel
from rich.console import Console

from rig.engine.appliers.base import (
    ApplyContext,
    DeviceApplyResult,
    update_device_state,
)
from rig.engine.appliers.registry import get_cba_applier, get_mc6_applier, get_scene_applier
from rig.engine.plan import Plan
from rig.engine.state import DeviceState, RigState, read_state, write_state
from rig.interaction import collect_midi_devices, prompt_midi_connect
from rig.midi.adapter import MidiManager
from rig.models.rig import Rig

logger = logging.getLogger(__name__)
console = Console()


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
    update_device_state(state, device, **fields)


# TODO: i think this is too big a function
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

    ctx = ApplyContext(
        dry_run=dry_run,
        midi=midi,
        state=state,
        config_path=config_path,
        rig=rig,
    )

    state_modified = False
    cba_results: list[DeviceApplyResult] = []
    scene_results: list[SceneApplyResult] = []

    # TODO: We probably should identify the controller first
    # For devices that can be configured via controller (CBA) that would be useful
    # For devices that need direct connection (HX), we should maybe make that more obvious in the configuration or the "apply" implementation

    # --- Phase -1: MIDI connection per unique device ---
    midi_devices = collect_midi_devices(plan, rig) if midi else set()

    if midi_devices and not dry_run:
        logger.info("MIDI connection phase: %d device(s)", len(midi_devices))
        console.print("\n[bold]MIDI Connection Phase[/bold]")

    for device_id in sorted(midi_devices):
        if device_id in ctx.connected_devices:
            continue
        if midi.is_connected(device_id):
            ctx.connected_devices.add(device_id)
            continue

        pedal = rig.pedals.get(device_id) if rig else None
        ch = (pedal.config.midi_channel or 1) if pedal else 1
        cached_port = state.devices.get(device_id, DeviceState()).midi_port

        if dry_run:
            console.print(
                f"  [cyan]🔌[/cyan] {device_id}: connect MIDI (ch {ch})[dim] (dry-run)[/dim]"
            )
            ctx.connected_devices.add(device_id)
            continue

        res, port_name = prompt_midi_connect(device_id, ch, midi, cached_port)
        if res == "quit":
            console.print("[red]Apply cancelled by user[/red]")
            return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)
        if res == "confirm" and port_name:
            update_device_state(state, device_id, midi_port=port_name)
            state_modified = True
            ctx.connected_devices.add(device_id)
        # If skipped → device not in connected_devices, falls back to manual prompts

    # --- Phase 0: CBA device setup ---
    # TODO: again, don't like this being on the plan - should be specific on the device plan & apply?
    if plan.cba_setup:
        logger.info("CBA setup phase: %d action(s)", len(plan.cba_setup))
        console.print("\n[bold]Chase Bliss Setup Phase[/bold]")

    cba_setup_result = get_cba_applier().apply_setup(plan.cba_setup, ctx)
    if cba_setup_result is None:
        # User cancelled during CBA setup
        return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)
    cba_results = cba_setup_result
    if any(r.status == "confirmed" for r in cba_results):
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

        device_results: list[DeviceApplyResult] = []
        cancelled = False

        for action in sp.device_actions:
            if action.status == "no_change":
                continue

            device = rig.devices.get(action.device) if rig else None
            config_type = device.config.type if device else "midi"

            applier = get_scene_applier(config_type)
            action_result = applier.apply_scene(action, ctx)

            if action_result.error == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                cancelled = True
                break

            if action_result.status == "confirmed":
                state_modified = True

            device_results.append(action_result)

        if cancelled:
            return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)

        state.scenes[sp.scene_name] = {}
        state_modified = True

        scene_results.append(
            SceneApplyResult(
                scene=sp.scene_name,
                status=sp.status,
                devices=device_results,
            )
        )

    # --- Phase 2: MC6 programming ---
    if rig and rig.controller and not scene:
        mc6_banks = rig.controller.config.banks
        if mc6_banks and midi:
            console.print("\n[bold]MC6 Programming Phase[/bold]")
            get_mc6_applier().apply_banks(mc6_banks, ctx)
            if state.devices.get("mc6"):
                state_modified = True

    if config_path and not dry_run and state_modified:
        logger.info("Saving state to .rig/state.json")
        write_state(config_path, state)
        console.print("[green]✓[/green] State saved to .rig/state.json")

    return ApplyResult(status="completed", cba_setup=cba_results, scenes=scene_results)
