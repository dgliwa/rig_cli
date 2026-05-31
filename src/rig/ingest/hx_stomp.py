from __future__ import annotations
import json
import zipfile
from pathlib import Path
from typing import Any


def ingest_hx_file(path: str) -> list[dict[str, Any]]:
    """Extract preset data from an HX Stomp .hlx bundle file.
    
    .hlx files are zip archives containing JSON preset definitions.
    Returns a list of preset dicts suitable for writing as YAML.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"HX file not found: {path}")

    presets: list[dict[str, Any]] = []

    with zipfile.ZipFile(path, "r") as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            with zf.open(name) as f:
                try:
                    data = json.loads(f.read())
                except json.JSONDecodeError:
                    continue

            preset = _parse_hx_json(data, name)
            if preset:
                presets.append(preset)

    return presets


def _parse_hx_json(data: dict[str, Any], source_name: str) -> dict[str, Any] | None:
    """Convert HX JSON preset structure to our YAML preset format."""
    preset_info = data.get("preset", data.get("meta", {}))
    preset_name = preset_info.get("name") or Path(source_name).stem

    blocks: list[dict[str, Any]] = []
    chain = data.get("chain", data.get("signalChain", []))
    for block_data in chain:
        block = {
            "name": block_data.get("name", "Untitled"),
            "type": block_data.get("type", "unknown"),
            "model": block_data.get("model", ""),
            "enabled": block_data.get("enabled", True),
            "settings": {},
        }
        params = block_data.get("parameters", {})
        if isinstance(params, dict):
            block["settings"] = params
        blocks.append(block)

    return {
        "id": preset_name.lower().replace(" ", "-"),
        "pedal": "hx-stomp",
        "name": preset_name,
        "blocks": blocks,
    }
