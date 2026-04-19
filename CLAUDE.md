# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A single-page browser tool that converts a LeaguePedia tournament results page (e.g. LFL Spring 2026) into a Google-Docs-ready draft recap. No build step, no backend, no framework — one self-contained `index.html` plus whatever assets it needs.

Distribution: clone or download the repo, open `index.html` in any modern browser.

## Architecture

Everything lives in `index.html`:
- **HTML** — controls bar (slug input + fetch button), status area, output container
- **CSS** — inline `<style>` block; design tokens in `:root` variables (`--blue-side`, `--red-side`, `--winner-blue`, `--winner-red`)
- **JS** — inline `<script>`; responsible for Cargo API calls, data reshaping, and HTML rendering

### Data flow

1. User enters a LeaguePedia **OverviewPage** slug (e.g. `LFL/2026 Season/Spring Season`).
2. Query the Fandom MediaWiki Cargo API:
   - `ScoreboardGames` — one row per game (winner, teams, GameId, date)
   - `PicksAndBansS7` — per-game pick/ban order (Blue_Pick1..5, Red_Pick1..5, bans, roles)
   - `ScoreboardPlayers` — per-game player rows (champion, role, team, GameId) — used to map picks to players for the aggregate table
3. Reshape: group by GameId; order games chronologically.
4. Render two sections:
   - **Per-game draft tables** — blue-side column (light blue) vs red-side column (light red); the winning team's header cell gets a dark accent. Matches the reference screenshot in `Dev/.cp-images/pasted-image-2026-04-19T21-01-07-242Z.png`.
   - **Aggregate player-picks table** — rows = players, columns = champions played (deduplicated or with counts).
5. Output HTML is structured so that `Ctrl+A` → `Ctrl+C` → paste into Google Docs preserves table structure and cell colors.

### API endpoint

Base: `https://lol.fandom.com/api.php`

Example query:
```
?action=cargoquery
&tables=ScoreboardGames
&fields=OverviewPage,Team1,Team2,Winner,DateTime_UTC,GameId
&where=OverviewPage LIKE "LFL/2026 Season/Spring%"
&limit=500
&format=json
&origin=*
```

CORS is open (`access-control-allow-origin: *` verified 2026-04-19). `origin=*` is not strictly required but keeps requests clean.

### Rate limiting

Fandom throttles aggressive callers. Serialize requests with a small delay (~300ms) between calls. Batch fields in a single query when possible rather than issuing many small queries.

## Preview

Option A — open `index.html` directly in a browser. Works for `fetch()` against HTTPS endpoints in current Chrome/Firefox/Safari/Edge.

Option B — if the browser blocks `file://` origin fetches (older security modes), run `make serve` and open `http://localhost:8080`.

## Out of scope

- No deploy target, no hosted site, no Docker, no Traefik, no hostname
- No package manager, no `node_modules`, no `package.json`
- No tests beyond the `make smoke` HTML parser check

## Reference

- Screenshot of target output format: `/home/osboxes/Documents/Dev/.cp-images/pasted-image-2026-04-19T21-01-07-242Z.png`
- Fandom Cargo API browser: https://lol.fandom.com/wiki/Special:CargoTables
