---
grounding_kind: domain-glossary
status: reviewed
last_verified: "2026-06-18"
source_anchors:
  - path: cli-anything-plugin/HARNESS.md
  - path: registry.json
owners: [cli-anything-team]
---

# Glossary

The ubiquitous language of CLI-Anything. Terms agents and contributors must use consistently.

- **Harness** — one app's CLI wrapper: the self-contained package at `<app>/agent-harness/`
  that makes a GUI/API application drivable from the command line. Defined by
  [[anchor: cli-anything-plugin/HARNESS.md]].
- **Backend** — the module `utils/<app>_backend.py` that locates and shells out to the *real*
  installed software (find the executable, run it headless, parse results).
- **Core** — the pure-stdlib state/data layer under `cli_anything/<app>/core/`; manipulates
  project state without importing Click or the real app.
- **Session** — in-memory project state with undo/redo, persisted as a locked JSON file
  ([[anchor: blender/agent-harness/cli_anything/blender/core/session.py#Session]]).
- **REPL skin** — the shared interactive-shell chrome (`ReplSkin`): banner, prompt, colored
  status output, reused by every harness.
- **SKILL.md** — the AI-discoverable skill definition generated for a harness; tells an agent
  what the CLI can do and how to call it.
- **Registry** — the repo-root [[anchor: registry.json]] catalog of every harness, consumed by
  CLI-Hub and the meta-skill for discovery and one-command install.
- **CLI-Hub** — the public site/registry where harnesses are browsed and installed.
- **Meta-skill** — `cli-hub-meta-skill/SKILL.md`, which lets an agent autonomously discover and
  install harnesses by reading the registry.
- **Plugin / tooling** — `cli-anything-plugin/`: the blueprint (`HARNESS.md`), scaffold/test/
  validate commands, and `skill_generator.py` used to author new harnesses.
