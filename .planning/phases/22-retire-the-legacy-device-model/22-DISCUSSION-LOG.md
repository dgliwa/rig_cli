# Phase 22: Retire the Legacy Device Model - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 22-retire-the-legacy-device-model
**Areas discussed:** models/device.py fate, Test fixture migration, Rig.devices type annotation depth

---

## models/device.py fate

### Q: What happens to DeviceType after Device(BaseModel) is removed?

| Option | Description | Selected |
|--------|-------------|----------|
| Repurpose — keep file, delete class | Remove Device(BaseModel) but leave DeviceType in models/device.py. Zero import-path churn. | |
| Move DeviceType into engine/plugin.py | Consolidates full type surface (Device Protocol + DeviceType) in one place. 2 plugin packages + 8 tests need import updates. | ✓ |
| New models/types.py home | Clean separation; more files to create; still requires updating plugin package imports. | |

**User's choice:** Move DeviceType into engine/plugin.py

---

### Q: models/device.py — delete entirely or keep as re-export shim?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete models/device.py entirely | No shim. Fix all importers directly. Clean, no ambiguity. | ✓ |
| Keep as a re-export shim | Leave re-export so existing imports don't break. Shims tend to linger; against CLAUDE.md policy. | |

**User's choice:** Delete models/device.py entirely (no shim)

---

### Q: What should models/__init__.py export after the move?

| Option | Description | Selected |
|--------|-------------|----------|
| Export Device + DeviceType from engine.plugin | Convenience re-export preserved; consumers import from rig.models as before. | |
| Drop Device from models/__init__ entirely | Device(Protocol) lives in engine.plugin; consumers import directly from there. Cleaner source-of-truth. | ✓ |

**User's choice:** Drop Device from models/__init__ entirely

---

## Test fixture migration

### Q: What replaces Device(BaseModel) fixtures in 8 test files?

| Option | Description | Selected |
|--------|-------------|----------|
| FakeDevice in tests/conftest.py | Minimal Protocol-satisfying class. Zero plugin-package deps in core tests. One file change covers all 8 test files. | ✓ |
| Swap to real plugin classes | Heavier fixtures; tests depend on plugin packages being installed. | |
| Drop tests that only tested the legacy class | Delete test_models.py; migrate structural tests separately. | |

**User's choice:** FakeDevice in tests/conftest.py

---

### Q: Where should FakeDevice live?

| Option | Description | Selected |
|--------|-------------|----------|
| packages/rig/tests/conftest.py | Pytest auto-discovers; no import boilerplate in individual test files. | ✓ |
| packages/rig/tests/test_utils.py | Explicit import required in each test file. | |

**User's choice:** packages/rig/tests/conftest.py

---

## Rig.devices type annotation depth

### Q: Static type enforcement vs runtime validator on Rig.devices?

| Option | Description | Selected |
|--------|-------------|----------|
| Static-type enforcement only | Change annotation; mypy/pyright catches violations. No runtime validator. Matches side project velocity stance. | ✓ |
| Add Pydantic model_validator | Assert Protocol attributes at load time. Catches misconfigured plugins earlier. | |

**User's choice:** Static-type enforcement only

---

### Q: hasattr guards in apply.py — plain call or assertion?

| Option | Description | Selected |
|--------|-------------|----------|
| Plain call — trust the Protocol | No guard, no assert. Fails loudly at call site if rogue object appears. Protocol + type checker is the enforcement. | ✓ |
| Replace with assert statements | Defensive but verbose; CLAUDE.md says avoid error handling for scenarios that can't happen. | |

**User's choice:** Plain call — trust the Protocol

---

## Claude's Discretion

None — user selected options for all questions.

## Deferred Ideas

None — discussion stayed within phase scope.
