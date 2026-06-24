from __future__ import annotations

import logging
from pathlib import Path

import typer

from rig.cli._shared import _CONFIG_OPTION, _SCENE_OPTION, _VERBOSE_OPTION, app, console
from rig.config.errors import ConfigError
from rig.config.loader import load_rig
from rig.engine.apply import apply_plan
from rig.engine.plan import compute_plan
from rig.engine.ports import FileStateWriter
from rig.log_setup import setup_logging
from rig.midi.adapter import MidiManager

logger = logging.getLogger(__name__)


@app.command()
def apply(
    config: str = _CONFIG_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    scene: str | None = _SCENE_OPTION,
    verbose: int = _VERBOSE_OPTION,
    device: str | None = typer.Option(None, "--device", help="Device ID to apply in isolation"),
    preset: str | None = typer.Option(None, "--preset", help="Preset ID to apply to device"),
):
    """Apply changes — walks through each device with MIDI prompts."""
    setup_logging(verbose)
    logger.info("Applying plan for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    # D-04: --scene is exclusive with --device/--preset
    if scene and (device or preset):
        console.print("[red]✗[/red] --scene cannot be combined with --device/--preset")
        raise typer.Exit(1)

    # D-05: --preset requires --device
    if preset and not device:
        console.print("[red]✗[/red] --preset requires --device")
        raise typer.Exit(1)

    # D-06: existence validation before MIDI port is opened
    if device and preset:
        if device not in rig.devices:
            console.print(f"[red]✗[/red] Device '{device}' not found in rig config")
            raise typer.Exit(1)
        target_device = rig.devices[device]
        if not any(p.id == preset for p in target_device.presets):
            console.print(f"[red]✗[/red] Preset '{preset}' not found on device '{device}'")
            raise typer.Exit(1)
    elif device:
        if device not in rig.devices:
            console.print(f"[red]✗[/red] Device '{device}' not found in rig config")
            raise typer.Exit(1)

    midi = MidiManager()
    config_path = str(Path(config).resolve())
    state_writer = FileStateWriter()
    try:
        if device and preset:
            from rig.engine.apply import apply_device_preset

            apply_device_preset(
                device,
                preset,
                state_writer=state_writer,
                rig=rig,
                config_path=config_path,
                dry_run=dry_run,
                midi=midi,
            )
        elif device:
            result = compute_plan(rig, root_path=config_path)
            apply_plan(
                result,
                state_writer=state_writer,
                rig=rig,
                config_path=config_path,
                dry_run=dry_run,
                scene=scene,
                midi=midi,
                device_filter=device,
            )
        else:
            result = compute_plan(rig, root_path=config_path)
            apply_plan(
                result,
                state_writer=state_writer,
                rig=rig,
                config_path=config_path,
                dry_run=dry_run,
                scene=scene,
                midi=midi,
            )
    finally:
        midi.disconnect_all()
