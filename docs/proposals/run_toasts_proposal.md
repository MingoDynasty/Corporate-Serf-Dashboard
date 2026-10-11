# Run Toasts Proposal

Status: Proposed
Date: 2026-10-11

## TL;DR

Today a run's toast carries the verdict on that run, and it shows only while
the Scenario Performance page is open. The Run History page will show that
verdict beside every run, so this proposal makes the toast plain: on every
page it says a new run was detected and links to that scenario on Run
History. Top N placement and the Score threshold verdict switch go with the
verdict. The personal best celebration is unchanged, and none of this lands
before the Run History page is public.

## Decisions needed

**Nothing in this proposal is ratified.** Three rows need the maintainer's
judgment, T1 to T3. Each repeats what the maintainer said in chat on
2026-10-10, which was a lean or an agreement and not a ruling. Each then
gives the argument, the cost, and what changes if the maintainer chooses
differently. T1 also holds two judgments the outline did not ask about,
each marked as one. The maintainer agreed to both on 2026-10-11. Reviewers
are invited to contest any row, and any author-owned choice in
[Design](#design).

**How this sits among the other Run History proposals.** Run History is
planned as five pieces: groundwork with no proposal, Sessions, Run toasts
(this one), the Run History page, and All scenarios. This proposal leans on
the page proposal in three places, and none blocks review:

- **The verdict's new home.** A toast can go plain only because the page
  shows a check and a star beside each run's score, and a latest-run card
  with the percentage of the PB. The page proposal owns all three.
- **The link's target.** The toast links to the page by its address, which
  is the page proposal's row R2, and calls it by its name, which is R1.
- **A link to a scenario the Playlist filter does not list.** The page
  proposal's row R7 has such a link clear the filter.

The page proposal is
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356).
It replaces the text of [run_history_proposal.md](run_history_proposal.md)
in place, and until it merges that file holds the older plan. The Sessions
proposal is
[PR #355](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/355),
and this proposal takes nothing from it.

**Already decided, and binding here.** The proposal is held to these and
does not reopen them:

- **How a repeatable toast behaves.** A toast whose fact can recur is a
  channel: a newer one replaces the one on screen and gets a full lifetime
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
  The run toast stays one channel.
- **The personal best celebration.** Its toast, its animation, its own
  channel, and its own setting are as ruled on
  [2026-09-02](../decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page).
  The maintainer, 2026-10-10: "PB celebration toast can stay as is."
- **What a run is judged against.** A run is judged against the PB it was
  chasing, the best score before it
  ([2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb)),
  by pace on a time-scored scenario
  ([2026-10-05](../decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace)).
  The rule survives. It becomes the rule for the check beside a score, which
  the page proposal owns.
- **The copy rules** in
  [AGENTS.md](../../AGENTS.md#styling-conventions).

### T1. A plain toast when a new run is detected, on every page, with no verdict

Status: Open. The maintainer's agreement of 2026-10-10, and of 2026-10-11
for the two clauses the outline did not ask about: a new personal best, and
runs detected together.

**Recommendation: a blue toast titled "New run detected", holding the
scenario's name and a link, "Open in Run History". The app shell builds it,
so it shows on every page. A run that the personal best celebration
announces keeps the celebration as its one toast. Runs detected together
share one toast, which names the newest.**

The maintainer's words, 2026-10-10:

> Moving forward I would expect a run notification to be barebones. It
> should avoid repeating information that can already be found on the new
> Run History page. Instead, a plain 'New run detected' notification, with a
> simple CTA to direct the user to the Run History page, is sufficient.

Told that this reverses a ratified decision, and shown the consequence in
one sentence: "I agree to reverse this ratified decision. 'the title carries
no verdict, and runs that earn no toast today get one.' is exactly correct."

**What it reverses.** The
[2026-08-03 decision](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
set three things for run toasts that T1 undoes:

- "The title carries the verdict." The new title says only that a run
  landed.
- A run that earns neither a verdict nor a placement "emits nothing,
  because the new point on the plot is the confirmation that it landed."
  A run now needs neither to earn a toast.
- Its test for whether an event deserves a toast: "Is it already visible
  somewhere (plot point, Position field, empty-state canvas, warmup status
  strip)? → nothing." While Run History is open, the run is already visible
  there, and the toast shows anyway.

The rest of that decision stands, for run toasts and for every other toast.
[Decisions this changes](#decisions-this-changes) lists each clause.

**Why.**

- **The verdict gets one home, and it lasts.** Today the pass or miss is in
  a toast for eight seconds, on one page. On Run History it is a check
  beside the run's score for as long as the run exists, and the percentage
  is on the latest-run card until the next run. A toast that repeated it
  would be a second copy with a shorter life. The roadmap's principle is
  "Compose, don't replicate."
- **Today's toast can't be relied on to appear.** It is built by one page's
  chart callback, so it shows only while that page is open, and only for
  the scenario that page is showing. A player on a playlist's scenario
  table, picking what to play next, gets no run toast at all.
- **A plain toast has a job on every page.** It confirms that the app saw
  the run, and it is one click from where the run is judged. Away from Run
  History, nothing else on screen says either.
- **Every run notifying is the maintainer's stated intent, twice before.**
  They raised it on 2026-09-13 as a candidate for the Run History work
  ([PR #351](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351)
  records it under H5). On 2026-09-22 they chose the README's Run
  notifications wording "intending every run to notify, which has not fully
  shipped"
  ([decision log](../decision_log.md#2026-09-22-the-readme-stops-explaining-how-the-installer-works)).

**What it costs.**

- **The app gets less quiet.** The 2026-08-03 decision opens with "The
  dashboard now stays quiet during normal play." A toast on every run, on
  every page, is the opposite direction. The **Run notifications** switch
  still turns it off, and the toast replaces itself instead of stacking.
- **The toast stops answering the question.** The roadmap's first principle
  is "Answer the question, don't just show the data." "Threshold passed" in
  green answered *how did that run go?* from across the room. "New run
  detected" answers nothing. The answer moves to the latest-run card, which
  takes a look at the page.
- **While Run History is open, the toast repeats the page.** A new row and
  a new card have just appeared. [Design](#while-run-history-is-open) says
  why it shows there anyway, and what the other choice costs.

**The one judgment inside this row: a new personal best.** "Every run"
needs an answer for the run the celebration announces. The recommendation
keeps the rule of 2026-09-02: "every run earns at most one notification,
and the celebrated run exactly one." So a celebrated run shows the "New
personal best" toast and no plain one. A plain toast beside it would say
less about the same run, at the moment the screen should be the
celebration's. The cost is that a celebrated run's toast has no link,
because the celebration is unchanged. The maintainer agreed to this clause
on 2026-10-11, which is an agreement and not a ruling.

*If the maintainer chooses a plain toast on a celebrated run too:* a new PB
puts two toasts on screen for one run, and that clause of the 2026-09-02
decision is superseded as well.

**A second judgment inside this row: runs detected together.** "Every run"
is the maintainer's phrase, and in one case the recommendation does not
meet it. The app looks for new runs once a second by default. Each look
that finds any shows one toast, for the newest run it found. The older runs
found in the same look get no toast of their own, which is today's rule for
a batch.

How often that happens, from the maintainer's 9,135 runs (fact 7 under
[Verified facts](#verified-facts)):

- **In normal play, never.** No two runs ended within a second of each
  other, so each is found alone.
- **With the tab hidden for more than five minutes,** Chromium slows the
  look to about one a minute. About 1.3% of runs would then have been found
  together with a newer one.
- **When the app is opened** less than about two minutes after several
  runs, they are found together.

The reason to accept it: a run toast is one channel, and a newer one
replaces the one on screen (2026-08-31, binding here). Toasts for three
runs found in one look would replace each other in the same instant, and
only the last would be seen. So only two other choices change what the
player sees, and neither is recommended:

- *If the maintainer chooses a count:* the title reads "3 new runs
  detected" for a batch. That is a second string and a plural rule, and the
  link still names one scenario.
- *If the maintainer chooses one toast per run, side by side:* run toasts
  leave the replace-in-place rule, which supersedes part of the 2026-08-03
  and 2026-08-31 decisions. An app opened after a few runs then shows
  several toasts at once.

The maintainer agreed to one toast for the newest run on 2026-10-11, which
is an agreement and not a ruling:

> The toast itself carries no information besides "a run came in; please
> look at the Run History page". Whether that's 1 run or 10 runs, doesn't
> matter to the user. It's also an edge case because runs shouldn't be
> piling up in the queue.

They asked for one thing to hold with it: when a run's toast replaces the
toast of the run before it, the new one still plays its entry animation, so
the player sees that another run came in. It does, and
[The rules it keeps](#the-rules-it-keeps) says why.

**If the maintainer chooses differently on the row:**

- **Keep the verdict in the toast.** The page then goes public with today's
  toast, still built by the page and shown only there. That is the page
  proposal's fallback, with N fixed at 5. T2 and T3 would need another
  look, since both follow from a toast with no verdict.
- **No run toast at all.** This is the quietest app, and it keeps the
  2026-08-03 test whole. It loses the link, and on any page but Run History
  it loses the only sign that the app saw the run.
- **A plain toast everywhere except on Run History.** See
  [While Run History is open](#while-run-history-is-open).

### T2. Top N placement is retired

Status: Open. The maintainer's lean of 2026-10-10.

**Recommendation: no surface says where a run placed. The run message loses
`nth_score`, and the glossary loses the term.**

Top N placement is where a new run's score places among the scenario's runs
at the same sensitivity. Today it exists only as toast copy: the trailing
sentence "Also your 2nd-best at 34.6 cm/360.", and the title "New 2nd-best
score" on a run that was not judged. A run counts as placed when its place
is within the chart's **Top N scores** setting.

The maintainer, 2026-10-10: "Lean toward your recommendation of retiring Top
N."

**Why.**

- **Its N is going away.** The page proposal's row R5 plots every run and
  removes the **Top N scores** control. Placement would then need an N from
  somewhere. The earlier lean was a fixed 5, a number nothing on screen
  would explain.
- **A plain toast has no room for it.** Under T1 the toast carries no
  judgment of the run, and a placement is one.
- **At the default settings it is almost never the headline.** A run that
  can be judged leads with the threshold verdict, and placement trails it.
  A run that can't be judged is nearly always the first at its sensitivity,
  where the title is always "New best score".

**What it costs.** "Your 2nd-best at this sensitivity" is a real fact, and
after this nothing states it. The run list shows every score, in time order
and not grouped by sensitivity, so a player who wants the fact has to read
for it. Score vs Sensitivity still plots every run at each sensitivity.

**If the maintainer chooses differently:**

- **Placement stays in the toast, with N fixed at 5.** The toast keeps a
  second sentence and `nth_score` stays. That contradicts "barebones".
- **Placement moves to the latest-run card.** `nth_score` stays in the run
  message, and the card is the page proposal's to change. This proposal
  recommends neither.

### T3. The Score threshold verdict switch is dropped

Status: Open. The maintainer's agreement of 2026-10-10. It follows T1: if
T1 is not agreed, T3 falls with it.

**Recommendation: remove the switch and its help text from the Chart
options panel. Clearing Score threshold percentage is the one way to stop
runs being judged.**

The switch decides whether a run toast carries a pass or a miss. It never
decided whether a toast shows
([2026-08-21](../decision_log.md#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)).

The maintainer, 2026-10-10: "Yes, drop the Score Threshold verdict switch."
And: "It can be entirely replaced with the 'green checkmark' idea in the
mockups to the right of the score. Essentially that green checkmark and/or
star IS the verdict, which tells the user whether this run passed the Score
Threshold or not, and if this was a PB or not."

**Why.** Under T1 no toast carries a verdict, so the switch gates nothing.
It could be kept to turn the checks off instead. But an empty **Score
threshold percentage** already means no run is judged, today and on the new
page, so the switch would be a second control for one job.

**What it costs.** One combination goes: the threshold line on the chart
with no pass or miss shown anywhere. Today that is **Score threshold
overlay** on and the verdict switch off. Afterwards the line needs a
percentage, and a percentage means checks. The reverse still works: checks
without the line, by turning the overlay off.

**If the maintainer chooses differently:** the switch stays and gates the
check and the card's verdict in place of the toast's. The page hosts it,
and this proposal removes nothing from the panel.

## Problem

### What a run toast does today

The watchdog (the thread that imports each new stats file) queues one
message per run. The app shell drains that queue on every page, once a
second by default, and publishes the drained runs as one batch. Two things
read a batch:

- **The shell itself** decides the personal best celebration and sends its
  toast, on every page.
- **Scenario Performance** builds the run toast, inside the callback that
  rebuilds its chart (`generate_graph`).

So the run toast has conditions the celebration does not. It shows only
when all of these hold
([notifications.md](../specs/notifications.md#run-notifications)):

- Scenario Performance is the open page.
- The run is the batch's latest run of the scenario that page lands on:
  the scenario just played with **Follow newly played scenario** on, and
  the selected scenario otherwise.
- The run is live, meaning it reached the drain within 120 seconds plus one
  poll period of being imported.
- The run is not the one the celebration announces.
- **Run notifications** is on.

A run that clears those gets one of three toasts, all on the `run-verdict`
channel:

| Title | When | Message |
|---|---|---|
| Threshold passed (green) | Judged, and at or above the goal | `{scenario}: {score}, {pct}% of PB.` plus `Also your {Nth-best} at {sensitivity}.` when placed |
| Below threshold (yellow) | Judged, and below the goal | `{scenario}: {score}, {pct}% of PB (need {goal}%).` plus `Still your {Nth-best} at {sensitivity}.` when placed |
| New best score, New 2nd-best score (green) | Not judged, and placed | `{scenario}: {score} at {sensitivity}.` |

A run that is neither judged nor placed gets nothing.

**At the default settings, nearly every such run already gets a toast.** A
run is judged unless it is the first at its sensitivity or the scenario has
no positive best yet, and a first run at a sensitivity always places first.
So on that page, "a toast on every run" changes less than it sounds. What
is new is every other page, and the scenarios the page is not showing. What
goes is the verdict.

### What the Run History page changes

- **The verdict gets a lasting place.** Each run in the list carries a check
  when it passed the threshold and a star when it set a new PB. The
  latest-run card shows the newest run's percentage of the PB, and the
  maintainer agreed that it keeps a worded "Below threshold".
- **Every run is plotted.** The **Top N scores** control goes, and with it
  the N that placement is measured against.
- **The page that built run toasts is replaced.** Under the page proposal,
  Scenario Performance shrinks into Home and Run History is a new page at
  its own address. Either the old toast builder is carried to the new page,
  or the toast is built somewhere else.

### What the shell already does

The drain moved to the shell on 2026-09-02 so that a new personal best could
celebrate on every page. That decision left run toasts where they were: "the
product question that deferral protected, app-wide verdict toasts, stays
deferred, and run toasts remain page-built and page-scoped." T1 answers the
deferred question, with a toast that has no verdict.

### Verified facts

Checked on 2026-10-11 against `main` at `4272fbb`.

1. **Follow does not act when the page is opened.** The callback that
   follows a new run (`check_for_new_data`) is set never to run on mount,
   on purpose: a remount must not replay a batch it already handled
   ([2026-09-19](../decision_log.md#2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory)).
   So a player who arrives from another page sees the scenario the browser
   remembers, which need not be the one just played.
2. **A toast can hold a working link, and the element matters.** No toast in
   the app holds a link today. A scratch Dash app with the same stack
   (DashProxy, Dash Pages, the Mantine notification container) sent a toast
   holding three kinds of link to
   `?scenario=Whisphere Small & Slow 70% +#? x/y`, and headless Edge clicked
   each:

   | Element | The address in the page | After the click |
   |---|---|---|
   | `dcc.Link` | Encoded, as built | The page changed with no reload, the toast stayed, and the page received the whole name |
   | `dmc.Anchor` | Decoded: `&`, `%`, `+` and `#` are bare | The page changed with no reload, and received `Whisphere Small ` |
   | `html.A` | Encoded, as built | The whole app reloaded, and the toast was gone |

   The `dmc.Anchor` result is the behavior the Evxl link already works
   around.
3. **Scenario names hold those characters.** Of the 3,219 scenario names in
   the bundled benchmark library, 259 hold `&`, `#`, `+`, or `%`.
4. **A toast is an alert to assistive technology.** Mantine renders it with
   `role="alert"`. The link inside one is an ordinary anchor: Tab reaches
   it and Enter follows it. No screen reader was run.
5. **The shell can't read the Run notifications switch.** The switch is a
   control in one page's layout, remembered by Dash's own persistence. The
   2026-09-02 decision met the same wall: "the master switch's persisted
   value lives on the Scenario Performance page, so the shell would need a
   second mirror store to see it."
6. **The drain already owns the outputs a toast needs.**
   `publish_run_events` writes the notification container and the registry
   of toasts on screen, for the celebration.
7. **Runs are almost never detected together.** From the maintainer's stats
   folder, 9,135 runs through 2026-10-10, by the end time in each file's
   name. No two runs ended within one second of each other, so the default
   one-second poll finds each run alone. 384 runs (4.2%) were followed by
   another within a minute. With the poll slowed to one a minute, as
   Chromium does to a tab hidden for more than five minutes, about 116
   (1.3%) would have been found together with a newer run, taking the
   poll's timing as random. A window the game only covers is not hidden, in
   the browsers checked on 2026-09-28
   ([2026-09-02](../decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page)).
8. **A link to the address the page already holds does nothing.** On the
   scratch app of fact 2, with the page open at `?scenario=` and a name, a
   second toast's link to that same address left the page as it was. The
   router saw no change and did not build the page again. With the run's id
   added to the address, the second toast's link built the page again and
   delivered the whole name, with no reload and the toast still up. A page
   ignores a parameter its layout does not name, as every page does today.

## Design

Every choice in this section is the author's, and open to challenge.

### The toast

One shape, for every run that earns one:

- **Blue, with the chart icon** the placement toast used. Blue is the app's
  color for information whose action is optional.
- **The title,** "New run detected".
- **The scenario's name,** on a line of its own.
- **A link,** "Open in Run History", on the line below.
- **The nominal eight-second lifetime.**

It holds no score, percentage, sensitivity, or goal.

**The scenario name stays** although the page shows it too. It is the one
fact that says which run the app saw, and it says where the link goes.
"The message leads with the scenario" is a 2026-08-03 standard, and this
keeps it.

**Eight seconds, not until dismissed.** The celebration stays until
dismissed because a new PB is rare and was earned in a fullscreen game. A
toast on every run that had to be dismissed would be a chore. A player who
tabs back later than eight seconds finds the run on the page, and the
navbar leads there.

### Where it is built

The shell's drain (`publish_run_events`) builds the toast, in the same
response that publishes the batch and sends the celebration.

- **It runs on every page,** which a toast that points at one page needs.
- **Each run is seen exactly once.** The drain empties the queue, so a run
  it finds was never seen by an earlier drain. A second callback listening
  to the published batch would have to prove it never fires twice for one
  batch, on a page load or a remount.
- **The celebration decision is already in hand,** so the rule for a
  celebrated run is one condition, not a message between two callbacks.
- **The channel keeps one producer.** The 2026-08-31 mechanism relies on
  each channel having exactly one callback that emits it. The page's
  builder is deleted in the same change, so there are never two.

One response can now carry two toasts, the celebration and the plain one,
each on its own channel. The registry is still written one key at a time,
never as a whole, as the 2026-08-31 decision requires.

The chart callback loses its three notification outputs, on whichever page
holds it by then.

### The rules it keeps

Each holds today for the run toast and still holds:

- **Freshness.** Only a live run earns a toast: one that reached the drain
  within 120 seconds plus one poll period of being imported. Runs that
  piled up with no tab open announce nothing older than that. The window
  itself is unchanged.
- **One channel, replaced in place.** At most one run toast is on screen
  once a response has been applied. A newer run's toast replaces it and
  gets a full lifetime. This holds per browser and survives a change of
  page. The channel stays separate from `pb-celebration`, so a run toast
  lands beside a celebration and never replaces it.
- **A replacement is seen to arrive.** When a run lands while the last
  run's toast is still up, the new toast slides in as the old one fades
  out. The player sees that another run came in, although the two toasts
  may read the same. Every channel already behaves this way: it was
  measured on 2026-08-29 as a slide of about 135 ms and a crossfade of
  about 250 ms
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
  The maintainer asked on 2026-10-11 that it hold for this toast. It holds
  because the toast stays on that mechanism, and Testing checks it.
- **The Run notifications switch turns it off.** Off means no plain toast,
  on any page. It still does not reach the celebration, the failed-import
  toast, or any other toast.
- **Changing a setting never replays a run.** The drain reads both settings
  as state, so flipping one sends nothing.
- **One active tab.** Each drain's batch reaches one browser tab. With two
  tabs open, on any pages, the toast shows in whichever asks first.

### A batch of several runs

A drain nearly always finds one run (fact 7). It finds several when the
tab has been hidden long enough for Chromium to slow the poll to about one
a minute, or when the app is opened shortly after a few runs.

**One toast, for the batch's newest run.** The other runs earn none, as
today, and their rows on the page are their record. The title does not
count them. This is a judgment for the maintainer, so it is argued in
[T1](#t1-a-plain-toast-when-a-new-run-is-detected-on-every-page-with-no-verdict),
with the two other choices and what each costs.

### A new personal best

The celebration is unchanged: its toast, its copy, its channel, its
setting, and that it stays until dismissed. The rule that a celebrated run
gets no second toast moves from the page into the drain.

| The batch's newest live run | Celebration setting | Run notifications | On screen |
|---|---|---|---|
| Set a new PB | On | On or off | The celebration |
| Set a new PB | Off | On | The plain toast |
| Did not, and an earlier run in the batch did | On | On | Both, about different runs |
| Did not, and none did | Either | On | The plain toast |
| Any | Either | Off | No plain toast. The celebration follows its own setting |
| No live run in the batch | Either | Either | Nothing |

The third line is today's behavior too: one batch can put two toasts on
screen when they concern different runs.

### The link

**It names the scenario.** The address is Run History's own, plus
`?scenario=` and the name of the run's scenario. Fact 1 is the reason:
without the name, a player arriving from another page lands on whatever
scenario the browser remembers, under a toast that named a different one.
With it, the page opens on the scenario just played. The page treats that
as an ordinary choice and remembers it, as it does for a link from a
playlist's table (2026-09-19).

**It names the run too.** The address also carries `run=` and the run's id,
which is its stats file's name. The page does not read it. It is there so
that each run's toast links to an address the page is not already at,
because a link to the address the page already holds does nothing (fact 8).
Without it that case is an ordinary one. A toast opens scenario A. The
player picks B by hand, with Follow off, and plays A again. The new toast's
link would be the address still in the address bar, and B would stay on
screen. With the run's id the new link is a new address, so the page opens
on A, and R7's rule for the Playlist filter runs with it.

One case is left. The same toast's link, used a second time after a choice
made by hand, does nothing. It lasts the eight seconds that toast is up.

**It is a `dcc.Link`,** by fact 2. It is the only one of the three that
both keeps the encoded name and changes the page without reloading the app.

**One function builds it.** Scenario links to the page are built in one
place today (`scenario_home_href`), with each value encoded by
`urlencode`. The toast's link comes from the same place, so the address is
spelled once.

**It carries no playlist.** The shell does not know what the page's
Playlist filter holds. So the link relies on the page proposal's row R7:
a `?scenario=` link clears a filter that does not list the scenario. If R7
goes the other way, a toast for a scenario outside the filtered playlist
opens the page without selecting it.

**The address keeps its parameters,** so a reload applies the scenario
again over a later choice. That is the accepted behavior of every such link
(2026-09-19), and the navbar entry leads to the page with no parameter.

**Reaching it without a mouse.** The link is reachable by keyboard while
the toast is up (fact 4). The app's rule for a notice printed into a page
is that one holding a control is not an alert, because the alert role is
meant for text
([2026-08-30](../decision_log.md#2026-08-30-one-severity-color-language-for-inline-notices)).
A toast can't follow that rule: Mantine gives every toast the alert role.
This would be the first toast to hold a control. A screen reader should
read it as one alert, link text included, and none was run. The cost is
accepted because the link is never the only way to the page: the navbar
holds the same destination.

### While Run History is open

**The same toast shows.** The maintainer, 2026-10-10: "I could go either
way on this; maybe pick whichever option is simpler for now." The simpler
one is no exception.

What the link does there depends on Follow:

- **Follow off, another scenario on screen.** The link is one click to the
  scenario just played. This is the case where the toast earns its place on
  the page.
- **Follow on.** The page has already moved to that scenario. The link
  opens the page again on it, which resets what the page does not
  remember, such as an open Chart options panel. Here the toast only
  repeats the page.

**Not recommended now: hide it on Run History.** The drain would have to
read which page is open, and to be right in the Follow-off case it would
also have to read the page's Follow switch, which the shell can't see
(fact 5). That is two more inputs and a rule to explain, for a toast that
leaves in eight seconds. It can be added after the toast has been lived
with.

### The Run notifications setting

**The setting becomes a value the shell holds, and its switch moves to the
Settings page.** The maintainer chose the Settings page on 2026-10-11. Both
are what the celebration setting has had since
[2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page):

- **A browser-local store in the shell** holds one value, on or off, and
  starts on. Only the exact off value silences the toast. Anything else,
  including a store the browser has lost, shows it, which is the default.
- **The switch sits on the Settings page,** in a **Notifications** section
  of its own, directly above **Celebrations**. Like that section it is
  outside the Save form and takes effect at once. The switch takes its
  value from the store when the page opens, and writes each change back.
- **The Chart options panel loses its Notifications group.** With T3, the
  panel then holds no notification control.
- **The drain reads the store as state.**

**Why Settings.** The 2026-09-02 decision put the celebration control there
because "The behavior is app-wide, so the Chart options inspector on one
page is the wrong home". Under T1 the run toast is app-wide too. It shows
on Playlists and on Settings, and the control that silences it would
otherwise sit in one page's chart options. It is also the smaller build.
Settings already has the tick described below, so this switch is a second
control that tick fills, and no second page takes on its hazard.

**What it costs.** The switch leaves the page where most toasts are seen.
The celebration setting accepted the same cost.

The switch and the store can't simply feed each other: that is a cycle the
renderer refuses, and a page-mounted control writes its layout default into
the store on every visit. The 2026-09-02 decision records both hazards and
the fix, a one-shot tick that fills the control and gates the write. This
reuses that fix, and the tick the Settings page already has.

**It stays browser-local.** A key in `data/settings.json` was rejected for
the celebration on cost, since it forces that file's first schema
migration, and the reasoning holds here.

**A stored "off" is lost once.** The old switch's value is kept by Dash's
persistence under the old control, and the store does not read it. So a
browser that had turned run toasts off starts on again when this lands, and
shows them until the switch on Settings is turned off. If this lands in the
release that makes the page public, that is part of the one-time reset of
remembered controls the page proposal already describes. If it lands later,
it is a second reset, for this one switch.

### What leaves

- **The page-built toast:** its two builders, the placement wording, and
  the chart callback's notification outputs.
- **The Score threshold verdict switch** and its help text (T3). The value
  a browser stored for it is left behind, unused.
- **`nth_score`** (T2): from the run message, from the batch record, and
  the watchdog's count that fills it, with the debug line that prints it.

What stays in the run message, and why:

- **`score`, `scenario_previous_best`, `pace_constant`, and `run_id`:** the
  celebration reads them.
- **`is_new_sensitivity` and `sensitivity`:** the judging rule skips the
  first run at a sensitivity. Whether the page's card and check read them
  from the message or from the run store is the page proposal's choice.

The functions that judge a run against the threshold are not deleted. They
move with the verdict, to the page.

### Copy

Every string this design adds, edits, or removes. Reviewers are asked to
endorse or redline this block.

**Added**

| Where | String | Why |
|---|---|---|
| Toast title | `New run detected` | The maintainer's words. Sentence case. The Follow switch's help already says "when a new run is detected". |
| Toast, first line | `{scenario}` | A readout, so no period. It says which run and where the link goes. |
| Toast, link | `Open in Run History` | "Open", as **Open scenario table** and **Open Settings** say. "In", because it opens that scenario and not the page's last view. A page name keeps its capitals and takes no bold. |
| Settings page, section heading | `Notifications` | The Chart options group's heading, moved with its switch. A section heading keeps Title Case, as **Celebrations** below it does. |

**Edited**

| Where | Now | Becomes | Why |
|---|---|---|---|
| **Run notifications**, its explanation | A help tooltip in Chart options: `Controls threshold verdict and placement notifications for your runs. Personal best celebrations use their own setting.` | The description under the switch on Settings: `Shows a notification on every page when a new run is detected. Personal best celebrations use their own setting. Takes effect right away.` | Neither named kind exists any more. "On every page" is the new fact. The last sentence is the celebration description's own, for the same reason: this section applies at once, unlike the Save form above it. The label, `Run notifications`, is unchanged. |
| **Score threshold percentage** help text, last sentence | `Notifications judge a run against the personal best you had before the run.` | `A run is judged against the personal best you had before the run.` | No notification judges a run. The sentence names no surface, so it is true before and after the page ships its check. |
| README, Features | `**Run notifications**: a toast to compare your new run against your personal best.` | `**Run notifications**: a toast on every page when a new run is detected, with a link to its scenario on Run History.` | The comparison is on the page now. Still one line. |
| User guide, pace paragraph | `so the threshold line and the run notification both judge by it, and the notification says "% of PB pace".` | `so the threshold line and the check beside a run's score both judge by it, and the latest-run card says "% of PB pace".` | The notification no longer judges. "Check" and "latest-run card" follow the page proposal's Copy block, whatever it settles on. |
| User guide, troubleshooting | `Keep one Scenario Performance tab open at a time.` | `Keep one tab of this app open at a time.` | The toast now goes to whichever tab asks first, on any page. |

**Removed**

| String | Where it was |
|---|---|
| `Threshold passed`, `Below threshold` | Toast titles. The page proposal keeps a worded "Below threshold" on the latest-run card. |
| `New best score`, `New {Nth}-best score` | Toast titles |
| `{scenario}: {score}, {pct}% of PB.` and its `% of PB pace` twin | Toast message, pass |
| `{scenario}: {score}, {pct}% of PB (need {goal}%).` and its `% of PB pace` twin | Toast message, miss |
| `Also your {best or Nth-best} at {sensitivity}.`, `Still your {best or Nth-best} at {sensitivity}.` | Toast message, placement |
| `{scenario}: {score} at {sensitivity}.` | Toast message, placed and not judged |
| `Notifications` | Chart options group heading. It moves to the Settings page. |
| `Score threshold verdict` | Switch label |
| `Adds a pass or fail verdict to run notifications when the run can be judged against the score threshold. Needs **Run notifications** turned on.` | Its help text |

One more string goes untrue and is not this proposal's: the **Top N scores**
help text ends "A new run that lands in the top N also triggers a
notification." It leaves with its control, under the page proposal's row
R5.

Checked and left as it is: the Settings page's celebration description says
the celebration "doesn't depend on **Run notifications**", which stays
true. The switch it names is now the one above it.

### Terms

As the entries would stand in [the glossary](../glossary.md).

**Run notification (changed).**

> The toast that says the app detected a new run. It names the run's
> scenario and links to it on the Run History page, and it carries no
> verdict on the run. When a run earns one is in
> [notifications.md](../specs/notifications.md#run-notifications).
>
> - On screen: New run detected.
> - In code: `run-verdict`, the toast channel's name.
> - Not the personal best celebration, a separate response to a new PB.

**Top-N placement (removed).** The entry is deleted. Nothing on screen
states a placement, and `nth_score` no longer exists.

One other entry is corrected in the same change, with no change of meaning.
**Score threshold** says its verdict reads "Threshold passed or Below
threshold" and points to the notifications spec for how a run is judged.
Both follow the verdict to the page.

### Decisions this changes

Each entry keeps its text and gains a dated note. None is erased.

| Entry | What this supersedes | What stands |
|---|---|---|
| [2026-08-03, One Quiet Notification Layer](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy) | For run toasts: the title carries the verdict; a run that earns neither emits nothing; the threshold verdict headlines and the placement trails; a failing verdict names its target; sensitivity as a trailing qualifier. Its "already visible somewhere" test gains the run toast as a named exception. | The one delivery path. The routing policy for every other event. Background threads never driving the UI. The four behaviors of the run toast's channel. "The message leads with the scenario." |
| [2026-07-08, Judge Against The Previous PB](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb) | The surface: no notification judges a run. | The rule and its exact comparison, now for the check and the card. |
| [2026-08-21, Run Notifications Have A Master Switch](../decision_log.md#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed) | The verdict switch and its four combinations (T3). What the master switch gates: one plain toast. Where it lives: its Notifications group leaves Chart options for the Settings page. That it is stored by Dash persistence. Its deferral of app-wide run toasts. | What the master switch does not gate. That flipping it rebuilds nothing. That it is browser-local, with `settings.json` and `config.toml` rejected. |
| [2026-09-02, A New Personal Best Celebrates On Every Page](../decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page) | "Run toasts remain page-built and page-scoped", and the deferred question of app-wide run toasts. The page's part in the coalescing rule: the shell now picks the batch's newest run, whatever its scenario. | The celebration in full. One notification per run at most. The two settings staying independent. |
| [2026-10-05, Time-Scored Scenarios Are Measured By Pace](../decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace) | Where the third of its five surfaces lives: the threshold verdict's "% of PB pace" is on the page, not in a toast. Top N placement leaves its list of things that order scores. | Every formula, the detection, and the other four surfaces. |
| [2026-08-09, The Graph Page Is Scenario Performance](../decision_log.md#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options) | Its list of the Score Threshold group's controls, which names the verdict switch. | The rest of the entry, as far as this proposal goes. The page proposal reverses its name ruling separately. |

Three more entries mention strings or rules that go, and get a one-line
note: the
[2026-09-14 copy entry](../decision_log.md#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)
(the run-toast strings it set), the
[2026-09-22 README entry](../decision_log.md#2026-09-22-the-readme-stops-explaining-how-the-installer-works)
(the Run notifications line, and that every run now notifies), and the
[2026-09-11 sensitivity entry](../decision_log.md#2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi)
(placement within the normalized group).

Two decisions are relied on and not changed. One is the
[2026-08-31 toast identity decision](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry).
The other is the
[2026-09-02 celebration setting decision](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page),
whose reason for the Settings page now covers a second control. It gains a
note that the celebration select is no longer the only browser-local
control on that page.

### Alternatives rejected

- **A second shell callback that listens to the batch.** It leaves the
  drain untouched, but it must be shown never to fire twice for one batch.
  The drain needs no such proof, because it empties the queue.
- **Keeping the switch in Chart options.** It stays where players have
  found it, on the page where most toasts show. It also leaves an app-wide
  setting in one page's chart panel, and puts a second copy of the store's
  wiring and its hazard on that page.
- **A mirror store beside a persisted switch.** The switch would keep
  Dash's persistence and copy its value into a shell store. Then two stored
  values can disagree: after an upgrade, a browser whose switch says off
  has a store that still says on, until the page is next opened. The
  switch would read off while toasts showed.
- **Reading Dash's persistence keys from the browser.** It depends on the
  renderer's private key format, which the 2026-09-19 decision already
  declined to rely on.
- **A link with no scenario.** By fact 1 it opens the wrong scenario from
  any other page.
- **Accepting a link that sometimes does nothing.** With Follow off, the
  jump to the scenario just played is the one thing the toast adds on Run
  History, and that is exactly where a link without the run's id fails.
- **The page removing the parameter once it has applied it.** That is the
  page proposal's to weigh, since it changes an accepted behavior of
  2026-09-19. It is also not known to close the case: the router does not
  see an address rewritten behind it, so a later link to the old address
  may still read as no change. Not probed.
- **The verdict and the link together.** It keeps the toast useful at a
  glance, and keeps the duplicate, the N, and the switch that T1 to T3
  remove. It is not what "barebones" asked for.
- **A count for a batch,** and **hiding the toast on Run History.** Both
  are above.

### Beyond the outline, optional

Neither of these is part of the proposal. Each is listed so the maintainer
can take or leave it, and neither is needed for T1 to T3.

- **Rename the channel** from `run-verdict` to `run-notification`. The toast
  holds no verdict, and the glossary would then give the code word its
  term's name. The cost is a rename across the helper, the spec's
  inventory, and three test files, for a name no user sees.
- **Give the celebration toast the same link.** A new PB is the run a
  player most wants to open, and under T1 its toast is the one without a
  link. The cost is a change to a toast the maintainer said can stay as it
  is.

A third item was here: moving the **Run notifications** switch to the
Settings page. The maintainer chose it on 2026-10-11, and it is now part of
the design.

## Delivery plan

One implementation PR. This is intent, not a contract.

**It lands in the page's going-public PR, or after it, never before.**
Until the page is public the verdict has nowhere else to live.

**What it needs from the page:**

- **Its address** (R2) and **its name** (R1), for the link.
- **The `?scenario=` link** carried over, and row R7's rule for a scenario
  the filter does not list.
- **A parameter it does not read, tolerated.** The link carries `run=`. The
  old page's layout accepts parameters it does not name, and the new page's
  has to as well.
- **The check, the star, and the latest-run card** on screen, so the
  verdict is somewhere before the toast drops it.
- **The judging functions** already moved to the page. This PR deletes only
  the toast builders.

**What it holds:**

- **The shell:** the toast in the drain, and the setting's store.
- **The Settings page:** the Notifications section and its switch.
- **The Chart options panel:** without its Notifications group.
- **The removals** under [What leaves](#what-leaves).
- **The docs:** the notifications spec's Run notifications section and its
  inventory row; the Chart options statements in the page's spec; the
  settings spec, which gains the Notifications section; the glossary, from
  [Terms](#terms); one decision-log entry and the notes
  under [Decisions this changes](#decisions-this-changes); the product
  inventory's Run notifications paragraph; the README line and the two
  user guide lines from [Copy](#copy); the architecture doc's lines on the
  run message and the two notification controls. It deletes this file.
- **The roadmap** entry for the milestone belongs to the page's
  going-public PR. This PR adds its number there.

**Who states the judging rule.** The notifications spec holds it today:
when a run is judged, the comparison, and the two display caps. The page's
spec takes it when the check ships, and this PR removes what is left in the
notifications spec.

**The fallback is the page's.** If this proposal is still open when the
page is ready, the page goes public with today's toast and N fixed at 5,
and this change follows. The page proposal designs that.

Recommended session: `claude-opus-5-5` at high. It touches `source/`, so
merging it cuts a release.

## Out of scope

- **The personal best celebration.** Unchanged, including that its toast
  has no link.
- **Playing the celebration's animation only on first opening Run
  History.** The maintainer's idea of 2026-10-10 for later: "we don't have
  to tackle this now."
- **The check, the star, and the latest-run card,** and the rule for a
  check on a past run. The page proposal.
- **The Top N scores control and the chart.** The page proposal, row R5.
- **The watchdog's pass or fail lines in the debug log.** They go when the
  page goes public, under the page proposal.
- **How long a run stays fresh.** The window is unchanged. Whether the
  celebration deserves a longer one is on the roadmap.
- **Hiding the toast on Run History, and a count for a batch.** Argued in
  Design, and open to revisit after use.

## Testing

For the implementation PR:

- **The drain, as unit tests.** One plain toast for a batch with a live
  run, for its newest run. None when every run is stale. None when the
  setting is off, with the celebration still sent. None for a celebrated
  newest run, and both toasts when an earlier run is the celebrated one.
  The plain toast for a new PB when the celebration setting is off. The
  registry patch holds both keys when both toasts go out.
- **The link.** It is a `dcc.Link`. Its address is the page's own plus the
  encoded name and the run's id, checked with a name that holds `&`, `%`,
  `+`, and `#`. Two runs of one scenario give two different addresses.
- **The setting.** The write is refused before the filling tick, with the
  tick's count at 0 and at none. An unknown stored value shows the toast.
  The Settings layout holds the switch, and the Chart options panel holds
  no Notifications group.
- **What is gone.** The tests for the verdict and placement toasts are
  removed. The tests for the judging functions move with those functions.
- **The channel.** `tests/test_home_run_verdict_lifetime.py` stays as the
  guard on replace-in-place behavior, which does not change.
- **In a browser, with a scratch stats folder.** A run dropped while the
  Playlists page is open shows the toast, and its link opens Run History on
  that scenario with the toast still up. The same with a scenario name
  that holds `&` and `%`. With **Run notifications** turned off on the
  Settings page, the next run shows nothing, with no Save. A new PB shows
  the celebration alone. A second run inside the first toast's eight
  seconds replaces it with the entry animation, and one toast is left on
  screen. After a toast's link has opened scenario A, pick B by hand with
  Follow off and land another run of A: the new toast's link opens A again,
  with no reload. In Edge and in Firefox.
- **The gates:** the five standard local checks in AGENTS.md.

For this proposal PR: `uv run pytest tests/test_docs.py` and
`git diff --check`.
