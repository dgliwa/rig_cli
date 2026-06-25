# Phase 29: Catalog Integrity — Context

## Phase Goal

The CBA control catalog is the single authoritative source for CC numbers; all tests derive expectations from the catalog, not hard-coded magic numbers.

## Requirement

**CAT-01**: CBA control catalog is the single authoritative source for CC numbers; tests derive from catalog constants, not duplicated literals; wet_bypass/loop_bypass CC numbers verified against Mood MkII MIDI spec.

## Root Cause (fully diagnosed)

`packages/rig-chasebliss/src/rig_chasebliss/catalog.py` has wet_bypass and loop_bypass CC numbers swapped:

| Control | Catalog (current, wrong) | Spec (correct) |
|---------|--------------------------|----------------|
| wet_bypass | CC103 | CC102 |
| loop_bypass | CC102 | CC103 |

**Evidence the spec says CC102=wet_bypass, CC103=loop_bypass:**
- PROJECT.md line 42: `✓ CBA-03: Mood MkII catalog backfill — CC102=wet_bypass, CC103=loop_bypass — v1.3`
- `packages/rig-chasebliss/tests/test_catalog.py` asserts `ccs[102].name == "wet_bypass"` and `ccs[103].name == "loop_bypass"`
- `packages/rig/tests/test_catalog.py` asserts `by_name["wet_bypass"].midi_cc == 102` and `by_name["loop_bypass"].midi_cc == 103`

## Current Failures

```
FAILED packages/rig/tests/test_catalog.py::TestMoodMkiiCatalog::test_knobs_have_correct_cc_numbers
FAILED packages/rig-chasebliss/tests/test_catalog.py::TestMoodMkiiCatalog::test_knobs_have_correct_cc_numbers
```

Both fail because catalog has wet_bypass=103 but test expects 102.

## Files in Scope

| File | Change |
|------|--------|
| `packages/rig-chasebliss/src/rig_chasebliss/catalog.py` | Swap wet_bypass/loop_bypass CC values; add named constants |
| `packages/rig/tests/test_catalog.py` | Use catalog constants instead of literal CC numbers |
| `packages/rig-chasebliss/tests/test_catalog.py` | Use catalog constants instead of literal CC numbers |

## Success Criteria

1. `make test` passes with 0 failures
2. Test assertions reference catalog constants, not duplicated literal CC numbers
3. The correct CC values (CC102=wet_bypass, CC103=loop_bypass) are verified against official Mood MkII MIDI spec

## Architecture Context

- `catalog.py` is in `packages/rig-chasebliss/src/rig_chasebliss/catalog.py`
- `MOOD_MKII_CONTROLS` is a module-level `list[Control]`
- Tests import `MOOD_MKII_CONTROLS` directly from `rig_chasebliss.catalog`
- No other code paths depend on the specific CC values for wet_bypass/loop_bypass (they're used only in tests and the catalog itself)

## Named Constants Pattern

Export module-level constants that the catalog list references, so tests import constants instead of using literals:

```python
# In catalog.py — define constants first
MOOD_MKII_WET_BYPASS_CC: int = 102   # per Mood MkII MIDI Implementation
MOOD_MKII_LOOP_BYPASS_CC: int = 103  # per Mood MkII MIDI Implementation

# Then the list references them
Control(name="wet_bypass", ..., midi_cc=MOOD_MKII_WET_BYPASS_CC, ...)
Control(name="loop_bypass", ..., midi_cc=MOOD_MKII_LOOP_BYPASS_CC, ...)
```

Tests then:
```python
from rig_chasebliss.catalog import MOOD_MKII_WET_BYPASS_CC, MOOD_MKII_LOOP_BYPASS_CC
assert by_name["wet_bypass"].midi_cc == MOOD_MKII_WET_BYPASS_CC
assert by_name["loop_bypass"].midi_cc == MOOD_MKII_LOOP_BYPASS_CC
```
