"""HX Stomp .hlx file ingest — parses both new-style JSON and old-style zip archives.

Usage::

    presets = ingest_hx_file("path/to/preset.hlx")
"""

from __future__ import annotations

import json
import logging
import zipfile
from pathlib import Path
from typing import Any

from rig.models.preset import HXStompPreset

logger = logging.getLogger(__name__)


def ingest_hx_file(path: str, repo_root: str | None = None) -> list[HXStompPreset]:
    """Extract preset metadata from an HX Stomp .hlx bundle file.

    .hlx files from newer firmware are plain JSON. Older exports are zip
    archives containing JSON entries. Returns a list of typed
    :class:`HXStompPreset` objects with ``preset_number=0`` as a placeholder —
    update the YAML to reflect the actual slot number on the device.

    If *repo_root* is provided, ``hlx_file`` is stored relative to that path;
    otherwise the absolute path is used.
    """
    p = Path(path).resolve()
    if not p.exists():
        logger.error("HX file not found: %s", p)
        raise FileNotFoundError(f"HX file not found: {p}")

    if repo_root:
        try:
            hlx_file = str(p.relative_to(Path(repo_root).resolve()))
        except ValueError:
            hlx_file = str(p)
    else:
        hlx_file = str(p)

    logger.info("Ingesting HX file: %s", p)
    presets: list[HXStompPreset] = []

    raw_data = _try_read_json(p)
    if raw_data is not None:
        preset = _parse_hx_json(raw_data, p.name, hlx_file)
        if preset:
            presets.append(preset)
    else:
        with zipfile.ZipFile(p, "r") as zf:
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

                preset = _parse_hx_json(data, name, hlx_file)
                if preset:
                    presets.append(preset)

    logger.info("Extracted %d preset(s) from .hlx file", len(presets))
    return presets


def _try_read_json(path: Path) -> dict[str, Any] | None:
    """Try to read *path* as plain JSON. Returns ``None`` on failure."""
    try:
        with open(path) as f:
            return json.loads(f.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _parse_hx_json(data: dict[str, Any], source_name: str, hlx_file: str) -> HXStompPreset | None:
    """Convert HX JSON preset structure to a typed :class:`HXStompPreset`."""
    inner = data.get("data", data)
    meta = inner.get("meta", {})
    preset_name = meta.get("name") or inner.get("name", "") or Path(source_name).stem
    logger.debug("Parsing HX preset '%s'", preset_name)

    return HXStompPreset(
        id=preset_name.lower().replace(" ", "-"),
        name=preset_name,
        preset_number=0,
        hlx_file=hlx_file,
    )
