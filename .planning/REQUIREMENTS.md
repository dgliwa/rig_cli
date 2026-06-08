# Requirements — v1.3 Chase Bliss Pedal Support

**Milestone:** v1.3 Chase Bliss Pedal Support
**Status:** Active
**Last updated:** 2026-06-08

---

## Milestone Goal

Add full MIDI CC catalog, preset validation, and apply integration for Mood MkII (gap-fill), Wombtone MkII, and Brothers AM Chase Bliss pedals, including a reset-to-defaults step in the apply flow for clean preset creation.

---

## Active Requirements

### Catalog

- [ ] **CBA-01**: Wombtone MkII MIDI CC catalog — all 8 parameter controls (CC14-21) with CC numbers, ranges, positions, and default values
- [ ] **CBA-02**: Brothers AM MIDI CC catalog — all 24 parameter controls (8 knobs, 3 toggles, 15 dip switches; CC14-77) with CC numbers, ranges, positions, and default values
- [ ] **CBA-03**: Mood MkII catalog backfill — add 10 missing controls (CC24-29 hidden options, CC31-33 sync/spread/buffer, CC52 stop-ramping), fix CC102/103 name swap (wet_bypass/loop_bypass are reversed), and add `default=` values to all existing controls
- [ ] **CBA-04**: `Control` model gains optional `default: float | None = None` field; footswitches and global/utility CCs always get `default=None` to exclude them from reset

### Validation

- [ ] **CBA-05**: When applying a Chase Bliss preset, parameter names are validated against the device's catalog controls (unknown name → `ValidationError` with helpful message); parameter values are validated against `control.min`/`control.max` range (out-of-range → `ValidationError`); validation runs before prompting the user to navigate to the preset slot on the pedal, and always runs including in dry-run mode

### Reset

- [ ] **CBA-06**: Before sending a preset's CC parameter values during apply Phase 2, all catalog controls with a non-None default are sent to their default CC value (reset-to-defaults); footswitches and utility CCs (`default=None`) are excluded from the reset batch; reset fires per-preset immediately before preset CC messages

---

## Future Requirements

| Requirement | Reason Deferred |
|-------------|-----------------|
| Synth Mode controls (Mood MkII CC57-84) | Saved globally, not per-preset; separate workflow concern |
| CBA pedals beyond these three | Add when hardware is available for testing |
| Plugin authoring docs (PKG-07) | Nice-to-have; not blocking pedal support |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Standard (non-BS) Wombtone MkII catalog separation | Billy Strings Wombtone uses standard CC map — same catalog applies |
| Pydantic model_validator for preset validation | Requires catalog lookup at construction time; imperative validation in apply() is correct |
| Delay/sleep between reset and preset CC sends | CBA pedals handle rapid CC messages; no evidence of buffer overflow |
| MIDI RESET (CC110) in reset flow | Factory reset — never invoke as part of apply |

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| CBA-04 | — | Pending roadmap |
| CBA-01 | — | Pending roadmap |
| CBA-02 | — | Pending roadmap |
| CBA-03 | — | Pending roadmap |
| CBA-05 | — | Pending roadmap |
| CBA-06 | — | Pending roadmap |
