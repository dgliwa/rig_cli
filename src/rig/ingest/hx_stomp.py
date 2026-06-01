from __future__ import annotations

import json
import logging
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def ingest_hx_file(path: str) -> list[dict[str, Any]]:
    """Extract preset data from an HX Stomp .hlx bundle file.

    .hlx files are zip archives containing JSON preset definitions.
    Returns a list of preset dicts suitable for writing as YAML.
    """
    path = Path(path)
    if not path.exists():
        logger.error("HX file not found: %s", path)
        raise FileNotFoundError(f"HX file not found: {path}")

    logger.info("Ingesting HX file: %s", path)
    presets: list[dict[str, Any]] = []

    with zipfile.ZipFile(path, "r") as zf:
        logger.debug("Opened .hlx archive with %d entries", len(zf.namelist()))
        for name in zf.namelist():
            if not name.endswith(".json"):
                logger.debug("Skipping non-JSON entry: %s", name)
                continue
            logger.debug("Reading entry: %s", name)
            with zf.open(name) as f:
                try:
                    data = json.loads(f.read())
                except json.JSONDecodeError as e:
                    logger.warning("Invalid JSON in .hlx entry '%s': %s", name, e)
                    continue

            preset = _parse_hx_json(data, name)
            if preset:
                presets.append(preset)

    logger.info("Extracted %d preset(s) from .hlx archive", len(presets))
    return presets


def _parse_hx_json(data: dict[str, Any], source_name: str) -> dict[str, Any] | None:
    """Convert HX JSON preset structure to our YAML preset format."""
    preset_info = data.get("preset", data.get("meta", {}))
    preset_name = preset_info.get("name") or Path(source_name).stem
    logger.debug("Parsing HX preset '%s'", preset_name)

    blocks: list[dict[str, Any]] = []
    chain = data.get("chain", data.get("signalChain", []))
    logger.debug("  %d block(s) in signal chain", len(chain))
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
        logger.debug(
            "  Block: %s (%s) — %d parameter(s)",
            block["name"],
            block["model"],
            len(params) if isinstance(params, dict) else 0,
        )

    return {
        "id": preset_name.lower().replace(" ", "-"),
        "pedal": "hx-stomp",
        "name": preset_name,
        "blocks": blocks,
    }
