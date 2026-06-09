# Features Research — CBA MIDI CC Catalogs

**Milestone:** v1.3 Chase Bliss Pedal Support
**Source:** Official Chase Bliss MIDI manuals (PDF)

---

## Mood MkII — Complete CC Map (from official manual)

| CC# | Control Name | Type | Min | Max | Default | Positions/Notes |
|-----|-------------|------|-----|-----|---------|-----------------|
| 14 | time | KNOB | 0 | 127 | 64 | Synced time values per manual pg.8 |
| 15 | mix | KNOB | 0 | 127 | 64 | |
| 16 | length | KNOB | 0 | 127 | 64 | Synced length values per manual pg.8 |
| 17 | wet_modify | KNOB | 0 | 127 | 64 | |
| 18 | clock | KNOB | 0 | 127 | 64 | Stepped clock values per manual pg.8 |
| 19 | loop_modify | KNOB | 0 | 127 | 64 | Tape/Stretch mode speed values per pg.8 |
| 20 | ramp_speed | KNOB | 0 | 127 | 64 | |
| 21 | wet_channel | TOGGLE | 0 | 127 | 0 | 0-1=reverb, 2=delay, >2=slip |
| 22 | routing | TOGGLE | 0 | 127 | 0 | 0-1=in, 2=wet_and_in, >2=wet |
| 23 | loop | TOGGLE | 0 | 127 | 0 | 0-1=env, 2=tape, >2=stretch |
| 24 | stereo_width | KNOB | 0 | 127 | 64 | Hidden option |
| 25 | ramping_waveform | KNOB | 0 | 127 | 0 | Hidden option; 0-14=saw, 15-54=triangle, 55-80=sine, 81-126=square, 127=random |
| 26 | loop_fade | KNOB | 0 | 127 | 64 | Hidden option |
| 27 | wet_tone | KNOB | 0 | 127 | 64 | Hidden option |
| 28 | level_balance | KNOB | 0 | 127 | 64 | Hidden option |
| 29 | direct_micro_loop | KNOB | 0 | 127 | 64 | Hidden option |
| 31 | sync | TOGGLE | 0 | 127 | 0 | 0-1=wet>loop, 2=no sync, >2=loop>wet |
| 32 | spread | TOGGLE | 0 | 127 | 0 | 0-1=loop only, 2=both, >2=wet only |
| 33 | buffer_length | TOGGLE | 0 | 127 | 0 | 0-1=half (MKI style), >1=full |
| 51 | midi_clock_ignore | SWITCH | 0 | 127 | 0 | 0=ignore, >0=follow |
| 52 | stop_ramping | SWITCH | 0 | 127 | 0 | 0=stop, >0=resume |
| 53 | wet_clock | TOGGLE | 0 | 7 | 5 | 0=32nd, 1=16th, 2=8th_triplet, 3=8th, 4=dotted_8th, 5=quarter, 6=half, 7=whole |
| 54 | loop_clock_division | TOGGLE | 0 | 7 | 5 | same divisions as CC53 |
| 55 | true_bypass | SWITCH | 0 | 127 | 0 | 0=standard buffered, 1-127=true bypass |
| 61 | dip_l_time | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 62 | dip_l_wet_modify | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 63 | dip_l_clock | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 64 | dip_l_loop_modify | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 65 | dip_l_length | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 66 | dip_l_bounce | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 67 | dip_l_sweep | DIPSWITCH | 0 | 127 | 0 | B=0, T=1+ |
| 68 | dip_l_polarity | DIPSWITCH | 0 | 127 | 0 | F=0, R=1+ |
| 71 | dip_r_classic | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 72 | dip_r_miso | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 73 | dip_r_spread | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 74 | dip_r_dry_kill | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 75 | dip_r_trails | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 76 | dip_r_latch | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 77 | dip_r_no_dub | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 78 | dip_r_smooth | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 93 | tap_tempo_alt | SWITCH | 0 | 127 | — | any value >0 triggers tap; excluded from reset |
| 100 | expression_over_midi | KNOB | 0 | 127 | — | EOM; excluded from preset reset |
| 102 | wet_bypass | SWITCH | 0 | 127 | — | footswitch; excluded from reset |
| 103 | loop_bypass | SWITCH | 0 | 127 | — | footswitch; excluded from reset |
| 105 | freeze | SWITCH | 0 | 127 | — | footswitch; excluded from reset |
| 106 | loop_overdub | SWITCH | 0 | 127 | — | footswitch; excluded from reset |
| 107 | tap_tempo | SWITCH | 0 | 127 | — | footswitch; excluded from reset |

### Gaps vs existing catalog.py

The existing `MOOD_MKII_CONTROLS` is missing:
- **CC24-29**: Hidden options (stereo_width, ramping_waveform, loop_fade, wet_tone, level_balance, direct_micro_loop)
- **CC31-33**: sync, spread, buffer_length
- **CC52**: stop_ramping
- **CC100**: expression_over_midi
- **CC103**: loop_bypass (catalog has `wet_bypass` as CC103 — **ERROR**: manual says loop_bypass=103, wet_bypass=102)
- **CC104**: hidden_menu (footswitch; not in scope)

Also: catalog has `micro_bypass` (CC102) which doesn't match the manual name — manual says "WET BYPASS" for CC102, "LOOP BYPASS" for CC103. Names need correction.

---

## Wombtone MkII (Billy Strings Edition) — Complete CC Map

| CC# | Control Name | Type | Min | Max | Default | Positions/Notes |
|-----|-------------|------|-----|-----|---------|-----------------|
| 14 | feed | KNOB | 0 | 127 | 64 | |
| 15 | volume | KNOB | 0 | 127 | 64 | |
| 16 | mix | KNOB | 0 | 127 | 64 | |
| 17 | rate | KNOB | 0 | 127 | 64 | |
| 18 | depth | KNOB | 0 | 127 | 64 | |
| 19 | form | KNOB | 0 | 127 | 64 | |
| 20 | ramp | KNOB | 0 | 127 | 64 | |
| 21 | midi_note_divisions | TOGGLE | 0 | 5 | 3 | 0=whole, 1=half, 2=quarter_triplet, 3=quarter, 4=eighth, 5=sixteenth |
| 51 | midi_clock_ignore | SWITCH | 0 | 127 | — | 0=off, 127=listening; global, excluded from reset |
| 93 | tap | SWITCH | 0 | 127 | — | footswitch; excluded from reset |
| 100 | expression_over_midi | KNOB | 0 | 127 | — | EOM; excluded from reset |
| 102 | bypass | SWITCH | 0 | 127 | — | 0-63=off, 64-127=on; footswitch; excluded from reset |

### Notes
- Billy Strings Wombtone (WT03) and standard Wombtone share the same MIDI implementation — no edition-specific CC differences confirmed in the manual.
- Very simple compared to Mood MkII: only 7 knobs + clock division toggle + 3 utility controls.
- No dip switches.

---

## Brothers AM — Complete CC Map

| CC# | Control Name | Type | Min | Max | Default | Positions/Notes |
|-----|-------------|------|-----|-----|---------|-----------------|
| 14 | gain_2 | KNOB | 0 | 127 | 64 | |
| 15 | volume_2 | KNOB | 0 | 127 | 64 | |
| 16 | gain_1 | KNOB | 0 | 127 | 64 | |
| 17 | tone_2 | KNOB | 0 | 127 | 64 | |
| 18 | volume_1 | KNOB | 0 | 127 | 64 | |
| 19 | tone_1 | KNOB | 0 | 127 | 64 | |
| 21 | gain_2_type | TOGGLE | 0 | 127 | 0 | 0-1=boost, 2=od, 3+=dist |
| 22 | treble_boost | TOGGLE | 0 | 127 | 1 | 0-1=full_sun, 2=off, 3+=half_sun |
| 23 | gain_1_type | TOGGLE | 0 | 127 | 2 | 0-1=dist, 2=od, 3+=boost |
| 27 | presence_2 | KNOB | 0 | 127 | 64 | |
| 29 | presence_1 | KNOB | 0 | 127 | 64 | |
| 61 | dip_l_volume_1 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 62 | dip_l_volume_2 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 63 | dip_l_gain_1 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 64 | dip_l_gain_2 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 65 | dip_l_tone_1 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 66 | dip_l_tone_2 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 67 | dip_l_sweep | DIPSWITCH | 0 | 127 | 0 | B=0, T=1+ |
| 68 | dip_l_polarity | DIPSWITCH | 0 | 127 | 0 | F=0, R=1+ |
| 71 | dip_r_hi_gain_1 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 72 | dip_r_hi_gain_2 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 73 | dip_r_motobyp_1 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 74 | dip_r_motobyp_2 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 75 | dip_r_pres_link_1 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 76 | dip_r_pres_link_2 | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 77 | dip_r_master | DIPSWITCH | 0 | 127 | 0 | off=0, on=1+ |
| 100 | expression_over_midi | KNOB | 0 | 127 | — | EOM; excluded from reset |
| 102 | ch1_bypass | SWITCH | 0 | 127 | — | footswitch; excluded from reset |
| 103 | ch2_bypass | SWITCH | 0 | 127 | — | footswitch; excluded from reset |
| 111 | preset_save | SWITCH | 1 | 122 | — | preset management; excluded from reset |

---

## Reset-to-Defaults Strategy

**What "reset" means:** Send all parameter controls to their neutral default value before applying a preset's CC values. The goal is a clean slate so the preset overrides are deterministic regardless of current pedal state.

**Default value rules:**
- **Knobs** (0-127): default = 64 (noon/center position)
- **Toggles**: default = first position value (0)
- **Dipswitches**: default = 0 (off)
- **Footswitches/bypass**: **excluded** — don't reset bypass state during preset apply
- **Global/utility CCs** (EOM, MIDI clock ignore, preset save, tap tempo): **excluded** — not per-preset parameters

**Controls excluded from reset:**
- All footswitch controls (CC93, CC102, CC103, CC104, CC105, CC106, CC107)
- EOM (CC100) — expression pedal assignment
- MIDI CLOCK IGNORE (CC51) — global behavior
- PRESET SAVE (CC111) — control message, not parameter
- MIDI RESET (CC110) — factory reset, never send in reset flow
- Synth mode controls (CC57-84 on Mood MkII) — saved globally, not per-preset

---

## Catalog Key

**Control types used:**
- `KNOB` — continuous 0-127 parameter
- `TOGGLE` — discrete positions (2-8 values)
- `SWITCH` — momentary or on/off (footswitch or mode toggle)
- `DIPSWITCH` — physical dip switch, on/off
