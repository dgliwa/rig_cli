---
phase: 22
slug: retire-the-legacy-device-model
status: complete
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-16
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for retire-the-legacy-device-model.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (uv run pytest) |
| **Config file** | `pyproject.toml` (`testpaths = ["packages"]`) |
| **Quick run command** | `uv run pytest packages/ -q` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/ -q`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 22-01-T1a | 01 | 1 | TYPE-01 — DeviceType in plugin.py; all importers updated | — | N/A | integration | `uv run pytest packages/ -q` | ✅ | ✅ green |
| 22-01-T1b | 01 | 1 | TYPE-01 — `models/device.py` deleted; Rig.devices: dict[str, Device] | — | N/A | unit | `uv run pytest packages/rig/tests/test_models.py -q` | ✅ | ✅ green |
| 22-01-T2a | 01 | 1 | TYPE-01 — hasattr guards removed from apply.py | — | N/A | integration | `uv run pytest packages/rig/tests/test_apply.py -q` | ✅ | ✅ green |
| 22-01-T2b | 01 | 1 | TYPE-01 — FakeDevice in conftest.py; 8 test files migrated | — | N/A | unit | `uv run pytest packages/rig/tests/ -q` | ✅ | ✅ green |
| 22-01-T2c | 01 | 1 | TYPE-01 — chasebliss _FakeDevice satisfies Device Protocol | — | N/A | unit | `uv run pytest packages/rig-chasebliss/tests/test_applier.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · 📋 manual*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Structural Verification Commands

These grep checks verify the structural invariants established by the phase:

```bash
# No legacy Device model imports remain
grep -r "from rig.models.device import" packages/

# No hasattr guards remain in apply.py
grep -n "hasattr(device" packages/rig/src/rig/engine/apply.py

# DeviceType is in plugin.py (canonical home)
grep -n "class DeviceType" packages/rig/src/rig/engine/plugin.py

# Rig.devices is typed as dict[str, Device]
grep -n "devices.*dict\[str.*Device\]" packages/rig/src/rig/models/rig.py
```

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0: existing infrastructure sufficient
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-16
