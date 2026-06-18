---
grounding_kind: domain-rules
status: reviewed
last_verified: "2026-06-18"
source_anchors:
  - path: cli-anything-plugin/HARNESS.md
  - path: cli-anything-plugin/skill_generator.py
    symbol: extract_cli_metadata
owners: [cli-anything-team]
---

# Domain Rules

The design rules that make a CLI "agent-native" in this project. These are conventions a
harness must satisfy to be a good CLI-Anything citizen; the non-negotiable, checker-relevant
subset is hardened as invariants (INV-NNN) in `invariants.md`.

## R1 — Dual output: human and machine

Every command supports a `--json` flag. Default output is human-readable (tables, colored
status); `--json` emits a structured payload an agent can parse without scraping text. The
JSON shape for a command is part of its contract.

## R2 — Stateful by default, scriptable on demand

A harness works both as a stateful REPL (default, for agents that maintain context) and as
one-shot subcommands (for pipelines). With no subcommand, the CLI enters the REPL. State is
carried in the `Session` and persisted to a JSON session file — this is the invariant INV-001
(locked writes) and the design recorded in ADR-0002.

## R3 — Probe before mutate

Each harness exposes read-only inspect/info commands so an agent can examine project state
before changing it. Mutation commands snapshot state first so the change is undoable.

## R4 — Graceful degradation when the app is absent

Backend wrappers must detect a missing real executable and raise a guided `RuntimeError`
with install instructions — never a raw subprocess crash (INV-003). Unit tests (`test_core.py`)
must pass with no backend installed, which requires `core/` to stay pure (INV-002).

## R5 — Self-describing for agents

Every harness ships a `skills/SKILL.md`, generated from the CLI's own command surface by
[[anchor: cli-anything-plugin/skill_generator.py#extract_cli_metadata]]. Because the generator
parses `@click` decorators statically, keep command/option declarations in the conventional
decorator form so they remain machine-extractable. The canonical statement of all of the above
is [[anchor: cli-anything-plugin/HARNESS.md]].
