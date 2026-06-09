# Pitfalls Research — v1.3 Chase Bliss Pedal Support

**Milestone:** v1.3 Chase Bliss Pedal Support
**Date:** 2026-06-08

---

## CC Transcription Risks

**What can go wrong:** CBA manuals use "or >" notation (e.g., "BOOST = 0, 1 / OD = 2 / DIST = 3 OR >") meaning the toggle position is determined by value ranges, not exact values. Misreading this as "value must be 3" instead of "value >= 3 means DIST" leads to incorrect `max` in the catalog and failing validation.

**Prevention:** Model toggle positions with `min`/`max` across the full 0-127 range. For Brothers AM GAIN 2 TYPE, the full range is 0-127 even though there are only 3 positions. The `positions` list encodes the semantics; validation checks the value is in `[min, max]` not in the positions list.

**Also watch:** The Wombtone BYPASS CC uses 0-63=off, 64-127=on (mid-range split), not a simple 0=off / 1=on. If we ever add bypass to preset parameters, the range interpretation matters.

---

## Model Evolution Risks (Adding `default` Field)

**What can go wrong:** All existing `Control(...)` calls in `MOOD_MKII_CONTROLS` will need `default=` added. If some are missed, those controls will have `default=None` and be silently excluded from reset — correct behavior, but unintentional if the goal was to include them.

**Prevention:** After adding the field, grep for `Control(name=` in catalog.py and verify every non-footswitch/non-utility control has an explicit `default=` set. Add a test that asserts `all(c.default is not None for c in get_controls("chase_bliss", "mood_mkii") if c.type not in (ControlType.SWITCH,))` — or similar filter.

**Also watch:** `default: float | None` — the value must be a valid CC integer (0-127). Using a float is fine for the type but ensure all defaults are whole numbers when constructing CC messages (use `int(c.default)`).

---

## Validation Risks

**What can go wrong:** The validation will reject existing YAML presets that use parameter names not in the catalog (e.g., typos, old names). This is correct behavior but could surprise users.

**Prevention:** When validation raises `ValidationError`, include the pedal model name, the invalid parameter key, and the list of valid parameter names in the error message so users know exactly what to fix.

**Don't validate in dry_run=False mode only.** Validation is read-only and should run in all modes including dry_run and plan, so users catch YAML errors without needing a MIDI connection.

**Numeric coercion:** `preset.parameters` values are `float | str | bool`. Validation must coerce to float for range checks. A value of `True` (Python bool, subtype of int) is `1.0`; `False` is `0.0` — both valid in range.

---

## Reset Flow Risks

**What can go wrong:** Sending reset CCs before preset CCs is correct sequencing, but the pedal receives them over MIDI at speed. Some CBA pedals may need a small delay between CC bursts to avoid message drop if the MIDI buffer is small.

**Prevention:** In practice, CBA pedals handle rapid CC messages fine (they are designed for this). No sleep needed. If issues arise in testing, add a configurable delay — but default to no delay.

**Footswitch exclusion is critical:** If `ch1_bypass` (CC102=0) is accidentally included in the Brothers AM reset, it will bypass channel 1 during preset creation. Verify the exclusion logic by checking `default is not None` — all footswitch controls must be constructed with `default=None`.

**Don't reset between preset CCs:** All reset CCs must be sent as a batch before any preset CCs begin, not interleaved. The implementation must separate the two passes.

---

## Edition Variant Risks (Billy Strings Wombtone)

**What can go wrong:** The Billy Strings Wombtone (WT03) and standard Wombtone MkII could have different CC maps if CBA shipped a different firmware. The manual says "CBA + BS ref 2024 – WT03" — this is a co-branded edition.

**Finding from manual:** The CC map in the Billy Strings manual (CC14-20 knobs, CC21 note divisions, CC93/102 footswitches, CC100 EOM, CC51 clock ignore) appears to be the standard Wombtone MIDI implementation. No Billy Strings-specific CCs were identified.

**Prevention:** Name the catalog key `"wombtone_mkii"` not `"wombtone_bs"` so the catalog is reusable for all Wombtone MkII variants. If a standard Wombtone MkII is later added and the CC maps differ, create a separate catalog entry at that point.

---

## Missing Mood MkII Catalog Controls

The existing catalog was written as a partial implementation. The manual shows several controls not yet in catalog.py:

| Missing | CC | Consequence if left out |
|---------|-----|------------------------|
| stereo_width | 24 | Can't control via YAML preset |
| ramping_waveform | 25 | Can't control via YAML preset |
| loop_fade | 26 | Can't control via YAML preset |
| wet_tone | 27 | Can't control via YAML preset |
| level_balance | 28 | Can't control via YAML preset |
| direct_micro_loop | 29 | Can't control via YAML preset |
| sync | 31 | Can't control via YAML preset |
| spread | 32 | Can't control via YAML preset |
| buffer_length | 33 | Can't control via YAML preset |
| stop_ramping | 52 | Can't control via YAML preset |

These should be added in Phase 14 when the Mood MkII catalog is updated with `default=` values. Don't skip them — a partially complete catalog makes preset authoring confusing.

Also: **catalog name mismatch**: existing catalog has `micro_bypass` at CC102 but the manual calls it "WET BYPASS". And `wet_bypass` at CC103 but the manual says "LOOP BYPASS". These are swapped. Fix during Phase 14.

---

## Prevention Strategy — Top 3

1. **Test default completeness:** After Phase 14, assert that every non-footswitch/non-utility control in every pedal catalog has a non-None default. Prevents silent reset omissions.

2. **Validate with dry_run:** Run `rig plan --dry-run` with a test YAML preset after Phase 15 to confirm validation fires correctly without a MIDI connection. Catch type errors and missing controls early.

3. **Check CC102/103 naming carefully:** The Mood MkII manual assigns CC102=WET_BYPASS and CC103=LOOP_BYPASS. The existing catalog has them swapped. Sending a CC to the wrong channel is a silent physical bug — the user's pedal does the wrong thing. Verify against the manual during implementation.
