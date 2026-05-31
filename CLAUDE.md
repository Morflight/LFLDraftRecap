# LFLDraftRecap

Claude Code adapter for this project.

Durable project knowledge now lives in shared, harness-neutral docs under `.ai/`. Claude-specific commands, settings, hooks, and skills remain in `.claude/`.

## Read First

1. `AGENTS.md` — primary project operating rules, shared with Codex.
2. `.ai/README.md` — shared project documentation index.
3. Relevant `.ai/*.md` files for architecture, workflow, setup, troubleshooting, API, schema, or feature details.

## Claude-Specific Material

- `.claude/skills/**` — Claude project skills, if present.
- `.claude/settings*.json` — Claude Code permissions/hooks only.
- `.claude/CLAUDE.local.md` — local Claude-only context, if present.

## Compatibility

Do not delete `.claude/**` just because a shared `.ai/` copy exists. Claude Code still expects `.claude` for native discovery of commands, settings, hooks, and skills.

The previous detailed Claude guidance has been copied into `.ai/` where applicable and remains available in `.claude/**` legacy docs.
