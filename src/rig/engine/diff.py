from __future__ import annotations

import logging
from typing import Any

from rig.engine.state import DeviceState, RigState, read_state
from rig.models.rig import Rig

logger = logging.getLogger(__name__)


def compute_diff(config: Rig, root_path: str | None = None) -> dict[str, Any]:
    """Compare desired config against actual state and return a structured diff."""
    actual = RigState()
    if root_path:
        actual = read_state(root_path)
        logger.debug("Read state from %s for diff", root_path)

    changes: dict[str, Any] = {
        "scenes": {},
        "pedals": {},
    }

    logger.debug("Computing diff for %d scenes", len(config.scenes))
    for scene_name, scene in config.scenes.items():
        actual_devices = actual.devices
        scene_diffs: dict[str, Any] = {}

        if scene_name not in actual.scenes:
            scene_diffs["_status"] = "new"
            scene_diffs["presets"] = {
                k: {"_status": "added", "new": v} for k, v in scene.presets.items()
            }
        else:
            scene_diffs["presets"] = {}
            for pedal_id, preset_id in scene.presets.items():
                actual_preset = actual_devices.get(pedal_id, DeviceState()).last_preset
                if actual_preset != preset_id:
                    scene_diffs["presets"][pedal_id] = {
                        "_status": "changed",
                        "old": actual_preset,
                        "new": preset_id,
                    }
            scene_diffs["_status"] = "unchanged" if not scene_diffs["presets"] else "changed"

        if scene_diffs.get("presets") or scene_diffs.get("_status") == "new":
            changes["scenes"][scene_name] = scene_diffs

    return changes


def format_diff(diff: dict[str, Any]) -> str:
    """Render structured diff as a human-readable string."""
    lines: list[str] = []

    for scene_name, scene_data in diff.get("scenes", {}).items():
        status = scene_data.get("_status", "changed")
        if status == "new":
            lines.append(f"[new]  {scene_name}")
        else:
            lines.append(f"[~]    {scene_name}")

        for pedal_id, preset_data in scene_data.get("presets", {}).items():
            pstatus = preset_data.get("_status", "changed")
            if pstatus == "added":
                lines.append(f"       + {pedal_id}: '{preset_data.get('new', '')}'")
            elif pstatus == "changed":
                old = preset_data.get("old", "(none)")
                new = preset_data.get("new", "(none)")
                lines.append(f"       ~ {pedal_id}: {old} → {new}")

    if not diff.get("scenes"):
        lines.append("(no changes)")

    return "\n".join(lines)
