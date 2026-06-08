"""Tests for the single-file rig.yaml loader (Phase 10 schema)."""

from pathlib import Path

import pytest

from rig.config.errors import FileNotFoundError_, MissingReferenceError, ParseError, ValidationError
from rig.config.loader import load_rig


def _write(base: Path, filename: str, content: str):
    """Write a file under *base*, creating parent dirs as needed."""
    full = base / filename
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)


BASE_RIG_YAML = """\
name: test-rig
description: A test rig
midi_channel: 1
devices:
  - id: brothers
    name: Brothers
    type: digital
    config:
      type: midi
      midi_channel: 3
    presets:
      - id: low-gain
        name: Low Gain
        preset_number: 4
      - id: lead
        name: Lead
        preset_number: 7

  - id: tumnus
    name: Tumnus
    type: analog
    config:
      type: manual
    presets:
      - id: edge
        name: Edge of Breakup
        values:
          Gain: 3.5

  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:
        billy-clean:
          presets:
            brothers: low-gain
      banks: []
"""


@pytest.fixture
def rig_dir(tmp_path):
    d = tmp_path / "rig"
    d.mkdir()
    _write(d, "rig.yaml", BASE_RIG_YAML)
    return d


class TestLoadRig:
    def test_loads_full_config(self, rig_dir):
        config = load_rig(str(rig_dir))
        assert config.name == "test-rig"
        assert config.midi_channel == 1
        assert "brothers" in config.devices
        assert "tumnus" in config.devices

    def test_loads_signal_chain_from_device_order(self, rig_dir):
        config = load_rig(str(rig_dir))
        expected = ["brothers", "tumnus", "mc6"]
        assert config.signal_chain == expected

    def test_loads_presets_inline(self, rig_dir):
        config = load_rig(str(rig_dir))
        brothers = config.devices["brothers"]
        tumnus = config.devices["tumnus"]
        assert len(brothers.presets) == 2
        assert len(tumnus.presets) == 1
        assert tumnus.presets[0].values["Gain"] == 3.5

    def test_loads_scenes_from_controller(self, rig_dir):
        config = load_rig(str(rig_dir))
        assert "billy-clean" in config.scenes
        assert config.scenes["billy-clean"].presets["brothers"] == "low-gain"

    def test_missing_rig_yaml(self, rig_dir):
        (rig_dir / "rig.yaml").unlink()
        with pytest.raises(FileNotFoundError_):
            load_rig(str(rig_dir))

    def test_no_signal_chain_file_needed(self, rig_dir):
        """Loader reads only rig.yaml — no signal-chain.yaml needed."""
        config = load_rig(str(rig_dir))
        assert len(config.signal_chain) == 3
        assert config.signal_chain == ["brothers", "tumnus", "mc6"]

    def test_invalid_yaml(self, rig_dir):
        _write(rig_dir, "rig.yaml", "name: test\nbroken: [\n")
        with pytest.raises(ParseError):
            load_rig(str(rig_dir))

    def test_broken_preset_reference(self, rig_dir):
        """Scene references a non-existent preset on a valid device."""
        bad_yaml = BASE_RIG_YAML.replace(
            "brothers: low-gain",
            "brothers: nonexistent-preset",
        )
        _write(rig_dir, "rig.yaml", bad_yaml)
        with pytest.raises(MissingReferenceError):
            load_rig(str(rig_dir))

    def test_broken_pedal_reference(self, rig_dir):
        """Scene references an unknown device."""
        bad_yaml = BASE_RIG_YAML.replace(
            "brothers: low-gain",
            "unknown-pedal: low-gain",
        )
        _write(rig_dir, "rig.yaml", bad_yaml)
        with pytest.raises(MissingReferenceError):
            load_rig(str(rig_dir))

    def test_non_cba_pedal_without_midi_channel_accepted(self, rig_dir):
        """Digital device with midi config and midi_channel works."""
        yaml = BASE_RIG_YAML.replace(
            "type: midi\n      midi_channel: 3",
            "type: midi\n      midi_channel: 1",
        )
        _write(rig_dir, "rig.yaml", yaml)
        config = load_rig(str(rig_dir))
        assert "brothers" in config.devices

    def test_hx_preset_loaded_as_hx_type(self, rig_dir):
        from rig_hx.preset import HXStompPreset

        yaml = """\
name: test-rig
devices:
  - id: hx-stomp
    name: HX Stomp
    type: modeler
    config:
      type: midi
      midi_channel: 1
    presets:
      - id: clean
        name: Clean Edge
        preset_number: 12
        hlx_file: hlx/clean-edge.hlx
"""
        _write(rig_dir, "rig.yaml", yaml)
        config = load_rig(str(rig_dir))
        hx_presets = [p for p in config.devices["hx-stomp"].presets if isinstance(p, HXStompPreset)]
        assert len(hx_presets) == 1
        assert hx_presets[0].preset_number == 12
        assert hx_presets[0].hlx_file == "hlx/clean-edge.hlx"

    def test_loads_controller_as_device(self, rig_dir):
        from rig.models.device import DeviceType

        config = load_rig(str(rig_dir))
        assert "mc6" in config.devices
        assert config.devices["mc6"].type == DeviceType.CONTROLLER
        assert config.controller is not None
        assert config.controller.id == "mc6"

    def test_scenes_accessible_via_controller(self, rig_dir):
        config = load_rig(str(rig_dir))
        assert "billy-clean" in config.scenes

    def test_empty_devices_list(self, rig_dir):
        yaml = """\
name: empty-rig
devices: []
"""
        _write(rig_dir, "rig.yaml", yaml)
        config = load_rig(str(rig_dir))
        assert len(config.devices) == 0
        assert len(config.signal_chain) == 0

    def test_direct_path_to_rig_yaml(self, rig_dir):
        """load_rig accepts a direct path to rig.yaml (not just directory)."""
        config = load_rig(str(rig_dir / "rig.yaml"))
        assert config.name == "test-rig"
        assert "brothers" in config.devices


class TestRegistryDispatch:
    """Loader produces concrete plugin device types via registry-driven dispatch."""

    def test_manual_config_produces_analog_device(self, rig_dir):
        from rig_analog.device import AnalogDevice

        config = load_rig(str(rig_dir))
        assert isinstance(config.devices["tumnus"], AnalogDevice)

    def test_midi_config_produces_hx_stomp_device(self, rig_dir):
        from rig_hx.device import HXStompDevice

        config = load_rig(str(rig_dir))
        assert isinstance(config.devices["brothers"], HXStompDevice)

    def test_controller_config_produces_mc6_device(self, rig_dir):
        from rig_morningstar.device import MC6Device

        config = load_rig(str(rig_dir))
        assert isinstance(config.devices["mc6"], MC6Device)

    def test_chase_bliss_config_produces_cba_device(self, rig_dir):
        from rig_chasebliss.device import ChaseBlissDevice

        yaml = (
            BASE_RIG_YAML
            + """
  - id: mood
    name: Mood
    type: digital
    config:
      type: chase_bliss
      midi_channel: 4
      controls: []
    presets: []
"""
        )
        _write(rig_dir, "rig.yaml", yaml)
        config = load_rig(str(rig_dir))
        assert isinstance(config.devices["mood"], ChaseBlissDevice)

    def test_unknown_config_type_raises_validation_error(self, rig_dir):

        yaml = """\
name: bad-rig
devices:
  - id: mystery
    name: Mystery
    type: digital
    config:
      type: unknown_plugin
      midi_channel: 1
    presets: []
"""
        _write(rig_dir, "rig.yaml", yaml)
        with pytest.raises(ValidationError, match="Unknown device config type"):
            load_rig(str(rig_dir))

    def test_all_devices_have_apply_method(self, rig_dir):
        config = load_rig(str(rig_dir))
        for device_id, device in config.devices.items():
            assert callable(getattr(device, "apply", None)), (
                f"device {device_id!r} missing apply() method"
            )

    def test_controller_composes_validation(self, rig_dir):
        """Controller with composes referencing a valid device works."""
        yaml = BASE_RIG_YAML.replace("banks: []", "banks: []\n      composes: [brothers, tumnus]")
        _write(rig_dir, "rig.yaml", yaml)
        config = load_rig(str(rig_dir))
        assert config.controller is not None

    def test_controller_composes_unknown_device(self, rig_dir):
        """Controller with composes referencing invalid device raises error."""
        yaml = BASE_RIG_YAML.replace("banks: []", "banks: []\n      composes: [nonexistent-device]")
        _write(rig_dir, "rig.yaml", yaml)
        with pytest.raises(MissingReferenceError, match="Controller.*composes unknown device"):
            load_rig(str(rig_dir))


# ---------------------------------------------------------------------------
