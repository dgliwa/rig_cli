"""Tests for helper functions in rig.engine.appliers.base."""

from __future__ import annotations

import ast
from pathlib import Path

from rig.engine.appliers.base import mark_preset_saved
from rig.engine.state import DeviceState, RigState

# ---------------------------------------------------------------------------
# CBA-01: mark_preset_saved unit test
# ---------------------------------------------------------------------------


def test_mark_preset_saved_sets_preset_id_to_true_in_new_device():
    state = RigState()
    mark_preset_saved(state, "cba-mood", "shimmer")

    assert state.devices["cba-mood"].presets_saved["shimmer"] is True


def test_mark_preset_saved_preserves_existing_entries_when_adding_new_preset():
    state = RigState()
    state.devices["cba-mood"] = DeviceState(presets_saved={"drone": True})

    mark_preset_saved(state, "cba-mood", "shimmer")

    assert state.devices["cba-mood"].presets_saved["drone"] is True
    assert state.devices["cba-mood"].presets_saved["shimmer"] is True


def test_mark_preset_saved_does_not_mutate_other_device_state_fields():
    state = RigState()
    state.devices["cba-mood"] = DeviceState(channel_established=True, midi_channel=3)

    mark_preset_saved(state, "cba-mood", "shimmer")

    device = state.devices["cba-mood"]
    assert device.channel_established is True
    assert device.midi_channel == 3
    assert device.presets_saved["shimmer"] is True


def test_mark_preset_saved_is_the_only_caller_of_update_device_state_for_presets_saved():
    """mark_preset_saved must be the single mutation path — no direct presets_saved writes in chase_bliss.py."""
    chase_bliss_src = (
        Path(__file__).parent.parent / "src" / "rig" / "engine" / "appliers" / "chase_bliss.py"
    ).read_text()
    tree = ast.parse(chase_bliss_src)

    for node in ast.walk(tree):
        # Look for attribute assignments: something.presets_saved = ...
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "presets_saved":
                    raise AssertionError(
                        "chase_bliss.py directly assigns .presets_saved — "
                        "all mutations must go through mark_preset_saved()"
                    )
        # Also look for keyword args in update_device_state(presets_saved=...) calls
        # made outside mark_preset_saved itself — those would bypass the helper too
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "update_device_state":
                for kw in node.keywords:
                    if kw.arg == "presets_saved":
                        # This is only acceptable inside mark_preset_saved itself,
                        # which lives in base.py — any occurrence here is a violation.
                        raise AssertionError(
                            "chase_bliss.py calls update_device_state(presets_saved=...) directly — "
                            "all presets_saved mutations must go through mark_preset_saved()"
                        )


# ---------------------------------------------------------------------------
# CBA-03: no private symbol references across engine module boundaries
# ---------------------------------------------------------------------------

_ENGINE_ROOT = Path(__file__).parent.parent / "src" / "rig" / "engine"


def _collect_py_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def test_no_private_symbol_cross_module_reference_in_engine():
    """No file in the engine package imports a private symbol (_name) from a sibling module."""
    violations: list[str] = []

    for py_file in _collect_py_files(_ENGINE_ROOT):
        src = py_file.read_text()
        tree = ast.parse(src, filename=str(py_file))

        for node in ast.walk(tree):
            # from <module> import _symbol or from <module> import _symbol as alias
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name.startswith("_"):
                        violations.append(
                            f"{py_file.relative_to(_ENGINE_ROOT)}: "
                            f"imports private symbol '{alias.name}' "
                            f"from '{node.module}'"
                        )

    assert not violations, "Private symbols imported across module boundaries:\n" + "\n".join(
        violations
    )
