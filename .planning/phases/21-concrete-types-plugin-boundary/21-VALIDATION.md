---
phase: 21
slug: concrete-types-plugin-boundary
status: complete
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-16
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for concrete-types-plugin-boundary.

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
| 21-01-T1 | 01 | 1 | Preset Protocol defined | — | N/A | unit | `uv run pytest packages/rig/tests/test_plugin.py -q` | ✅ | ✅ green |
| 21-01-T2 | 01 | 1 | AnalogConfig + AnalogDevice typed | — | N/A | unit | `uv run pytest packages/rig-analog/tests/test_analog_device.py -q` | ✅ | ✅ green |
| 21-01-T3 | 01 | 1 | HXStompConfig + HXStompDevice typed | — | N/A | unit | `uv run pytest packages/rig-hx/tests/test_hx_device.py -q` | ✅ | ✅ green |
| 21-01-T4 | 01 | 1 | ChaseBlissDevice typed; guards removed | — | N/A | unit | `uv run pytest packages/rig-chasebliss/tests/test_device.py -q` | ✅ | ✅ green |
| 21-01-T5 | 01 | 1 | MC6Config + MC6Device typed | — | N/A | unit | `uv run pytest packages/rig-morningstar/tests/test_mc6_device.py -q` | ✅ | ✅ green |
| 21-01-T6 | 01 | 1 | Registry placeholder uses model_construct | — | N/A | unit | `uv run pytest packages/rig/tests/test_plugin.py -q` | ✅ | ✅ green |
| 21-01-T7 | 01 | 1 | isinstance(config, dict) guards removed | — | N/A | integration | `uv run pytest packages/rig/tests/test_plan.py packages/rig/tests/test_cli_plan.py -q` | ✅ | ✅ green |
| 21-01-T8 | 01 | 1 | Regression: typed preset annotations | — | N/A | unit | `uv run pytest packages/rig/tests/test_plugin.py -k "preset_field" -q` | ✅ | ✅ green |
| 21-01-MC6-presets | 01 | 1 | MC6Device.presets typed | — | N/A | manual | — | — | 📋 manual |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · 📋 manual*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `MC6Device.presets` typed as `list[PresetBase]` | T5 deviation | `Protocol` is not a valid Pydantic field annotation type; `isinstance(x, Protocol)` raises `TypeError`. MC6 has no real presets (always `[]`). The regression test in `test_plugin.py` explicitly excludes MC6 with a comment. | `grep -n "presets" packages/rig-morningstar/src/rig_morningstar/device.py` — confirms `list[Any]`; comment explains why |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are declared manual-only
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0: existing infrastructure sufficient
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-16
