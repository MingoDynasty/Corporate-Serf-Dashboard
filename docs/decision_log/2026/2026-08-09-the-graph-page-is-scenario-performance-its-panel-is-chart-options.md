# 2026-08-09: The Graph Page Is Scenario Performance, Its Panel Is Chart Options

Status: Accepted

Three surfaces used to answer to the name "Settings", two of them with the same
icon. The graph page's preference panel is now called "Chart options", the page
itself is called "Scenario Performance" in the navbar and the browser tab, and
the Settings page keeps its name. The controls inside the panel are named the
way the app's own charts and the aim-training community already name them,
rather than in invented vocabulary.

Decision, four rulings:

- The disclosure button and the panel are **"Chart options"**.
- **`/settings` keeps the name "Settings".** The collision is resolved from the
  graph page's side; an "App setup" rename was considered and rejected.
- The graph page's product name is **"Scenario Performance"**, applied as
  labels only: the navbar link, the page's registered `name` and `title`, and
  doc vocabulary. `/` still serves it and `/home` and `/index` still redirect.
- The panel's column claims **no exclusive tenancy of the page's right side**.
  It is a page-local column a later design may share, stack with, or re-host.

Why: the surfaces sharing the "Settings" name are different in kind. `/settings`
edits server-persisted app setup through one validated Save with restart
semantics; the panel edits instant-apply browser preferences that only the chart
can give feedback on. Naming the panel after what it configures also follows the
repo's precedent that controls live on the surface owning their effect —
playlist management left this same modal for `/playlists`
([2026-07-11](2026-07-11-the-playlist-overview-is-the-playlist-management-surface.md)).
"Scenario Performance" is the page's product identity, distinct from its route
position as the default landing page, which is why the rename is labels-only.

Consequences and constraints:

- **The control labels are the app's own vocabulary, not the proposal's.** The
  proposal recommended a *Score goal* group with "Playlist rank lines",
  "Personal-best line", "Show goal line", "Goal percentage of PB", and "Show
  goal verdict". The maintainer rejected that on first local test: the app's own
  chart annotations already render "PB Score" and "Score Threshold", and "Score
  Threshold" is what the aim-training community says. What shipped is *Overlays*
  ("Rank Thresholds", "PB Score") and *Score Threshold* ("Score Threshold
  Overlay", "Score Threshold Percentage", "Score Threshold Notification") —
  the modal's original labels, verbatim. The general rule this carries: proposed
  UI copy is checked against the app's existing plot annotations and sibling
  pages before it ships, however settled a proposal declares it.
- **"Score Threshold Notification" is knowingly imprecise.** Since the
  notification redesign it gates only whether a run is judged against the
  threshold (`_threshold_verdict` returns `None` when it is off); placement
  toasts fire regardless. The maintainer accepted the wording and deferred the
  fix to a later copy pass; a dated comment at the control in
  `source/pages/home.py` records it. The help tooltip is accurate as written and
  is unchanged. That copy pass has since happened: the control is now "Score
  Threshold Verdict"
  ([2026-08-21](2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed.md)).
- **The route restructure is deferred, not dropped.** Reserving `/` for a future
  Overview page and giving this page a durable `/scenario` route waits until an
  Overview has concrete plans.
- **Run History composes into this column rather than adding a second one.** If
  a run history tied to Scenario Performance arrives, how the two share the
  space is the run-history proposal's question; this one only promises not to
  have claimed the space.

**Superseded in part, for copy (2026-09-14).** The control labels and chart
annotations quoted above are sentence case: "Rank thresholds", "PB score",
"Score threshold overlay", "Score threshold percentage", "Score threshold
verdict", and the annotations "PB score" and "Score threshold". The group
headings keep their capitals as section headings. The vocabulary rule this
entry carries is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md).

**Superseded in part (2026-10-12).** The page's name is now "Run History",
which reverses the third ruling above. "The route restructure is deferred" is
resolved: Run History is served at `/run-history`, in place of the
`/scenario` this entry expected, and `/` serves a new Home page. "Run History
composes into this column" is answered with a second column: the run list
has a column of its own beside the chart, and Chart options opens between the
two. Chart options' name, Settings' name, the ruling that the panel's column
claims no exclusive tenancy, and the rule that copy is checked against the
app's own words all stand. See
[The Chart Page Is Named Run History](2026-10-12-the-chart-page-is-named-run-history.md),
[Run History Has Its Own Address, And The Landing Address Is Home](2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md),
and
[The Run List Is A Second Column Beside The Chart](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md).

Shipped in PRs #209 and #215; design discussion in #206. Distilled with
[the inspector entry](2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph.md)
from `docs/chart_options_inspector_proposal.md`, now deleted.

**Superseded in part (2026-10-13).** The Score Threshold group no longer holds
the verdict switch this entry lists as "Score Threshold Notification". The
group holds the overlay switch and the percentage. See
[Top N Placement And The Score Threshold Verdict Switch Are Retired](2026-10-13-top-n-placement-and-the-score-threshold-verdict-switch-are-retired.md).
