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

    # Newer HX firmware exports as plain JSON; older as zip archives.
    # Try JSON first, then fall back to zip.
    raw_data = _try_read_json(path)
    if raw_data is not None:
        preset = _parse_hx_json(raw_data, path.name)
        if preset:
            presets.append(preset)
    else:
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

    logger.info("Extracted %d preset(s) from .hlx file", len(presets))
    return presets


def _try_read_json(path: Path) -> dict[str, Any] | None:
    """Try to read *path* as plain JSON. Returns None on failure."""
    try:
        with open(path) as f:
            return json.loads(f.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _parse_hx_json(data: dict[str, Any], source_name: str) -> dict[str, Any] | None:
    """Convert HX JSON preset structure to our YAML preset format."""
    # Handle both new-style (plain JSON with dsp blocks) and old-style (zip with chain array).
    inner = data.get("data", data)
    meta = inner.get("meta", {})
    preset_name = meta.get("name") or inner.get("name", "") or Path(source_name).stem
    logger.debug("Parsing HX preset '%s'", preset_name)

    blocks: list[dict[str, Any]] = []

    # New-style: blocks live under tone.dsp0 / tone.dsp1 with @model keys
    tone = inner.get("tone", {})
    if tone:
        for dsp_key in ("dsp0", "dsp1"):
            dsp = tone.get(dsp_key, {})
            if not dsp:
                continue
            for block_key in sorted(
                dsp,
                key=lambda k: dsp[k].get("@position", 999) if isinstance(dsp.get(k), dict) else 999,
            ):
                if not block_key.startswith("block"):
                    continue
                block_data = dsp[block_key]
                if not isinstance(block_data, dict):
                    continue

                model = block_data.get("@model", "unknown")
                enabled = block_data.get("@enabled", True)
                stereo = block_data.get("@stereo", False)
                path = block_data.get("@path", 0)

                # Everything not prefixed with @ is a parameter
                settings = {k: v for k, v in block_data.items() if not k.startswith("@")}

                blocks.append(
                    {
                        "name": model,
                        "model": model,
                        "enabled": enabled,
                        "stereo": stereo,
                        "path": path,
                        "settings": settings,
                    }
                )
                logger.debug("  Block %s: %s — %d parameter(s)", block_key, model, len(settings))

    # Old-style: blocks live under a "chain" key (from older zip format)
    if not blocks:
        chain = data.get("chain", inner.get("chain", []))
        if chain:
            logger.debug("  %d block(s) in chain", len(chain))
            for block_data in chain:
                settings = dict(block_data.get("parameters", {}))
                blocks.append(
                    {
                        "name": block_data.get("name", "Untitled"),
                        "type": block_data.get("type"),
                        "model": block_data.get("model", ""),
                        "enabled": block_data.get("enabled", True),
                        "settings": settings,
                    }
                )

    return {
        "id": preset_name.lower().replace(" ", "-"),
        "pedal": "hx-stomp",
        "name": preset_name,
        "blocks": blocks,
    }
