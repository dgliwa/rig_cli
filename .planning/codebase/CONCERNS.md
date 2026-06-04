# Codebase Concerns

**Analysis Date:** 2026-06-03

## Tech Debt

**Loader — dual YAML layout support (legacy vs. new):**
- Issue: `load_rig` supports both `pedals/` (legacy) and `devices/` (new) directory names, and both `mc6.yaml` (legacy) + `controller.yaml` (new) controller loading paths. The branching logic is intertwined throughout the loader.
- Files: `src/rig/config/loader.py:63`, `src/rig/config/loader.py:71`, `src/rig/config/loader.py:200-221`
- Impact: Every loader change must account for two paths; accidental regressions easy to miss.
- Fix approach: Migrate rig config repo to new layout, then delete `_parse_controller_legacy`, the `pedals/` fallback, and the `mc6.yaml` branch.

**Loader — inline vs. directory presets:**
- Issue: `_merge_presets` supports both inline presets (in device YAML) and filesystem presets (per-device subdirectory). Author comments suggest inline is the desired end-state but directory loading is still active code.
- Files: `src/rig/config/loader.py:82-117`
- Impact: Dead weight; two code paths to maintain and test.
- Fix approach: Require inline presets, delete the directory-scanning branch.

**Preset type dispatch via raw conditionals:**
- Issue: `_merge_presets` dispatches to `AnalogPreset`, `HXStompPreset`, or `DigitalPreset` via `if/elif/else` on `device.type`. The `assert_never` exhaustiveness check is missing (noted in comment).
- Files: `src/rig/config/loader.py:100-109`
- Impact: Adding a new `DeviceType` will silently fall through to `DigitalPreset` instead of failing loudly.
- Fix approach: Add `typing.assert_never` in the else branch; consider a `Protocol`-based factory.

**Validation uses `isinstance` instead of Protocol dispatch:**
- Issue: `_validate_references` checks `isinstance(device.config, ChaseBlissConfig)` to apply CBA-specific validation. The author flagged this at `src/rig/config/loader.py:167`. Other device types get no equivalent validation.
- Files: `src/rig/config/loader.py:167-187`
- Impact: CBA-specific logic is hardcoded; new device types require surgical edits in validation.
- Fix approach: Move device/preset validation to a `validates()` method on each config type (Protocol-based).

**Rig model — deprecated property aliases:**
- Issue: `Rig.pedals`, `Rig.digital_presets`, `Rig.hx_presets`, `Rig.analog_presets`, `Rig.mc6` are backward-compat shims marked "pending migration". Code in `cli.py` and `apply.py` still uses `rig.pedals` instead of `rig.devices`.
- Files: `src/rig/models/rig.py:25-54`, `src/rig/cli.py:74`, `src/rig/cli.py:80`, `src/rig/cli.py:209`, `src/rig/cli.py:221`, `src/rig/engine/apply.py:95`, `src/rig/engine/appliers/mc6.py:66`
- Impact: Confusing API; callers are not migrated despite the aliases existing.
- Fix approach: Migrate all call sites to `rig.devices`, then delete the compat properties.

**`apply_plan` is too large and does too much:**
- Issue: `apply_plan` handles MIDI connection, CBA setup, scene apply, and MC6 programming in one 150-line function. Author noted this at `src/rig/engine/apply.py:46`.
- Files: `src/rig/engine/apply.py:46-199`
- Impact: Hard to unit test individual phases; changes in one phase risk breaking others.
- Fix approach: Extract each phase into its own function or class, called by a thin coordinator.

**CBA setup detection is embedded in plan, applied in apply:**
- Issue: `_detect_cba_setup` lives in `plan.py` but is re-called from `appliers/chase_bliss.py` to enqueue follow-on actions mid-apply. The coupling is explicitly flagged at `src/rig/engine/plan.py:219` and `src/rig/engine/apply.py:117`.
- Files: `src/rig/engine/plan.py:219-223`, `src/rig/engine/apply.py:117`, `src/rig/engine/appliers/chase_bliss.py:9` (imports `_detect_cba_setup` — internal function)
- Impact: Plan/apply boundary is blurred; plan output is not fully self-contained.
- Fix approach: Make plan output enumerate all required CBA actions before apply begins; remove re-detection during apply.

**`Device.presets` type redundancy:**
- Issue: `Device.presets` is typed as `list[AnalogPreset | DigitalPreset | HXStompPreset]` — identical to the `Preset` alias defined two lines above. Author noted this at `src/rig/models/device.py:87`.
- Files: `src/rig/models/device.py:78`, `src/rig/models/device.py:88`
- Fix approach: Use `list[Preset]`.

**Controls defined inline on model instead of in config:**
- Issue: `Device._populate_cba_controls` is a `model_validator` that mutates `config.controls` from the catalog on load. Author flagged this at `src/rig/models/device.py:92`. Controls logically belong to the device config, not injected at model instantiation.
- Files: `src/rig/models/device.py:93-103`
- Impact: Side-effectful validators are hard to reason about and test; catalog lookup happens implicitly.
- Fix approach: Load controls explicitly in the config constructor or at loader time.

**`Device.get_scene_pc_command` ownership is wrong:**
- Issue: Author noted at `src/rig/models/device.py:105` that `Scene` should own PC commands, not `Device`. This is a domain modeling inconsistency.
- Files: `src/rig/models/device.py:106-122`
- Impact: PC command generation is scattered; scenes cannot customize per-device behavior.

**`ingest/` module referenced in CLAUDE.md but does not exist:**
- Issue: The architecture diagram in `CLAUDE.md` lists `ingest/` for importing from HX `.hlx`, MC6 JSON, and manual formats. No `src/rig/ingest/` directory exists in the codebase.
- Impact: Planned import functionality is entirely unimplemented.

## Known Bugs / Risks

**`compute_plan` state always starts empty when `root_path` is None:**
- Files: `src/rig/engine/plan.py:128-133`
- Risk: If a caller omits `root_path`, all scenes appear as "new" and the plan will always show changes. No warning is emitted.
- Note: `# TODO: issue #13` is the only reference; the issue is not accessible externally.

**`compute_diff` always marks existing scenes as "changed" regardless of actual preset state:**
- Files: `src/rig/engine/diff.py:35-36`
- Issue: Line 35 sets `_status: "changed"` unconditionally when a scene exists in state, even if no presets changed. The preset loop below may produce an empty `presets` dict, making a "changed" label misleading in the formatted output.

**Scene state stored as empty dict:**
- Files: `src/rig/engine/apply.py:174`
- Issue: `state.scenes[sp.scene_name] = {}` stores no useful information. Scene state is non-functional beyond tracking which scene names have been applied.
- Impact: Diff and plan cannot detect what preset was active per-scene; they fall back to per-device `last_preset` only.

## Security Considerations

**No secrets in source detected.** YAML loader uses `yaml.safe_load` throughout — no arbitrary code execution risk from YAML files.

## Fragile Areas

**CBA 3-phase setup loop with dynamic re-queuing:**
- Files: `src/rig/engine/appliers/chase_bliss.py:37-59`
- Why fragile: `_detect_cba_setup` is called mid-loop to enqueue follow-on actions. If state mutations inside the loop produce unexpected phase transitions, infinite re-queuing is possible (guarded only by the `seen` set on `(device, type, preset_id)` — the tuple key).
- Safe modification: Add a maximum iteration guard; consider linearizing the phase sequence.

**Controller detection during apply is ambiguous:**
- Files: `src/rig/engine/apply.py:77-79` (comment), `src/rig/engine/apply.py:95`
- Issue: `pedal = rig.pedals.get(device_id)` is used to look up MIDI channel for connection prompts. If the device is the controller (MC6) rather than a pedal, this returns `None` and falls back to channel 1 silently.

## Test Coverage Gaps

**`engine/diff.py` has a test file but limited coverage:**
- Files: `tests/test_diff.py` (114 lines), `src/rig/engine/diff.py`
- Missing: No test for the "changed" scene status bug (scene exists in state, no preset changes → still labeled "changed").

**`cli.py` integration coverage is shallow:**
- Files: `tests/test_cli.py` (181 lines), `src/rig/cli.py` (285 lines)
- Missing: `rig show`, `rig devices`, and `rig apply --dry-run` paths are not tested end-to-end with a real loader fixture.

**No tests for the `ingest/` layer** — because it does not exist.

**`config/loader.py` legacy path (pedals/ + mc6.yaml) not covered:**
- Files: `tests/test_loader.py`, `src/rig/config/loader.py:200-221`
- Missing: Test fixtures using the old directory names; regressions will be silent.

## Open Design Questions

**Terraform-like declarative structure:**
- Author comment at `src/rig/config/loader.py:226` notes dissatisfaction with the implied YAML structure and a desire for a more terraform-like approach. No design has been decided.

**Controller flexibility:**
- `src/rig/config/loader.py:213` notes the controller type is hardcoded to MC6. A second controller type would require changes throughout loader, plan, apply, and generators.

**Scene should own PC commands:**
- `src/rig/models/device.py:105` — open question about whether `Scene` or `Device` owns PC command generation. Currently `Device.get_scene_pc_command` is used by `generators/mc6_presets.py`.

---

*Concerns audit: 2026-06-03*
