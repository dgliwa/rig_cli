from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def ingest_mc6_config(path: str) -> list[dict[str, Any]]:
    """Extract scene definitions from an MC6 JSON config file.
    
    MC6 config files map bank/switch positions to MIDI commands.
    Returns a list of scene dicts suitable for writing as YAML.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MC6 config not found: {path}")

    with open(path) as f:
        data = json.load(f)

    scenes: list[dict[str, Any]] = []

    for bank_key, bank_data in data.items():
        if not isinstance(bank_data, dict):
            continue
        presets = bank_data.get("presets", {})
        for switch_label, switch_data in presets.items():
            commands = switch_data.get("commands", [])
            scene_name = switch_data.get("name", f"{bank_key}-{switch_label}")
            presets_map: dict[str, str] = {}

            # Map MC6 commands to pedal names and preset IDs
            # MC6 sends PC messages: PC value → HX Stomp preset number
            # We store the scene but the user may need to map pedal/preset names
            for cmd in commands:
                if cmd.get("type") == "pc":
                    pedal_ref = f"unknown-ch{cmd.get('channel', 1)}"
                    preset_ref = f"pc{cmd.get('value', 0)}"
                    presets_map[pedal_ref] = preset_ref

            scene = {
                "name": scene_name.lower().replace(" ", "-"),
                "description": f"Imported from MC6 {bank_key}/{switch_label}",
                "presets": presets_map,
                "mc6_bank": int(bank_key.replace("bank", "")),
                "mc6_switch": switch_label,
            }
            scenes.append(scene)

    return scenes
