---
grounding_kind: flow
status: reviewed
last_verified: "2026-06-18"
source_anchors:
  - path: cli-anything-plugin/HARNESS.md
  - path: cli-anything-plugin/skill_generator.py
    symbol: generate_skill_file
  - path: cli-anything-plugin/verify-plugin.sh
  - path: registry.json
owners: [cli-anything-team]
---

# Flow: Add a new app harness

The end-to-end path a contributor (or agent) follows to make a new application
agent-native and ship it in CLI-Anything. The authoritative procedure is the blueprint
[[anchor: cli-anything-plugin/HARNESS.md]]; this flow is the boundary-level map.

## Steps

1. **Recon the app** — identify its backend engine, data model (file formats / project
   state), any existing CLI it ships, and its undo/command system (HARNESS.md Phase 1).
2. **Scaffold the package** — create `<app>/agent-harness/` with `setup.py` (console entry
   `cli-anything-<app>`), and the namespace tree `cli_anything/<app>/` containing `core/`,
   `utils/`, `tests/`, `skills/`. `cli_anything/` has NO `__init__.py`; `<app>/` HAS one
   (INV-006).
3. **Build core** — implement the pure state model in `core/` (scene/data ops, plus a
   `Session` for undo/redo). Keep it stdlib-only and importable without the real app (INV-002).
4. **Build the CLI** — define Click groups in `<app>_cli.py`; every command supports `--json`
   and the root group enters the REPL when invoked with no subcommand.
5. **Build the backend** — `utils/<app>_backend.py` finds the executable via `shutil.which`
   and shells out headless; a missing app raises a guided `RuntimeError` (INV-003).
6. **Add the REPL skin** — copy `repl_skin.py` into `utils/` and wire `ReplSkin` into the REPL.
7. **Plan then write tests** — author `tests/TEST.md` first, then `test_core.py` (no backend)
   and `test_full_e2e.py` (backend required).
8. **Generate SKILL.md** — run
   [[anchor: cli-anything-plugin/skill_generator.py#generate_skill_file]] over the harness path
   to emit `skills/SKILL.md`.
9. **Register** — add one `clis[]` entry to [[anchor: registry.json]] with `name`,
   `entry_point`, `install_cmd`, `skill_md`, and `category` (INV-005).
10. **Verify** — `python3 -m pytest cli_anything/<app>/tests/ -v` is green and
    `bash cli-anything-plugin/verify-plugin.sh` passes ([[anchor: cli-anything-plugin/verify-plugin.sh]]).

## Touch points

- New tree under `<app>/agent-harness/` (independent package — ADR-0001).
- Exactly one new entry in `registry.json` (the registry seam — see code-map §3).
- A generated `skills/SKILL.md` for the new app.
