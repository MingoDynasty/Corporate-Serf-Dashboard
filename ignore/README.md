# ignore/ — local scratch (gitignored)

Everything here except this README is untracked scratch. Route new files into
a subdirectory — don't drop them at the top level.

## Routing rules

| What | Where |
|---|---|
| PR / proposal review handoff docs | `pr-reviews/` (`pr<num>-review.md` — the `/pr-review` skill already writes here) |
| Kickoff / implementation prompts for agent sessions | `prompts/` |
| One-off scripts, runners, experiments in code | `scripts/` |
| Data samples: API responses, stats CSVs, tool test outputs | `data/` |
| Downloaded playlist JSONs | `playlists/` |
| Playlist-generator output | `Playlist Generator - generated/` |
| Superseded / abandoned proposal drafts | `superseded-proposals/` |
| pytest basetemp (`--basetemp=ignore/pt`) | `pt/` — disposable; parallel sessions may create `pt2/`, `pt-audit/`, etc., all safe to delete anytime |

Anything that doesn't fit: make a new descriptively-named subdirectory rather
than leaving files loose.

Standalone experiments with their own config/cache get their own directory
(e.g. `ManicTime Comparison/`).
