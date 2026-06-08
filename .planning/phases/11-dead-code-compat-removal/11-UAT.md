---
status: complete
phase: 11-dead-code-compat-removal
source: .planning/phases/11-dead-code-compat-removal/11-PLAN.md
started: 2026-06-08T09:35:00Z
updated: 2026-06-08T09:36:00Z
---

## Current Test

[testing complete]

## Tests

### 1. No TODO:1.2 markers remain
expected: `grep -rn "TODO.*1\.2" packages/rig/src/` returns zero results
result: pass

### 2. No multi-file config paths in source
expected: `grep -rn "mc6\.yaml\|signal-chain\.yaml\|pedals/.*\.yaml\|scenes/.*\.yaml" --include="*.py" packages/rig/src/` returns zero results
result: pass

### 3. `_load_scenes` dead code removed
expected: Function `_load_scenes` is absent from both loader.py and test_loader.py; `grep -rn "_load_scenes" packages/` returns zero
result: pass

### 4. Core Preset is barebones
expected: Core `packages/rig/src/rig/models/preset.py` defines only a base `Preset` class (id, name, notes, tags); no AnalogPreset, DigitalPreset, or HXStompPreset classes defined there
result: pass

### 5. Plugin packages define their own preset types
expected: Each plugin has its own preset module — `rig_analog/preset.py` (AnalogPreset), `rig_chasebliss/preset.py` (DigitalPreset), `rig_hx/preset.py` (HXStompPreset)
result: pass

### 6. `CbaSetupAction` lives in CBA plugin only
expected: `CbaSetupAction` is defined in `rig_chasebliss/models.py` and NOT in core `rig.engine.plan.models`; test imports from `rig_chasebliss.models`
result: pass

### 7. `apply.py` has no `cba_results` or `cba_setup` field
expected: `ApplyResult` model no longer has `cba_setup` field; no `cba_results` variable in `apply_plan()`
result: pass

### 8. `generate.py` error message uses rig config language
expected: Error message no longer references `mc6.yaml` — uses "rig config" terminology instead
result: pass

### 9. All tests pass
expected: `uv run pytest packages/ -q --tb=short` shows 273 passed, 0 failed
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
