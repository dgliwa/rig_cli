# Architecture Research — v1.3 Chase Bliss Pedal Support

**Milestone:** v1.3 Chase Bliss Pedal Support
**Date:** 2026-06-08

---

## Existing Apply Flow (rig-chasebliss plugin)

The `ChaseBlissDevice.apply(action, ctx)` method runs 3 phases keyed on setup state flags:

```
Phase 1: Channel setup (channel_established=False)
  → prompt user to set MIDI channel on pedal
  → send channel verification CC
  → set channel_established=True in state

Phase 2: Build presets (presets_saved[preset_id]=False)
  → for each preset in the scene:
    → prompt user to navigate to preset slot on pedal
    → send preset CCs (DigitalPreset.parameters → CC messages)
    → set presets_saved[preset_id]=True in state

Phase 3: Register scene (registration_done=False)
  → send PC message to activate the preset
  → set registration_done=True in state
```

The CC send step in Phase 2 iterates `preset.parameters` and sends each parameter as a CC message using the device's `midi_cc` from the catalog.

---

## Reset-to-Defaults Integration Point

**Where:** Inside Phase 2 ("build presets"), immediately before sending preset CCs.

**Why:** Phase 2 is the moment the user has navigated to the correct preset slot on the pedal and is ready for CC values to be set. Sending reset CCs first ensures the pedal is at a known neutral state before the preset CCs override specific values. This matches the user's intent: "clean slate for preset creation."

**Timing:**
```
Phase 2 (per preset):
  1. Prompt user to navigate to preset slot
  2. [NEW] Send reset CCs: all controls where default is not None → CC(cc, default)
  3. Send preset CCs: preset.parameters → CC(cc, value)
  4. Mark preset_saved in state
```

**Implementation:**

```python
def _build_reset_messages(controls: list[Control]) -> list[tuple[int, int]]:
    return [(c.midi_cc, int(c.default)) for c in controls if c.midi_cc is not None and c.default is not None]
```

Called in Phase 2 before the preset CC send loop.

---

## Validation Integration Point

**Where:** At the start of Phase 2, before prompting the user.

**Why:** Fail fast — if the YAML preset has an invalid parameter, tell the user before they physically navigate to the preset slot on the pedal. Failing after the user has already touched the pedal is worse UX.

**What it checks:**
1. Each key in `preset.parameters` must match a `control.name` in the device catalog
2. Each value must be within `control.min` to `control.max`

**Raises:** `ValidationError` from `rig.config.errors` with a message like:
```
Invalid parameter 'time_mode' for Brothers AM — not in catalog
Invalid parameter value 127.5 for 'mix' — must be between 0 and 127
```

---

## Control.default Field

**Required: yes.**

Without `default` on `Control`, the reset logic must hard-code rules (knob→64, toggle→0, etc.) in the apply code. That's fragile — it breaks if a pedal has a knob where "neutral" is not 64 (e.g., a trim knob where max=0 means clean). Encoding the default per-control in the catalog is the correct ownership boundary: the catalog knows what neutral means for each control.

Footswitches and utility CCs (bypass, tap tempo, EOM) get `default=None` to explicitly opt out of reset.

---

## New vs Modified Components

### New
- `rig_chasebliss/catalog.py`: `WOMBTONE_MKII_CONTROLS` catalog (new constant)
- `rig_chasebliss/catalog.py`: `BROTHERS_AM_CONTROLS` catalog (new constant)
- `rig_chasebliss/catalog.py`: Register new pedals in `_CATALOG` dict
- Reset helper function (can be in catalog.py or a new `reset.py`)

### Modified
- `rig_chasebliss/catalog.py`: Add `default: float | None = None` to `Control` model
- `rig_chasebliss/catalog.py`: Add `default=` values to existing `MOOD_MKII_CONTROLS`
- `rig_chasebliss/catalog.py`: Fix `MOOD_MKII_CONTROLS` gaps (CC24-29, CC31-33, CC52, CC103 name)
- `ChaseBlissDevice.apply()` (wherever it lives in the plugin): add validation + reset steps to Phase 2

---

## Suggested Build Order

### Phase 14: Control model + catalog data
- Add `default` field to `Control`
- Write `WOMBTONE_MKII_CONTROLS`, `BROTHERS_AM_CONTROLS`
- Backfill `default` values into existing `MOOD_MKII_CONTROLS`
- Fix Mood MkII catalog gaps (CC24-29, CC103 name)
- Register new pedals in `_CATALOG`
- Tests: catalog lookup, default values present

### Phase 15: Preset validation
- Add imperative validation in `ChaseBlissDevice.apply()` Phase 2
- Validate parameter names against catalog controls
- Validate parameter values against min/max ranges
- Raise `ValidationError` with clear message
- Tests: invalid param name, out-of-range value, valid preset passes

### Phase 16: Reset-to-defaults
- Implement `_build_reset_messages(controls)` helper
- Wire into Phase 2 before preset CC send
- Tests: reset CCs sent before preset CCs, footswitches excluded, None-default controls excluded

---

## Anti-Patterns to Avoid

**Don't add reset to Phase 1 (channel setup).** Reset is about parameter state, not channel configuration. Phase 1 fires only once per device; reset fires per-preset.

**Don't skip validation in dry_run mode.** Validation is read-only (no MIDI sent) and should always run so users catch YAML errors without needing a MIDI connection.

**Don't include footswitch CCs in reset.** Sending bypass=off would put the pedal into bypass during preset creation. Always check `default is not None` before including in reset batch.
