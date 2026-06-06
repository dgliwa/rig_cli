import json

from rig.engine.diff import compute_diff
from rig.engine.plan import compute_plan
from rig.models.device import (
    ChaseBlissConfig,
    ControllerConfig,
    Device,
    DeviceType,
    ManualConfig,
    MidiConfig,
)
from rig.models.preset import AnalogPreset, DigitalPreset, HXStompPreset
from rig.models.rig import Rig
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition


def _make_rig(scene_presets: dict | None = None) -> Rig:
    hx = Device(
        id="hx-stomp",
        manufacturer="Line6",
        model="HX Stomp",
        type=DeviceType.MODELER,
        config=MidiConfig(midi_channel=1),
        presets=[
            HXStompPreset(
                id="clean-edge", name="Clean Edge", preset_number=12, hlx_file="hlx/clean-edge.hlx"
            )
        ],
    )
    bro = Device(
        id="brothers",
        manufacturer="CBA",
        model="Brothers",
        type=DeviceType.DIGITAL,
        config=ChaseBlissConfig(midi_channel=3),
        presets=[DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)],
    )
    tum = Device(
        id="tumnus",
        manufacturer="Wampler",
        model="Tumnus",
        type=DeviceType.ANALOG,
        config=ManualConfig(),
    )
    ctrl = Device(
        id="mc6",
        manufacturer="Morningstar",
        model="MC6",
        type=DeviceType.CONTROLLER,
        config=ControllerConfig(
            midi_channel=1,
            scenes={
                "test-scene": Scene(
                    name="test-scene",
                    presets=scene_presets or {"hx-stomp": "clean-edge", "brothers": "low-gain"},
                )
            },
        ),
    )
    return Rig(
        name="test",
        signal_chain=[SignalChainPosition(device_ref="hx-stomp", position=1)],
        devices={"hx-stomp": hx, "brothers": bro, "tumnus": tum, "mc6": ctrl},
    )


class TestComputePlan:
    def test_plan_clean_when_state_matches(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps(
                {
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
                }
            )
        )
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
        state.write_text(
            json.dumps(
                {
                    "devices": {
                        "hx-stomp": {"last_preset": "old-preset"},
                        "brothers": {"last_preset": "low-gain"},
                    },
                    "scenes": {"test-scene": {}},
                }
            )
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        assert plan.status == "changes_detected"
        hx_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "hx-stomp"][
            0
        ]
        assert hx_action.status == "configure"
        assert hx_action.preset_number == 12

    def test_plan_lists_analog_instructions(self, tmp_path):
        rig = _make_rig({"tumnus": "edge-of-breakup"})
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({"devices": {}, "scenes": {}}))
        plan = compute_plan(rig, root_path=str(tmp_path))
        analog_actions = [
            a for a in plan.scenes["test-scene"].device_actions if a.device_type == "analog"
        ]
        assert len(analog_actions) == 1
        assert analog_actions[0].status == "analog"

    def test_plan_unchanged_skip_when_preset_same(self, tmp_path):
        rig = _make_rig({"hx-stomp": "clean-edge"})
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps(
                {
                    "devices": {"hx-stomp": {"last_preset": "clean-edge"}},
                    "scenes": {"test-scene": {}},
                }
            )
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        hx_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "hx-stomp"][
            0
        ]
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
        state.write_text(
            json.dumps(
                {
                    "devices": {"brothers": {"channel_established": True, "midi_channel": 3}},
                }
            )
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        cba = [a for a in plan.cba_setup if a.device == "brothers"]
        assert not any(a.type == "establish_channel" for a in cba)

    def test_detects_preset_build_needed(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps(
                {
                    "devices": {
                        "brothers": {
                            "channel_established": True,
                            "midi_channel": 3,
                            "presets_saved": {},
                        }
                    },
                }
            )
        )
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
        state.write_text(
            json.dumps(
                {
                    "devices": {
                        "brothers": {
                            "channel_established": True,
                            "midi_channel": 3,
                            "presets_saved": {"low-gain": True},
                        }
                    },
                }
            )
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        cba = [a for a in plan.cba_setup if a.device == "brothers"]
        assert not any(a.type == "build_preset" for a in cba)

    def test_detects_registration_needed(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps(
                {
                    "devices": {
                        "brothers": {
                            "channel_established": True,
                            "midi_channel": 3,
                            "presets_saved": {"low-gain": True},
                        }
                    },
                }
            )
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        cba = [a for a in plan.cba_setup if a.device == "brothers"]
        assert any(a.type == "register_scenes" for a in cba)

    def test_non_cba_pedal_ignored(self):
        rig = _make_rig()
        plan = compute_plan(rig)
        assert not any(a.device == "hx-stomp" for a in plan.cba_setup)
        assert not any(a.device == "tumnus" for a in plan.cba_setup)


def _make_rig_with_extra_preset() -> Rig:
    """Rig with an extra DigitalPreset on brothers that is NOT referenced in any scene."""
    hx = Device(
        id="hx-stomp",
        manufacturer="Line6",
        model="HX Stomp",
        type=DeviceType.MODELER,
        config=MidiConfig(midi_channel=1),
        presets=[
            HXStompPreset(
                id="clean-edge", name="Clean Edge", preset_number=12, hlx_file="hlx/clean-edge.hlx"
            )
        ],
    )
    bro = Device(
        id="brothers",
        manufacturer="CBA",
        model="Brothers",
        type=DeviceType.DIGITAL,
        config=ChaseBlissConfig(midi_channel=3),
        presets=[
            DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4),
            DigitalPreset(id="high-gain", pedal="brothers", name="High Gain", preset_number=5),
        ],
    )
    tum = Device(
        id="tumnus",
        manufacturer="Wampler",
        model="Tumnus",
        type=DeviceType.ANALOG,
        config=ManualConfig(),
    )
    ctrl = Device(
        id="mc6",
        manufacturer="Morningstar",
        model="MC6",
        type=DeviceType.CONTROLLER,
        config=ControllerConfig(
            midi_channel=1,
            scenes={
                "test-scene": Scene(
                    name="test-scene",
                    presets={"hx-stomp": "clean-edge", "brothers": "low-gain"},
                )
            },
        ),
    )
    return Rig(
        name="test",
        signal_chain=[SignalChainPosition(device_ref="hx-stomp", position=1)],
        devices={"hx-stomp": hx, "brothers": bro, "tumnus": tum, "mc6": ctrl},
    )


class TestMissingRefs:
    def test_missing_device_in_scene(self):
        rig = _make_rig({"ghost-device": "some-preset"})
        plan = compute_plan(rig)
        assert any("ghost-device" in entry and "not found" in entry for entry in plan.missing_refs)

    def test_missing_preset_on_existing_device(self):
        rig = _make_rig({"hx-stomp": "nonexistent-preset"})
        plan = compute_plan(rig)
        assert any(
            "hx-stomp" in entry and "nonexistent-preset" in entry for entry in plan.missing_refs
        )

    def test_valid_refs_produce_empty_missing_refs(self):
        rig = _make_rig()
        plan = compute_plan(rig)
        assert plan.missing_refs == []


class TestUnusedPresets:
    def test_unused_digital_preset_detected(self):
        rig = _make_rig_with_extra_preset()
        plan = compute_plan(rig)
        assert any("high-gain" in entry and "brothers" in entry for entry in plan.unused_presets)

    def test_unused_hx_preset_detected(self):
        hx = Device(
            id="hx-stomp",
            manufacturer="Line6",
            model="HX Stomp",
            type=DeviceType.MODELER,
            config=MidiConfig(midi_channel=1),
            presets=[
                HXStompPreset(
                    id="clean-edge",
                    name="Clean Edge",
                    preset_number=12,
                    hlx_file="hlx/clean-edge.hlx",
                ),
                HXStompPreset(
                    id="unused-patch",
                    name="Unused Patch",
                    preset_number=13,
                    hlx_file="hlx/unused-patch.hlx",
                ),
            ],
        )
        bro = Device(
            id="brothers",
            manufacturer="CBA",
            model="Brothers",
            type=DeviceType.DIGITAL,
            config=ChaseBlissConfig(midi_channel=3),
            presets=[
                DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)
            ],
        )
        tum = Device(
            id="tumnus",
            manufacturer="Wampler",
            model="Tumnus",
            type=DeviceType.ANALOG,
            config=ManualConfig(),
        )
        ctrl = Device(
            id="mc6",
            manufacturer="Morningstar",
            model="MC6",
            type=DeviceType.CONTROLLER,
            config=ControllerConfig(
                midi_channel=1,
                scenes={
                    "test-scene": Scene(
                        name="test-scene",
                        presets={"hx-stomp": "clean-edge", "brothers": "low-gain"},
                    )
                },
            ),
        )
        rig = Rig(
            name="test",
            signal_chain=[SignalChainPosition(device_ref="hx-stomp", position=1)],
            devices={"hx-stomp": hx, "brothers": bro, "tumnus": tum, "mc6": ctrl},
        )
        plan = compute_plan(rig)
        assert any("unused-patch" in entry and "hx-stomp" in entry for entry in plan.unused_presets)

    def test_analog_presets_excluded_from_unused(self):
        tum = Device(
            id="tumnus",
            manufacturer="Wampler",
            model="Tumnus",
            type=DeviceType.ANALOG,
            config=ManualConfig(),
            presets=[
                AnalogPreset(
                    id="edge-of-breakup",
                    pedal="tumnus",
                    name="Edge of Breakup",
                    values={"gain": 5.0},
                )
            ],
        )
        hx = Device(
            id="hx-stomp",
            manufacturer="Line6",
            model="HX Stomp",
            type=DeviceType.MODELER,
            config=MidiConfig(midi_channel=1),
            presets=[
                HXStompPreset(
                    id="clean-edge",
                    name="Clean Edge",
                    preset_number=12,
                    hlx_file="hlx/clean-edge.hlx",
                )
            ],
        )
        bro = Device(
            id="brothers",
            manufacturer="CBA",
            model="Brothers",
            type=DeviceType.DIGITAL,
            config=ChaseBlissConfig(midi_channel=3),
            presets=[
                DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)
            ],
        )
        ctrl = Device(
            id="mc6",
            manufacturer="Morningstar",
            model="MC6",
            type=DeviceType.CONTROLLER,
            config=ControllerConfig(
                midi_channel=1,
                scenes={
                    "test-scene": Scene(
                        name="test-scene",
                        presets={"hx-stomp": "clean-edge", "brothers": "low-gain"},
                    )
                },
            ),
        )
        rig = Rig(
            name="test",
            signal_chain=[SignalChainPosition(device_ref="hx-stomp", position=1)],
            devices={"hx-stomp": hx, "brothers": bro, "tumnus": tum, "mc6": ctrl},
        )
        plan = compute_plan(rig)
        assert not any("tumnus" in entry for entry in plan.unused_presets)

    def test_all_referenced_produces_empty_unused_presets(self):
        rig = _make_rig()
        plan = compute_plan(rig)
        assert plan.unused_presets == []


class TestBeforeAfterFields:
    def test_before_none_when_no_prior_state(self):
        rig = _make_rig()
        plan = compute_plan(rig)
        hx_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "hx-stomp"][
            0
        ]
        assert hx_action.before is None
        assert hx_action.after == "clean-edge"

    def test_before_populated_from_state(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps({"devices": {"hx-stomp": {"last_preset": "old-patch"}}, "scenes": {}})
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        hx_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "hx-stomp"][
            0
        ]
        assert hx_action.before == "old-patch"
        assert hx_action.after == "clean-edge"

    def test_analog_action_has_before_after(self):
        rig = _make_rig({"tumnus": "edge-of-breakup"})
        plan = compute_plan(rig)
        tum_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "tumnus"][
            0
        ]
        assert tum_action.after == "edge-of-breakup"
        assert tum_action.before is None


class TestComputeDiff:
    def test_diff_unchanged_when_state_matches(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps(
                {
                    "devices": {
                        "hx-stomp": {"last_preset": "clean-edge"},
                        "brothers": {"last_preset": "low-gain"},
                    },
                    "scenes": {"test-scene": {}},
                }
            )
        )
        changes = compute_diff(rig, root_path=str(tmp_path))
        assert changes["scenes"] == {}

    def test_diff_changed_when_preset_differs(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps(
                {
                    "devices": {"hx-stomp": {"last_preset": "old-patch"}},
                    "scenes": {"test-scene": {}},
                }
            )
        )
        changes = compute_diff(rig, root_path=str(tmp_path))
        assert "test-scene" in changes["scenes"]
        assert changes["scenes"]["test-scene"]["_status"] == "changed"
