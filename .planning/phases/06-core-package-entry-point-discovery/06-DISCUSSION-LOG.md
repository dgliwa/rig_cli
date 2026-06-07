# Discussion Log — Phase 6: Core Package & Entry Point Discovery

**Date:** 2026-06-07

## Questions Asked

No formal questions needed — user provided clear direction in milestone context. Decisions captured directly in CONTEXT.md based on:

1. User's explicit specification: "Distributed pip Package Model combined with Setuptools Entry Points"
2. User's vision: "each device system is its own managed package that can be optionally installed"
3. User's design constraint: "if a device's plan requires a MIDI connection to configure, that should be handled at the device setup level"
4. User's confirmation: core package is `rig`, plugins are `rig-analog`, `rig-chasebliss`, `rig-morningstar`, `rig-hx`
5. Existing WIP code structure in `packages/`

## User Direction

- User explicitly asked to stop asking questions and write decisions to CONTEXT.md instead
- "Should you be writing this stuff to the roadmap?" → Corrective: make decisions and document, don't discuss

## Decisions Made (by Claude, within user's expressed constraints)

- D-01: Entry points → Device class directly, not `register()` callbacks
- D-02: Discovery at PluginRegistry init (CLI startup), graceful degradation
- D-03: Remove old `devices.py` hard-coded registrations; entry points are single path
- D-04: Plugin authoring interface = Model class + pyproject.toml entry point, no register()
- D-05: Device-level MIDI ownership — plugins manage their own connections
- D-06: Core `rig` declares empty `rig.devices` group in pyproject.toml

## Deferred Ideas

- MIDI port sharing/connection pooling
- Plugin version compatibility checking
- Plugin discovery caching
- Hot-reload of plugins

---
*Phase: 6-core-package-entry-point-discovery*
*Discussion concluded: 2026-06-07*
