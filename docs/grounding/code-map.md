---
grounding_kind: code-map
status: reviewed
last_verified: "2026-06-18"
source_anchors:
  - path: registry.json
  - path: cli-anything-plugin/HARNESS.md
  - path: cli-anything-plugin/skill_generator.py
    symbol: generate_skill_file
  - path: blender/agent-harness/cli_anything/blender/blender_cli.py
    symbol: cli
  - path: blender/agent-harness/cli_anything/blender/core/session.py
    symbol: Session
owners: [cli-anything-team]
---

# Code Map

CLI-Anything (HKUDS) is a **monorepo of independent CLI harnesses** that wrap GUI / API
software so AI coding agents can drive them headlessly. There is no single application
process: each supported app lives in its own self-contained package under
`<app>/agent-harness/` (32 such directories today). The **canonical Python harness** —
Blender, used as the exemplar throughout this map — follows the shared blueprint
([[anchor: cli-anything-plugin/HARNESS.md]]): a `cli_anything/<pkg>/` namespace tree with a
Click command tree, an in-memory `Session` with undo/redo and file-locked JSON saves, a
`utils/<app>_backend.py` that shells out to the real software, a `ReplSkin` interactive
shell, and a generated `skills/SKILL.md`. Real harnesses vary from this shape: the inner
package name need not equal the directory (`obs-studio/` → `cli_anything/obs_studio/`,
`iterm2/` → `cli_anything/iterm2_ctl/`); some apps have no `utils/<app>_backend.py`
(`obs-studio`, `tiled`); and a few harnesses are not Python at all (`sketch` is a Node.js
package with `src/cli.js` and no `cli_anything/` tree). A repo-root `registry.json`
([[anchor: registry.json]]) is the machine catalog the CLI-Hub site and meta-skill read to
discover and install harnesses; it lists both in-repo and **external** harnesses (e.g. the
Rust `clibrowser` crate) and is not a 1:1 mirror of the on-disk `agent-harness/` directories
(see INV-005).

## 1. System overview

A monorepo, not a service. The three things it does: (1) ships agent-native CLI harnesses
(32 `agent-harness/` directories today), each an independent installable package — most via
`pip install ...#subdirectory=<app>/agent-harness`, a few via other toolchains (`sketch` via
`npm`);
(2) provides a plugin / meta-tooling layer (`cli-anything-plugin/`) that scaffolds, tests,
validates and SKILL-documents new harnesses against the `HARNESS.md` blueprint; (3) keeps a
central `registry.json` catalog powering the CLI-Hub discovery/install experience. The
"entry point" to understand any one harness is its Click root group
([[anchor: blender/agent-harness/cli_anything/blender/blender_cli.py#cli]]); the entry point
to understand the system is the blueprint plus the registry.

## 2. Module inventory

Rows are the durable module *kinds* in this monorepo (the standard Python harness
instantiates these, so one harness — Blender — is used as the canonical exemplar; some
harnesses omit or rename rows, e.g. no `harness-backend`, or a non-Python shape like
`sketch` — see §1). `entry` is the file/symbol to open first.

| Module                | Purpose (1 line)                                                      | Entry                                                                        | Key files                                                                                                                  | Depends-on            | Depended-by        |
| --------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | --------------------- | ------------------ |
| `harness-cli`         | Click command tree (subcommands + REPL) exposing one app to agents    | `blender/agent-harness/cli_anything/blender/blender_cli.py#cli`               | `blender_cli.py` (groups `scene`/`object`/`repl`, `output`, `handle_error`)                                                | `harness-core`, `harness-backend`, `repl-skin` | (agents / shell)   |
| `harness-core`        | Pure project-state model: scene/data ops + undo/redo session          | `blender/agent-harness/cli_anything/blender/core/session.py#Session`          | `core/session.py` (`Session`, `_locked_save_json`), `core/scene.py`, `core/objects.py`, `core/render.py`                    | (stdlib only)         | `harness-cli`      |
| `harness-backend`     | Shells out to the real installed software (find exe, invoke headless) | `blender/agent-harness/cli_anything/blender/utils/blender_backend.py#find_blender` | `utils/blender_backend.py` (`find_blender`, `render_scene_headless`), `utils/bpy_gen.py`                                | (real app + stdlib)   | `harness-cli`      |
| `repl-skin`           | Shared interactive-shell chrome (banner, prompt, colored output)      | `cli-anything-plugin/repl_skin.py#ReplSkin`                                   | plugin `repl_skin.py`, copied into each `utils/repl_skin.py`                                                                | `prompt-toolkit`      | `harness-cli`      |
| `plugin-tooling`      | Scaffold / test / validate / refine harnesses against the blueprint   | `cli-anything-plugin/HARNESS.md`                                              | `HARNESS.md`, `commands/*.md`, `scripts/setup-cli-anything.sh`, `verify-plugin.sh`, `guides/*.md`                           | (none)                | (harness authors)  |
| `skill-generator`     | Parse a harness's CLI and emit its `skills/SKILL.md`                   | `cli-anything-plugin/skill_generator.py#generate_skill_file`                  | `skill_generator.py` (`extract_cli_metadata`, `generate_skill_md`), `templates/SKILL.md.template`                          | (stdlib + jinja2)     | `plugin-tooling`   |
| `registry`            | Machine catalog of harnesses (in-repo + external) for Hub discovery    | `registry.json`                                                              | `registry.json` (`clis[]`), `docs/hub/SKILL.md`                                                                            | (none)                | `cli-hub-meta-skill` |
| `cli-hub-meta-skill`  | Lets agents autonomously browse/install harnesses from the registry   | `cli-hub-meta-skill/SKILL.md`                                                | `cli-hub-meta-skill/SKILL.md`                                                                                               | `registry`            | (agents)           |

## 3. Boundaries / seams

The interfaces most likely to break when changed.

| Seam                          | Kind   | What crosses it                                          | Owner / definition                                                                 | Compatibility rule                                                                 |
| ----------------------------- | ------ | ------------------------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| CLI command surface           | CLI    | Subcommand names, options, and `--json` payload shape    | each harness `*_cli.py` Click groups (e.g. [[anchor: blender/agent-harness/cli_anything/blender/blender_cli.py#cli]]) | Agents and `SKILL.md` depend on stable command/flag names; rename = breaking change. |
| `registry.json` schema        | JSON   | `clis[]` entries (`name`, `entry_point`, `install_cmd`, `skill_md`) | [[anchor: registry.json]]                                                          | CLI-Hub + meta-skill parse this; keep keys/entry_point stable, additive only.     |
| Session JSON file             | File   | Serialized project state written under exclusive lock    | [[anchor: blender/agent-harness/cli_anything/blender/core/session.py#_locked_save_json]] | Always write under `fcntl` lock (open `r+`, lock, truncate); no unlocked writes.  |
| `backend` ↔ real software     | subprocess | argv passed to the installed app executable          | [[anchor: blender/agent-harness/cli_anything/blender/utils/blender_backend.py#find_blender]] | Missing exe must raise `RuntimeError` with install instructions, never crash raw. |
| `SKILL.md` generation contract| parse  | CLI metadata extracted by static parsing of `*_cli.py`   | [[anchor: cli-anything-plugin/skill_generator.py#extract_cli_metadata]]             | Generator reads `@click` decorators by regex; keep decorator form parseable.       |

## 4. Data-model pointers

- In-memory project state and history: [[anchor: blender/agent-harness/cli_anything/blender/core/session.py#Session]]
  (`project` dict, `_undo_stack`/`_redo_stack`, `MAX_UNDO`).
- Persisted session shape: JSON written by
  [[anchor: blender/agent-harness/cli_anything/blender/core/session.py#save_session]].
- Harness catalog (the cross-cutting data model): [[anchor: registry.json]] `clis[]`.
- Generated agent-facing metadata: [[anchor: cli-anything-plugin/skill_generator.py#SkillMetadata]].

## 5. Dependency-direction rules

**Allowed (imports point this way):**
- `harness-cli` → `harness-core` and `harness-cli` → `harness-backend` (the CLI orchestrates;
  state and subprocess wrappers do not import the CLI).
- `harness-cli` → `repl-skin` (REPL chrome is presentation; it never imports core/back).
- `cli-hub-meta-skill` → `registry` (read-only consumer of `registry.json`).

**Forbidden:**
- `harness-core` → `harness-cli` or `harness-core` → `harness-backend` (the state model is
  pure stdlib; it must not know about Click or the real software — see INV-002).
- Any harness → another harness (packages are independent; no cross-app imports — see INV-004).
- Writing a session file without the exclusive-lock path (see INV-001).

## 6. Where do I change X? (task -> files index)

| Task ("I want to change…")                         | Files to edit                                                                                       | Watch out for                                                              |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Add a subcommand to a harness                      | that harness's `*_cli.py` + the matching `core/*.py`                                                 | CLI command surface seam (§3); regenerate `SKILL.md` (see verification).    |
| Add a brand-new app harness                        | new `<app>/agent-harness/...` tree, then a `clis[]` entry in `registry.json`                         | Follow `HARNESS.md`; keep `registry.json` schema (§3); run `verify-plugin.sh`. |
| Change how sessions persist                        | `core/session.py` (`save_session`, `_locked_save_json`)                                              | Must keep the `fcntl` lock + atomic truncate (INV-001).                      |
| Change SKILL.md generation                         | `cli-anything-plugin/skill_generator.py`, `templates/SKILL.md.template`                              | Generator parses `@click` decorators by regex — keep them parseable.        |
| Change the backend invocation of an app            | that harness's `utils/<app>_backend.py`                                                              | Missing-exe must still raise a clear `RuntimeError` with install steps.      |
