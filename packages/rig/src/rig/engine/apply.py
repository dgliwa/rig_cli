from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel
from rich.console import Console

from rig.engine.appliers.base import (
    ApplyContext,
    DeviceApplyResult,
)
from rig.engine.plan import Plan
from rig.engine.plugin import DeviceApplyContext, SetupContext
from rig.engine.ports import ConfirmationIO, RichConfirmationIO, StateWriter
from rig.engine.state import RigState
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
    scenes: list[SceneApplyResult] = []


def apply_plan(
    plan: Plan | None = None,
    *,
    state_writer: StateWriter,
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

    connected_devices: set[str] = set()

    ctx = ApplyContext(
        dry_run=dry_run,
        confirmation_io=confirmation_io or RichConfirmationIO(),
        midi=midi,
        state=state,
        config_path=config_path,
        rig=rig,
        connected_devices=connected_devices,
    )

    state_modified = False
    scene_results: list[SceneApplyResult] = []

    # --- Phase: Device setup (each device manages its own MIDI connection + one-time init) ---
    # Every device plugin that needs MIDI handles its own port connection in setup().
    # Devices that don't need MIDI (analog) return a no-op SetupResult().
    if rig:
        setup_ctx = SetupContext(
            state=state,
            rig=rig,
            dry_run=dry_run,
            confirmation_io=confirmation_io or RichConfirmationIO(),
            midi=midi,
            config_path=config_path,
            connected_devices=connected_devices,
        )
        for _device_id, device in rig.devices.items():
            if hasattr(device, "setup"):
                result = device.setup(setup_ctx)
                if result.cancelled:
                    console.print("[red]Apply cancelled by user[/red]")
                    return ApplyResult(status="cancelled", scenes=scene_results)
                if result.state_modified:
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
            return ApplyResult(status="cancelled", scenes=scene_results)

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

    # --- Phase 2: Controller programming ---
    if rig and rig.controller and not scene:
        controller = rig.controller
        if hasattr(controller, "apply") and midi:
            console.print("\n[bold]Controller Programming Phase[/bold]")
            from rig.engine.plan.models import DeviceAction

            controller_action = DeviceAction(
                device=controller.id,
                device_type="controller",
                status="configure",
                preset_name="",
            )
            controller_ctx = DeviceApplyContext(
                action=controller_action,
                state=ctx.state,
                rig=rig,
                dry_run=ctx.dry_run,
                confirmation_io=ctx.confirmation_io,
                midi=ctx.midi,
                connected_devices=ctx.connected_devices,
                config_path=ctx.config_path,
            )
            controller.apply(controller_ctx)
            if controller.id in state.devices:
                state_modified = True

    if config_path and not dry_run and state_modified:
        logger.info("Saving state to .rig/state.json")
        state_writer.write(config_path, state)
        console.print("[green]✓[/green] State saved to .rig/state.json")

    return ApplyResult(status="completed", scenes=scene_results)
