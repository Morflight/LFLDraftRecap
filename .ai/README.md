# LFLDraftRecap Shared AI Knowledge

This directory is harness-neutral. Put durable project knowledge here when it should be usable by Codex, Claude Code, or any future coding agent.

## Shared Docs

- `CLAUDE.md` — migrated from `.claude/CLAUDE.md`.

## Harness-Specific Entry Points

- `../AGENTS.md` — Codex adapter.
- `../CLAUDE.md` — Claude Code adapter.
- `../.claude/` — Claude-native commands, settings, hooks, skills, and legacy docs.

## Migration Rule

Move knowledge here gradually. Do not mass-delete `.claude/**`; Claude Code still discovers commands, settings, hooks, and skills there.
