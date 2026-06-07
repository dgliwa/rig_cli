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
from rig.engine.plan import Plan
from rig.engine.plugin import DeviceApplyContext, SetupContext
from rig.engine.ports import ConfirmationIO, MidiConnectionIO, RichConfirmationIO, StateWriter
from rig.engine.state import DeviceState, RigState
from rig.interaction.midi import collect_midi_devices
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
    plan: Plan | None = None,
    *,
    state_writer: StateWriter,
    midi_connection_io: MidiConnectionIO,
    confirmation_io: ConfirmationIO | None = None,
    rig: Rig | None = None,
    config_path: str | None = None,
    dry_run: bool = False,
    scene: str | None = None,
    midi: MidiManager | None = None,
) -> ApplyResult:
    if plan is None:
        if rig is None:
            raise ValueError("apply_plan requires either a pre-computed plan or a rig instance")
        from rig.engine.plan import compute_plan

        plan = compute_plan(rig, root_path=config_path)
    if plan.status == "clean":
        logger.info("No changes needed — state matches config")
        console.print("[green]✓[/green] No changes needed. State matches config.")
        return ApplyResult(status="no_changes")

    logger.debug("Reading current state")
    state = RigState()
    if config_path:
        state = state_writer.read(config_path)

    ctx = ApplyContext(
        dry_run=dry_run,
        confirmation_io=confirmation_io or RichConfirmationIO(),
        midi=midi,
        state=state,
        config_path=config_path,
        rig=rig,
    )

    state_modified = False
    cba_results: list[DeviceApplyResult] = []
    scene_results: list[SceneApplyResult] = []

    # --- Phase -2: Device setup (each device manages its own MIDI connection + one-time init) ---
    # Devices that have been migrated to their own packages implement real setup() here.
    # Devices still in core return no-op SetupResult(). Phase -1 below handles legacy MIDI
    # connections for devices whose setup() is still a no-op.
    if rig:
        setup_ctx = SetupContext(
            state=state,
            rig=rig,
            dry_run=dry_run,
            confirmation_io=confirmation_io or RichConfirmationIO(),
            midi=midi,
            midi_connection_io=midi_connection_io,
            config_path=config_path,
        )
        for _device_id, device in rig.devices.items():
            if hasattr(device, "setup"):
                result = device.setup(setup_ctx)
                if result.cancelled:
                    console.print("[red]Apply cancelled by user[/red]")
                    return ApplyResult(
                        status="cancelled", cba_setup=cba_results, scenes=scene_results
                    )
                if result.state_modified:
                    state_modified = True

    # TODO: We probably should identify the controller first
    # For devices that can be configured via controller (CBA) that would be useful
    # For devices that need direct connection (HX), we should maybe make that more obvious in the configuration or the "apply" implementation

    # --- Phase -1: MIDI connection per unique device ---
    midi_devices = collect_midi_devices(plan) if midi else set()

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

        res, port_name = midi_connection_io.prompt_connect(device_id, ch, midi, cached_port)
        if res == "quit":
            console.print("[red]Apply cancelled by user[/red]")
            return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)
        if res == "confirm" and port_name:
            update_device_state(state, device_id, midi_port=port_name)
            state_modified = True
            ctx.connected_devices.add(device_id)
        # If skipped → device not in connected_devices, falls back to manual prompts

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
            device = rig.devices.get(action.device) if rig else None

            if device is None or not hasattr(device, "apply"):
                logger.warning(
                    "Device '%s' not found or missing apply() — skipping action", action.device
                )
                action_result = DeviceApplyResult(
                    device=action.device, status="skipped", preset=action.preset_name
                )
            else:
                device_ctx = DeviceApplyContext(
                    action=action,
                    state=ctx.state,
                    rig=rig,
                    dry_run=ctx.dry_run,
                    confirmation_io=ctx.confirmation_io,
                    midi=ctx.midi,
                    connected_devices=ctx.connected_devices,
                    config_path=ctx.config_path,
                )
                action_result = device.apply(device_ctx)

            if action_result.error == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                cancelled = True
                break

            if action_result.status == "confirmed":
                state_modified = True

            device_results.append(action_result)

        if cancelled:
            return ApplyResult(status="cancelled", cba_setup=cba_results, scenes=scene_results)

        if any(r.status == "confirmed" for r in device_results):
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
        mc6_device = rig.controller
        mc6_banks = mc6_device.config.banks if hasattr(mc6_device.config, "banks") else []
        if mc6_banks and midi and hasattr(mc6_device, "apply"):
            console.print("\n[bold]MC6 Programming Phase[/bold]")
            from rig.engine.plan.models import DeviceAction

            mc6_action = DeviceAction(
                device=mc6_device.id,
                device_type="controller",
                status="configure",
                preset_name="",
            )
            mc6_ctx = DeviceApplyContext(
                action=mc6_action,
                state=ctx.state,
                rig=rig,
                dry_run=ctx.dry_run,
                confirmation_io=ctx.confirmation_io,
                midi=ctx.midi,
                connected_devices=ctx.connected_devices,
                config_path=ctx.config_path,
            )
            mc6_device.apply(mc6_ctx)
            if state.devices.get("mc6"):
                state_modified = True

    if config_path and not dry_run and state_modified:
        logger.info("Saving state to .rig/state.json")
        state_writer.write(config_path, state)
        console.print("[green]✓[/green] State saved to .rig/state.json")

    return ApplyResult(status="completed", cba_setup=cba_results, scenes=scene_results)
