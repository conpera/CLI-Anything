---
grounding_kind: verification
status: reviewed
last_verified: "2026-06-18"
source_anchors:
  - path: CONTRIBUTING.md
  - path: blender/agent-harness/cli_anything/blender/tests/test_core.py
  - path: cli-anything-plugin/verify-plugin.sh
  - path: cli-anything-plugin/skill_generator.py
    symbol: generate_skill_file
owners: [cli-anything-team]
---

# Verification Standard

How anyone — human or AI — proves a change to a CLI-Anything harness is correct before
merging. Because this is a monorepo of independent packages, verification is **per
harness**: you build and test only the `<app>/agent-harness` you touched. Commands below
are taken from `CONTRIBUTING.md`.

## Environment

- Python 3.10+ (`python_requires=">=3.10"` in every `setup.py`).
- `click>=8.1`, `prompt-toolkit>=3.0`; dev extras add `pytest>=7` and `pytest-cov>=4`.
- Install the harness you changed in editable mode from inside its `agent-harness` dir:

```bash
cd <app>/agent-harness
pip install -e .[dev]
```

## Test map

| Layer            | What it covers                                         | Where                                                                 | Backend app needed? |
| ---------------- | ------------------------------------------------------ | --------------------------------------------------------------------- | ------------------- |
| Unit (core)      | Pure state model: scene/object ops, `Session` undo/redo | `cli_anything/<app>/tests/test_core.py`                               | No                  |
| E2E              | Full CLI invocation through the real backend           | `cli_anything/<app>/tests/test_full_e2e.py`                           | Yes (app installed) |
| Test plan        | Inventory + per-module plan (authored before code)     | `cli_anything/<app>/tests/TEST.md`                                    | —                   |
| Plugin structure | Meta-tooling files present + plugin.json valid          | `cli-anything-plugin/verify-plugin.sh`                                | No                  |

## Commands

```bash
# Unit tests — no backend software needed (run these always; they gate INV-002)
python3 -m pytest cli_anything/<app>/tests/test_core.py -v

# E2E tests — requires the real backend installed
python3 -m pytest cli_anything/<app>/tests/test_full_e2e.py -v

# All tests for a harness
python3 -m pytest cli_anything/<app>/tests/ -v

# Smoke-check the CLI itself
cli-anything-<app> --help
cli-anything-<app> --json <some-subcommand>     # confirm JSON output is well-formed

# Verify the plugin / meta-tooling structure
bash cli-anything-plugin/verify-plugin.sh

# Regenerate a harness's SKILL.md after changing its command surface
python3 cli-anything-plugin/skill_generator.py <app>/agent-harness
```

## Per-change-type checklist

**Changed a `core/` module (state/data model):**
1. `pytest cli_anything/<app>/tests/test_core.py -v` is green.
2. Confirm no new `click` / `prompt_toolkit` / backend import crept into `core/` (INV-002).
3. If you touched session persistence, confirm saves still route through the locked writer (INV-001).

**Added / renamed a subcommand or option:**
1. `cli-anything-<app> --help` shows the new surface; `--json` payload parses.
2. Regenerate `skills/SKILL.md` with `skill_generator.py` so the agent-facing doc matches
   ([[anchor: cli-anything-plugin/skill_generator.py#generate_skill_file]]).
3. Run the full harness test suite.

**Touched a `utils/<app>_backend.py`:**
1. Run with the app uninstalled → guided `RuntimeError`, not a raw subprocess crash (INV-003).
2. Run `test_full_e2e.py` with the app installed.

**Added a new harness or edited `registry.json`:**
1. `python3 -c "import json; json.load(open('registry.json'))"` succeeds (INV-005).
2. `bash cli-anything-plugin/verify-plugin.sh` passes (INV-006).
3. New harness has unit + E2E tests, a `TEST.md`, and a `skills/SKILL.md`.

## Grounding self-check

After editing any doc under `docs/grounding/`, run the drift-checker from the repo root and
fix every error:

```bash
python3 docs/grounding/check_grounding.py
```
