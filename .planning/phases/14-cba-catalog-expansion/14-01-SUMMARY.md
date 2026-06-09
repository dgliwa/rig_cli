---
phase: 14-cba-catalog-expansion
plan: 01
status: complete
commit: 2e4ed2e
---

## What was done

Expanded the rig-chasebliss catalog package with complete control definitions for three Chase Bliss Audio pedals.

**Control model change:**
- Added `default: float | None = None` field to `Control` (backward-compatible; existing call sites that omit `default` get `None`)
- Removed stale TODO comment

**Mood MkII fixes and additions:**
- CC102 renamed `micro_bypass` → `wet_bypass`; CC103 renamed `wet_bypass` → `loop_bypass` (per CBA-03)
- Added 13 missing controls: CC24-29 (hidden options), CC31-33 (sync/spread/buffer), CC51 (midi_clock_ignore), CC52 (stop_ramping), CC53-54 (clock divisions), CC55 (true_bypass)
- All KNOB controls have `default=64`; all SWITCH controls have `default=None`; all DIPSWITCH controls have `default=0`
- Total: 47 controls

**New catalogs:**
- `WOMBTONE_MKII_CONTROLS` — 12 controls (CC14-21 parameter controls + 4 utility switches); registered as `"Chase Bliss Audio/Wombtone MkII"`
- `BROTHERS_AM_CONTROLS` — 28 controls (8 knobs, 3 toggles, 15 dipswitches, 2 footswitches); registered as `"Chase Bliss Audio/Brothers AM"`

**Tests:**
- Created `packages/rig-chasebliss/tests/test_catalog.py` with 14 tests covering model backward-compat, CC name correctness, default value rules, and `get_controls` lookup
- All 14 tests pass; no regressions

## Must-haves satisfied

- [x] `Control` model has `default: float | None = None`
- [x] All SWITCH controls have `default=None`
- [x] All KNOB controls have numeric defaults
- [x] `WOMBTONE_MKII_CONTROLS` exists and is registered in `_CATALOG`
- [x] `BROTHERS_AM_CONTROLS` exists and is registered in `_CATALOG`
- [x] Mood MkII CC102 is `wet_bypass`; CC103 is `loop_bypass`
- [x] Mood MkII contains CC24, CC25, CC26, CC27, CC28, CC29, CC31, CC32, CC33, CC52
- [x] `uv run pytest packages/rig-chasebliss/ -q` passes (14 passed)
