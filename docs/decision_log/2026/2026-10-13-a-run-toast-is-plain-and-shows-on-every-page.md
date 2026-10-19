# 2026-10-13: A Run Toast Is Plain And Shows On Every Page

Status: Accepted

A new run now shows one plain blue toast on whatever page is open, with a
link to that scenario on Run History. It no longer says how the run went,
because the Run History page shows that beside the run for as long as the
run exists. A run that sets a new personal best keeps the celebration as its
one toast, and runs detected together share one toast, for the newest. The
app is less quiet for it, and one switch turns the toast off.

**Superseded in part (2026-10-18).** [The unsaved note text entry](2026-10-18-unsaved-note-text-is-never-lost-to-a-change-of-scenario-or-page.md):
on Run History, while a scenario note has unsaved changes, the toast's link
is stopped before the page is drawn again and asks in the note's dialog; Save
or Discard then selects the scenario in place, and the address stays. A link
to the edited scenario itself is stopped with no dialog. With no unsaved
changes the link draws the page again, as this entry says. The toast itself
is unchanged.

**The ruling.** Row T1 of the Run toasts proposal, ratified by the
maintainer on 2026-10-11 with its two clauses, on a new personal best and on
runs detected together. Their words on 2026-10-10:

> Moving forward I would expect a run notification to be barebones. It
> should avoid repeating information that can already be found on the new
> Run History page. Instead, a plain 'New run detected' notification, with a
> simple CTA to direct the user to the Run History page, is sufficient.

Told that this reverses a ratified decision: "I agree to reverse this
ratified decision. 'the title carries no verdict, and runs that earn no
toast today get one.' is exactly correct."

**What it reverses.** The
[2026-08-03 entry](2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy.md)
set three things for run toasts that this undoes. The rest of that entry
stands, for run toasts and for every other toast.

- "The title carries the verdict." The title says only that a run landed.
- A run that earned neither a verdict nor a placement "emits nothing,
  because the new point on the plot is the confirmation that it landed." A
  run needs neither to earn a toast.
- Its test for whether an event deserves a toast: "Is it already visible
  somewhere? → nothing." While Run History is open the run is already
  visible there, and the toast shows anyway.

**Why.**

- **The verdict has one home, and it lasts.** The pass or miss was in a
  toast for eight seconds, on one page. On Run History it is a check beside
  the run's score for as long as the run exists, and the percentage is on
  the latest-run card until the next run. A toast that repeated it would be
  a second copy with a shorter life.
- **The old toast could not be relied on to appear.** One page's chart
  callback built it, so it showed only while that page was open, and only
  for the scenario that page was showing.
- **A plain toast has a job on every page.** It confirms that the app saw
  the run, and it is one click from where the run is judged.
- **Every run notifying was the maintainer's stated intent,** on 2026-09-13
  and again on 2026-09-22
  ([the README entry](2026-09-22-the-readme-stops-explaining-how-the-installer-works.md)).

**What it costs.**

- **The app gets less quiet.** A toast on every run, on every page, is the
  opposite direction from "The dashboard now stays quiet during normal
  play." The Run notifications switch turns it off, and the toast replaces
  itself instead of stacking.
- **The toast stops answering the question.** "Threshold passed" in green
  answered how the run went from across the room. "New run detected"
  answers nothing. The answer is on the latest-run card, which takes a look
  at the page.
- **While Run History is open, the toast repeats the page.**

**The toast.** Blue, the app's color for information whose action is
optional, with the chart icon the placement toast used. The title is "New
run detected". The scenario's name is on a line of its own, and the link
"Open in Run History" is on the line below. It lasts the nominal eight
seconds, and holds no score, percentage, sensitivity, or goal.

- The scenario's name stays although the page shows it too. It is the one
  fact that says which run the app saw, and it says where the link goes.
- Eight seconds, not until dismissed. The celebration stays because a new PB
  is rare and was earned in a fullscreen game. A toast on every run that had
  to be dismissed would be a chore, and the navbar leads to the same page.

**The shell's drain builds it,** in the response that publishes the batch
and sends the celebration.

- It runs on every page, which a toast that points at one page needs.
- Each run is seen exactly once. The drain empties the queue, so a run it
  finds was never seen by an earlier drain. A second callback listening to
  the published batch would have to prove it never fires twice for one
  batch, on a page load or a remount.
- The celebration decision is already in hand, so the rule for a celebrated
  run is one condition, not a message between two callbacks.
- The channel keeps one producer, which replace-in-place relies on
  ([2026-08-31](2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry.md)).
  The page's builder was deleted in the change that gave the drain its own,
  and Run History's chart callback lost its three notification outputs.

One response can carry two toasts, each on its own channel. An output takes
one value and two `dash.Patch` objects cannot be joined, so
`channel_toasts` builds one patch that assigns both keys. The registry is
still written one key at a time and never as a whole.

**Which run earns it.** The batch's newest live run. A batch's other runs
earn none, and their rows on the page are their record.

| The batch's newest live run | Celebration setting | Run notifications | On screen |
|---|---|---|---|
| Set a new PB | On | On or off | The celebration |
| Set a new PB | Off | On | The plain toast |
| Did not, and an earlier run in the batch did | On | On | Both, about different runs |
| Did not, and none did | Either | On | The plain toast |
| Any | Either | Off | No plain toast. The celebration follows its own setting |
| No live run in the batch | Either | Either | Nothing |

- **A celebrated run gets no second toast.** This keeps the 2026-09-02
  rule, "every run earns at most one notification, and the celebrated run
  exactly one." A plain toast beside the celebration would say less about
  the same run. The cost is that a celebrated run's toast has no link.
- **Freshness is unchanged:** a run is live when it reached the drain within
  120 seconds plus one poll period of being imported.
- **One channel, replaced in place.** The key stays `run-verdict`, separate
  from `pb-celebration`, so a run toast lands beside a celebration and never
  replaces it. A newer run's toast replaces the one on screen and gets a
  full lifetime, per browser and across a change of page.
- **A replacement is seen to arrive.** The maintainer asked on 2026-10-11
  that when a run's toast replaces the last run's, the new one still plays
  its entry animation. It does, because the toast stays on the 2026-08-31
  mechanism: a fresh instance slides in as the old one fades out.
- **Changing a setting never replays a run.** The drain reads both settings
  as state.
- **One active tab.** Each drain's batch reaches one browser tab. With two
  tabs open, on any pages, the toast shows in whichever asks first.

**Runs detected together share one toast.** "Every run" is the maintainer's
phrase, and in this case the design does not meet it. Measured on their
9,135 runs through 2026-10-10: no two ended within a second of each other,
so the default poll finds each run alone. With the poll slowed to one a
minute, as Chromium does to a tab hidden for more than five minutes, about
1.3% would have been found together with a newer run. An app opened within
about two minutes of several runs finds them together too. Toasts for three
runs found in one look would replace each other in the same instant, so
only two other choices change what the player sees, and neither was taken:
a count in the title, which is a second string and a plural rule over a
link that still names one scenario, and one toast per run side by side,
which leaves the replace-in-place rule. The maintainer, 2026-10-11:

> The toast itself carries no information besides "a run came in; please
> look at the Run History page". Whether that's 1 run or 10 runs, doesn't
> matter to the user. It's also an edge case because runs shouldn't be
> piling up in the queue.

**The link.**

- **It names the scenario.** The page's Follow switch does not act when the
  page is opened, so without the name a player arriving from another page
  lands on whatever scenario the browser remembers, under a toast that named
  a different one. The page treats the link as an ordinary choice and
  remembers it
  ([2026-09-19](2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)).
- **It names the run too,** as `run=` and the run's id, which is its stats
  file's name. The page does not read it. A link to the address the page
  already holds does nothing, and the address keeps a link's parameters. So
  without the run, this ordinary case fails: a toast opens scenario A, the
  player picks B by hand with Follow off, and plays A again. The new toast's
  link would be the address still in the address bar, and B would stay on
  screen. One case is left: the same toast's link, used a second time after
  a choice made by hand, does nothing, for the eight seconds that toast is
  up.
- **It is a `dcc.Link`.** Measured on 2026-10-11 on a scratch app with the
  same stack, with a name holding `&`, `%`, `+` and `#`: a `dcc.Link` kept
  the encoded address and changed the page with no reload, with the toast
  still up. A `dmc.Anchor` decoded the address, so the page received the
  name cut short at the `&`. An `html.A` reloaded the whole app, and the
  toast was gone. Of the 3,219 scenario names in the bundled benchmark
  library, 259 hold one of those characters.
- **One function builds it,** `scenario_run_history_href`, which builds
  every link to a scenario on the page.
- **It carries no playlist.** The shell does not know what the page's
  Playlist filter holds, so the link relies on a `?scenario=` link clearing
  a filter that does not list the scenario
  ([2026-10-12](2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md)).
- **Reaching it without a mouse.** Tab reaches the link while the toast is
  up, and Enter follows it. Mantine gives every toast the alert role, and
  the app's rule for a notice printed into a page is that one holding a
  control is not an alert
  ([2026-08-30](2026-08-30-one-severity-color-language-for-inline-notices.md)).
  A toast can't follow that rule, and this is the first toast to hold a
  control. No screen reader was run. The cost is accepted because the link
  is never the only way to the page: the navbar holds the same destination.

**While Run History is open, the same toast shows.** The maintainer,
2026-10-10: "I could go either way on this; maybe pick whichever option is
simpler for now." The simpler one is no exception. With Follow off and
another scenario on screen, the link is one click to the scenario just
played, which is where the toast earns its place on that page. With Follow
on, the page has already moved, and the link opens the page again on the
same scenario, which resets what the page does not remember, such as an
open Chart options panel. Hiding the toast there would need the drain to
read which page is open and the page's Follow switch, which the shell can't
see.

**Alternatives rejected.**

- **A second shell callback that listens to the batch.** It must be shown
  never to fire twice for one batch. The drain needs no such proof.
- **A link with no scenario.** It opens the wrong scenario from any other
  page.
- **The page removing the parameter once it has applied it.** It changes an
  accepted behavior of 2026-09-19, and it does not close the case: the
  router does not see an address rewritten behind it, so a later link to
  the old query still does nothing. Probed on the scratch app, twice.
- **A verdict and the link, on every page.** The strongest alternative. The
  shell would send "Threshold passed" or "Below threshold" with the
  percentage and the link, and a plain toast for a run that can't be judged.
  It keeps the answer readable from across the room. It was not taken
  because of what the toast is for: it confirms that the run arrived and
  offers the way to look, and the judgment has one home that lasts. If a
  glance at the result becomes the priority again, this is the version to
  reconsider.
- **No run toast at all.** The quietest app. It loses the link, and on any
  page but Run History it loses the only sign that the app saw the run.

**Not decided here.** Two things the proposal listed as optional, which the
ratification does not cover: renaming the channel from `run-verdict` to
`run-notification`, and giving the celebration toast the same link. Also
left for later, by the maintainer's word of 2026-10-10: playing the
celebration's animation only on first opening Run History.

Top N placement and the Score threshold verdict switch left with the
verdict
([their entry](2026-10-13-top-n-placement-and-the-score-threshold-verdict-switch-are-retired.md)),
and the switch that turns the toast off moved to the Settings page
([its entry](2026-10-13-run-notifications-is-a-browser-local-setting-on-the-settings-page.md)).

Shipped in PR #376; proposal and rulings in #354. Distilled from
`docs/proposals/run_toasts_proposal.md`, deleted in the shipping PR.
