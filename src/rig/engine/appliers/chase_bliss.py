from __future__ import annotations

import logging

from rich.console import Console

from rig.engine.appliers.base import (
    ApplyContext,
    DeviceApplyResult,
    mark_preset_saved,
    update_device_state,
)
from rig.engine.plan import CbaSetupAction, detect_cba_setup

logger = logging.getLogger(__name__)
console = Console()


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

        def _enqueue_new_actions() -> None:
            if ctx.rig is None:
                return
            for a in detect_cba_setup(ctx.rig, ctx.state):
                key = (a.device, a.type, a.preset_id)
                if key not in seen:
                    pending.append(a)

        while pending:
            action = pending.pop(0)
            action_key = (action.device, action.type, action.preset_id)
            if action_key in seen:
                continue
            seen.add(action_key)

            if action.type == "establish_channel":
                result = self._establish_channel(action, ctx)
                if result is None:
                    # quit
                    return None
                results.append(result)
                if result.status == "confirmed":
                    _enqueue_new_actions()

            elif action.type == "build_preset":
                result = self._build_preset(action, ctx)
                if result is None:
                    return None
                results.append(result)
                if result.status == "confirmed":
                    _enqueue_new_actions()

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
            res = ctx.confirmation_io.prompt_cba_channel(action.device, action.midi_channel, False)
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
                res = ctx.confirmation_io.prompt_cba_channel(
                    action.device, action.midi_channel, True
                )
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
            logger.debug("Dry-run: CB build preset '%s' on %s", action.preset_name, action.device)
            console.print(
                f"  [cyan]→[/cyan] {action.device}: build preset #{action.preset_number} "
                f"'{action.preset_name}' ({cc_count} CC params)[dim] (dry-run)[/dim]"
            )
            return DeviceApplyResult(
                device=action.device, status="skipped", preset=action.preset_name
            )

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

        cc_sent = _send_ccs()
        if cc_sent:
            logger.info("Sent %d CC params to %s", cc_sent, action.device)
            console.print(f"  [green]✓[/green] {cc_sent}/{len(action.cc_params)} CC params sent")

        while True:
            res = ctx.confirmation_io.prompt_cba_preset(
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

        res = ctx.confirmation_io.prompt_cba_register(action.device, action.scene_refs)
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
