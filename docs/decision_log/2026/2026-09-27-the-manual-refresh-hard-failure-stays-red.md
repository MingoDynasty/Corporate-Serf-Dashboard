# 2026-09-27: The Manual-Refresh Hard Failure Stays Red

Status: Accepted

When a clicked position refresh gets nothing usable back, its toast stays red
instead of softening to yellow. The app's color scale reserves red for an
operation that failed, and a refresh the user asked for that returned nothing
is exactly that. The outcome that falls back to a cached position stays
yellow, so the two still differ by color as well as by title.

**Ruling.** Ruled (user) 2026-09-27, in a decisions chat. It closes the color
question the 2026-08-03 notification entry left open in `docs/tech_debt.md`
("Manual-refresh failure color"), whose precondition, a title of its own for
the served-stale toast, the 2026-09-14 copy sweep met. Nothing in the code
changes: `_rank_refresh_problem_notification` in `source/pages/home.py` stays
red "Position refresh failed" for a hard failure and yellow "Refresh failed ·
data from cache" for a served-stale one, on one `rank-refresh-problem`
channel.

**Why red.** The severity scale makes red an operation that failed and yellow
caution without anything having failed
([2026-08-30](2026-08-30-one-severity-color-language-for-inline-notices.md)).
The routing policy gives a user-initiated failure, manual Refresh named among
them, an error toast, and its peers are red: "Playlist import failed",
"Cleanup failed", "Skip wasn't saved". For this pair the scale reads as
whether anything usable came back: the served-stale outcome returned a cached
position, the hard failure returned nothing.

**The argument for yellow, rejected.** From the user's seat both outcomes
leave an older position on screen: the hard failure leaves the field
untouched, and the served-stale one re-serves the cache, so only the
service's confirmation of the fallback differs. That is why they share one
channel, but softening one toast turns the scale into an exception list for
little gain, since an icon-bearing notification shows its color only as the
icon's circle, not as Mantine's full-height bar.
