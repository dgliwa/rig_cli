"""Chase Bliss Audio device implementation.

ChaseBlissDevice is a Pydantic BaseModel that implements the Device Protocol.
setup() handles MIDI port connection and the 3-phase CBA initialization
(establish_channel → build_preset → register_scenes). apply() sends PC messages
for scene switching (same as HXStompDevice/analog PC send behavior).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console

from rig.config.errors import ValidationError
from rig.engine.plugin import (
    DeviceApplyContext,
    DeviceApplyResult,
    DeviceType,
    SetupContext,
    SetupResult,
    update_device_state,
)
from rig.engine.state import DeviceState, RigState
from rig_chasebliss.catalog import Control, get_controls
from rig_chasebliss.preset import DigitalPreset

if TYPE_CHECKING:
    from rig.models.rig import Rig


class ChaseBlissConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["chase_bliss"] = "chase_bliss"
    midi_channel: int | None = None
    model: str | None = None


def validate_cc_params(
    parameters: dict[str, Any],
    controls: list[Control],
) -> list[str]:
    """Validate preset parameters against a device's catalog controls.

    Returns a list of error strings. Empty list means valid.
    """
    errors: list[str] = []
    for param_name, param_value in parameters.items():
        control = None
        for c in controls:
            if c.name == param_name:
                control = c
                break

        if control is None:
            errors.append(f"'{param_name}' is not a valid parameter for this device")
            continue

        if control.positions and isinstance(param_value, str):
            if param_value not in control.positions:
                errors.append(
                    f"'{param_name}': '{param_value}' is not a valid position; allowed: {control.positions}"
                )
        elif control.positions:
            try:
                idx = int(param_value)
                if idx < 0 or idx >= len(control.positions):
                    errors.append(
                        f"'{param_name}': {param_value} is out of range (0-{len(control.positions) - 1}, as position index)"
                    )
            except (ValueError, TypeError):
                errors.append(f"'{param_name}': '{param_value}' is not a valid numeric value")
        else:
            try:
                val = int(param_value)
                if control.min is not None and val < control.min:
                    errors.append(
                        f"'{param_name}': {param_value} is out of range ({control.min}-{control.max})"
                    )
                if control.max is not None and val > control.max:
                    errors.append(
                        f"'{param_name}': {param_value} is out of range ({control.min}-{control.max})"
                    )
            except (ValueError, TypeError):
                errors.append(f"'{param_name}': '{param_value}' is not a valid numeric value")

    return errors


def _resolve_toggle_cc_value(raw: Any, ctrl: Control) -> int:
    """Resolve a toggle parameter to its CC value.

    When position_cc_values is set, the pedal uses threshold-based encoding
    (e.g. ENV=0-1, TAPE=2, STRETCH=>2) rather than bare indices.
    """
    idx = ctrl.positions.index(raw) if isinstance(raw, str) else int(raw)
    if ctrl.position_cc_values:
        return ctrl.position_cc_values[idx]
    return idx


def _get_cc_params(parameters: dict[str, Any], controls: list[Control]) -> list[dict[str, int]]:
    """Build CC param list from preset parameters and resolved controls."""
    result = []
    for ctrl in controls:
        if ctrl.midi_cc is not None and ctrl.name in parameters:
            raw = parameters[ctrl.name]
            value = _resolve_toggle_cc_value(raw, ctrl) if ctrl.positions else int(raw)
            result.append({"cc": ctrl.midi_cc, "value": value})
    return result


logger = logging.getLogger(__name__)
console = Console()


def _detect_cba_setup_for_device(device: ChaseBlissDevice, state: RigState, rig: Rig) -> list[Any]:
    """Detect which CBA setup actions are needed for this device.

    Checks state for channel establishment, saved presets, and scene registration.
    """
    from rig_chasebliss.models import CbaSetupAction

    actions: list[CbaSetupAction] = []
    ch = device.config.midi_channel or 1
    ds = state.devices.get(device.id, DeviceState())

    if not ds.channel_established:
        actions.append(CbaSetupAction(device=device.id, midi_channel=ch, type="establish_channel"))

    controls = get_controls("Chase Bliss Audio", getattr(device.config, "model", None) or "") or []
    errors: list[str] = []

    for preset in [p for p in device.presets if hasattr(p, "preset_number")]:
        if not ds.presets_saved.get(preset.id):
            param_errors = validate_cc_params(preset.parameters, controls)
            for err in param_errors:
                errors.append(f"  {device.id}: preset '{preset.name}' ({preset.id}) — {err}")
            actions.append(
                CbaSetupAction(
                    device=device.id,
                    midi_channel=ch,
                    type="build_preset",
                    preset_id=preset.id,
                    preset_name=preset.name,
                    preset_number=preset.preset_number,
                    cc_params=_get_cc_params(preset.parameters, controls),
                )
            )

    if errors:
        msg = f"CBA preset validation failed for device '{device.id}':\n" + "\n".join(errors)
        raise ValidationError(msg)

    if not ds.registration_done:
        scene_refs = [sn for sn, s in rig.scenes.items() if device.id in s.presets]
        if scene_refs:
            actions.append(
                CbaSetupAction(
                    device=device.id,
                    midi_channel=ch,
                    type="register_scenes",
                    scene_refs=scene_refs,
                )
            )

    return actions


class ChaseBlissDevice(BaseModel):
    """Chase Bliss Audio pedal — PC-message-based with 3-phase MIDI setup.

    setup() handles MIDI port connection and runs the 3-phase initialization
    (establish MIDI channel, build presets via CC params, register scenes).
    apply() sends PC messages for scene switching, same as HXStompDevice.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    id: str
    name: str = ""
    config: ChaseBlissConfig
    type: DeviceType = DeviceType.DIGITAL
    presets: list[DigitalPreset] = Field(default_factory=list)

    @classmethod
    def from_raw_yaml(cls, data: dict[str, Any]) -> ChaseBlissDevice:
        config = ChaseBlissConfig(**(data.get("config") or {}))
        presets = [DigitalPreset(**p) for p in (data.get("presets") or [])]
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            type=DeviceType.DIGITAL,
            config=config,
            presets=presets,
        )

    def setup(self, ctx: SetupContext) -> SetupResult:
        """Connect MIDI and run 3-phase CBA setup.

        1. Prompt user for MIDI port selection
        2. Detect required setup actions (channel, presets, registration)
        3. Execute actions via ChaseBlissApplier
        """
        ch = self.config.midi_channel or 1
        state_modified = False

        # Step 1: MIDI connection
        if ctx.dry_run or ctx.midi is None:
            ctx.connected_devices.add(self.id)
        else:
            from rig.interaction.midi import prompt_midi_connect

            cached_port = ctx.state.devices.get(self.id, DeviceState()).midi_port
            res, port_name = prompt_midi_connect(self.id, ch, ctx.midi, cached_port)

            if res == "quit":
                return SetupResult(cancelled=True)
            if res == "confirm" and port_name:
                update_device_state(ctx.state, self.id, midi_port=port_name)
                ctx.connected_devices.add(self.id)
                state_modified = True

        # Step 2: 3-phase CBA setup
        if ctx.rig is None:
            return SetupResult(state_modified=state_modified)

        actions = _detect_cba_setup_for_device(self, ctx.state, ctx.rig)
        if not actions:
            return SetupResult(state_modified=state_modified)

        from rig_chasebliss.applier import ChaseBlissApplier

        applier = ChaseBlissApplier()
        results = applier.apply_setup(actions, ctx)
        if results is None:
            return SetupResult(cancelled=True)
        if any(r.status == "confirmed" for r in results):
            state_modified = True

        return SetupResult(state_modified=state_modified)

    def get_scene_pc_command(self, preset_id: str) -> dict[str, Any] | None:
        """Return a PC command dict for the given preset_id, or None."""
        ch = self.config.midi_channel
        if ch is None:
            return None
        for preset in self.presets:
            if (
                preset.id == preset_id
                and hasattr(preset, "preset_number")
                and preset.preset_number is not None
            ):
                return {
                    "type": "pc",
                    "channel": ch,
                    "value": preset.preset_number,
                    "label": f"{self.id}: {preset_id}",
                }
        return None

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
        """Send PC message and prompt user for confirmation.

        CBA scene switching is just a PC message — same behavior as HXStompDevice.
        """
        action = ctx.action
        midi_connected = action.device in ctx.connected_devices

        if ctx.dry_run:
            logger.debug(
                "Dry-run: would send PC#%s on ch %s to %s",
                action.preset_number,
                action.midi_channel,
                action.device,
            )
            console.print(
                f"  [dim]→ PC#{action.preset_number} ch {action.midi_channel} "
                f"→ {action.device} '{action.preset_name}'[/dim]"
            )
            return DeviceApplyResult(
                device=action.device, status="skipped", preset=action.preset_name
            )

        def _try_send_pc() -> bool:
            if (
                midi_connected
                and action.preset_number is not None
                and action.midi_channel is not None
                and ctx.midi is not None
            ):
                try:
                    ctx.midi.send_program_change(
                        action.device, action.preset_number, action.midi_channel
                    )
                    return True
                except Exception as e:
                    logger.error("Failed PC send to %s: %s", action.device, e)
            return False

        _try_send_pc()

        while True:
            result = ctx.confirmation_io.prompt_device(
                action.device,
                action.preset_name,
                action.preset_number,
                action.midi_channel,
                midi_connected,
            )
            if result == "confirm":
                update_device_state(ctx.state, action.device, last_preset=action.preset_name)
                return DeviceApplyResult(
                    device=action.device,
                    status="confirmed",
                    preset=action.preset_name,
                )
            if result == "retry":
                _try_send_pc()
                continue
            if result == "skip":
                return DeviceApplyResult(
                    device=action.device,
                    status="skipped",
                    preset=action.preset_name,
                )
            return DeviceApplyResult(
                device=action.device,
                status="error",
                preset=action.preset_name,
                error="quit",
            )
