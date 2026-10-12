# 2026-08-01: No Username Stays Fully Offline — User-Independent Totals Rejected

Status: Rejected

Decision: an empty `kovaaks_username` keeps its documented meaning — the app
runs fully offline and no leaderboard feature makes network calls. The
proposal to resolve leaderboard IDs and show Total Players without a
configured username (PR #166, split out of the leaderboard-ID seeding
proposal) was reviewed independently twice and closed as not planned.

Why:

- The README promises that leaving the username empty runs the app fully
  offline, and today the rank service short-circuits before any network call.
  The proposed lazy per-scenario totals fetch at playlist open would silently
  break that zero-network contract.
- A board's population without the user's position or percentile answers none
  of the product's core questions ("am I improving? where am I weak?") — it
  fills a grid column, not a need.
- The proposal understated the plumbing: `_with_leaderboard_total` rejects
  non-RANKED/UNRANKED results by design, and the progressive-fill accounting
  counts UNKNOWN rows as unavailable positions, so username-less playlist
  opens would fetch totals and still end in red "positions unavailable"
  messaging unless both grew new semantics.

What survives: the leaderboard-ID seeding (PR #169,
[its entry](2026-07-20-seed-leaderboard-ids-from-the-bundled-benchmark-corpus.md)) stands on
its own merits. The worthwhile kernel — treating "leaderboard features off"
as a normal quiet state rather than a red error, skipping the futile
progressive position fill, and pointing at how to enable the features — is
deferred until a settings page exists to give that pointer a destination
(settings/config work proposed in PR #171, not yet agreed as of this
writing). The optional import-warmup companion (prefetching
unplayed scenarios of a freshly imported playlist) is dropped with the
proposal; revisit only if the import-then-open flow proves slow in practice.
