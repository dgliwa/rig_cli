import pytest

from rig.catalog.chase_bliss import MOOD_MKII_CONTROLS
from rig.config.errors import ValidationError
from rig.config.loader import load_rig
from rig.engine.plan import compute_plan
from rig.generators.mc6_presets import generate_mc6
from rig.models.device import (
    ChaseBlissConfig,
    Control,
    ControlType,
    ManualConfig,
    MidiConfig,
)
from rig.models.device import (
    Device as PedalDefinition,
)
from rig.models.device import (
    DeviceType as PedalType,
)
from rig.models.preset import DigitalPreset, HXStompPreset
from rig.models.rig import RigConfig

FIXTURE_PATH = "tests/fixtures/sample_rig"


class TestMoodMkiiCatalog:
    def test_has_expected_knob_count(self):
        knobs = [c for c in MOOD_MKII_CONTROLS if c.type == ControlType.KNOB]
        assert len(knobs) == 7

    def test_knobs_have_correct_cc_numbers(self):
        by_name = {c.name: c for c in MOOD_MKII_CONTROLS}
        assert by_name["time"].midi_cc == 14
        assert by_name["mix"].midi_cc == 15
        assert by_name["wet_bypass"].midi_cc == 103
        assert by_name["micro_bypass"].midi_cc == 102

    def test_dip_banks_complete(self):
        l_bank = [c for c in MOOD_MKII_CONTROLS if c.name.startswith("dip_l_")]
        r_bank = [c for c in MOOD_MKII_CONTROLS if c.name.startswith("dip_r_")]
        assert len(l_bank) == 8
        assert len(r_bank) == 8
        assert [c.midi_cc for c in l_bank] == list(range(61, 69))
        assert [c.midi_cc for c in r_bank] == list(range(71, 79))


class TestGetCcParams:
    def _midi_config_with_controls(self):
        return MidiConfig(
            midi_channel=2,
            controls=[
                Control(name="time", type=ControlType.KNOB, midi_cc=14, min=0, max=127),
                Control(name="mix", type=ControlType.KNOB, midi_cc=15, min=0, max=127),
            ],
        )

    def test_returns_cc_value_pairs(self):
        cfg = self._midi_config_with_controls()
        result = cfg.get_cc_params({"time": 64, "mix": 90})
        assert {"cc": 14, "value": 64} in result
        assert {"cc": 15, "value": 90} in result

    def test_unknown_params_excluded(self):
        cfg = self._midi_config_with_controls()
        result = cfg.get_cc_params({"time": 64, "unknown_param": 99})
        assert len(result) == 1
        assert result[0]["cc"] == 14

    def test_empty_params_returns_empty(self):
        cfg = self._midi_config_with_controls()
        assert cfg.get_cc_params({}) == []

    def test_manual_config_returns_empty(self):
        cfg = ManualConfig(controls=[])
        assert cfg.get_cc_params({"anything": 127}) == []

    def test_chase_bliss_config_inherits_midi_config(self):
        cfg = ChaseBlissConfig(
            midi_channel=2,
            controls=[Control(name="time", type=ControlType.KNOB, midi_cc=14, min=0, max=127)],
        )
        result = cfg.get_cc_params({"time": 50})
        assert result == [{"cc": 14, "value": 50}]


class TestGetScenePcCommand:
    def _rig_with_hx_and_digital(self):
        hx_preset = HXStompPreset(id="lead", name="Lead", preset_number=5, hlx_file="lead.hlx")
        digital_preset = DigitalPreset(id="preset-1", pedal="mood", name="Shimmer", preset_number=1)
        hx_pedal = PedalDefinition(
            id="hx-stomp",
            manufacturer="Line 6",
            model="HX Stomp XL",
            type=PedalType.MODELER,
            config=MidiConfig(midi_channel=1),
            presets=[hx_preset],
        )
        mood_pedal = PedalDefinition(
            id="mood",
            manufacturer="Chase Bliss Audio",
            model="MOOD MKII",
            type=PedalType.DIGITAL,
            config=ChaseBlissConfig(midi_channel=2),
            presets=[digital_preset],
        )
        analog_pedal = PedalDefinition(
            id="comp",
            manufacturer="Acme",
            model="Compressor",
            type=PedalType.ANALOG,
            config=ManualConfig(),
        )
        rig = RigConfig(
            name="test",
            signal_chain=[],
            devices={"hx-stomp": hx_pedal, "mood": mood_pedal, "comp": analog_pedal},
        )
        return rig, hx_pedal, mood_pedal, analog_pedal

    def test_hx_pedal_returns_pc_command(self):
        rig, hx_pedal, _, _ = self._rig_with_hx_and_digital()
        cmd = hx_pedal.get_scene_pc_command("lead")
        assert cmd == {"type": "pc", "channel": 1, "value": 5, "label": "hx-stomp: lead"}

    def test_digital_pedal_returns_pc_command(self):
        rig, _, mood_pedal, _ = self._rig_with_hx_and_digital()
        cmd = mood_pedal.get_scene_pc_command("preset-1")
        assert cmd == {"type": "pc", "channel": 2, "value": 1, "label": "mood: preset-1"}

    def test_analog_pedal_returns_none(self):
        rig, _, _, analog_pedal = self._rig_with_hx_and_digital()
        assert analog_pedal.get_scene_pc_command("anything") is None

    def test_unknown_preset_returns_none(self):
        rig, hx_pedal, _, _ = self._rig_with_hx_and_digital()
        assert hx_pedal.get_scene_pc_command("nonexistent") is None


class TestLoaderValidation:
    def test_valid_fixture_loads(self):
        rig = load_rig(FIXTURE_PATH)
        assert rig.name == "sample-rig"
        assert "mood" in rig.pedals
        assert "hx-stomp" in rig.pedals
        assert "mood" in rig.digital_presets
        assert "hx-stomp" in rig.hx_presets

    def test_unknown_cba_param_raises(self, tmp_path):
        (tmp_path / "pedals" / "mood" / "presets").mkdir(parents=True)
        (tmp_path / "scenes").mkdir()
        (tmp_path / "rig.yaml").write_text("name: test\n")
        (tmp_path / "signal-chain.yaml").write_text(
            "chain:\n  - pedal_ref: mood\n    position: 1\n    loop: front\n    stereo: false\n"
        )
        (tmp_path / "pedals" / "mood.yaml").write_text(
            "id: mood\nmanufacturer: Chase Bliss Audio\nmodel: MOOD MKII\ntype: digital\n"
            "config:\n  type: chase_bliss\n  midi_channel: 2\n  controls:\n"
            "    - name: time\n      type: knob\n      midi_cc: 14\n      min: 0\n      max: 127\n"
        )
        (tmp_path / "pedals" / "mood" / "presets" / "p1.yaml").write_text(
            "id: p1\npedal: mood\nname: Test\npreset_number: 1\nparameters:\n  time: 64\n  TYPO_PARAM: 99\n"
        )
        with pytest.raises(ValidationError, match="unknown parameters"):
            load_rig(str(tmp_path))


class TestPlanCcParams:
    def test_build_preset_action_has_cc_params(self, tmp_path):
        import json
        import shutil

        # Copy fixture into tmp_path so we can write state without mutating it
        shutil.copytree(FIXTURE_PATH, tmp_path / "rig", dirs_exist_ok=True)
        rig_root = str(tmp_path / "rig")

        # Simulate channel already established so the plan advances to build_preset
        state_dir = tmp_path / "rig" / ".rig"
        state_dir.mkdir()
        (state_dir / "state.json").write_text(
            json.dumps(
                {
                    "devices": {
                        "mood": {
                            "channel_established": True,
                            "midi_channel": 2,
                            "presets_saved": {},
                            "registration_done": False,
                        }
                    },
                    "scenes": {},
                }
            )
        )

        rig = load_rig(rig_root)
        plan = compute_plan(rig, rig_root)
        build_actions = [a for a in plan.cba_setup if a.type == "build_preset"]
        assert len(build_actions) == 1
        assert len(build_actions[0].cc_params) > 0
        cc_numbers = [p["cc"] for p in build_actions[0].cc_params]
        assert 14 in cc_numbers  # time
        assert 15 in cc_numbers  # mix


class TestMc6GeneratorDigitalPedals:
    def test_generates_pc_for_hx_and_mood(self):
        rig = load_rig(FIXTURE_PATH)
        out = generate_mc6(rig)
        commands = out["bank1"]["presets"]["A"]["commands"]
        channels = {cmd["channel"] for cmd in commands}
        assert 1 in channels  # HX Stomp on ch1
        assert 2 in channels  # Mood on ch2

    def test_hx_correct_preset_number(self):
        rig = load_rig(FIXTURE_PATH)
        out = generate_mc6(rig)
        hx_cmd = next(c for c in out["bank1"]["presets"]["A"]["commands"] if c["channel"] == 1)
        assert hx_cmd["value"] == 5

    def test_mood_correct_preset_number(self):
        rig = load_rig(FIXTURE_PATH)
        out = generate_mc6(rig)
        mood_cmd = next(c for c in out["bank1"]["presets"]["A"]["commands"] if c["channel"] == 2)
        assert mood_cmd["value"] == 1
