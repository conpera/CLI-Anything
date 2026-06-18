---
grounding_kind: adr
status: reviewed
last_verified: "2026-06-18"
source_anchors:
  - path: blender/agent-harness/cli_anything/blender/core/session.py
    symbol: Session
  - path: blender/agent-harness/cli_anything/blender/core/session.py
    symbol: _locked_save_json
owners: [cli-anything-team]
---

# ADR-0002: In-memory Session with undo/redo, persisted via locked atomic JSON

## Context

Agents drive these CLIs as a sequence of one-shot subcommand invocations (and in the REPL,
as a sequence of lines). State — the open project, edits, cursor — must survive between
commands, support undo/redo so an agent can recover from a wrong step, and tolerate two
agents touching the same session file at once. We needed a state model that works without
the GUI app running and without a database.

## Decision

State lives in an in-memory `Session`
([[anchor: blender/agent-harness/cli_anything/blender/core/session.py#Session]]) holding the
project dict plus bounded `_undo_stack` / `_redo_stack` (capped at `MAX_UNDO`), serialized to
a plain JSON session file. All persistence goes through one helper,
[[anchor: blender/agent-harness/cli_anything/blender/core/session.py#_locked_save_json]],
which opens the file `"r+"`, takes an `fcntl` exclusive lock, then truncates and dumps inside
the lock — atomic against concurrent writers. The `Session`/`core` layer stays pure stdlib so
it is unit-testable with no backend installed. See ADR-0001 for why this lives in an
independent package, and `cli-anything-plugin/guides/session-locking.md` for the locking pattern.

## Consequences

- Undo/redo and status come "for free" to every harness that uses `core/session.py`
  (this is the basis of INV-001 and INV-002).
- Concurrent agents cannot corrupt a session mid-write; the lock degrades gracefully where
  `fcntl` is unavailable (e.g. some Windows shells) by skipping the lock rather than failing.
- The state model must never import Click, prompt-toolkit, or the real app — keeping `core/`
  pure is a standing constraint, not just a convention.
