# 2026-10-04: The Scenario Table's Row Fields Use The Words On Screen

Status: Accepted

The code behind a playlist's scenario table now names its Position and PB
Score columns the way the screen does. The Position fields were named for
rank and sat beside fields named for tier that hold the Rank column, so the
two words were swapped against what a user sees. Nothing a user sees or has
saved changes. The rest of the code still says rank for a leaderboard
position.

**Direction.** The maintainer chose this on 2026-10-04, in chat, over leaving
every identifier as it was and over parking the question. It supersedes one
consequence of the
[2026-07-06 entry](#2026-07-06-one-word-per-concept-in-leaderboard-verbiage),
which kept row field names along with every other internal identifier.

**What changed.** On the row a scenario table draws, `rank_sort`,
`rank_display`, and `rank_pending` are now `position_sort`,
`position_display`, and `position_pending`, and `high_score_sort` and
`high_score_display` are now `pb_score_sort` and `pb_score_display`. The class
on a cell whose value is still loading was `playlist-rank-pending` and is now
`playlist-cell-pending`, because it marks the Position, Total Players, and
Percentile cells and never the Rank column. The Rank column's `tier_*` and
`next_tier_*` fields stay. Renaming them to `rank_*` in the same change would
have made `rank_sort` mean the position in one commit and the tier in the
next.

**Why only here.** `rank` has three meanings in code: a leaderboard position,
a benchmark tier, and KovaaK's own field name for the position. After this
change it still appears about 870 times under `source/` and about 1,650 under
`tests/` (counted 2026-10-04), and each use would need sorting into one of the
three by hand. Renaming every position use would still not make the code
consistent, because four kinds of name stay `rank` or cost something to
change:

- The fields KovaaK's sends, which the app cannot rename.
- The `rank` key and the `RANKED` and `UNRANKED` statuses, which are written
  to the cache.
- The `scenario_rank_cache_ttl_hours` config key, which a user's `config.toml`
  already holds.
- The `leaderboard/user_rank/` cache folder, whose rename would orphan every
  cached position.

A blanket rename moves the boundary between the two words. It does not remove
it. The scenario table was the one place where the two words met and pointed
the wrong way: `"position": "rank_sort"` beside `"rank": "tier_sort"` in the
table that maps `?sort=` names to column IDs.

**Consequences.** The names in `?sort=` are unchanged, so a link saved before
this change still sorts the table. `SORT_URL_NAMES` is the one place a name
meets a column ID, which is what the
[2026-09-27 entry](#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)
set it up for. No stored state keys on a row field name: the page's stores
hold nothing between visits, and the grid's column state is read only to
write the address. Everything else that says `rank` for a position is
unchanged, including `ScenarioRankInfo`, the Home page's component IDs, and
the cache. The [glossary](glossary.md) gives the code words as they now
stand. A new row field for a leaderboard position says `position`.

**Provenance.** No proposal. The change came out of a check of the glossary
against the code, whose docs-only half shipped in PR #333. Shipped in PR
#342.
