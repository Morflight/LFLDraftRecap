# LFLDraftRecap — Architecture Notes for Claude

## What it is

A Static HTML Tool (single-page, clone-and-run) that scrapes a LeaguePedia tournament page and renders a Google-Docs-ready draft recap.

## Key rules

- **Single file** — keep everything in `index.html` (inline `<style>` and `<script>`). Add separate files only if the HTML grows past ~1500 lines.
- **No build step** — no bundler, no preprocessor, no package manager.
- **No secrets, no env vars** — the tool is fully client-side against a public API.
- **Browser target** — latest Chrome, Firefox, Safari, Edge. No legacy support.
- **kebab-case** for any file or asset added (images, CSS, JS).

## Data source

Fandom MediaWiki Cargo API — `https://lol.fandom.com/api.php`

Key tables:
| Table | Purpose |
|-------|---------|
| `ScoreboardGames` | Per-game metadata: GameId, Team1, Team2, Winner, DateTime_UTC, OverviewPage |
| `PicksAndBansS7` | Pick/ban sequence per game: `Team1Pick1..5`, `Team2Pick1..5`, bans, roles, GameId |
| `ScoreboardPlayers` | Per-player rows: Link (player), Champion, Role, Team, GameId |

CORS is open (`access-control-allow-origin: *`, verified 2026-04-19). `origin=*` query param recommended.

## Rate limiting

Fandom throttles burst queries. Between API calls, wait ~300ms. Prefer one large query over many small ones. On 429, back off with exponential retry (start at 2s).

## Rendering rules

### Per-game draft table

- Two columns: blue-side team on left, red-side on right
- Background: `--blue-side` (light blue) for the blue column, `--red-side` (light red) for the red column
- Header row: team tricode; the winning team's header cell uses `--winner-blue` or `--winner-red` (dark, white text)
- Picks in draft order (P1, P2, P3, P4, P5) — one champion per row per side
- Bans: optional initial rows, greyed out (can be added as a toggle later)

### Aggregate player-picks table

- One row per player across the whole split
- Columns: Player, Role, Team, Champions played (comma-separated or list of cells)
- Sort: by team, then by role (Top → Jungle → Mid → Bot → Support)

### Google Docs compatibility

- Use real `<table>` elements (not CSS grid)
- Inline background colors on `<td>`/`<th>` via the `style` attribute — Google Docs strips most `<style>` blocks on paste but respects inline `style="background-color:..."`
- Avoid CSS custom properties in inline styles; resolve them to hex values at render time

## Reference

- Target output format: `/home/osboxes/Documents/Dev/.cp-images/pasted-image-2026-04-19T21-01-07-242Z.png`
- Cargo table browser: https://lol.fandom.com/wiki/Special:CargoTables
