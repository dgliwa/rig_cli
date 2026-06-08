# Phase 12: Clean Up Deferred Items — Context

**Gathered:** 2026-06-08
**Status:** Ready for planning
**Source:** User discussion following Phase 11 execution

<domain>
## Phase Boundary

Phase 12 resolves the two deferred items from Phase 10 (Schema & Loader Rewrite):

- **DEFER-01:** The `rig generate mc6` CLI command writes MC6 bank JSON files to disk, but this is vestigial — `rig apply` programs the MC6 over MIDI SysEx directly. The generator is unused in practice and should be removed entirely.
- **DEFER-02:** The `composes` field on controller devices is validated during loading (cross-referencing device IDs) but nothing in the runtime reads it. Since it has no consumers, the validation can be removed.
</domain>

<decisions>
## Implementation Decisions

### DEFER-01 — Remove `generate mc6` entirely

- The `rig generate mc6` CLI command, the `gen_app` Typer group, and the `rig_morningstar.generator` module are all dead code
- The MIDI-based `rig apply` pipeline is the real mechanism for MC6 programming
- Remove the CLI command, the generator module, and all associated tests
- Do not replace with anything — the gap does not exist

### DEFER-02 — Remove `composes` validation

- `_get_composes()` in loader.py reads the field; `_validate_references()` validates device IDs exist
- No applier, plan engine, generator, or runtime code consumes the value
- Remove `_get_composes()` and the composes validation block from `_validate_references()`
- The YAML field can remain silently in data (no schema enforcement needed)

### Claude's Discretion
- No other decisions needed — both items are straightforward removals
</decisions>

<canonical_refs>
## Canonical References

### Generate command
- `packages/rig/src/rig/cli/commands/generate.py` — CLI command to remove
- `packages/rig/src/rig/cli/_shared.py` — defines `gen_app` Typer
- `packages/rig/src/rig/cli/__init__.py` — imports and registers `gen_app`

### Morningstar generator
- `packages/rig-morningstar/src/rig_morningstar/generator.py` — generator module to remove

### Composes validation
- `packages/rig/src/rig/config/loader.py` — `_get_composes()` (lines 144-149) and validation block (lines 183-191)

### Test files
- `packages/rig/tests/test_mc6_generator.py` — 5 tests for `generate_mc6`/`write_mc6_config`
- `packages/rig/tests/test_catalog.py` — 4 tests importing `generate_mc6`
- `packages/rig/tests/test_cli.py` — `TestGenerateMC6` class (1 test)
- `packages/rig/tests/test_loader.py` — `test_controller_composes_validation` and `test_controller_composes_unknown_device` (2 tests)
</canonical_refs>

<specifics>
## Specific Ideas

- The `generator.py` file is 75 lines — `generate_mc6()` and `write_mc6_config()`
- The `generate.py` CLI file is 41 lines — single `mc6` subcommand on `gen_app`
- Removing `gen_app` from `_shared.py` also removes the Typer group entirely
- `cli/__init__.py` needs both the import of `generate` module and the `app.add_typer(gen_app)` line removed
- `composes` validation is ~15 lines total across `_get_composes()` and the validation loop
- Test fixture that referenced composes is inline in `test_loader.py` (not in a fixture file)
</specifics>

<deferred>
## Deferred Ideas

- None — both deferred items are resolved in this phase
</deferred>

---

*Phase: 12-clean-up-deferred-items*
*Context gathered: 2026-06-08 via user discussion*
