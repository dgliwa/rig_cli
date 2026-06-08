---
phase: 09-core-model-cleanup
plan: 04
subsystem: models
tags: [cleanup, manufacturer-model, schena-06]
requires:
  - phase: 09
    provides: clean Scene/Rig models, list[str] signal chain, plugin config types removed
provides:
  - Device stripped to id, type, config, presets, image, notes
  - All plugin-level config references purged from core tests
  - Backward-compatible YAML loading (extra fields silently ignored)
affects: [phase 10, phase 11]
tech-stack:
  added: []
  patterns: []
key-files:
  deleted: []
  modified:
    - packages/rig/src/rig/models/device.py
    - packages/rig/tests/test_graph.py
key-decisions:
  - "Pydantic v2 default extra='ignore' handles backward compat — existing YAML files with manufacturer/model fields load without error"
requirements-completed:
  - SCHEMA-06
  - MODEL-02 (completion)
duration: 3min
completed: 2026-06-08
---

# Phase 09: Core Model Cleanup — Wave 4 Summary

**Removed `manufacturer` and `model` from core `Device` model; cleaned up last test reference**

## Performance
- **Duration:** 3 min
- **Tests:** 272 passing (same as pre-Wave 4 - no breakage due to Pydantic extra=ignore)
- **Files modified:** 2

## Accomplishments
- Removed `manufacturer: str` and `model: str` fields from `Device` class
- Updated `test_graph.py` to not pass `manufacturer=`/`model=` to Device constructor
- Pydantic v2 default `extra="ignore"` means existing YAML files still load fine

## Verification
- `Device.model_fields` contains `id`, `type`, `config`, `presets`, `image`, `notes` — NOT `manufacturer` or `model`
- `uv run pytest packages/ -q` exits 0 (272 passed)
