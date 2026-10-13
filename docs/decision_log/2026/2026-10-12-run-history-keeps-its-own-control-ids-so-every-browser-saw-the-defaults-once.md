# 2026-10-12: Run History Keeps Its Own Control Ids, So Every Browser Saw The Defaults Once

Status: Accepted

Run History's controls have ids of their own, where they could have taken
over the old page's. A browser stores each remembered setting under its
control's id, so on the day the page went public every browser showed the
defaults once, whatever had been set on the old page. The maintainer accepted
that as a one-time reset on a page that looks new anyway. A user who had
changed a setting on the old page had to set it again, once.

**Ruling.** By the maintainer, 2026-10-12, on
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356):
"I ratify the proposal." This was not a numbered row. It is author-owned
design the ratification covered, and the maintainer had already accepted its
cost: "I can accept the user browser settings reset. It's only a one time
reset, and the page would look and feel like a new page anyways." What the
page remembers today is in [run_history.md](../../specs/run_history.md).

**The decision.** The page kept its own control ids, while it was hidden and
after it went public. Every one starts `run-history-`. Dash stores a
remembered value under the control's id, so every browser saw the defaults
once on the day the page went public: a threshold of 95, **Run
notifications** on, the default point size and color, and no playlist or
scenario until Follow, the switch that selects the scenario just played,
picked one up. The proposal asked for one line about it in that release's
notes. A release's notes are a fixed header and a generated list of merged
pull request titles, so the line is the title of the pull request that made
the page public.

- **The page was built beside the old one,** with both registered in the app
  for three releases
  ([the build approach](2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md)).
  Two pages cannot share part of a callback: a page that holds one output of
  a callback has to hold every input of it.
- **How narrow that rule is was checked, and nothing depended on the
  answer.** A scratch Dash 4.4.1 app on 2026-10-11 showed that a page may
  hold an id that is only an input of another page's callback. It breaks
  when it holds a callback's output without all of that callback's inputs.
  That was not tried under `DashProxy`, which the app uses. The page keeps
  its own ids either way.
- **Each page kept its own values while both existed.** In PR #370's check
  the old page held its scenario, its filter, and its chart settings across
  two visits to the new page, and the new page arrived on its defaults with
  nothing carried over.

**What the page remembers.** The Playlist filter, the Selected scenario,
Follow, the chart mode, the two ranges, the Chart options controls, and the
Columns menu's two checkboxes. Chart options has nine controls while both
notification switches are carried, and seven once the Run toasts change
lands. Not remembered: whether Chart options is open, as before, and which
session rows are open.

**"Ids and defaults survive verbatim" is set aside once.** The
[2026-08-09 panel entry](2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph.md)
says that because Dash persistence is keyed by component id, and because
changing a layout default silently drops every stored value. This move to a
new page is the one exception. The rule stands for every later change: a
renamed id or a changed default on this page resets that value for every
user. The two rules of
[2026-09-19](2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)
for a remembered control bind the page as well.

**The old page's stored values are left where they are.** They sit in each
browser under the old ids, unread, and nothing clears them.

**One switch is reset once more.** The
[Run toasts proposal](../../proposals/run_toasts_proposal.md), ratified and
not yet built when the page went public, moves **Run notifications** to the
Settings page and keeps it in a store that does not read the old control's
value. A browser that had turned run toasts off starts on again when that
change lands. Had it landed in the release that made the page public, that
would have been part of this reset. The page went public first, so it is a
second reset, for that one switch. Until then the page carries both
notification switches as they were.

Proposed in
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
which merged as `a65f72d`. The ids were set in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370),
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371), and
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372),
and the reset happened with
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373),
which made the page public. The proposal file,
`docs/proposals/run_history_proposal.md`, is deleted, and git history keeps
it.
