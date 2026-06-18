---
grounding_kind: invariants
status: reviewed
last_verified: "2026-06-18"
source_anchors:
  - path: blender/agent-harness/cli_anything/blender/core/session.py
    symbol: _locked_save_json
  - path: blender/agent-harness/cli_anything/blender/utils/blender_backend.py
    symbol: find_blender
  - path: registry.json
  - path: cli-anything-plugin/HARNESS.md
owners: [cli-anything-team]
---

# Invariants

Constraints any agent or human MUST obey in this monorepo, and the forbidden zones they
must NEVER touch. Each invariant has a stable `INV-NNN` id (referenced from `code-map.md`
and `verification.md`), a MUST/NEVER statement, and how to verify it still holds.

## INV-001 — Session JSON is written only under an exclusive file lock

**MUST**: Every write of a harness session/project file goes through the locked, atomic
writer ([[anchor: blender/agent-harness/cli_anything/blender/core/session.py#_locked_save_json]]):
open `"r+"`, take an `fcntl` exclusive lock, then `seek(0)`/`truncate()`/`json.dump` inside
the lock. **NEVER** add an unlocked `open(path, "w")` + `json.dump` for session state.
Concurrent agents share the same session file; an unlocked write corrupts it mid-stream.
*Verify*: grep each harness for direct `json.dump` to a session path; all saves route through
`_locked_save_json` (or the equivalent locked helper). See `cli-anything-plugin/guides/session-locking.md`.

## INV-002 — The `core/` state model stays pure (no Click, no real-software imports)

**MUST**: Modules under `cli_anything/<app>/core/` (e.g.
[[anchor: blender/agent-harness/cli_anything/blender/core/session.py#Session]]) depend only on
the standard library and sibling `core` modules. **NEVER** import `click`, `prompt_toolkit`,
the backend module, or the real application package (`bpy`, etc.) from `core/`. The state
layer must be importable and testable without the GUI app installed — this is what lets
`test_core.py` pass in CI with no backend present.
*Verify*: `grep -rn "import click\|prompt_toolkit\|_backend\|^import bpy" <app>/agent-harness/cli_anything/<app>/core/`
returns nothing.

## INV-003 — A missing real executable raises a clear RuntimeError, never a raw crash

**MUST**: Backend wrappers locate the real software via `shutil.which` and, when it is not
installed, raise a `RuntimeError` whose message includes install instructions — see
[[anchor: blender/agent-harness/cli_anything/blender/utils/blender_backend.py#find_blender]].
**NEVER** let a `FileNotFoundError` from `subprocess` escape to the user, and NEVER hardcode
an absolute path to the executable.
*Verify*: run the harness's backend-touching command with the app uninstalled; you get the
guided `RuntimeError`, not a stack trace from `subprocess.run`.

## INV-004 — Harnesses are independent packages; no cross-harness imports

**MUST**: Each `<app>/agent-harness` is a self-contained installable package; shared helpers
(e.g. `repl_skin.py`) are **copied** into each harness's `utils/`, not imported across apps.
**NEVER** add `from cli_anything.<other_app> import ...` inside a harness. The packages ship
and version independently via `pip install ...#subdirectory=<app>/agent-harness`.
*Verify*: `grep -rn "from cli_anything\." <app>/...` only ever references the harness's own
`<app>` namespace.

## INV-005 — `registry.json` stays valid, unique, and `skill_md`-resolvable

**MUST**: [[anchor: registry.json]] MUST remain valid JSON; each `clis[]` entry MUST have a
unique `name`, an `entry_point`, an `install_cmd`, and a `skill_md` that is either `null` or a
path that exists on disk. **NEVER** point a non-null `skill_md` at a missing file, and NEVER
duplicate a `name` — CLI-Hub and the meta-skill parse this file to discover and install
harnesses. Note the registry is a **catalog**, not a mirror of this repo's directory tree: it
can list external harnesses installed from another repo (e.g. `clibrowser`, a Rust crate via
`cargo install --git …`, which has no `agent-harness/` here), and an in-repo `<app>/agent-harness`
may not yet have a `clis[]` entry (e.g. `tiled`). Do not assume a 1:1 mapping between on-disk
harness directories and registry entries.
*Verify*: `python3 -c "import json; d=json.load(open('registry.json')); n=[c['name'] for c in d['clis']]; assert len(n)==len(set(n))"` succeeds,
and every non-null `skill_md` path resolves on disk.

## INV-006 — New harnesses follow the HARNESS.md blueprint structure

**MUST**: A new harness matches the canonical layout enforced by
[[anchor: cli-anything-plugin/HARNESS.md]] and `verify-plugin.sh`: `cli_anything/` is a PEP-420
namespace package (NO `__init__.py`), `<app>/` is a regular sub-package (HAS `__init__.py`),
with `core/`, `utils/`, `tests/` (`test_core.py` + `test_full_e2e.py` + `TEST.md`), and
`skills/SKILL.md`. **NEVER** put an `__init__.py` in `cli_anything/` (it breaks namespace
co-installation of multiple harnesses).
*Verify*: run `cli-anything:validate` against the harness, or check the structure rules in
`HARNESS.md`.
