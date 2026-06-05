from __future__ import annotations

import logging
from pathlib import Path

import typer

from rig.cli._shared import _CONFIG_OPTION, _SCENE_OPTION, _VERBOSE_OPTION, app, console
from rig.config.errors import ConfigError
from rig.config.loader import load_rig
from rig.engine.apply import apply_plan
from rig.engine.plan import compute_plan
from rig.engine.ports import FileStateWriter, InteractiveMidiConnectionIO
from rig.log_setup import setup_logging
from rig.midi.adapter import MidiManager

logger = logging.getLogger(__name__)


@app.command()
def apply(
    config: str = _CONFIG_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    scene: str | None = _SCENE_OPTION,
    verbose: int = _VERBOSE_OPTION,
):
    """Apply changes — walks through each device with MIDI prompts."""
    setup_logging(verbose)
    logger.info("Applying plan for config: %s", config)
    try:
        rig = load_rig(config)
    except ConfigError as e:
        console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1)

    midi = MidiManager()
    config_path = str(Path(config).resolve())
    result = compute_plan(rig, root_path=config_path)
    state_writer = FileStateWriter()
    midi_connection_io = InteractiveMidiConnectionIO()
    try:
        apply_plan(
            result,
            state_writer=state_writer,
            midi_connection_io=midi_connection_io,
            rig=rig,
            config_path=config_path,
            dry_run=dry_run,
            scene=scene,
            midi=midi,
        )
    finally:
        midi.disconnect_all()
