---
phase: 5
plan: P4
type: implementation
wave: 3
depends_on: [P2, P3]
files_modified:
  - src/rig/cli/commands/plan.py
requirements: [PLAN-03, PLAN-04, PLAN-05, PLAN-06, PLAN-07, PLAN-08, PLAN-09, D-06, D-07, D-08, D-09]
must_haves:
  - rig plan exits 0 when plan.status == "clean" and missing_refs is empty
  - rig plan exits 2 when plan.status == "changes_detected" OR missing_refs is non-empty
  - Cold-start warning printed when .rig/state.json is absent
  - Setup Actions section appears before Scenes section when cba_setup is non-empty
  - All CBA setup actions use the ~ marker; configure uses ~, verify uses checkmark, analog uses warning triangle
  - --show-unchanged flag controls display of scenes with ScenePlan.status == "unchanged" (scene-level, not device-action-level)
  - ConfigError (including CycleError) from compute_plan() is caught and printed cleanly with Exit(1)
  - Summary line appears after scenes section
  - Warnings section at bottom shows missing_refs with red X and unused_presets with yellow exclamation
  - CLI smoke tests in tests/test_cli_plan.py: exit code 0 on clean, exit code 2 on changes, cold-start warning
  - --scene flag continues to filter output
  - --format json continues to work and includes new fields
---

# Phase 5 P4: rig plan CLI Command Overhaul

## Context

The existing `rig plan` command in `src/rig/cli/commands/plan.py` has a basic output format with
inconsistent markers and no exit code discipline. This plan delivers the full specification from
PLAN-03 through PLAN-09 and D-06 through D-09: two-section output (Setup Actions then Scenes),
visual markers, summary line, exit codes, cold-start warning, warnings section, and the
`--show-unchanged` flag.

Read `src/rig/cli/commands/plan.py` fully before editing. The existing command is 96 lines.
The rewrite is a full replacement of the `plan()` function body while keeping the same function
signature (plus `show_unchanged`), the same imports where still needed, and the same error
handling pattern.

---

## Task P5-T8: Rewrite plan() command body in plan.py

**File:** `src/rig/cli/commands/plan.py`

**Changes:**

**Signature addition (PLAN-08):** Add `show_unchanged: bool = typer.Option(False, "--show-unchanged", help="Show devices with no changes")` as the last parameter of the `plan()` function. All other parameters stay the same.

**ConfigError catch around compute_plan():** The existing try/except in plan.py only wraps
`load_rig()`. DeviceGraph cycle detection raises `ConfigError` (a `CycleError` subclass) inside
`compute_plan()`. Wrap the `compute_plan()` call too:

```python
try:
    result = compute_plan(rig, root_path=...)
except ConfigError as e:
    console.print(f"[red]✗[/red] {e}")
    raise typer.Exit(1)
```

**Cold-start detection (PLAN-07):** After `rig = load_rig(config)` succeeds and before calling
`compute_plan()`, check for the state file:

```python
state_path = Path(config).resolve() / ".rig" / "state.json"
if not state_path.exists():
    console.print("[yellow]⚠ Cold start — no state file found. Treating all scenes as new.[/yellow]")
```

The `Path(config).resolve()` call handles both relative and absolute config paths. The existing
line 41 already passes `Path(config).resolve()` to `compute_plan` — keep that.

**JSON format (PLAN-04):** Unchanged — `_emit_json(result.model_dump_json(indent=2))` already
handles it. The new fields (`missing_refs`, `unused_presets`, `before`, `after`) are
automatically included in `model_dump_json()` since they are on the Pydantic models. No change
needed here.

**Two-section output (D-07):** Replace the entire rendering block (lines 47-95) with the
following structure:

*Section 1 — Setup Actions* (only when `result.cba_setup` is non-empty):

Print `"\n[bold]Setup Actions[/bold]"` as the section header.
For each action in `result.cba_setup`:
- All types use the `~` marker (D-08):
  `[yellow]~[/yellow]  {action.device}: {action.type}`
  Append detail inline: for `establish_channel` add `" (ch {action.midi_channel})"`, for
  `build_preset` add `" preset #{action.preset_number} '{action.preset_name}'"`, for
  `register_scenes` add `" ({len(action.scene_refs)} scene(s))"`.

*Section 2 — Scenes*:

Print `"\n[bold]Scenes[/bold]"` as the section header.

Build `scene_names` from `[scene]` if the `--scene` flag was passed, else from
`list(result.scenes.keys())` (PLAN-09 — already handled this way; preserve it).

For each `name` in `scene_names`:
- Get `sp = result.scenes.get(name)`. If `None`, print `[yellow]Scene '{name}' not found[/yellow]`
  and continue.
- If `sp.status == "unchanged"` AND `not show_unchanged`, skip the scene entirely (PLAN-08).
- Print scene header: use status-specific prefix and color:
  - `"new"` → `[cyan]+[/cyan] [bold]{sp.scene_name}[/bold] (new)`
  - `"changed"` → `[yellow]~[/yellow] [bold]{sp.scene_name}[/bold] (changed)`
  - `"unchanged"` → `[green]·[/green] [bold]{sp.scene_name}[/bold] (unchanged)`
- For each action in `sp.device_actions`:
  - `status == "analog"` → `  [yellow]⚠[/yellow]  {action.device}: set to '{action.after or action.preset_name}' (manual)`
  - `status == "configure"` → `  [yellow]~[/yellow]  {action.device}` + optional ` PC#{action.preset_number}` if non-None + ` '{action.after or action.preset_name}'` + optional ` (ch {action.midi_channel})` if non-None
  - `status == "verify"` → `  [green]✓[/green]  {action.device}: '{action.after or action.preset_name}' (already set)`

*Summary line (PLAN-05, D-09)*:

Count across all scenes and setup actions:
- `configure_count`: actions with `status == "configure"` across all scene `device_actions` + `len(result.cba_setup)` (CBA setup actions count as "to configure", per D-09)
- `manual_count`: actions with `status == "analog"` across all scene `device_actions`
- `already_set_count`: actions with `status == "verify"` across all scene `device_actions`

Print after the scenes section:
- If `configure_count == 0` and `manual_count == 0`: `"\n[green]No changes. Rig is up to date.[/green]"`
- Else: `"\nPlan: [yellow]{configure_count} to configure[/yellow], [yellow]{manual_count} manual[/yellow], [green]{already_set_count} already set[/green]"`

*Warnings section (D-06)*:

If `result.missing_refs` is non-empty, print `"\n[bold red]Warnings — Missing References:[/bold red]"` then for each entry print `"  [red]✗[/red]  {ref}"`.

If `result.unused_presets` is non-empty, print `"\n[bold yellow]Warnings — Unused Presets:[/bold yellow]"` then for each entry print `"  [yellow]![/yellow]  {pid}"`.

*State source dim line*:

Remove the existing conditional `config_exists` check (lines 93-95) and replace with an
unconditional dim footer printed after warnings:
`console.print("\n[dim]State source: .rig/state.json[/dim]")`

**Exit codes (PLAN-06):**

After all output is printed, add:

```python
if result.status == "changes_detected" or result.missing_refs:
    raise typer.Exit(2)
```

No explicit `raise typer.Exit(0)` is needed — Typer's implicit return is exit code 0 when no
exception is raised. Exit code 1 is already used for `ConfigError` (line 39). Exit code 2 is new
for "changes pending or errors detected".

**Remove or replace:** The existing emoji-based CBA section (lines 76-88) is replaced by the
Setup Actions section above. The old status icon dict (lines 55-57) is replaced by the per-status
inline logic above.

### Task P5-T8b: Add CLI smoke tests for plan command (tests/test_cli_plan.py)

**File:** `tests/test_cli_plan.py` (new file)

Create 4 CliRunner tests using `typer.testing.CliRunner` and `from rig.cli import app`. Each
test writes a minimal rig config to `tmp_path` (at minimum a `rig.yaml`, `signal-chain.yaml`,
and one scene). Use the fixture-based pattern from `tests/test_plan.py`.

- `test_plan_exits_0_when_clean(tmp_path)`: write a rig config and a matching `state.json`;
  invoke `runner.invoke(app, ["plan", str(tmp_path)])`; assert `result.exit_code == 0`.
- `test_plan_exits_2_when_changes_detected(tmp_path)`: write a rig config with no state.json;
  invoke plan; assert `result.exit_code == 2`.
- `test_plan_cold_start_warning(tmp_path)`: write a rig config, no state.json; invoke plan;
  assert `"Cold start"` in `result.output`.
- `test_plan_summary_line_present(tmp_path)`: write a rig config with no state.json; invoke plan;
  assert `"Plan:"` in `result.output` OR `"No changes"` in `result.output`.

To write minimal rig YAML config: use `load_rig()` from the loader, which expects a directory
path with `rig.yaml`, `signal-chain.yaml`, and `pedals/<id>.yaml` files. Simplest approach:
write the YAML files programmatically using `yaml.dump()` with the minimal fields required by
the loader, then invoke the CLI with the directory path.

Alternatively, check if `tests/fixtures/` or `tests/data/` has a sample rig directory that can
be reused as the config path.

### Verification

```
uv run pytest tests/test_cli_plan.py -v
uv run pytest tests/ -v -k "not test_apply"
```

All tests (existing + new) must pass. Zero failures.

```
uv run python -c "from rig.cli.commands.plan import plan; print('import ok')"
```

Must print `import ok` with no import errors.
