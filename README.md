# LFL Draft Recap

Outil de coach : convertit une page LeaguePedia de résultats de matchs (ex. LFL Spring 2026) en un résumé de drafts prêt à coller dans Google Docs.

## Ce qu'il produit

1. **Un tableau par game** — draft blue-side vs red-side, en-tête de colonne surligné pour l'équipe gagnante (même format que le screenshot de référence).
2. **Un tableau agrégé** — pour chaque joueur, la liste de tous les champions qu'il a joués sur le split.

Le HTML généré se copie-colle directement dans Google Docs : couleurs, fusion de cellules et structure préservées.

## Usage

1. Cloner ou télécharger ce dépôt.
2. Ouvrir `index.html` directement dans un navigateur récent (Chrome/Firefox/Safari/Edge).
   - Si `fetch()` est bloqué depuis `file://`, lancer `make serve` puis ouvrir `http://localhost:8080`.
3. Coller le **OverviewPage** LeaguePedia (ex. `LFL/2026 Season/Spring Season`) dans le champ.
4. Cliquer **Charger** — l'outil interroge l'API Cargo de Fandom.
5. Copier la sortie et la coller dans un Google Doc.

## Source des données

- API MediaWiki Cargo de Fandom : `https://lol.fandom.com/api.php`
- Tables utilisées : `ScoreboardGames`, `PicksAndBansS7`, `ScoreboardPlayers`
- CORS : ouvert (`access-control-allow-origin: *`) — pas de backend requis
- Rate limit : Fandom throttle les requêtes agressives ; l'outil les sérialise avec un délai.

## Statut

Scaffold — implémentation à venir. Voir `CLAUDE.md` pour le plan.
