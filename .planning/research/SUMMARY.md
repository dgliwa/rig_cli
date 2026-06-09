# Research Summary — v1.3 Chase Bliss Pedal Support

**Project:** rig-cli — v1.3 Chase Bliss Pedal Support
**Sources:** Official Chase Bliss MIDI manuals (Mood MkII MD2, Billy Strings Wombtone WT03, Brothers AM BAM01)
**Date:** 2026-06-08
**Confidence:** HIGH

## Executive Summary

Three-phase milestone: add `default` field to Control model + write Wombtone MkII and Brothers AM catalogs (also fix Mood MkII gaps), then add imperative preset parameter validation in the ChaseBlissDevice apply flow, then implement reset-to-defaults (send all parameter CCs to neutral before applying a preset). No new dependencies.

The existing Mood MkII catalog is partially complete — 10 controls from the manual are missing (CC24-29, CC31-33, CC52) and CC102/CC103 names are swapped vs the manual. These must be fixed in Phase 14 when the `default` field is added.

## Key Findings

### Stack

No new dependencies. One additive model change: `default: float | None = None` on `Control`. Backward compatible — all existing `Control(...)` calls continue to work. `None` means "excluded from reset" (footswitches, utility CCs).

### Features

**Wombtone MkII:** 7 knobs (CC14-20, default=64) + 1 toggle/note-divisions (CC21, default=3/quarter note). Very simple. No dip switches. 3 utility controls excluded from reset.

**Brothers AM:** 8 knobs (CC14-19, CC27, CC29, default=64) + 3 toggles (CC21-23, defaults=0/0/2) + 15 dip switches (CC61-68, CC71-77, default=0 each). Richest control surface of the three pedals.

**Mood MkII gaps to fix:** Add CC24-29 (hidden options), CC31-33 (sync/spread/buffer_length), CC52 (stop_ramping). Fix name swap: CC102 = wet_bypass, CC103 = loop_bypass (currently reversed in code).

### Architecture

**Reset-to-defaults** fires in Phase 2 ("build presets") immediately before preset CC messages. `_build_reset_messages(controls)` returns `[(cc, int(default)) for c in controls if c.midi_cc and c.default is not None]`.

**Validation** fires at the start of Phase 2 before prompting the user to navigate to the preset slot — fail fast, before any physical interaction.

**Build order:** Phase 14 (catalog data + Control.default) → Phase 15 (validation) → Phase 16 (reset)

### Watch Out For

1. **CC102/103 name swap** — existing catalog has `micro_bypass` at CC102 and `wet_bypass` at CC103, but the manual says CC102=WET_BYPASS and CC103=LOOP_BYPASS. Sending the wrong CC is a silent physical bug.

2. **Brothers AM toggle range semantics** — "BOOST = 0, 1 / OD = 2 / DIST = 3 OR >" means value ranges, not exact integers. Validate against `min`/`max` (0-127); the `positions` list is metadata only.

3. **Footswitch default=None is load-bearing** — if any footswitch accidentally gets a numeric default, the reset flow will bypass the pedal during preset creation. Assert `SWITCH` type controls always have `default=None`.

## Phase Recommendation

| Phase | Focus | Key Deliverable |
|-------|-------|-----------------|
| 14 | Catalog data | `WOMBTONE_MKII_CONTROLS`, `BROTHERS_AM_CONTROLS`, `default=` on all controls, Mood MkII gap/name fixes |
| 15 | Preset validation | Imperative validation in apply() Phase 2; `ValidationError` on bad param names/values |
| 16 | Reset-to-defaults | `_build_reset_messages()` helper; wired into apply() Phase 2 before preset CCs |

---
*Research completed: 2026-06-08 | Ready for roadmap: yes*
