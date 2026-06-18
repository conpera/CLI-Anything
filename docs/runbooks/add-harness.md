# Runbook: scaffold, test, and register a new app harness

**Trigger:** Adding agent-native CLI support for a new application to CLI-Anything.
Authoritative blueprint: `cli-anything-plugin/HARNESS.md`. This runbook is the command
sequence; the boundary-level flow is `docs/grounding/domain/flows/add-a-new-harness.md`.

1. Create the package skeleton (`cli_anything/` must NOT get an `__init__.py`):

   ```bash
   mkdir -p <app>/agent-harness/cli_anything/<app>/{core,utils,tests,skills}
   touch <app>/agent-harness/cli_anything/<app>/__init__.py
   ```
   Add `<app>/agent-harness/setup.py` with the console entry `cli-anything-<app>` and
   `python_requires=">=3.10"`, `install_requires=["click>=8.1","prompt-toolkit>=3.0"]`
   (model it on `blender/agent-harness/setup.py`).

2. Implement `core/` (pure stdlib state model + `Session`), `<app>_cli.py` (Click groups,
   `--json`, REPL-by-default), and `utils/<app>_backend.py` (find exe + headless invoke).
   Copy the shared `repl_skin.py` into `utils/`.

3. Install in editable mode and run the tests:

   ```bash
   cd <app>/agent-harness
   pip install -e .[dev]
   python3 -m pytest cli_anything/<app>/tests/ -v
   ```

4. Generate the agent-facing skill doc:

   ```bash
   python3 cli-anything-plugin/skill_generator.py <app>/agent-harness
   ```

5. Register the harness — add one `clis[]` entry to `registry.json` (`name`, `version`,
   `entry_point: cli-anything-<app>`, `install_cmd`, `skill_md`, `category`), then confirm
   it still parses:

   ```bash
   python3 -c "import json; json.load(open('registry.json'))"
   ```

6. **Verify:** structure + plugin checks pass and the CLI runs.

   ```bash
   bash cli-anything-plugin/verify-plugin.sh
   cli-anything-<app> --help
   ```

**Rollback:** delete the `<app>/agent-harness/` directory and remove the harness's
`clis[]` entry from `registry.json` (re-run the `json.load` check to confirm valid JSON).

**Validated-by:** command sequence taken from `CONTRIBUTING.md` and
`cli-anything-plugin/HARNESS.md`; `registry.json` JSON-parse check run green 2026-06-18.
