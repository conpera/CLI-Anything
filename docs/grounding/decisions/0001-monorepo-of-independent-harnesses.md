---
grounding_kind: adr
status: reviewed
last_verified: "2026-06-18"
source_anchors:
  - path: registry.json
  - path: blender/agent-harness/setup.py
  - path: cli-anything-plugin/HARNESS.md
owners: [cli-anything-team]
---

# ADR-0001: One monorepo of independent, per-app harness packages

## Context

CLI-Anything makes "ALL software agent-native" by shipping a CLI wrapper for each
supported application. We needed a structure that lets dozens of harnesses (32 today)
coexist, be authored by different community contributors, and be installed à la carte by
agents — without forcing users to pull in code or dependencies for apps they do not have.
Two shapes were considered: (a) a single distributable package exposing every app, or
(b) one independent package per app, all living in this monorepo.

## Decision

Each app lives at `<app>/agent-harness/` as its **own** pip-installable package with its
own `setup.py` (see [[anchor: blender/agent-harness/setup.py]]) and a distinct console
entry point `cli-anything-<app>`. Packages share the `cli_anything` namespace via PEP-420
(no `__init__.py` in `cli_anything/`) so multiple harnesses co-install cleanly. They are
installed individually with
`pip install "git+https://github.com/HKUDS/CLI-Anything.git#subdirectory=<app>/agent-harness"`,
and the repo-root [[anchor: registry.json]] is the single catalog the CLI-Hub site and
meta-skill read to discover and install them. The common blueprint every harness follows is
[[anchor: cli-anything-plugin/HARNESS.md]].

## Consequences

- Agents install only the harness(es) they need; no global dependency bloat.
- Contributors add a self-contained app directory plus one `registry.json` entry — low
  coupling, parallel development (this drives INV-004 and INV-005).
- Cost: structural duplication. Shared helpers like `repl_skin.py` are **copied** into each
  harness rather than imported, and the namespace-package rule (no `__init__.py` in
  `cli_anything/`) must be enforced by `verify-plugin.sh` or co-installation breaks.
- There is no single version for "CLI-Anything"; each harness versions independently.
