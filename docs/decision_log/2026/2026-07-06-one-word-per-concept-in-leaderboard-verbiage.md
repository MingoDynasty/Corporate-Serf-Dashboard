# 2026-07-06: One Word Per Concept In Leaderboard Verbiage

Status: Accepted

Decision: "Rank" was used for both benchmark tiers (Bronze/Silver/..., Rank
Overlay) and leaderboard placement (Home "Rank:", grid "Current Rank"),
mirroring a split in the ecosystem (KovaaK's leaderboards: rank = position;
Voltaic/Aimlabs: rank = tier). In user-facing text, **Rank** means tier only,
**Position** means leaderboard placement ("Total Players" for board size), and
**PB** prefixes stats of the personal-best run (PB Score, PB cm/360, PB
Accuracy). "Unranked" is retained as KovaaK's own term for having no leaderboard
entry.

Consequences: Labels, plot annotations, and toasts follow the invariant.
Internal identifiers, component ids, and row field names keep their old names
because this is a label-only rename. New UI text must not reintroduce "rank" for
leaderboard placement.

**Superseded in part (2026-10-04).** Row field names no longer all keep their
old names: the playlist scenario table's Position and PB Score fields now say
`position` and `pb_score`. Every other internal identifier still keeps its
old name
([2026-10-04](#2026-10-04-the-scenario-tables-row-fields-use-the-words-on-screen)).
