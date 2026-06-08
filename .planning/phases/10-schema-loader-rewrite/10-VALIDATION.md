---
phase: 10
slug: schema-loader-rewrite
status: validated
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-08
---

# Phase 10 — Validation Strategy

> Schema & Loader Rewrite — single-file rig.yaml and plugin-dispatched device construction.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `packages/rig/pyproject.toml` |
| **Quick run command** | `uv run pytest packages/rig/tests/test_loader.py -q --tb=short` |
| **Full suite command** | `uv run pytest packages/ -q --tb=short` |
| **Estimated runtime** | ~4.5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/rig/tests/test_loader.py -q --tb=short`
- **After every plan wave:** Run `uv run pytest packages/ -q --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

All 6 requirements are COVERED by automated tests. Every test passes green (274/274).

| Requirement | Task(s) | Test File(s) | Tests | Status |
|-------------|---------|-------------|-------|--------|
| SCHEMA-01 | Single rig.yaml file | `test_loader.py`, `test_catalog.py` | `test_loads_full_config`, `test_missing_rig_yaml`, `test_empty_devices_list`, `test_direct_path_to_rig_yaml`, `test_valid_fixture_loads` | ✅ green |
| SCHEMA-02 | Device order = signal chain | `test_loader.py` | `test_loads_signal_chain_from_device_order`, `test_no_signal_chain_file_needed` | ✅ green |
| SCHEMA-04 | Controller composes | `test_loader.py` | `test_controller_composes_validation`, `test_controller_composes_unknown_device` | ✅ green |
| SCHEMA-05 | Scenes in controller config | `test_loader.py` | `test_loads_scenes_from_controller`, `test_scenes_accessible_via_controller` | ✅ green |
| LOADER-01 | Single-file parser | `test_loader.py` | (same tests as SCHEMA-01) | ✅ green |
| LOADER-02 | Plugin dispatch via type | `test_loader.py` | `test_manual_config_produces_analog_device`, `test_midi_config_produces_hx_stomp_device`, `test_controller_config_produces_mc6_device`, `test_chase_bliss_config_produces_cba_device`, `test_unknown_config_type_raises_validation_error`, `test_all_devices_have_apply_method` | ✅ green |

### Wave mapping

| Wave | Task | Requirements | Verification |
|------|------|-------------|-------------|
| Wave 1 — Schema + Loader | Rewrite `load_rig()`, update fixture | SCHEMA-01, SCHEMA-02, LOADER-01, LOADER-02 | Single-file read, device dispatch, signal chain from order, unknown type error |
| Wave 2 — Composes + Scenes | Scene extraction, composes validation | SCHEMA-04, SCHEMA-05 | Scenes in rig.scenes, composes refs validated |
| Wave 3 — Test updates | Update test helpers, fix FIXTURE_PATH | All | All 274 tests pass, 11 plugin tests pass |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 setup needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification. Nothing is manual-only.

---

## Threat Model Verification

| Threat ID | Category | Disposition | Verification |
|-----------|----------|-------------|-------------|
| T-10-01 | Tampering — Device YAML → plugin model | accept | Plugin models validate own data; test_unknown_config_type_raises_validation_error confirms unknown types rejected |
| T-10-02 | Tampering — Controller scenes extraction | accept | test_broken_preset_reference, test_broken_pedal_reference confirm reference validation |
| T-10-03 | Information Disclosure — Signal chain as device order | accept | No test needed — device IDs are not secrets |

---

## Validation Sign-Off

- [x] All 6 requirements have automated tests that pass green
- [x] Sampling continuity: no gaps between tasks
- [x] Wave 0: not needed (infrastructure exists)
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-08

---

## Validation Audit 2026-06-08

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
