---
phase: "02"
slug: engine-i-o-decoupling
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-06
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_appliers.py tests/test_apply.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_appliers.py tests/test_apply.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DEC-01 | T-02-02 | Production adapters delegate to interaction.* without new external surface | import | `uv run python -c "from rig.engine.ports import ConfirmationIO, StateWriter, MidiConnectionIO, RichConfirmationIO, FileStateWriter, InteractiveMidiConnectionIO; print('OK')"` | ✅ | ✅ green |
| 02-01-02 | 01 | 1 | DEC-02 / DEC-03 | T-02-01 | In-memory fakes never touch disk; test-only classes not imported in production | import | `uv run python -c "from tests.fakes import InMemoryPromptAdapter, InMemoryStateAdapter, InMemoryMidiConnectionIO; print('OK')"` | ✅ | ✅ green |
| 02-01-03 | 01 | 1 | DEC-04 | T-02-02 | Appliers use ctx.confirmation_io — no direct interaction.* imports | lint + behavior | `uv run ruff check src/rig/engine/appliers/ && uv run pytest tests/test_appliers.py -q` | ✅ | ✅ green |
| 02-02-01 | 02 | 2 | DEC-05 | T-02-04 | apply_plan accepts state_writer and midi_connection_io; delegates state I/O | integration | `uv run pytest tests/test_apply.py -q` | ✅ | ✅ green |
| 02-02-02 | 02 | 2 | DEC-06 | T-02-03 | state.scenes only written when ≥1 device confirmed; skipped scenes not persisted | integration | `uv run pytest tests/test_apply.py::TestApplyEngine::test_apply_skip_does_not_write_device_state tests/test_apply.py::TestApplyEngine::test_apply_writes_state -v` | ✅ | ✅ green |
| 02-02-03 | 02 | 2 | DEC-07 | — | Zero builtins.input patches; all interaction via fakes | structural | `grep -rn 'patch("builtins.input"' tests/ \| wc -l` (must be 0) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covered all phase requirements — pytest was already installed and configured.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Audit 2026-06-06

| Metric | Count |
|--------|-------|
| Gaps found | 2 |
| Resolved | 2 |
| Escalated | 0 |

Gaps resolved: DEC-06 scene-write invariant was unverified in both the positive and negative case.
Added `assert state.scenes == {}` to `test_apply_skip_does_not_write_device_state` and `assert "test-scene" in state.scenes` to `test_apply_writes_state`.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-06
