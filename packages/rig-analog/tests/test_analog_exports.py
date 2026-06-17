from __future__ import annotations

import importlib

import pytest


def test_prompt_analog_not_importable_from_rig_analog():
    with pytest.raises((ImportError, AttributeError)):
        from rig_analog import prompt_analog  # noqa: F401


def test_prompt_analog_not_importable_from_rig_analog_interaction():
    with pytest.raises(ImportError):
        importlib.import_module("rig_analog.interaction")


def test_rig_analog_does_not_expose_prompt_analog_in_all():
    import rig_analog

    assert "prompt_analog" not in dir(rig_analog)
