# 2026-10-14: A Session's Count Jumps To It In The Tree, And An Open Session Row Has Show All Runs

Status: Accepted

Under This scenario, a session row's count, such as `7 of 47 runs`, is now a
link that switches the run list to All scenarios and opens that session there,
with the selected scenario's runs showing. Under All scenarios, an open
session row has a Show all runs button that opens every scenario of that
session down to its runs. The count says how many runs went somewhere else,
and the link shows where they went. A jump moves the list's switch, so a
reload afterwards opens on All scenarios.

**Rulings.** By the maintainer, 2026-10-14, on
[PR #375](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/375):
"I ratify the proposal." This entry is row A2, ratified as recommended, both
halves. Before it, the design note of 2026-10-07 recorded the count's wording
as the author's, "not objected to", and the link as a lean; on 2026-10-13 the
maintainer agreed what **Show all runs** opens. Built in
[#378](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/378). The
view the link leads to is
[the All scenarios entry](2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md),
and what the list does today is in
[run_history.md](../../specs/run_history.md#the-run-list).

**The link.**

- The count on every session row under This scenario is a button drawn as a
  link, the first row's `0 of 47 runs` included. Its text is unchanged and is
  its accessible name; its hover, `Show the whole session`, is its
  description. A click on it does not open or close the row.
- Following it switches the list to All scenarios, opens that session and
  every scenario row of the selected scenario in it, and scrolls the
  session's row to the top of the list, just under the first row. Rows
  already open in the tree stay open. From `0 of 47 runs` it opens the
  session and nothing under it.
- A jump that brings the tree's rows for the first time in a visit decides
  what opens, and the tree's first arrival opens nothing of its own: only
  runs that landed after the page was drawn open their rows beside the
  jump's. Without that, the arrival would open the newest session and its
  last visit, which under a session followed from `0 of 47 runs` is another
  scenario's runs. This was the Codex seat's must-fix F2 on PR #378.
- Keyboard focus goes to the session's row. The pressed count is not in the
  tree, because a session row's right side differs between the views, and
  focus would otherwise fall to the page.
- If the tree that arrives does not hold the session, it shows from its top
  with focus on its first row. A run that lands late can give a session a
  new first run, and with it a new id.

**Why a link, and why it reaches back.** The count raises the question the
tree answers. For a session that isn't recent, the switch alone doesn't get
there: the tree loads 30 sessions at a time, and on the maintainer's history
on 2026-10-14 the 30th session This scenario lists for the most-played
scenario is the 233rd session back. Without the link, reaching it meant remembering its date,
pressing the switch, and pressing **Show older sessions** seven times.

**How it is built.**

- A session row under This scenario carries its place among all sessions,
  counting back from the newest. The script writes that place to a store
  that is always in the layout.
- **One server callback answers,** writing the switch's value and the number
  of sessions All scenarios loads, both plain outputs. If the tree has
  loaded fewer sessions than the place, it loads that many, and the session
  is the last one listed. The callback that builds the rows takes both as
  inputs, so Dash holds it until the jump has answered and the tree is built
  once, already reaching the session. Dash holds a callback back for a plain
  output of one already queued and not for an `allow_duplicate` one.
- **The switch is written from the server and not by the script.** A value a
  callback writes to a remembered control is remembered
  ([2026-09-19](2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)).
  A value the script writes with `set_props` was never tried. One rule then
  covers the switch and the jump: the view on screen is the view a reload
  shows.
- **The script keeps what to open, where to scroll, and where focus goes.**
  The server hears how far back to load, and still never which rows are
  open. The jump's callback does not run as the page mounts, and does
  nothing for an empty store.

**What a deep jump costs.** The tree has to hold every session from the
newest to the one asked for. Reaching the 233rd session on the maintainer's
history is 9,326 rows and a model of about 4 MB, built on the server in
372 ms the first time and 86 ms after; the tree stays that size until the
page is loaded again, and every run that lands meanwhile sends it again. The
grid draws only the rows in view. The browser figures, from the press to the
tree painted and for a run landing afterwards, are in the PR. The proposal's
fallbacks, smaller rows and then a jump that shows the session alone, were
kept for a jump found too slow; it was not.

**Show all runs.**

- An open session row under All scenarios carries it at the end of its
  facts. It opens every scenario row of that session down to its runs, and
  reads **Hide all runs** once they are all open, following every way a row
  can open or close. **Hide all runs** closes them and leaves the session
  open. Both say `Expanded` or `Collapsed` through the list's live region,
  because a button's changed name is not reported in Chrome and Edge.
- A session opened in the tree shows its scenario rows closed, its outline:
  5 rows in the maintainer's median session and up to 71. **Expand all**
  doesn't open runs on purpose: every run of 30 sessions is about a thousand
  rows at once.
- A closed session row has none. Thirty closed rows would each carry a link,
  and the widest row would be every row.

**If the maintainer had chosen otherwise.** Without the link the count stays
plain text and an old session is reached by loading every session newer than
it by hand. Without **Show all runs** each scenario row is opened by hand.
Neither half needs the other.
