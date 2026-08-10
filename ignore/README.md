# ignore/ — local scratch (gitignored)

Everything here except this README is untracked scratch. Route new files into
a subdirectory — don't drop them at the top level.

## Routing rules

| What | Where |
|---|---|
| PR / proposal review handoff docs | `pr-reviews/` (`pr<num>-review.md` — the `/pr-review` skill already writes here): the live queue holds only reviews still in flight, so `ls ignore/pr-reviews/*.md` answers "what's mid-review?" (merged/closed ones live in the `done/` subdir) |
| Completed review handoff docs | `pr-reviews/done/` — move a review here once it's no longer in flight: its PR merged/closed, or (for a proposal review) the proposal shipped or was abandoned. Keeps the top level as reviews-in-flight only; everything here is untracked, so move, never delete |
| Kickoff / implementation prompts for agent sessions | `prompts/` — the live queue: only prompts with no PR in flight, so `ls ignore/prompts/*.md` answers "what's ready to start?" (consumed ones live in the `done/` subdir) |
| Consumed kickoff prompts | `prompts/done/` — move a prompt here when opening the PR that consumes it; move it back if that PR closes unmerged. Kept as the house-style reference corpus for writing new prompts; everything here is untracked, so move, never delete |
| Parked kickoff prompts (valid but deliberately not queued — e.g. a contingency that didn't fire) | `prompts/icebox/` — keeps the live queue meaning "ready to fire"; add a dated parking note at the top of the prompt; move back to `prompts/` to reactivate |
| Design notes for future/deferred proposals: findings, probed facts, settled direction, open questions — the pickup point for drafting the eventual proposal | `design-notes/` (one file per arc; delete or archive into the proposal when it ships) |
| One-off scripts, runners, experiments in code | `scripts/` |
| Data samples: API responses, stats CSVs, tool test outputs | `data/` |
| Downloaded playlist JSONs | `playlists/` |
| Playlist-generator output | `Playlist Generator - generated/` |
| Superseded / abandoned proposal drafts | `superseded-proposals/` |
| pytest basetemp (`--basetemp=ignore/pt`) | `pt/` — disposable; parallel sessions may create `pt2/`, `pt-audit/`, etc., all safe to delete anytime |

The `/merge-sweep` skill reconciles both live queues against merged PRs and
archives anything a shipping PR missed — run it whenever the queues look
stale.

Anything that doesn't fit: make a new descriptively-named subdirectory rather
than leaving files loose.

Standalone experiments with their own config/cache get their own directory
(e.g. `ManicTime Comparison/`).
