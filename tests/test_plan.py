import json
from rig.models.rig import RigConfig
from rig.models.pedal import PedalDefinition, PedalType
from rig.models.preset import DigitalPreset, HXStompPreset, HXBlock
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition
from rig.engine.plan import compute_plan


def _make_rig(scene_presets: dict | None = None) -> RigConfig:
    hx = PedalDefinition(id="hx-stomp", manufacturer="Line6", model="HX Stomp", type=PedalType.MODELER, midi_channel=1)
    bro = PedalDefinition(id="brothers", manufacturer="CBA", model="Brothers", type=PedalType.DIGITAL, midi_channel=3)
    tum = PedalDefinition(id="tumnus", manufacturer="Wampler", model="Tumnus", type=PedalType.ANALOG)
    block = HXBlock(name="Amp", type="amp", model="US Double Nrm", settings={"Drive": 4.5})
    hx_preset = HXStompPreset(id="clean-edge", pedal="hx-stomp", name="Clean Edge", preset_number=12, blocks=[block])
    return RigConfig(
        name="test",
        signal_chain=[SignalChainPosition(pedal_ref="hx-stomp", position=1)],
        pedals={"hx-stomp": hx, "brothers": bro, "tumnus": tum},
        hx_presets={"hx-stomp": [hx_preset]},
        digital_presets={"brothers": [DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)]},
        scenes={
            "test-scene": Scene(
                name="test-scene",
                presets=scene_presets or {"hx-stomp": "clean-edge", "brothers": "low-gain"},
            )
        },
    )


class TestComputePlan:
    def test_plan_clean_when_state_matches(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "devices": {
                "hx-stomp": {"last_preset": "clean-edge"},
                "brothers": {
                    "last_preset": "low-gain",
                    "channel_established": True,
                    "midi_channel": 3,
                    "presets_saved": {"low-gain": True},
                    "registration_done": True,
                },
            },
            "scenes": {"test-scene": {}},
        }))
        plan = compute_plan(rig, root_path=str(tmp_path))
        assert plan.status == "clean"
        assert plan.scenes["test-scene"].status == "unchanged"
        assert plan.cba_setup == []

    def test_plan_detects_new_scene(self, tmp_path):
        rig = _make_rig()
        plan = compute_plan(rig, root_path=str(tmp_path))
        assert plan.status == "changes_detected"
        assert plan.scenes["test-scene"].status == "new"

    def test_plan_detects_changed_preset(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "devices": {"hx-stomp": {"last_preset": "old-preset"}, "brothers": {"last_preset": "low-gain"}},
            "scenes": {"test-scene": {}},
        }))
        plan = compute_plan(rig, root_path=str(tmp_path))
        assert plan.status == "changes_detected"
        hx_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "hx-stomp"][0]
        assert hx_action.status == "configure"
        assert hx_action.preset_number == 12

    def test_plan_lists_analog_instructions(self, tmp_path):
        rig = _make_rig({"tumnus": "edge-of-breakup"})
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({"devices": {}, "scenes": {}}))
        plan = compute_plan(rig, root_path=str(tmp_path))
        analog_actions = [a for a in plan.scenes["test-scene"].device_actions if a.device_type == "analog"]
        assert len(analog_actions) == 1
        assert analog_actions[0].status == "analog"

    def test_plan_unchanged_skip_when_preset_same(self, tmp_path):
        rig = _make_rig({"hx-stomp": "clean-edge"})
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "devices": {"hx-stomp": {"last_preset": "clean-edge"}},
            "scenes": {"test-scene": {}},
        }))
        plan = compute_plan(rig, root_path=str(tmp_path))
        hx_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "hx-stomp"][0]
        assert hx_action.status == "verify"


class TestCbaDetection:
    def test_detects_channel_establishment_needed(self):
        rig = _make_rig()
        plan = compute_plan(rig)
        cba_actions = [a for a in plan.cba_setup if a.device == "brothers"]
        assert any(a.type == "establish_channel" for a in cba_actions)
        assert plan.status == "changes_detected"

    def test_skips_channel_when_already_established(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "devices": {"brothers": {"channel_established": True, "midi_channel": 3}},
        }))
        plan = compute_plan(rig, root_path=str(tmp_path))
        cba = [a for a in plan.cba_setup if a.device == "brothers"]
        assert not any(a.type == "establish_channel" for a in cba)

    def test_detects_preset_build_needed(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "devices": {"brothers": {
                "channel_established": True,
                "midi_channel": 3,
                "presets_saved": {},
            }},
        }))
        plan = compute_plan(rig, root_path=str(tmp_path))
        cba = [a for a in plan.cba_setup if a.device == "brothers"]
        assert any(a.type == "build_preset" for a in cba)
        build = [a for a in cba if a.type == "build_preset"]
        assert len(build) == 1
        assert build[0].preset_id == "low-gain"

    def test_skips_preset_when_already_saved(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "devices": {"brothers": {
                "channel_established": True,
                "midi_channel": 3,
                "presets_saved": {"low-gain": True},
            }},
        }))
        plan = compute_plan(rig, root_path=str(tmp_path))
        cba = [a for a in plan.cba_setup if a.device == "brothers"]
        assert not any(a.type == "build_preset" for a in cba)

    def test_detects_registration_needed(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "devices": {"brothers": {
                "channel_established": True,
                "midi_channel": 3,
                "presets_saved": {"low-gain": True},
            }},
        }))
        plan = compute_plan(rig, root_path=str(tmp_path))
        cba = [a for a in plan.cba_setup if a.device == "brothers"]
        assert any(a.type == "register_scenes" for a in cba)

    def test_non_cba_pedal_ignored(self):
        rig = _make_rig()
        plan = compute_plan(rig)
        assert not any(a.device == "hx-stomp" for a in plan.cba_setup)
        assert not any(a.device == "tumnus" for a in plan.cba_setup)
