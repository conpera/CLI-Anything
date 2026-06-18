# CLI-Anything — agent entrypoint (read in this order)

CLI-Anything is a monorepo of independent, per-app CLI harnesses that make GUI/API
software agent-native. New here? Read top to bottom. Each line says WHY it's here.

1. **CLAUDE-contract.snippet.md** — house rules + what you MUST NOT do (CONTRACT).
2. **docs/grounding/code-map.md** — the module map: harnesses, the shared blueprint, seams.
3. **docs/grounding/invariants.md** — the INV-NNN rules that must always hold (locking, pure core).
4. **docs/grounding/domain/glossary.md** + **domain/rules.md** — the language and the agent-native design rules.
5. **docs/grounding/domain/flows/add-a-new-harness.md** — the canonical end-to-end flow.
6. **docs/grounding/decisions/** — why it's built this way (ADR-0001 monorepo, ADR-0002 session/locking).
7. **docs/runbooks/add-harness.md** — how to scaffold, test, and register a new harness.
8. **docs/memory/** — lessons & pitfalls; current working state → `docs/memory/session_continue.yaml`.

Source-of-truth files at repo root: `cli-anything-plugin/HARNESS.md` (the blueprint),
`registry.json` (the harness catalog), `CONTRIBUTING.md` (build/test commands).
