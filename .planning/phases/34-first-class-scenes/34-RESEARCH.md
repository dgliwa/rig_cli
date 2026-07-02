# Phase 34: First-Class Scenes — Research

**Researched:** 2026-07-01
**Domain:** Python / Pydantic domain model refactor; YAML schema migration; engine wiring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Hard cutover — no dual-read fallback. `MC6Config.scenes` is removed entirely (field dropped). Existing `rig.yaml` files with scenes under `config.scenes` must be migrated; the loader will not read them from there.
- **D-02:** All test fixtures must be updated to the new top-level `scenes:` schema as part of this phase.
- **D-03:** Scenes live inline in `rig.yaml` under a top-level `scenes:` block — same structure as today but promoted out of the controller device. No separate `scenes/` directory support in this phase.
- **D-04:** `MC6Config.scenes` field is removed entirely. MC6Config contains `banks` only. Banks reference scene names (strings); scene definitions live at the top level of `rig.yaml`. No silent-ignore, no deprecation warning — the field simply doesn't exist.
- **D-05:** `rig apply --scene <name>` works without a controller device. The engine iterates the scene's `presets` map and applies each device's preset (MIDI PC for digital/modeler, analog prompt for analog). MC6 bank/switch programming is skipped if no controller device is present. No error, no warning — controller is optional.

### Claude's Discretion
- Exact YAML key name for top-level scenes (`scenes:` seems natural; confirm in implementation).
- Whether `Rig.scenes` stays `dict[str, Scene]` or needs ordering guarantees.
- How `Rig.controller` property and `Rig.scenes` property are updated (property → real field migration approach).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 34 promotes scene definitions from being buried inside the MC6 controller device's `config.scenes` block to a proper top-level `scenes:` key in `rig.yaml`. The change has three interlocking parts: (1) `Rig.scenes` changes from a computed `@property` that aggregates from controller devices to a real Pydantic field loaded directly from YAML, (2) `MC6Config.scenes` field is removed entirely so MC6Config only knows about banks, and (3) `apply_plan` already handles controller-less rigs correctly — the controller programming phase is gated on `if rig and rig.controller and not scene and not device_filter`, so D-05 is already satisfied in the engine.

The blast radius is well-contained. All consumers of `rig.scenes` — plan compute, diff, apply, CLI commands, CBA device — already treat `rig.scenes` as `dict[str, Scene]` and will work transparently once the property becomes a real field. The only callers that need active changes are: loader.py (read `scenes:` from top-level YAML, pass to `Rig(...)`), `Rig` model (replace property with field), `MC6Config` (remove `scenes` field, handle `extra`), test fixtures that embed scenes inside `mc6.config.scenes`, and test_models.py which has a test asserting `scenes` is NOT a Pydantic field.

**Primary recommendation:** Replace the property with a field, update the loader to parse top-level `scenes:`, remove `MC6Config.scenes`, remove `MC6Config.extra="ignore"`, and migrate all fixtures and tests to the new schema.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Scene storage / schema | Domain Model (`Rig`) | YAML loader | `Rig.scenes` is the canonical in-memory store; loader parses YAML into it |
| Scene loading from YAML | Config Loader | — | `loader.py::load_rig` reads `rig.yaml` and constructs `Rig(scenes=...)` |
| Scene-to-device-preset mapping | Plan Engine | — | `compute_plan` iterates `rig.scenes` to build device actions |
| MC6 bank programming (controller) | MC6Device plugin | Apply Engine | `apply_plan` dispatches to `MC6Device.apply()` only when a controller is present |
| Controller-less scene apply | Apply Engine | — | Already gated: controller programming phase runs `if rig.controller` |
| Scene reference validation | Config Loader | — | `_validate_references` iterates `rig.scenes` — no change needed to logic |
| CBA 3-phase setup targeting | CBA Device plugin | — | `ChaseBlissDevice.setup()` calls `ctx.rig.scenes.get(ctx.target_scene)` |

---

## Current State Analysis

### Rig.scenes — current implementation

`packages/rig/src/rig/models/rig.py` — `scenes` is a `@property` (lines 18–38):

```python
@property
def scenes(self) -> dict[str, Scene]:
    aggregated: dict[str, Scene] = {}
    for device in self.devices.values():
        if device.type == DeviceType.CONTROLLER:
            cfg = device.config
            raw_scenes = getattr(cfg, "scenes", {})
            for name, data in raw_scenes.items():
                if isinstance(data, dict):
                    aggregated[name] = Scene(
                        name=name,
                        description=data.get("description"),
                        presets=data.get("presets", {}),
                        tags=data.get("tags", []),
                    )
    return aggregated
```

This property: (a) only works when a controller device exists, (b) reads raw dicts and constructs `Scene` objects on every call, (c) does not support the `tempo` field on `Scene`, and (d) blocks D-05 (controller-less apply) at the model level.

### MC6Config — current implementation

`packages/rig-morningstar/src/rig_morningstar/config.py`:

```python
class MC6Config(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["controller"] = "controller"
    scenes: dict[str, Any] = Field(default_factory=dict)
    banks: list[dict[str, Any]] = Field(default_factory=list)
```

Two things to remove: `scenes` field and `extra="ignore"`. The `extra="ignore"` setting currently causes old YAML files with `scenes:` under the controller config to silently pass through Pydantic without error even after the field is removed. For a hard cutover (D-01, D-04), `extra="ignore"` must also be removed — or replaced with `extra="forbid"` — so that stale `scenes:` data under the controller raises a Pydantic `ValidationError` rather than being silently discarded. [ASSUMED: "forbid" vs "remove entirely" is implementation choice — recommend "forbid" for strictness, but either satisfies D-04 since D-04 says "field simply doesn't exist".]

### loader.py — current scene loading

`packages/rig/src/rig/config/loader.py` — no explicit scene-loading code. The loader currently just:
1. Parses devices (line 150–153): `_parse_device(device_entry)` dispatches to plugin `from_raw_yaml`
2. Constructs `Rig(name=..., signal_chain=..., devices=...)` (lines 155–161) — no `scenes=` arg
3. Calls `_validate_references(rig)` which iterates `rig.scenes` (lines 101–115)

The `_validate_references` function already iterates `rig.scenes` by calling `.items()` — this works transparently whether `scenes` is a property or a field. No changes needed to validation logic, only to the `Rig(...)` constructor call (add `scenes=scenes_dict`).

### Where scenes data lives in the YAML today

`packages/rig/tests/fixtures/sample_rig/rig.yaml` — scenes are nested four levels deep:

```yaml
devices:
  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      scenes:             # <-- must move to top level
        lead:
          description: Lead tone with Mood shimmer delay
          presets:
            hx-stomp: lead
            mood: preset-1
          tags: [lead]
      banks:
        ...
```

After migration, the fixture becomes:

```yaml
scenes:                   # <-- top-level key
  lead:
    description: Lead tone with Mood shimmer delay
    presets:
      hx-stomp: lead
      mood: preset-1
    tags: [lead]

devices:
  - id: mc6
    name: MC6
    type: controller
    config:
      type: controller
      midi_channel: 1
      banks:
        ...
```

---

## Change Impact Map

### Files requiring code changes

| File | Change Required |
|------|----------------|
| `packages/rig/src/rig/models/rig.py` | Replace `@property def scenes(...)` with `scenes: dict[str, Scene] = {}` Pydantic field |
| `packages/rig/src/rig/config/loader.py` | Parse `data.get("scenes", {})` from top-level YAML; construct `Scene` objects; pass `scenes=scenes_dict` to `Rig(...)` constructor; update docstring |
| `packages/rig-morningstar/src/rig_morningstar/config.py` | Remove `scenes` field from `MC6Config`; remove `extra="ignore"` (or set to `"forbid"`) |

### Files requiring test changes

| File | Change Required |
|------|----------------|
| `packages/rig/tests/test_models.py` | `test_rig_controller_and_scenes_are_not_pydantic_fields` asserts `"scenes" not in Rig.model_fields` — must be inverted (or renamed and fixed); `test_rig_scenes_returns_empty_when_no_controller` and `test_rig_scenes_returns_controller_config_scenes` both test the old property behavior — must be rewritten to pass `scenes=` directly to `Rig(...)` |
| `packages/rig/tests/test_loader.py` | `BASE_RIG_YAML` has scenes inside `mc6.config.scenes` block — must migrate to top-level `scenes:`; `test_loads_scenes_from_controller` and `test_scenes_accessible_via_controller` test names imply old schema — tests still valid after fixture migration but names should be updated to reflect new schema |
| `packages/rig/tests/test_plan.py` | All `_make_rig()` and similar builder helpers construct `FakeDevice(config=SimpleNamespace(scenes={...}, ...))` — this works today because `Rig.scenes` reads from the controller config. After the change, `Rig.scenes` is a field, so the `Rig(...)` constructor call in each builder must pass `scenes={...}` directly. The `SimpleNamespace` configs can drop `scenes=` |
| `packages/rig/tests/test_apply.py` | Same as test_plan.py: every `_make_config()` and `_make_two_device_rig()` and inline Rig builds that put scenes on `FakeDevice.config` must move scenes to `Rig(scenes=...)` |
| `packages/rig/tests/test_apply_device_preset.py` | Uses `Rig(...)` with `FakeDevice` controllers — check if any set `config.scenes` (needs inspection) |
| `packages/rig/tests/fixtures/sample_rig/rig.yaml` | Migrate `mc6.config.scenes` to top-level `scenes:` |

### Complete list of `Rig.scenes` consumers (no logic change needed)

These files call `rig.scenes` but need no changes — they work with the dict interface unchanged:

| File | Usage |
|------|-------|
| `packages/rig/src/rig/config/loader.py` | `_validate_references`: iterates `rig.scenes.items()` |
| `packages/rig/src/rig/config/loader.py` | `load_rig` log: `len(rig.scenes)` |
| `packages/rig/src/rig/engine/plan/compute.py` | `compute_plan`: iterates `rig.scenes.items()`, `rig.scenes.values()` |
| `packages/rig/src/rig/engine/diff.py` | `compute_diff`: iterates `config.scenes.items()`, checks `actual.scenes` (RigState, different object) |
| `packages/rig/src/rig/engine/apply.py` | No direct `rig.scenes` call — reads from `plan.scenes` |
| `packages/rig/src/rig/cli/commands/status.py` | `list(rig.scenes.keys())` |
| `packages/rig/src/rig/cli/commands/validate.py` | `len(rig.scenes)` |
| `packages/rig/src/rig/cli/commands/plan.py` | Uses `result.scenes` (plan object, not rig) |
| `packages/rig-chasebliss/src/rig_chasebliss/device.py` | `rig.scenes.items()` (line 168), `ctx.rig.scenes.get(ctx.target_scene)` (line 242) |
| `packages/rig-morningstar/src/rig_morningstar/device.py` | `rig.scenes.get(scene_name)` (line 115) |

### Consumers of `MC6Config.scenes` (all change targets)

| Location | Current use | What changes |
|----------|-------------|--------------|
| `packages/rig-morningstar/src/rig_morningstar/config.py` | Field definition | Remove field |
| `packages/rig/src/rig/models/rig.py` | `getattr(cfg, "scenes", {})` in property | Property removed entirely |
| Test YAML fixtures embedding scenes in controller config | Data location | Move scenes to top level |
| Test builder helpers with `SimpleNamespace(scenes={...})` | Passes scenes via controller config | Move scenes to `Rig(scenes=...)` |

---

## Implementation Notes

### 1. Rig model change — property to field

Replace the property with a typed Pydantic field. The `Scene` import is already present.

```python
# before
@property
def scenes(self) -> dict[str, Scene]:
    ...aggregates from controller...

# after
scenes: dict[str, Scene] = {}
```

Ordering guarantee: Python 3.7+ dicts preserve insertion order. `dict[str, Scene]` is sufficient — no `OrderedDict` needed.

The `DeviceType` and `Device` imports in `rig.py` are only used by the `controller` property and `apply_order()`. The `DeviceType` import is still needed for the `controller` property; `Device` type annotation is still needed. No import cleanup required.

### 2. Loader change — parse scenes from top level

```python
# In load_rig(), after extracting rig_name/description/midi_channel:
raw_scenes: dict[str, Any] = data.get("scenes") or {}
scenes: dict[str, Scene] = {}
for scene_name, scene_data in raw_scenes.items():
    if isinstance(scene_data, dict):
        scenes[scene_name] = Scene(
            name=scene_name,
            description=scene_data.get("description"),
            tempo=scene_data.get("tempo"),
            presets=scene_data.get("presets", {}),
            tags=scene_data.get("tags", []),
        )

# Then pass to Rig constructor:
rig = Rig(
    name=rig_name,
    description=rig_description,
    midi_channel=rig_midi_channel,
    signal_chain=signal_chain,
    devices=devices,
    scenes=scenes,       # NEW
)
```

Note: The current property implementation silently drops the `tempo` field (line 33 in rig.py does not pass `tempo`). The loader should pass `tempo` so Scene objects are fully hydrated.

Also update the module docstring — lines 15–22 show `scenes:` under the controller config; update to show the new top-level location.

### 3. MC6Config change — remove scenes field and extra="ignore"

```python
# before
class MC6Config(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["controller"] = "controller"
    scenes: dict[str, Any] = Field(default_factory=dict)
    banks: list[dict[str, Any]] = Field(default_factory=list)

# after
class MC6Config(BaseModel):
    model_config = ConfigDict(extra="forbid")   # strict: reject unknown fields
    type: Literal["controller"] = "controller"
    banks: list[dict[str, Any]] = Field(default_factory=list)
```

**Recommendation: use `extra="forbid"`** rather than removing `model_config` entirely. This means any rig.yaml that still has `scenes:` under the controller config will produce a clear Pydantic `ValidationError` at load time — which is the right behavior for a hard cutover (D-01, D-04). Without `extra="forbid"`, Pydantic's default is to silently ignore extra fields, which partially defeats D-01.

The only existing test for MC6Config is `packages/rig-morningstar/tests/test_mc6_device.py` — none of the four tests set `scenes` on the config, so they pass without modification. However, a new test verifying that `scenes:` under the controller config raises `ValidationError` should be added as a Nyquist requirement.

### 4. Test builder helpers — the `SimpleNamespace` pattern

Many test files build a `FakeDevice` controller with `config=SimpleNamespace(scenes={...})`. After the change, `rig.scenes` no longer reads from device configs. The pattern in every `_make_rig()`, `_make_config()`, `_make_two_device_rig()`, etc. must change from:

```python
# before
ctrl = FakeDevice(
    id="mc6",
    type=DeviceType.CONTROLLER,
    config=SimpleNamespace(
        scenes={"test-scene": {"presets": {"hx-stomp": "clean-edge"}}},
        ...
    ),
)
return Rig(name="test", ..., devices={"mc6": ctrl})
```

to:

```python
# after
ctrl = FakeDevice(
    id="mc6",
    type=DeviceType.CONTROLLER,
    config=SimpleNamespace(type="controller", midi_channel=1, banks=[]),  # no scenes
)
return Rig(
    name="test",
    ...,
    devices={"mc6": ctrl},
    scenes={"test-scene": Scene(name="test-scene", presets={"hx-stomp": "clean-edge"})},
)
```

This pattern appears in: `test_plan.py::_make_rig`, `test_plan.py::_make_ordered_rig`, `test_plan.py::_make_analog_rig_with_presets`, `test_plan.py::_make_digital_rig_with_presets`, `test_plan.py::_make_rig_with_extra_preset`, `test_apply.py::_make_config`, `test_apply.py::TestDevicePluginRouting::_make_concrete_config`, `test_apply.py::TestVerifyActionSkipped` (inline), `test_apply.py::TestDeviceFilterApply::_make_two_device_rig`, `test_apply.py::TestVerifyDisplay` (inline), `test_models.py::_make_controller_device`.

### 5. Controller-less apply — already works

`apply_plan` in `engine/apply.py` line 170:

```python
if rig and rig.controller and not scene and not device_filter:
    # controller programming phase
```

This block is already gated on `rig.controller` being non-None. Since `Rig.controller` is a `@property` that scans `devices` for `DeviceType.CONTROLLER`, a rig with no controller device correctly returns `None` and skips the programming phase. D-05 is satisfied by existing code — no engine changes needed.

Similarly, `compute_plan` iterates `rig.scenes` directly, not through the controller. Once scenes are a top-level field, a rig without a controller will still plan and apply scenes correctly.

### 6. CBA device — scenes access is already correct

`ChaseBlissDevice.setup()` (line 242): `scene = ctx.rig.scenes.get(ctx.target_scene)` — accesses `rig.scenes` as a dict. Works unchanged after the field migration.

`_detect_cba_setup_for_device` (line 168): `scene_refs = [sn for sn, s in rig.scenes.items() if device.id in s.presets]` — iterates `rig.scenes` items. Works unchanged.

### 7. MC6Device.apply() — scenes access is already correct

`packages/rig-morningstar/src/rig_morningstar/device.py` line 115:
`scene_obj = rig.scenes.get(scene_name) if rig and hasattr(rig, "scenes") else None`

The `hasattr(rig, "scenes")` guard is now unnecessary once `scenes` is a proper field (it's always present), but it is harmless to leave in place. Recommend removing it for cleanliness as it obscures intent, but it is not a correctness issue.

---

## MC6Config.extra="ignore" — Analysis and Recommendation

**Current behavior:** `extra="ignore"` silently discards any YAML fields not on the model. This means that after removing the `scenes` field from `MC6Config`, a rig.yaml with:
```yaml
config:
  type: controller
  scenes:           # stale data from old schema
    lead: ...
  banks: [...]
```
would be silently accepted by Pydantic — the `scenes` block would be discarded without error. This violates the hard-cutover intent (D-01, D-04).

**Recommendation: change to `extra="forbid"`.**

With `extra="forbid"`, the same YAML causes a Pydantic `ValidationError` at `MC6Config(**config_data)` time, which bubbles up through `MC6Device.from_raw_yaml()` → `_parse_device()` → `load_rig()` as an uncaught exception (currently not wrapped in `ConfigError`). The loader should either let it propagate as-is (which would surface as an unhandled exception) or wrap it in `ValidationError` from `rig.config.errors`. Review `_parse_device()` to ensure Pydantic validation errors are handled gracefully.

Note: `ChaseBlissConfig` also uses `extra="ignore"`. This is not in scope for this phase (D-04 specifically targets `MC6Config.scenes`), but the same rationale applies.

---

## Fixture Migration Map

All fixtures that embed scenes under the controller config must be updated:

| Fixture / YAML string | Location | Change |
|-----------------------|----------|--------|
| `packages/rig/tests/fixtures/sample_rig/rig.yaml` | On-disk file | Move `mc6.config.scenes` block to top-level `scenes:` |
| `BASE_RIG_YAML` in `test_loader.py` | Python string constant | Move `mc6.config.scenes` to top-level `scenes:` |
| All inline YAML strings in `test_loader.py` that embed scenes | Various test methods | Update per-test |

---

## Nyquist Validation Requirements

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (current suite: 399 tests, all passing) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/rig/tests/ -q` |
| Full suite command | `make test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | Hard cutover: old `mc6.config.scenes` rejected, not silently ignored | unit | `uv run pytest packages/rig-morningstar/tests/test_mc6_device.py -k "reject" -x` | No — Wave 0 |
| D-02 | All fixtures use new top-level `scenes:` schema | integration | `make test` | Partial — existing tests pass fixtures; fixtures need migration |
| D-03 | `load_rig` parses `scenes:` from top-level YAML into `Rig.scenes` | unit | `uv run pytest packages/rig/tests/test_loader.py -x` | Partial — existing test `test_loads_scenes_from_controller` must become `test_loads_scenes_from_top_level` |
| D-04 | `MC6Config` has no `scenes` field; `"banks"` is its only config key | unit | `uv run pytest packages/rig-morningstar/tests/ -x` | Partial — existing tests don't verify field absence |
| D-05 | `apply_plan` runs scene apply without controller device; skips controller programming phase | unit | `uv run pytest packages/rig/tests/test_apply.py -k "no_controller" -x` | No — Wave 0 |
| — | `Rig.scenes` is a real Pydantic field (in `model_fields`) | unit | `uv run pytest packages/rig/tests/test_models.py -x` | Partial — existing test asserts OPPOSITE; must invert |
| — | `Rig(scenes={"s": Scene(...)})` constructor works | unit | `uv run pytest packages/rig/tests/test_models.py -x` | No — Wave 0 |
| — | `compute_plan` produces correct plan when `rig.scenes` is populated as a field (not via controller) | integration | `uv run pytest packages/rig/tests/test_plan.py -x` | Partial — after builder helpers are migrated |
| — | `Scene.tempo` is preserved through loader round-trip | unit | `uv run pytest packages/rig/tests/test_loader.py -k "tempo" -x` | No — Wave 0 |

### Wave 0 Gaps (tests that must be created before implementation)

- [ ] `packages/rig/tests/test_models.py` — add: `test_rig_scenes_is_pydantic_field`, `test_rig_scenes_constructor_accepts_scene_dict`, `test_rig_scenes_empty_by_default`; update: `test_rig_controller_and_scenes_are_not_pydantic_fields` (rename + invert scenes assertion)
- [ ] `packages/rig/tests/test_loader.py` — add: `test_loads_scenes_from_top_level_yaml`, `test_loader_preserves_scene_tempo`, `test_loader_rejects_scenes_in_controller_config` (when `extra="forbid"` is set); update: `test_loads_scenes_from_controller` → rename to `test_loads_scenes_from_top_level`
- [ ] `packages/rig-morningstar/tests/test_mc6_device.py` — add: `test_mc6_config_has_no_scenes_field`, `test_mc6_config_rejects_scenes_key` (Pydantic ValidationError when `scenes:` is present under controller config)
- [ ] `packages/rig/tests/test_apply.py` — add: `test_apply_scene_without_controller_device_skips_controller_phase` (Rig with no CONTROLLER device, scene apply completes normally)

### Sampling Rate
- **Per task commit:** `uv run pytest packages/rig/tests/test_models.py packages/rig/tests/test_loader.py packages/rig-morningstar/tests/ -q`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green (`make test`) before `/gsd-verify-work`

---

## Common Pitfalls

### Pitfall 1: Forgetting `tempo` in the loader
**What goes wrong:** The current `Rig.scenes` property silently drops `tempo` from scene data (line 33 in rig.py: no `tempo=` kwarg). If the loader replicates this bug, `Scene.tempo` will always be `None` even when specified in YAML.
**Why it happens:** Copy-paste from property implementation.
**How to avoid:** Pass `tempo=scene_data.get("tempo")` explicitly in the loader's `Scene(...)` constructor call.
**Warning signs:** Test that checks `rig.scenes["s"].tempo == 120` fails.

### Pitfall 2: test_models.py has an assertion that directly contradicts the change
**What goes wrong:** `test_rig_controller_and_scenes_are_not_pydantic_fields` asserts `assert "scenes" not in Rig.model_fields`. This test will fail immediately after the change.
**Why it happens:** The test was written to verify the current property-based design. It must be updated — either renamed and the assertion inverted (`assert "scenes" in Rig.model_fields`), or the test is split.
**How to avoid:** Update this test in the same task as the model change.

### Pitfall 3: SimpleNamespace(scenes=...) in test builders still works, but does nothing
**What goes wrong:** After the change, `FakeDevice.config = SimpleNamespace(scenes={"s": {...}})` still parses without error, but `Rig.scenes` no longer reads from it. Tests that rely on scene data will silently get an empty `Rig.scenes` and produce confusing empty-plan outputs.
**Why it happens:** Python dicts don't validate that extra attributes are unused.
**How to avoid:** Migrate ALL test `_make_rig()`/`_make_config()` builders to pass `scenes=` to `Rig(...)` in the same wave as the model change. Run the full test suite immediately to catch any missed builder.

### Pitfall 4: MC6Config extra="ignore" trap
**What goes wrong:** If `extra="ignore"` is left on `MC6Config` after removing the `scenes` field, old rig.yaml files will load without error — the scenes data will be silently discarded. Users with old configs get no warning.
**Why it happens:** Removing a field from a Pydantic model with `extra="ignore"` is a silent change.
**How to avoid:** Change `extra="ignore"` to `extra="forbid"` in the same task as removing the field.

### Pitfall 5: `_parse_device()` does not catch Pydantic ValidationError
**What goes wrong:** When `extra="forbid"` rejects old `scenes:` data, a Pydantic `ValidationError` propagates through `_parse_device()` uncaught. This surfaces as an ugly traceback instead of a clean `ConfigError` message.
**Why it happens:** `_parse_device()` only wraps `ValidationError` from `rig.config.errors`, not Pydantic's.
**How to avoid:** Add a `except pydantic.ValidationError as e: raise ValidationError(str(e)) from e` wrapper in `_parse_device()` — or verify that existing error handling already covers this path (it does not currently).

### Pitfall 6: loader docstring describes old schema
**What goes wrong:** The module docstring at lines 1–27 of `loader.py` shows `scenes:` nested under the controller config. After the change, it documents incorrect schema.
**Why it happens:** Docstrings are not caught by tests.
**How to avoid:** Update the module docstring as part of the loader change task.

---

## Runtime State Inventory

This is a code/schema refactor, not a rename/migration of stored data. The `state.json` file uses `state.scenes` as a dict of scene-name → `{}` (applied scenes tracker). Scene names in state.json are set by `apply_plan` at `state.scenes[sp.scene_name] = {}`. These names come from the plan, which comes from `rig.scenes`. As long as scene names stay the same in `rig.yaml` (just moved to top level), state.json is unaffected.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `state.scenes` in `.rig/state.json` — keys are scene names | None — scene names unchanged, only location in YAML moves |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |

**Nothing found requiring data migration** — verified by examining `state.py`, `apply.py` (line 158: `state.scenes[sp.scene_name] = {}`), and `compute.py` (line 181: `if scene_name not in actual.scenes`).

---

## Environment Availability

Step 2.6: SKIPPED (no external tool dependencies — pure Python code changes, test execution uses existing `uv run pytest` / `make test`).

---

## Security Domain

`security_enforcement` is enabled (config shows `"security_enforcement": true`). This phase has no new authentication, session management, cryptography, or network-facing surface. The only relevant ASVS category is:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes (YAML parsing) | `yaml.safe_load` already used; Pydantic model validation |

YAML parsing already uses `yaml.safe_load()` (not `yaml.load()`), which prevents arbitrary Python object instantiation. The new `scenes:` parsing follows the same code path. No new threat surface introduced.

---

## Sources

### Primary (HIGH confidence — direct code inspection)
- `packages/rig/src/rig/models/rig.py` — Rig model, `scenes` property, `controller` property [VERIFIED: direct read]
- `packages/rig/src/rig/models/scene.py` — Scene model fields [VERIFIED: direct read]
- `packages/rig/src/rig/config/loader.py` — full load_rig implementation, line-by-line [VERIFIED: direct read]
- `packages/rig-morningstar/src/rig_morningstar/config.py` — MC6Config with `scenes` field and `extra="ignore"` [VERIFIED: direct read]
- `packages/rig-morningstar/src/rig_morningstar/device.py` — MC6Device.apply(), `rig.scenes.get(scene_name)` [VERIFIED: direct read]
- `packages/rig/src/rig/engine/apply.py` — apply_plan controller gate at line 170 [VERIFIED: direct read]
- `packages/rig/src/rig/engine/plan/compute.py` — compute_plan scene iteration [VERIFIED: direct read]
- `packages/rig/src/rig/engine/diff.py` — compute_diff scene iteration [VERIFIED: direct read]
- `packages/rig-chasebliss/src/rig_chasebliss/device.py` — `rig.scenes` access at lines 168, 242 [VERIFIED: direct read]
- `packages/rig/tests/test_models.py` — `test_rig_controller_and_scenes_are_not_pydantic_fields` [VERIFIED: direct read]
- `packages/rig/tests/test_loader.py` — BASE_RIG_YAML with scenes in controller config [VERIFIED: direct read]
- `packages/rig/tests/test_plan.py` — all `_make_rig()` builder helpers with `SimpleNamespace(scenes=...)` [VERIFIED: direct read]
- `packages/rig/tests/test_apply.py` — all `_make_config()` and inline Rig builders [VERIFIED: direct read]
- `packages/rig/tests/fixtures/sample_rig/rig.yaml` — primary on-disk fixture with scenes under mc6.config [VERIFIED: direct read]
- `make test` output — 399 tests passing at research time [VERIFIED: executed]

### Secondary (MEDIUM confidence)
- Pydantic v2 `extra="forbid"` behavior — raises `ValidationError` for unknown fields [ASSUMED: based on Pydantic v2 training knowledge; consistent with existing test `test_from_raw_yaml_invalid_banks_type_raises`]

---

## Metadata

**Confidence breakdown:**
- Current state analysis: HIGH — all files read directly
- Change impact map: HIGH — all consumers grep-verified
- Controller-less apply behavior: HIGH — apply.py line 170 confirms gate is already in place
- MC6Config `extra="forbid"` behavior: MEDIUM — Pydantic v2 knowledge, consistent with existing test pattern
- `_parse_device()` error wrapping gap: HIGH — code read confirms no Pydantic ValidationError catch

**Research date:** 2026-07-01
**Valid until:** Until any of the listed files are modified — this is a point-in-time snapshot of a stable codebase
