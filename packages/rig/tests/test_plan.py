import json
from types import SimpleNamespace

from rig.engine.diff import compute_diff
from rig.engine.plan import compute_plan
from rig.engine.plan.models import ParamDiff
from rig.engine.plugin import DeviceType
from rig.models.rig import Rig
from rig_analog.preset import AnalogPreset
from rig_chasebliss.device import ChaseBlissConfig
from rig_chasebliss.preset import DigitalPreset
from rig_hx.preset import HXStompPreset
from tests.conftest import FakeDevice


def _make_rig(scene_presets: dict | None = None) -> Rig:
    hx = FakeDevice(
        id="hx-stomp",
        type=DeviceType.MODELER,
        config={"type": "midi", "midi_channel": 1},
        presets=[
            HXStompPreset(
                id="clean-edge", name="Clean Edge", preset_number=12, hlx_file="hlx/clean-edge.hlx"
            )
        ],
    )
    bro = FakeDevice(
        id="brothers",
        type=DeviceType.DIGITAL,
        config=ChaseBlissConfig(midi_channel=3),
        presets=[DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)],
    )
    tum = FakeDevice(
        id="tumnus",
        type=DeviceType.ANALOG,
        config={"type": "manual"},
    )
    scene_presets = scene_presets or {"hx-stomp": "clean-edge", "brothers": "low-gain"}
    ctrl = FakeDevice(
        id="mc6",
        type=DeviceType.CONTROLLER,
        config=SimpleNamespace(
            scenes={"test-scene": {"presets": scene_presets}},
            type="controller",
            midi_channel=1,
            banks=[],
        ),
    )
    return Rig(
        name="test",
        signal_chain=["hx-stomp"],
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


def _make_rig_with_extra_preset() -> Rig:
    """Rig with an extra DigitalPreset on brothers that is NOT referenced in any scene."""
    hx = FakeDevice(
        id="hx-stomp",
        type=DeviceType.MODELER,
        config={"type": "midi", "midi_channel": 1},
        presets=[
            HXStompPreset(
                id="clean-edge", name="Clean Edge", preset_number=12, hlx_file="hlx/clean-edge.hlx"
            )
        ],
    )
    bro = FakeDevice(
        id="brothers",
        type=DeviceType.DIGITAL,
        config=ChaseBlissConfig(midi_channel=3),
        presets=[
            DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4),
            DigitalPreset(id="high-gain", pedal="brothers", name="High Gain", preset_number=5),
        ],
    )
    tum = FakeDevice(
        id="tumnus",
        type=DeviceType.ANALOG,
        config={"type": "manual"},
    )
    ctrl = FakeDevice(
        id="mc6",
        type=DeviceType.CONTROLLER,
        config=SimpleNamespace(type="controller", midi_channel=1, banks=[]),
    )
    return Rig(
        name="test",
        signal_chain=["hx-stomp"],
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
        hx = FakeDevice(
            id="hx-stomp",
            type=DeviceType.MODELER,
            config={"type": "midi", "midi_channel": 1},
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
        bro = FakeDevice(
            id="brothers",
            type=DeviceType.DIGITAL,
            config=ChaseBlissConfig(midi_channel=3),
            presets=[
                DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)
            ],
        )
        tum = FakeDevice(
            id="tumnus",
            type=DeviceType.ANALOG,
            config={"type": "manual"},
        )
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(type="controller", midi_channel=1, banks=[]),
        )
        rig = Rig(
            name="test",
            signal_chain=["hx-stomp"],
            devices={"hx-stomp": hx, "brothers": bro, "tumnus": tum, "mc6": ctrl},
        )
        plan = compute_plan(rig)
        assert any("unused-patch" in entry and "hx-stomp" in entry for entry in plan.unused_presets)

    def test_analog_presets_excluded_from_unused(self):
        tum = FakeDevice(
            id="tumnus",
            type=DeviceType.ANALOG,
            config={"type": "manual"},
            presets=[
                AnalogPreset(
                    id="edge-of-breakup",
                    pedal="tumnus",
                    name="Edge of Breakup",
                    values={"gain": 5.0},
                )
            ],
        )
        hx = FakeDevice(
            id="hx-stomp",
            type=DeviceType.MODELER,
            config={"type": "midi", "midi_channel": 1},
            presets=[
                HXStompPreset(
                    id="clean-edge",
                    name="Clean Edge",
                    preset_number=12,
                    hlx_file="hlx/clean-edge.hlx",
                )
            ],
        )
        bro = FakeDevice(
            id="brothers",
            type=DeviceType.DIGITAL,
            config=ChaseBlissConfig(midi_channel=3),
            presets=[
                DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)
            ],
        )
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(type="controller", midi_channel=1, banks=[]),
        )
        rig = Rig(
            name="test",
            signal_chain=["hx-stomp"],
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

    def test_analog_gets_verify_when_preset_already_matches_state(self, tmp_path):
        """STATE-01: analog device with matching state gets VERIFY, not ANALOG."""
        rig = _make_rig({"tumnus": "edge-of-breakup"})
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps({"devices": {"tumnus": {"last_preset": "edge-of-breakup"}}, "scenes": {}})
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        tum_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "tumnus"][
            0
        ]
        assert tum_action.status == "verify", (
            f"Expected 'verify' for analog device with matching state, got '{tum_action.status}'"
        )

    def test_analog_gets_analog_when_preset_differs_from_state(self, tmp_path):
        """STATE-01: analog device with different state keeps ANALOG (manual change required)."""
        rig = _make_rig({"tumnus": "edge-of-breakup"})
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps({"devices": {"tumnus": {"last_preset": "crunch"}}, "scenes": {}})
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        tum_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "tumnus"][
            0
        ]
        assert tum_action.status == "analog", (
            f"Expected 'analog' for analog device needing manual change, got '{tum_action.status}'"
        )

    def test_analog_with_no_state_gets_analog(self, tmp_path):
        """STATE-01: analog device with no prior state record always requires manual set."""
        rig = _make_rig({"tumnus": "edge-of-breakup"})
        # No state.json at all — cold start
        plan = compute_plan(rig, root_path=str(tmp_path))
        tum_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "tumnus"][
            0
        ]
        assert tum_action.status == "analog", (
            f"Expected 'analog' for analog device with no state, got '{tum_action.status}'"
        )


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


def _make_ordered_rig() -> Rig:
    """Rig with two signal-chain devices at known positions and an off-chain CBA device."""
    hx = FakeDevice(
        id="hx-stomp",
        type=DeviceType.MODELER,
        config={"type": "midi", "midi_channel": 1},
        presets=[
            HXStompPreset(
                id="clean-edge", name="Clean Edge", preset_number=12, hlx_file="hlx/clean-edge.hlx"
            )
        ],
    )
    tuner = FakeDevice(
        id="polytune",
        type=DeviceType.DIGITAL,
        config={"type": "midi", "midi_channel": 2},
        presets=[DigitalPreset(id="mute", pedal="polytune", name="Mute", preset_number=1)],
    )
    ctrl = FakeDevice(
        id="mc6",
        type=DeviceType.CONTROLLER,
        config=SimpleNamespace(
            scenes={"test-scene": {"presets": {"polytune": "mute", "hx-stomp": "clean-edge"}}},
            type="controller",
            midi_channel=1,
            banks=[],
        ),
    )
    return Rig(
        name="test",
        signal_chain=[
            "polytune",
            "hx-stomp",
        ],
        devices={"hx-stomp": hx, "polytune": tuner, "mc6": ctrl},
    )


def _make_analog_rig_with_presets(presets: list, scene_preset_id: str) -> Rig:
    """Rig with an analog device that has explicit preset objects and a scene reference."""
    tum = FakeDevice(
        id="tumnus",
        type=DeviceType.ANALOG,
        config={"type": "manual"},
        presets=presets,
    )
    ctrl = FakeDevice(
        id="mc6",
        type=DeviceType.CONTROLLER,
        config=SimpleNamespace(
            scenes={"test-scene": {"presets": {"tumnus": scene_preset_id}}},
            type="controller",
            midi_channel=1,
            banks=[],
        ),
    )
    return Rig(
        name="test",
        signal_chain=[],
        devices={"tumnus": tum, "mc6": ctrl},
    )


def _make_digital_rig_with_presets(presets: list, scene_preset_id: str) -> Rig:
    """Rig with a digital (Chase Bliss) device with explicit preset objects."""
    bro = FakeDevice(
        id="brothers",
        type=DeviceType.DIGITAL,
        config=ChaseBlissConfig(midi_channel=3),
        presets=presets,
    )
    ctrl = FakeDevice(
        id="mc6",
        type=DeviceType.CONTROLLER,
        config=SimpleNamespace(
            scenes={"test-scene": {"presets": {"brothers": scene_preset_id}}},
            type="controller",
            midi_channel=1,
            banks=[],
        ),
    )
    return Rig(
        name="test",
        signal_chain=[],
        devices={"brothers": bro, "mc6": ctrl},
    )


class TestParamDiff:
    def test_analog_param_diff_populated_when_no_prior_state(self):
        """PLAN-32-01: analog preset with no prior state yields param_diff with before=None."""
        presets = [
            AnalogPreset(
                id="crunch",
                pedal="tumnus",
                name="Crunch",
                values={"gain": 8.0, "tone": 7.0},
            )
        ]
        rig = _make_analog_rig_with_presets(presets, "crunch")
        plan = compute_plan(rig)
        tum_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "tumnus"][
            0
        ]
        assert tum_action.status == "analog"
        assert len(tum_action.param_diff) == 2
        diff_map = {d.name: d for d in tum_action.param_diff}
        assert diff_map["gain"].before is None
        assert diff_map["gain"].after == 8.0
        assert diff_map["tone"].before is None
        assert diff_map["tone"].after == 7.0

    def test_analog_param_diff_shows_changed_params_only(self, tmp_path):
        """PLAN-32-02: only changed parameters appear in param_diff when switching presets."""
        presets = [
            AnalogPreset(
                id="edge",
                pedal="tumnus",
                name="Edge of Breakup",
                values={"gain": 5.0, "tone": 3.0},
            ),
            AnalogPreset(
                id="crunch",
                pedal="tumnus",
                name="Crunch",
                values={"gain": 8.0, "tone": 3.0},
            ),
        ]
        rig = _make_analog_rig_with_presets(presets, "crunch")
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {}}))
        plan = compute_plan(rig, root_path=str(tmp_path))
        tum_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "tumnus"][
            0
        ]
        assert tum_action.status == "analog"
        # Only gain changed (5.0 → 8.0); tone unchanged (3.0 == 3.0)
        assert len(tum_action.param_diff) == 1
        assert tum_action.param_diff[0].name == "gain"
        assert tum_action.param_diff[0].before == 5.0
        assert tum_action.param_diff[0].after == 8.0

    def test_analog_verify_action_has_empty_param_diff(self, tmp_path):
        """PLAN-32-01 truth: VERIFY actions never have param_diff lines."""
        presets = [
            AnalogPreset(
                id="edge",
                pedal="tumnus",
                name="Edge of Breakup",
                values={"gain": 5.0},
            )
        ]
        rig = _make_analog_rig_with_presets(presets, "edge")
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps(
                {"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {"test-scene": {}}}
            )
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        tum_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "tumnus"][
            0
        ]
        assert tum_action.status == "verify"
        assert tum_action.param_diff == []

    def test_digital_param_diff_populated_when_no_prior_state(self):
        """PLAN-32-03: digital (Chase Bliss) preset with no prior state yields param_diff."""
        presets = [
            DigitalPreset(
                id="low-gain",
                pedal="brothers",
                name="Low Gain",
                preset_number=4,
                parameters={"level": 0.8, "tone": 0.5},
            )
        ]
        rig = _make_digital_rig_with_presets(presets, "low-gain")
        plan = compute_plan(rig)
        bro_action = [
            a for a in plan.scenes["test-scene"].device_actions if a.device == "brothers"
        ][0]
        assert bro_action.status == "configure"
        assert len(bro_action.param_diff) == 2
        diff_map = {d.name: d for d in bro_action.param_diff}
        assert diff_map["level"].before is None
        assert diff_map["level"].after == 0.8

    def test_digital_param_diff_shows_changed_params_only(self, tmp_path):
        """PLAN-32-04: only changed CC parameters appear when switching Chase Bliss presets."""
        presets = [
            DigitalPreset(
                id="low-gain",
                pedal="brothers",
                name="Low Gain",
                preset_number=4,
                parameters={"level": 0.5, "reverb": 0.3},
            ),
            DigitalPreset(
                id="high-gain",
                pedal="brothers",
                name="High Gain",
                preset_number=5,
                parameters={"level": 0.9, "reverb": 0.3},
            ),
        ]
        rig = _make_digital_rig_with_presets(presets, "high-gain")
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps({"devices": {"brothers": {"last_preset": "low-gain"}}, "scenes": {}})
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        bro_action = [
            a for a in plan.scenes["test-scene"].device_actions if a.device == "brothers"
        ][0]
        assert bro_action.status == "configure"
        # Only level changed (0.5 → 0.9); reverb unchanged
        assert len(bro_action.param_diff) == 1
        assert bro_action.param_diff[0].name == "level"
        assert bro_action.param_diff[0].before == 0.5
        assert bro_action.param_diff[0].after == 0.9

    def test_hx_stomp_has_no_param_diff(self):
        """PLAN-32-01: HX Stomp presets produce empty param_diff (no parameters field)."""
        rig = _make_rig()
        plan = compute_plan(rig)
        hx_action = [a for a in plan.scenes["test-scene"].device_actions if a.device == "hx-stomp"][
            0
        ]
        assert hx_action.param_diff == []

    def test_param_diff_is_pydantic_model(self):
        """ParamDiff is serializable as a Pydantic model."""
        diff = ParamDiff(name="gain", before=None, after=8.0)
        assert diff.name == "gain"
        assert diff.before is None
        assert diff.after == 8.0
        data = diff.model_dump()
        assert data == {"name": "gain", "before": None, "after": 8.0}


class TestDeviceOrdering:
    def test_device_actions_sorted_by_apply_order(self):
        """D-07: device_actions within ScenePlan match DeviceGraph.apply_order() sequence."""
        from rig.models.graph import DeviceGraph

        rig = _make_ordered_rig()
        graph = DeviceGraph(rig)
        expected_order = [d.id for d in graph.apply_order()]

        plan = compute_plan(rig)
        scene_plan = plan.scenes["test-scene"]
        actual_order = [a.device for a in scene_plan.device_actions]

        # Filter expected_order to only devices that appear in device_actions
        filtered_expected = [dev_id for dev_id in expected_order if dev_id in actual_order]
        assert actual_order == filtered_expected, (
            f"device_actions order {actual_order!r} does not match apply_order {filtered_expected!r}"
        )

    def test_signal_chain_device_comes_before_off_chain_device(self):
        """D-07: devices in the signal chain appear before off-chain devices in device_actions."""
        hx = FakeDevice(
            id="hx-stomp",
            type=DeviceType.MODELER,
            config={"type": "midi", "midi_channel": 1},
            presets=[
                HXStompPreset(
                    id="clean-edge",
                    name="Clean Edge",
                    preset_number=12,
                    hlx_file="hlx/clean-edge.hlx",
                )
            ],
        )
        bro = FakeDevice(
            id="brothers",
            type=DeviceType.DIGITAL,
            config={"type": "midi", "midi_channel": 3},
            presets=[
                DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)
            ],
        )
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(
                scenes={
                    "test-scene": {"presets": {"brothers": "low-gain", "hx-stomp": "clean-edge"}}
                },
                type="controller",
                midi_channel=1,
                banks=[],
            ),
        )
        rig = Rig(
            name="test",
            signal_chain=["hx-stomp"],
            devices={"hx-stomp": hx, "brothers": bro, "mc6": ctrl},
        )
        plan = compute_plan(rig)
        actions = plan.scenes["test-scene"].device_actions
        device_ids = [a.device for a in actions]

        hx_idx = device_ids.index("hx-stomp")
        bro_idx = device_ids.index("brothers")
        assert hx_idx < bro_idx, (
            f"Signal-chain device 'hx-stomp' (pos {hx_idx}) should precede "
            f"off-chain 'brothers' (pos {bro_idx})"
        )
