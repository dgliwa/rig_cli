from __future__ import annotations

import pytest
from pydantic import ValidationError

from rig_morningstar.config import MC6Config
from rig_morningstar.device import MC6Device


def test_from_raw_yaml_parses_banks_into_config():
    banks = [{"name": "Bank 1", "switches": {}}]
    device = MC6Device.from_raw_yaml(
        {"id": "mc6", "config": {"type": "controller", "banks": banks}}
    )
    assert device.config.banks == banks


def test_from_raw_yaml_empty_banks_is_default():
    device = MC6Device.from_raw_yaml({"id": "mc6", "config": {"type": "controller"}})
    assert device.config.banks == []


def test_config_is_mc6_config_instance():
    device = MC6Device.from_raw_yaml({"id": "mc6", "config": {"type": "controller"}})
    assert isinstance(device.config, MC6Config)


def test_from_raw_yaml_invalid_banks_type_raises():
    with pytest.raises(ValidationError):
        MC6Device.from_raw_yaml({"id": "mc6", "config": {"type": "controller", "banks": "bad"}})
