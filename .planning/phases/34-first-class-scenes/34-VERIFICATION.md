---
phase: 34-first-class-scenes
verified: 2026-07-02T05:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 34: First-Class Scenes Verification Report

**Phase Goal:** Scenes are defined at the top level of `rig.yaml`, not embedded inside the controller device's config; `Rig.scenes` is a real Pydantic field; `MC6Config` rejects stale `scenes:` under the controller config; a rig with scenes but no CONTROLLER device validates and applies correctly.
**Verified:** 2026-07-02T05:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `rig.yaml` schema supports a top-level `scenes:` key; loader populates `Rig.scenes` directly from it | VERIFIED | `loader.py` line 158: `raw_scenes: dict[str, Any] = data.get("scenes") or {}` + `Rig(scenes=scenes)` at line 186; `sample_rig/rig.yaml` has top-level `scenes:` block |
| 2 | Controller config no longer owns scene definitions; scenes referenced in MC6 bank/switch config are resolved from `Rig.scenes` | VERIFIED | `MC6Config` has no `scenes` field (`'scenes' not in MC6Config.model_fields` = True); `device.py` line 114: `rig.scenes.get(scene_name) if rig else None` |
| 3 | A rig with no controller device but a `scenes:` key validates and applies correctly | VERIFIED | `TestControllerlessApply.test_apply_scene_without_controller_device_skips_controller_phase` passes — constructs `Rig` with scenes and only HX Stomp (no CONTROLLER), asserts apply completes, device state written, controller programming skipped |
| 4 | `Rig.scenes` property removed in favor of a real field; `controller` remains for MC6-specific routing | VERIFIED | `rig.py`: `scenes: dict[str, Scene] = {}` is a real Pydantic field; `'scenes' in Rig.model_fields` = True; `controller` is still a `@property` scanning devices |
| 5 | Existing sample fixtures and tests updated; no regressions | VERIFIED | 407 tests pass (`make test` green); no `SimpleNamespace(scenes=...)` on any controller config in test builders; all 12 affected test files migrated |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/rig/src/rig/models/rig.py` | `scenes: dict[str, Scene] = {}` Pydantic field (not `@property`) | VERIFIED | Field present; `controller` remains a property |
| `packages/rig/src/rig/config/loader.py` | Reads `data.get("scenes")` at top level, passes `scenes=scenes` to `Rig(...)` | VERIFIED | Lines 158-168: scene parsing; line 186: `scenes=scenes` in constructor |
| `packages/rig-morningstar/src/rig_morningstar/config.py` | `MC6Config` with no `scenes` field, `extra="forbid"` | VERIFIED | Only `type`, `midi_channel`, `banks` fields; `ConfigDict(extra="forbid")` confirmed |
| `packages/rig/tests/fixtures/sample_rig/rig.yaml` | Top-level `scenes:` key, no nested scenes under mc6 config | VERIFIED | `scenes:` at root; mc6 config has only `type`, `midi_channel`, `banks` |
| `packages/rig/tests/test_apply.py` | Controller-less apply test (`TestControllerlessApply`) | VERIFIED | Class and test at lines 1030-1103; passes |
| `packages/rig-morningstar/tests/test_mc6_device.py` | `test_mc6_config_has_no_scenes_field`, `test_mc6_config_rejects_scenes_key` | VERIFIED | Both tests exist at lines 33 and 37; all 6 MC6 tests pass |
| `packages/rig/tests/test_loader.py` | `test_loads_scenes_from_top_level`, `test_loader_preserves_scene_tempo`, `test_loader_rejects_scenes_in_controller_config` | VERIFIED | All 3 tests exist and pass |
| `packages/rig/tests/test_models.py` | `test_rig_scenes_is_pydantic_field`, scenes tests | VERIFIED | 6 scenes-related tests pass |

---

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `rig.yaml` top-level `scenes:` | `Rig.scenes` field | `loader.py` `load_rig()` → `data.get("scenes") or {}` → `Rig(scenes=scenes)` | WIRED |
| `Rig.scenes` field | `MC6Device.apply()` | `rig.scenes.get(scene_name) if rig else None` (no `hasattr` guard) | WIRED |
| `apply_plan` controller gate | controller-less path | `if rig and rig.controller and not scene and not device_filter:` in `apply.py` line 170 — skips when `rig.controller is None` | WIRED |
| Stale `scenes:` in MC6 controller config | `ConfigError` via `_parse_device` | `MC6Config(extra="forbid")` raises `pydantic.ValidationError`; `_parse_device` wraps as `ValidationError` from `rig.config.errors` | WIRED |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `Rig.scenes` is a real Pydantic field | `python3 -c "from rig.models.rig import Rig; print('scenes' in Rig.model_fields)"` | `True` | PASS |
| `MC6Config` has no scenes field + extra=forbid | `python3 -c "from rig_morningstar.config import MC6Config; print('scenes' not in MC6Config.model_fields, MC6Config.model_config.get('extra') == 'forbid')"` | `True True` | PASS |
| `hasattr` guard removed from `MC6Device.apply()` | `grep -q 'hasattr(rig, "scenes")' packages/rig-morningstar/src/rig_morningstar/device.py` | exit 1 (not found) | PASS |
| Loader reads top-level scenes | `grep -n "data.get.*scenes" packages/rig/src/rig/config/loader.py` | line 158 match | PASS |
| Controller-less apply test | `uv run pytest packages/rig/tests/test_apply.py -k "without_controller" -v -q` | 1 passed | PASS |
| D-04 rejection test | `uv run pytest packages/rig/tests/test_loader.py -k "rejects_scenes" -v -q` | 1 passed | PASS |
| Full suite | `make test` | 407 passed, 0 failed | PASS |
| Lint | `make lint` | All checks passed | PASS |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| SCENE-01 | Scenes defined at top level of rig.yaml, not inside a controller device's config | SATISFIED | Fixture, loader, and model all confirm top-level placement |
| D-01 | MC6Config has no scenes field; uses `extra="forbid"` | SATISFIED | `MC6Config` verified: no `scenes` field, `ConfigDict(extra="forbid")`; `test_mc6_config_has_no_scenes_field` + `test_mc6_config_rejects_scenes_key` both pass |
| D-02 | All test fixtures and builders use new top-level schema | SATISFIED | No `SimpleNamespace(scenes=...)` on controller configs; `make test` green across all 12 migrated files |
| D-03 | `load_rig` reads `data['scenes']` and populates `Rig.scenes` | SATISFIED | `loader.py` line 158; `test_loads_scenes_from_top_level` + `test_loader_preserves_scene_tempo` pass |
| D-04 | Stale `scenes:` under controller config raises a clean ConfigError | SATISFIED | `test_loader_rejects_scenes_in_controller_config` passes; error is wrapped `ConfigError` not raw pydantic traceback |
| D-05 | `apply_plan` works on a rig with scenes but no CONTROLLER device | SATISFIED | `test_apply_scene_without_controller_device_skips_controller_phase` passes; asserts device state written, scene recorded, no cancellation |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

No `TBD`, `FIXME`, `XXX`, `HACK`, `PLACEHOLDER`, or placeholder returns found in any modified source file. No `SimpleNamespace(scenes=...)` patterns remain on controller device configs in any test builder.

---

### Human Verification Required

None. All success criteria are programmatically verifiable and confirmed passing.

---

### Summary

Phase 34 goal is fully achieved. The three interlocking parts of the refactor are all confirmed in the codebase:

1. **Model:** `Rig.scenes` is a real `dict[str, Scene] = {}` Pydantic field — the old `@property` aggregating from controller devices is gone.

2. **Loader:** `loader.py` reads `data.get("scenes") or {}` from the top-level YAML and passes `scenes=scenes` to the `Rig(...)` constructor. Scene tempo is preserved. Stale `scenes:` under a controller config raises a clean `ConfigError` via `_parse_device`'s `pydantic.ValidationError` wrapping.

3. **MC6Config:** `scenes` field removed, `extra="forbid"` enforces hard cutover. A `midi_channel` field was added as a necessary deviation (the YAML includes it and `extra="forbid"` would reject it otherwise) — this is a correct fix, not scope creep.

4. **Controller-less apply:** `apply_plan` already gated controller programming on `if rig and rig.controller`. `TestControllerlessApply` pins this path with a regression test. `MC6Device.apply()` has no `hasattr` guard.

5. **No regressions:** 407 tests pass, 0 failures. All 12 affected test files migrated to the top-level scenes schema.

---

_Verified: 2026-07-02T05:00:00Z_
_Verifier: Claude (gsd-verifier)_
