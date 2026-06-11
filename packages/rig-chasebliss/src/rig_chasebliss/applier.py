from __future__ import annotations

import logging

from rich.console import Console

from rig.engine.appliers.base import (
    ApplyContext,
    DeviceApplyResult,
    mark_preset_saved,
    update_device_state,
)
from rig_chasebliss.catalog import get_controls
from rig_chasebliss.interaction import (
    prompt_cba_after_pc,
    prompt_cba_build_preset,
    prompt_cba_channel,
    prompt_cba_register,
)
from rig_chasebliss.models import CbaSetupAction

logger = logging.getLogger(__name__)
console = Console()


def _find_device(rig, device_id: str):
    """Find a device by ID in the rig, or return None."""
    if rig is None:
        return None
    return next((d for d in rig.devices.values() if d.id == device_id), None)


class ChaseBlissApplier:
    def apply_setup(
        self,
        actions: list[CbaSetupAction],
        ctx: ApplyContext,
    ) -> list[DeviceApplyResult] | None:
        """Run the 3-phase CBA setup: establish_channel → build_preset → register_scenes.

        Returns None if the user cancelled, or the list of results on completion.
        """
        results: list[DeviceApplyResult] = []
        pending = list(actions)
        seen: set[tuple] = set()

        while pending:
            action = pending.pop(0)
            action_key = (action.device, action.type, action.preset_id)
            if action_key in seen:
                continue
            seen.add(action_key)

            if action.type == "establish_channel":
                result = self._establish_channel(action, ctx)
                if result is None:
                    return None
                results.append(result)

            elif action.type == "build_preset":
                result = self._build_preset(action, ctx)
                if result is None:
                    return None
                results.append(result)

            elif action.type == "register_scenes":
                result = self._register_scenes(action, ctx)
                if result is None:
                    return None
                results.append(result)

        return results

    def _establish_channel(
        self, action: CbaSetupAction, ctx: ApplyContext
    ) -> DeviceApplyResult | None:
        """Phase 1: power-cycle + hold footswitches to enter learn mode, then send PC#0."""
        if ctx.dry_run:
            logger.debug(
                "Dry-run: CB establish channel %d on %s",
                action.midi_channel,
                action.device,
            )
            console.print(
                f"  [cyan]→[/cyan] {action.device}: establish MIDI channel "
                f"{action.midi_channel}[dim] (dry-run)[/dim]"
            )
            return DeviceApplyResult(device=action.device, status="skipped", preset=None)

        # Step 1: guide user to power-cycle + enter learn mode
        while True:
            res = prompt_cba_channel(action.device, action.midi_channel, False)
            if res != "retry":
                break
        if res == "quit":
            console.print("[red]Apply cancelled by user[/red]")
            return None
        if res == "skip":
            return DeviceApplyResult(device=action.device, status="skipped", preset=None)

        # Step 2: send PC#0 to lock the channel
        midi_sent = False
        if action.device in ctx.connected_devices and ctx.midi is not None:
            try:
                ctx.midi.send_program_change(action.device, 0, action.midi_channel)
                logger.info("Sent PC#0 on ch %d to %s", action.midi_channel, action.device)
                midi_sent = True
            except Exception as e:
                logger.error("Failed to send to %s: %s", action.device, e)
                console.print(f"  [red]✗[/red] MIDI send failed: {e}")

        if midi_sent:
            # Step 3: prompt user to hold footswitches to save
            while True:
                res = prompt_cba_channel(action.device, action.midi_channel, True)
                if res == "retry":
                    try:
                        ctx.midi.send_program_change(action.device, 0, action.midi_channel)
                    except Exception as e:
                        console.print(f"  [red]✗[/red] MIDI resend failed: {e}")
                else:
                    break
            if res == "quit":
                console.print("[red]Apply cancelled by user[/red]")
                return None

        if res == "confirm" and midi_sent:
            update_device_state(
                ctx.state,
                action.device,
                channel_established=True,
                midi_channel=action.midi_channel,
            )
        return DeviceApplyResult(
            device=action.device,
            status="confirmed" if (res == "confirm" and midi_sent) else "skipped",
            preset=None,
        )

    def _build_preset(self, action: CbaSetupAction, ctx: ApplyContext) -> DeviceApplyResult | None:
        """Phase 2: send CC params, prompt user to save preset."""
        if ctx.dry_run:
            cc_count = len(action.cc_params)
            device = _find_device(ctx.rig, action.device)
            reset_count = 0
            if device is not None:
                model = getattr(device.config, "model", None) or ""
                controls = get_controls("Chase Bliss Audio", model) or []
                reset_count = len(
                    [c for c in controls if c.default is not None and c.midi_cc is not None]
                )
            logger.debug(
                "Dry-run: CB build preset '%s' on %s (%d resettable controls)",
                action.preset_name,
                action.device,
                reset_count,
            )
            console.print(
                f"  [cyan]→[/cyan] {action.device}: build preset #{action.preset_number} "
                f"'{action.preset_name}' ({cc_count} CC params)[dim] (dry-run)[/dim]"
            )
            if reset_count:
                console.print(
                    f"  [dim]→ reset {reset_count} defaults before {cc_count} CC params[/dim]"
                )
            return DeviceApplyResult(
                device=action.device, status="skipped", preset=action.preset_name
            )

        def _send_reset_ccs() -> int:
            """Send CC messages for all resettable controls to their catalog defaults."""
            sent = 0
            device = _find_device(ctx.rig, action.device)
            if device is None:
                return sent
            model = getattr(device.config, "model", None) or ""
            all_controls = get_controls("Chase Bliss Audio", model) or []
            resettable = [
                c for c in all_controls if c.default is not None and c.midi_cc is not None
            ]
            if not resettable:
                return sent
            if ctx.midi is None:
                return sent
            for control in resettable:
                try:
                    ctx.midi.send_control_change(
                        action.device, control.midi_cc, int(control.default), action.midi_channel
                    )
                    sent += 1
                except Exception as e:
                    logger.error("Reset CC %d failed on %s: %s", control.midi_cc, action.device, e)
                    console.print(
                        f"  [red]✗[/red] Reset CC send failed (CC {control.midi_cc}): {e}"
                    )
            return sent

        def _send_ccs() -> int:
            sent = 0
            if action.device in ctx.connected_devices and action.cc_params and ctx.midi is not None:
                for param in action.cc_params:
                    try:
                        ctx.midi.send_control_change(
                            action.device, param["cc"], param["value"], action.midi_channel
                        )
                        sent += 1
                    except Exception as e:
                        logger.error("Failed CC %d on %s: %s", param["cc"], action.device, e)
                        console.print(f"  [red]✗[/red] CC send failed (CC {param['cc']}): {e}")
            return sent

        reset_sent = _send_reset_ccs()
        if reset_sent:
            logger.info("Sent %d reset CCs to %s", reset_sent, action.device)
            console.print(f"  [dim]→ {reset_sent} defaults reset[/dim]")

        cc_sent = _send_ccs()
        if cc_sent:
            logger.info("Sent %d CC params to %s", cc_sent, action.device)
            console.print(f"  [green]✓[/green] {cc_sent}/{len(action.cc_params)} CC params sent")

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
            return None
        if res == "confirm":
            if (
                action.device in ctx.connected_devices
                and action.preset_number is not None
                and ctx.midi is not None
            ):
                while True:
                    try:
                        ctx.midi.send_program_change(
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
                        break
                    after = prompt_cba_after_pc(
                        action.device, action.preset_name, action.preset_number
                    )
                    if after == "retry":
                        continue
                    if after == "quit":
                        console.print("[red]Apply cancelled by user[/red]")
                        return None
                    break
            update_device_state(ctx.state, action.device, last_preset=action.preset_name)
            mark_preset_saved(ctx.state, action.device, action.preset_id)
        return DeviceApplyResult(
            device=action.device,
            status="confirmed" if res == "confirm" else "skipped",
            preset=action.preset_name,
        )

    def _register_scenes(
        self, action: CbaSetupAction, ctx: ApplyContext
    ) -> DeviceApplyResult | None:
        """Phase 3: confirm that all referenced scenes have been built."""
        if ctx.dry_run:
            logger.debug("Dry-run: CB register %s scenes", action.device)
            console.print(
                f"  [cyan]→[/cyan] {action.device}: register presets to scenes[dim] (dry-run)[/dim]"
            )
            return DeviceApplyResult(device=action.device, status="skipped", preset=None)

        res = prompt_cba_register(action.device, action.scene_refs)
        if res == "quit":
            console.print("[red]Apply cancelled by user[/red]")
            return None
        if res == "confirm":
            update_device_state(ctx.state, action.device, registration_done=True)
        return DeviceApplyResult(
            device=action.device,
            status="confirmed" if res == "confirm" else "skipped",
            preset=None,
        )
