#!/usr/bin/env python3
"""
sync.py — pull an LFL season's drafts + scoreboard-players from LeaguePedia's
Cargo API into a single JSON blob the browser viewer (index.html) reads.

Runs independently of the viewer, so the rate-limit cost is moved out of
the user's click path. Intended usage: `make sync` (once per day, or before
a recap session), commit the regenerated JSON, push. The viewer is 100%
offline after that.

Two Cargo quirks this handles:

1. `PicksAndBansS7` chokes with MWException when the WHERE uses LIKE, even
   on indexed columns. Workaround: enumerate the season's distinct
   OverviewPages via `TournamentRosters` (LIKE works there) and fire one
   exact-match PBS7 query per stage. LFL 2026 has ~4 stages
   (Invitational / Promotion / Spring Split / ...), so this is still cheap.

2. Fandom's anon throttle is hostile. Everything is serialised, paced by
   GAP_SEC, and retried with long backoffs. A stubborn 429 can block a run
   for several minutes; retry later if that happens.

Stdlib-only — no pip deps.
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://lol.fandom.com/api.php"

# MediaWiki APIs 403 the default `Python-urllib/X.Y` UA. Identify the client
# per MediaWiki etiquette: tool name + contact, not a browser spoof.
USER_AGENT = (
    "LFLDraftRecap-sync/1.0 "
    "(https://github.com/Morflight/LFLDraftRecap; "
    "LeaguePedia data scraper for draft recaps)"
)

DEFAULT_SEASON_LIKE = "LFL/2026 Season/%"
DEFAULT_SEASON_LABEL = "LFL 2026"
# Single shared JSON format consumed by the viewer's "Importer depuis
# fichier" menu. Same shape as what the browser exports, so sync-output
# and browser-export round-trip interchangeably.
DEFAULT_OUT = "data/lfl-2026-nav.json"

# Pacing — tuned from observation on 2026-04-24 when Fandom's anon throttle
# was deeply hot. At 3s/query, successive queries rate-limited even after
# the previous cleared. 60s between queries empirically avoids the
# cascading-throttle trap. Retries are shorter in count but longer per
# attempt, because once Fandom rate-limits us, it stays rate-limited for
# minutes — a 15s retry is pure waste.
GAP_SEC = 60.0
RETRY_WAIT_SEC = [60, 300]

# Per-query disk cache. When Fandom is deeply throttled, a full sync can
# need 3+ attempts to complete; without caching, each attempt redoes the
# queries that already succeeded and burns API budget. With caching, every
# successful query's result is written to PROGRESS_DIR and reused on the
# next run — the re-attempt only hits the network for queries that
# haven't completed yet.
PROGRESS_DIR = Path(".sync-progress")


def _cache_path(params):
    """Stable path for a query's cached result, keyed on the params dict."""
    blob = json.dumps(params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]
    return PROGRESS_DIR / f"{digest}.json"


def cargo_query(params):
    """One Cargo call with per-query disk cache + retry on ratelimited."""
    cache = _cache_path(params)
    if cache.exists():
        print(f"  ✓ cache hit ({cache.name})", file=sys.stderr)
        return json.loads(cache.read_text(encoding="utf-8"))

    qs = urllib.parse.urlencode({
        "action": "cargoquery", "format": "json", "origin": "*", **params,
    })
    url = f"{API}?{qs}"
    attempts = [0] + list(RETRY_WAIT_SEC)
    for i, wait in enumerate(attempts):
        if wait:
            print(f"  … rate-limited, waiting {wait}s then retrying ({i}/{len(RETRY_WAIT_SEC)})",
                  file=sys.stderr)
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise SystemExit(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise SystemExit(f"Network error: {e.reason}")
        err = data.get("error")
        if err and err.get("code") == "ratelimited":
            continue
        if err:
            raise SystemExit(f"Cargo error [{err.get('code')}]: {err.get('info', 'unknown')}")
        rows = [row["title"] for row in data.get("cargoquery", [])]
        PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        return rows
    raise SystemExit("Rate-limit Fandom persistant après tous les retries. Réessaie dans quelques minutes.")


def fetch_meta_for_season(season_like):
    """All game metadata for the season in one ScoreboardGames query.

    SG is where Team1/Team2/Winner/DateTime/GameId/OverviewPage live
    safely. PBS7's own copies of those fields tripped MWException on
    2026-04-24; SG has no such problem.
    """
    return cargo_query({
        "tables": "ScoreboardGames",
        "fields": "Team1,Team2,Winner,DateTime_UTC,GameId,OverviewPage",
        "where": f'OverviewPage LIKE "{season_like}"',
        "limit": "500",
    })


def fetch_picks_for_stage(overview_page):
    """PBS7 picks for one stage — 11 fields, keyed on GameId."""
    esc = overview_page.replace('"', '')
    return cargo_query({
        "tables": "PicksAndBansS7",
        "fields": ("GameId,"
                   "Team1Pick1,Team1Pick2,Team1Pick3,Team1Pick4,Team1Pick5,"
                   "Team2Pick1,Team2Pick2,Team2Pick3,Team2Pick4,Team2Pick5"),
        "where": f'OverviewPage="{esc}"',
        "limit": "500",
    })


def fetch_bans_for_stage(overview_page):
    """PBS7 bans for one stage — 11 fields, keyed on GameId."""
    esc = overview_page.replace('"', '')
    return cargo_query({
        "tables": "PicksAndBansS7",
        "fields": ("GameId,"
                   "Team1Ban1,Team1Ban2,Team1Ban3,Team1Ban4,Team1Ban5,"
                   "Team2Ban1,Team2Ban2,Team2Ban3,Team2Ban4,Team2Ban5"),
        "where": f'OverviewPage="{esc}"',
        "limit": "500",
    })


def fetch_players_page(season_like, offset, limit=500):
    """ScoreboardPlayers — LIKE works here, unlike on PBS7."""
    return cargo_query({
        "tables": "ScoreboardPlayers",
        "fields": "Link,Champion,Role,Team,OverviewPage,GameId,DateTime_UTC",
        "where": f'OverviewPage LIKE "{season_like}"',
        "limit": str(limit),
        "offset": str(offset),
    })


def map_draft_row(r):
    """PicksAndBansS7 row → the shape the browser viewer renders."""
    blue = r.get("Team1") or ""
    red = r.get("Team2") or ""
    if not blue or not red:
        return None
    has_picks = any(r.get(f"Team{t}Pick{n}") for t in (1, 2) for n in range(1, 6))
    if not has_picks:
        return None  # forfeit / empty row
    winner_field = str(r.get("Winner") or "")
    winner_side = "B" if winner_field == "1" else "R" if winner_field == "2" else None
    slot_map = {}
    for n in range(1, 6):
        slot_map[f"ban-B-{n}"] = r.get(f"Team1Ban{n}") or ""
        slot_map[f"ban-R-{n}"] = r.get(f"Team2Ban{n}") or ""
        slot_map[f"pick-B-{n}"] = r.get(f"Team1Pick{n}") or ""
        slot_map[f"pick-R-{n}"] = r.get(f"Team2Pick{n}") or ""
    dt = r.get("DateTime UTC") or r.get("DateTime_UTC") or ""
    overview = r.get("OverviewPage") or ""
    # Derive tournament label from OverviewPage's last segment — e.g.
    # "LFL/2026 Season/Spring Playoffs" → "Spring Playoffs". Avoids the
    # MWException-triggering Tournament column.
    tournament = overview.rsplit("/", 1)[-1] if overview else ""
    return {
        "date": dt[:10],
        "tournament": tournament,
        "overviewPage": overview,
        "gameId": r.get("GameId") or "",
        "blueTeam": blue,
        "redTeam": red,
        "team1": blue,
        "team2": red,
        "team1Side": "B",
        "slotMap": slot_map,
        "winnerSide": winner_side,
    }


def derive_teams(games):
    s = set()
    for g in games:
        if g.get("blueTeam"):
            s.add(g["blueTeam"])
        if g.get("redTeam"):
            s.add(g["redTeam"])
    return sorted(s)


def main():
    ap = argparse.ArgumentParser(description="Sync a LeaguePedia season into data/*.json.")
    ap.add_argument("--season-like", default=DEFAULT_SEASON_LIKE,
                    help='OverviewPage LIKE pattern covering every stage (e.g. "LFL/2026 Season/%%").')
    ap.add_argument("--season-label", default=DEFAULT_SEASON_LABEL,
                    help="Human-readable label shown in the viewer UI.")
    ap.add_argument("-o", "--out", default=DEFAULT_OUT, help="Output JSON path.")
    ap.add_argument("--clean", action="store_true",
                    help="Wipe .sync-progress/ before starting. Use when you want to refetch everything from scratch.")
    args = ap.parse_args()

    if args.clean and PROGRESS_DIR.exists():
        shutil.rmtree(PROGRESS_DIR)
        print(f"✗ Cleared {PROGRESS_DIR}/", file=sys.stderr)

    # Phase 1: ScoreboardGames gives us the whole season's metadata in one
    # LIKE query — Team1/Team2/Winner/DateTime/GameId/OverviewPage. Stages
    # are derived from its distinct OverviewPages (so we only sync stages
    # that have actually-played games, not rostered-but-unplayed ones).
    print(f"→ Metadata (ScoreboardGames LIKE {args.season_like!r})", file=sys.stderr)
    meta_rows = fetch_meta_for_season(args.season_like)
    print(f"  got {len(meta_rows)} game metadata rows", file=sys.stderr)
    if not meta_rows:
        raise SystemExit(f"No games found for {args.season_like!r}.")

    stages = sorted({r.get("OverviewPage") for r in meta_rows if r.get("OverviewPage")})
    print(f"  stages: {stages}", file=sys.stderr)

    # Phase 2: per stage, fetch picks and bans from PBS7 and merge by GameId.
    # Two 11-field queries per stage is the widest PBS7 will tolerate without
    # MWException (diagnosed 2026-04-24 — picks+bans in one SELECT blows up).
    picks_by_gameid = {}
    bans_by_gameid = {}
    for stage in stages:
        time.sleep(GAP_SEC)
        print(f"→ Picks for {stage!r}", file=sys.stderr)
        for r in fetch_picks_for_stage(stage):
            gid = r.get("GameId") or ""
            if gid:
                picks_by_gameid[gid] = r
        time.sleep(GAP_SEC)
        print(f"→ Bans for {stage!r}", file=sys.stderr)
        for r in fetch_bans_for_stage(stage):
            gid = r.get("GameId") or ""
            if gid:
                bans_by_gameid[gid] = r

    # Merge each SG meta row with its PBS7 picks + bans (keyed on GameId).
    games = []
    for m in meta_rows:
        merged = {**m, **picks_by_gameid.get(m.get("GameId") or "", {}),
                        **bans_by_gameid.get(m.get("GameId") or "", {})}
        mapped = map_draft_row(merged)
        if mapped:
            games.append(mapped)
    games.sort(key=lambda g: g.get("date", ""))
    print(f"  {len(games)} total games after merge", file=sys.stderr)

    players = []
    offset = 0
    while True:
        time.sleep(GAP_SEC)
        print(f"→ Players (offset {offset})", file=sys.stderr)
        rows = fetch_players_page(args.season_like, offset)
        if not rows:
            break
        players.extend(rows)
        if len(rows) < 500:
            break
        offset += 500

    print(f"  {len(players)} total player rows", file=sys.stderr)

    imported_days = sorted({g["date"] for g in games if g.get("date")})
    blob = {
        "at": int(time.time() * 1000),
        "importedDays": imported_days,
        "games": games,
        "players": players,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(blob, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"✓ Wrote {out_path} — {len(games)} games, {len(players)} player rows, {len(imported_days)} days. "
        f"Load it in the viewer via 💾 Base locale → Remplacer par un fichier.",
        file=sys.stderr,
    )
    # Successful end-to-end — wipe the per-query cache so the next run
    # starts fresh. Use `make sync-clean` to force a fresh run mid-way.
    if PROGRESS_DIR.exists():
        shutil.rmtree(PROGRESS_DIR)


if __name__ == "__main__":
    main()
