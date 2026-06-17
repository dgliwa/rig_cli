---
phase: 23
slug: applycontext-consolidation-test-capture-fixes
status: complete
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-16
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for applycontext-consolidation-test-capture-fixes.

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
| 23-01-T1a | 01 | 1 | TYPE-05 — DeviceApplyResult/helpers moved to plugin.py | — | N/A | unit | `uv run pytest packages/rig/tests/test_base_helpers.py -q` | ✅ | ✅ green |
| 23-01-T1b | 01 | 1 | TYPE-05 — appliers/base.py deleted; all importers updated | — | N/A | integration | `uv run pytest packages/ -q` | ✅ | ✅ green |
| 23-01-T1c | 01 | 1 | TYPE-05 — ApplyContext retired from apply.py | — | N/A | integration | `uv run pytest packages/rig/tests/test_apply.py -q` | ✅ | ✅ green |
| 23-01-T2a | 01 | 1 | TYPE-05 — ConfirmationIO.prompt() on Protocol + RichConfirmationIO + InMemoryPromptAdapter | — | N/A | integration | `uv run pytest packages/rig/tests/test_appliers.py packages/rig-chasebliss/tests/test_applier.py -q` | ✅ | ✅ green |
| 23-01-T2b | 01 | 1 | TYPE-05 — All 4 CBA interaction functions accept confirmation_io; no raw input() | — | N/A | unit | `uv run pytest packages/rig-chasebliss/tests/test_applier.py -q` | ✅ | ✅ green |
| 23-01-T3a | 01 | 1 | TEST-02 — test_build_preset_confirm_sends_ccs_and_updates_state passes | — | N/A | unit | `uv run pytest packages/rig/tests/test_appliers.py -k "build_preset_confirm" -q` | ✅ | ✅ green |
| 23-01-T3b | 01 | 1 | TEST-02 — test_midi_connect_and_send passes | — | N/A | integration | `uv run pytest packages/rig/tests/test_apply.py -k "midi_connect_and_send" -q` | ✅ | ✅ green |
| 23-01-T3c | 01 | 1 | TEST-02 — test_cba_channel_establishment_writes_state passes | — | N/A | integration | `uv run pytest packages/rig/tests/test_apply.py -k "channel_establishment" -q` | ✅ | ✅ green |

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
# No legacy base.py imports remain
grep -r "from rig.engine.appliers.base" packages/

# ApplyContext is gone from src (only DeviceApplyContext, which is the new class, remains)
grep -r "ApplyContext" packages/rig/src/ | grep -v "DeviceApplyContext"

# base.py does not exist
ls packages/rig/src/rig/engine/appliers/

# ConfirmationIO has prompt() method
grep -n "def prompt" packages/rig/src/rig/engine/ports.py
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
