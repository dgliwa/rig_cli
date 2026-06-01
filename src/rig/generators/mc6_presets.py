from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from rig.models.rig import RigConfig

logger = logging.getLogger(__name__)


def generate_mc6(rig: RigConfig) -> dict[str, Any]:
    """Generate MC6 bank definitions from rig config's mc6 mapping + scenes."""
    mc6_config = rig.mc6
    banks = mc6_config.get("banks", [])
    logger.info("Generating MC6 config for %d banks", len(banks))
    output: dict[str, Any] = {}

    for bank in banks:
        bank_num = bank["bank"]
        bank_name = bank.get("name", f"Bank {bank_num}")
        switches = bank.get("switches", {})

        bank_key = f"bank{bank_num}"
        output[bank_key] = {"name": bank_name, "presets": {}}
        logger.debug("Bank %d '%s': %d switch(es)", bank_num, bank_name, len(switches))

        for switch_label, switch_data in switches.items():
            scene_name = switch_data.get("scene")
            commands: list[dict[str, Any]] = []

            if scene_name and scene_name in rig.scenes:
                scene = rig.scenes[scene_name]
                for pedal_id, preset_id in scene.presets.items():
                    pedal = rig.pedals.get(pedal_id)
                    if pedal is None:
                        logger.warning("Pedal '%s' in scene '%s' not found", pedal_id, scene_name)
                        continue

                    if pedal.type.value == "modeler":
                        for hp in rig.hx_presets.get(pedal_id, []):
                            if hp.id == preset_id and hp.preset_number is not None:
                                commands.append(
                                    {
                                        "type": "pc",
                                        "channel": pedal.config.midi_channel or 1,
                                        "value": hp.preset_number,
                                        "label": f"{pedal_id}: {preset_id}",
                                    }
                                )
                                logger.debug(
                                    "  Switch %s → PC ch%s val%s (%s)",
                                    switch_label,
                                    pedal.config.midi_channel,
                                    hp.preset_number,
                                    preset_id,
                                )

            output[bank_key]["presets"][switch_label] = {
                "name": scene_name or "empty",
                "commands": commands,
            }

    logger.info("Generated %d MC6 bank(s)", len(output))
    return output


def write_mc6_config(mc6_data: dict[str, Any], output_path: str = "generated/mc6") -> Path:
    out_dir = Path(output_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Writing MC6 config files to %s", out_dir)

    for bank_key, bank_data in mc6_data.items():
        path = out_dir / f"{bank_key}.json"
        with open(path, "w") as f:
            json.dump(bank_data, f, indent=2)
        logger.debug("Wrote %s", path.relative_to(out_dir.parent))

    return out_dir
