# 2026-10-12: Run History Has Its Own Address, And The Landing Address Is Home

Status: Accepted

Run History now has an address of its own, and the address the app opens on
shows a small new page called Home. Home holds first-time setup and one line
that says how many runs the app found, because setup belongs to the app and
not to one scenario's history. Each launch now lands on Home, one click from
Run History, and an old bookmark that named a scenario opens Home and selects
nothing. The page was built hidden beside the old one over three releases and
replaced it in a fourth.

**Rulings.** By the maintainer, 2026-10-12, on
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356):
"I ratify the proposal." This entry is row R2, ratified as written, with no
forwarding of an old link that carries parameters. The ratification also
covered the author-owned design of Home and the build approach, both below.
Before it, the maintainer, 2026-10-10: "Does it make sense to create a
placeholder Home page for now? Eventually this will become the Overview page,
which I plan to design/propose/ship after Run History page. This way the
first time setup cards can live on its proper page." The rules as the app
applies them are in [run_history.md](../../specs/run_history.md) and
[home.md](../../specs/home.md). This entry holds the reasons, the forwarding
that was set aside, and how the page was built and made public.

**R2, the addresses.** Run History is served at `/run-history`. `/` serves
Home, and `/home` and `/index` redirect to it. The navbar reads Home, Run
History, Playlists, Settings.

- **The 2026-08-09 naming entry deferred exactly this.** "Reserving `/` for a
  future Overview page and giving this page a durable `/scenario` route waits
  until an Overview has concrete plans." An Overview is now planned after Run
  History, and Home is its placeholder. That sentence of
  [the naming entry](2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options.md)
  is resolved here, with `/run-history` in place of `/scenario`.
- **The page was moving anyway.** It is a new module with control ids of its
  own
  ([the ids entry](2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md)),
  so its address could change in the release where everything else about it
  did. Moving it later would have been a second change, for users and for
  every link.
- **Two new links need an address that won't move again:** the run toast's,
  and the Playlists pages' scenario links.
- **Setup belongs to the app,** not to one scenario's history.
- **`/run-history`, not `/scenario`.** The address follows the page's name,
  as `/playlists`, `/settings`, and `/aim-training-journey` do. `/scenario`
  stays free for the scenario-first page in the
  [roadmap](../../roadmap.md)'s Future list.

**What Home holds.** Top to bottom: the stats-folder hint and the setup card
when they apply, exactly as the old page showed them, then one line of stats.
The hint speaks for a stats folder that is set and can't be used. The setup
card has three states: two yellow ones, "Your settings can't be read" and
"Finish setting up", and a blue account offer. On what else Home shows, the
maintainer: "I think 'plain links' is not necessary; that's already the job
of the left navbar. Instead just show some simple stats that we already
collect, such as 'Detected 10,000 runs across 1,000 scenarios.' Or even have
a blank home page, if needed."

- **The stats line counts the runs and the scenarios in the run store.** It
  reads `Found {runs} runs across {scenarios} scenarios in your stats
  folder.`, singular where a count is one, with thousands separators as the
  maintainer's example has them. It answers a new user's first
  question after setup: did the app find my runs. "Found" is the setup card's
  own word on the same page ("No KovaaK's stats folder was found"), and
  "stats folder" is the app's term.
- **With a stats folder and no runs in it** the line reads `No runs found in
  your stats folder yet. Play a scenario in KovaaK's and your runs will
  appear in Run History.` That is what happened, then what to do.
- **It is drawn only while the app has a usable stats folder,** because the
  hint already speaks for the other case. It is worked out when the page is
  drawn and does not tick, so the count is as old as the page load.
- **Home lists no links and forwards nowhere.**

**Home ignores `?scenario=` and `?playlist_code=`.** The old page lived at
`/` and read both, so an old bookmark or a link kept outside the app can
still carry them. Home's layout accepts any parameter and reads none: such a
link draws Home and selects nothing. Two kinds of forwarding were considered
and neither was taken.

- **Forwarding `/` to Run History once setup is done.** The launch click
  would go away. The maintainer: "Disagree, because eventually the Home
  page/Overview page will have things for the user to look at. So we would be
  putting in logic that we will soon remove."
- **Forwarding only a `/` link that carries one of the two parameters,**
  while a plain `/` still opens Home. Old bookmarks would keep working. It is
  not the forwarding declined above, because the Overview would not remove
  it, and that is its cost: it is compatibility code with no date on which it
  could go. This was the row's contested point in review. The maintainer,
  2026-10-12: "Long term, I don't think we should be supporting
  `/?playlist_code=X&scenario=Y`. And if we do, it would probably be for
  something else more specific to the Overview page, and not for a redirect
  to the Run History page; so it would be confusing for the user to be
  navigated to a location that they should not expect." So the address stays
  free for the Overview to give the parameters a meaning of its own.

**The navbar and the links.**

- **Home has a navbar entry** because the launcher lands there on every
  start. The proposal's second reason, that a landing page missing from the
  navbar would highlight nothing, rested on a belief that turned out false:
  the navbar marks no page as the open one, on any page, because nothing
  sets its links' `active` state and the component's default is never
  active. Found while the page was made public. Marking the open page is
  left to a later change, on the maintainer's word of 2026-10-13: "let's
  keep the idea for a future PR."
  Home keeps the house icon and Run History has one of its own.
- **The header title still leads to `/`,** which is now Home. The navbar's
  Run History link leads to the page with no parameters.
- **The Playlists pages' scenario links** point at
  `/run-history?playlist_code=...&scenario=...`. One function builds them.
- **The launcher is unchanged.** It opens `/`.

**Queued notices show on Home and on Run History.** A failed run import and
a playlist that did not load at startup each wait in a queue for a page to
show them. They used to reach the screen only while the old page was open.
Home and Run History both host the two flushes, so a warning raised at
startup still shows on the page the launcher opens. Whichever page is open
empties the queue.

**Run History explains an empty page itself.** With no runs to read it shows
what Home shows in that case, above its top row: the stats-folder hint, and
the setup card's two yellow states. Neither has Skip, the button that
declines the account offer.

- **The hint alone would not cover it.** It speaks only for a stats folder
  that is set and can't be used. With no folder set, or with a settings file
  the app can't read, the page would be empty with no reason given.
- **The blue account offer is Home's alone.** It is the app's first-run
  offer, and it explains nothing about an empty page.
- **The chart and the list keep their ordinary empty states.**
- **How.** The builders of the hint and the card live in a shared module,
  `source/components/setup_surfaces.py`, so Run History draws its own copies
  without importing the Home page's module. Dash Pages loads each page file
  under its own name, and a second import path would make a second copy of
  that module with its own state.

**What it costs.**

- **Each launch lands on Home.** The launcher opens `/`, so until the
  Overview ships the player is one click from Run History at every start.
- **An old bookmark of `/?scenario=...` lands on Home,** which ignores the
  parameters. The Playlists pages' own links were rebuilt for the new
  address.

**If the maintainer had chosen otherwise.** With Run History left at `/`
there is no Home, the setup card stays on Run History, and the address moves
when the Overview arrives, taking the toast's link, the Playlists links, and
bookmarks with it then. With Home forwarding to Run History the launch click
goes away, and the forwarding is removed again when the Overview ships.

**The build approach.** The page was built as a new page beside the old one,
at its final address, with no navbar entry and nothing linking to it, until
it could replace the old page in one release. It reused the old page's
working parts and did not rewrite them. This was a stated lean and not a row,
and it was ratified with the proposal. The maintainer had leaned to it three
times. On 2026-10-07: "If a whole page rewrite will result in a cleaner and
more efficient implementation, then I'll vote for that. I can accept the
additional releases that the user won't see until the page fully ships. The
final swap can be derisked if I am part of the verification process while the
new page is being built." On 2026-10-10: "I agree on this approach. My
thinking is that this approach will lead to a cleaner implementation and
less-risky shipping process; at any time we can rollback by simply deleting
the new page." And of many changes landing in one release: "I think this is a
non-issue."

- **The alternative was changing the page in place, in shipped slices,**
  which `claude-fable-5-1` first recommended. Its breakdown of 2026-10-10 no
  longer contested the new page: the smaller version 1 gave most of what
  changing in place offered, and the groundwork was the same work either
  way.
- **The old page was large.** `source/pages/home.py` was 2,630 lines and
  `tests/test_home_*.py` totalled 5,657, on `main` at `4272fbb`. Three
  groundwork PRs moved the kept blocks into modules both pages could import,
  which left `home.py` at 1,214 lines.
- **Every hidden PR was a public release with nothing visible in it.** A
  push cuts a release unless every changed path is documentation, tests, or
  repository tooling. The maintainer accepted releases that change nothing a
  user can see.
- **Four PRs.**
  [#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370)
  built the page's skeleton, top row, and chart.
  [#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371)
  built the run list.
  [#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372)
  built the latest-run card.
  [#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373)
  made the page public: it shrank `home.py` into Home, deleted the old
  page's controls, chart, and callbacks, and changed the navbar and the
  links.
- **Each hidden PR showed the old page unchanged.** A harness dumped what
  the app served for `/` before and after, as the callback list, the routed
  layout, and callbacks fired over HTTP. In all three PRs every old-page
  entry was the same: 95 in a fresh install's state and 159 in a configured
  one.
- **The maintainer tried each hidden PR in their own Firefox,** at the hidden
  address, before it merged.

**The contract for going public.** The new page replaced the old one when
every statement of the old page's spec on `main` at `4272fbb` was true of the
new page, except a list of named rows. The rows came from a keep, change, or
drop list the maintainer answered on 2026-10-10. It had one row per statement
of that spec, 121 of them, and 23 more for what other pages and the
user-facing docs rely on: 99 keep, 32 change, 13 drop. The list is
untracked. What each of the 45 changed and dropped rows did is in the entry
for the decision that moved it, among
[the page's entries](2026-10-12-the-chart-page-is-named-run-history.md).
Seven of the 45 were the Run toasts proposal's to decide. One more condition
came from row R4 and not from that spec: that the NVDA screen reader had been
run on the built list and what it said was recorded
([the list's entry](2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md)).

**What the page carries until the Run toasts change lands.** The
[Run toasts proposal](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/blob/2c5c072d0670c7c6d4873eb9e77f676dca1f6d43/docs/proposals/run_toasts_proposal.md) is ratified and
was not built when the page went public. Nothing here waited on it. Until it
lands:

- Run History builds the old page's run toast, as the old page built it, so
  a run toast shows only while Run History is open.
- That toast's top-N placement is against a fixed 5, with no control, since
  the chart no longer has a Top N.
- Chart options keeps its four groups and both notification switches,
  **Score threshold verdict** and **Run notifications**. After that change
  the panel has three groups and no notification control.

**Superseded in part (2026-10-13).** The Run toasts change has landed, and the
page carries none of those three any more. The app shell's drain builds a
plain run toast on every page, nothing places a run, and Chart options has
three groups and no notification control. See
[A Run Toast Is Plain And Shows On Every Page](2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md),
[Top N Placement And The Score Threshold Verdict Switch Are Retired](2026-10-13-top-n-placement-and-the-score-threshold-verdict-switch-are-retired.md),
and
[Run Notifications Is A Browser-Local Setting, On The Settings Page](2026-10-13-run-notifications-is-a-browser-local-setting-on-the-settings-page.md).

Proposed in
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
which merged as `a65f72d`. The page was built hidden at `/run-history` in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370),
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371), and
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372).
Home, the navbar, and the links shipped in
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373).
The proposal file, `docs/proposals/run_history_proposal.md`, is deleted, and
git history keeps it.
