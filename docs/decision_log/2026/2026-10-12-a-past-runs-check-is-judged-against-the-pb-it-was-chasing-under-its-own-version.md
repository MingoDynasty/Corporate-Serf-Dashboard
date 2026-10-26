# 2026-10-12: A Past Run's Check Is Judged Against The PB It Was Chasing, Under Its Own Version

Status: Accepted

Run History marks each run in its list with a check when the run passed the
score threshold and a star when it was a new personal best, and a card at the
top reports the latest run the same way. A check means the run passed when it
was played, against the personal best it was chasing then, so a later record
takes no check away. On a scenario scored by time, a past run is measured
under its own version of the scenario and never under the version a newer run
names. Changing the threshold percentage re-marks every run at once, because
the percentage in force when an old run was played was never recorded.

**Superseded in part (2026-10-15).** [T4's age rule](2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md)
makes the latest-run card's time relative, with its exact time on hover and
focus. Its time-of-day or date display below is historical. The card still
reports the last run played on whatever scenario, and every rule of its
marks and comparisons stands.

**Superseded in part (2026-10-18).** [The latest-run card's rule](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md)
makes the card report the selected scenario's latest run, not the last run
played on whatever scenario, and removes its scenario button with the script
that handed keyboard focus on. Its third line takes two lines and names an
older session. A late run "leaves the card alone, since the card reports the
newest run" now holds per scenario: a late run on the selected scenario
becomes the card's run once it is newer than that scenario's latest. The
card's one height through every state stands, at 135 px where it was 132,
because its tallest state gained the fourth line. The marks, the badge, the
second line, and a past run's pace basis stand.

**Superseded in part (2026-10-25).** [The card ends with the run's cm/360 and accuracy](2026-10-25-the-latest-run-card-ends-with-the-runs-cm360-and-accuracy.md):
the second line holds the PB comparison alone, and the run's accuracy moves
to the card's last line, beside its cm/360. Where there is no comparison the
line is absent, where it read the accuracy alone. The marks, the badge, the
comparison's words and caps, and a past run's pace basis stand.

**Superseded in part (2026-10-25).** [The card measures the run against the typical score at session start](2026-10-25-the-latest-run-card-measures-the-run-against-the-typical-score-at-session-start.md):
on a run that isn't a new PB, the second line opens with the run's distance
from the typical score as it stood when its session began, before the PB
comparison. The marks, the badge, the PB comparison's words and caps, and a
past run's pace basis stand.

**Rulings.** By the maintainer, 2026-10-12, on
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356):
"I ratify the proposal." Nothing here was a numbered row. It is the
author-owned design of the marks, of a past run's pace basis, and of the
latest-run card, which the ratification covered. The maintainer had worked
three of its consequences through on 2026-10-10, quoted below. The marks were
built in
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371) and
the card in
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372).
The rules as the app applies them are in run_history.md, under
[Marks](../../specs/run_history.md#marks-the-check-and-the-star) and
[The latest-run card](../../specs/run_history.md#the-latest-run-card). This
entry holds the reasons, the worked example, and the options set aside.

**Three words.** The score threshold is a percentage of the personal best
that a run has to reach, set by the player in Chart options. The PB a run was
chasing is the scenario's best score before that run, at any sensitivity. A
version of a scenario is the one a run's stats file names in its `Hash:`
line.

**Two marks.** Two facts about a run are drawn beside its score in the run
list, and worded as the card's badge.

- **Threshold passed,** a check. The run met the score threshold, judged as
  the run toast judges a run: against the PB it was chasing
  ([2026-07-08](2026-07-08-judge-score-threshold-notifications-against-the-previous-pb.md)).
  It is judged by pace where the app measures pace on the run's own version
  of the scenario.
- **New PB,** a star: the rule the chart's stars use. A run can carry both.

Both are verdicts against a bar the player set or a record they hold, and
neither is advice, which is what the
[2026-10-04 principles](2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
allow. This carries the Marks section of
[PR #351](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351),
less its line about a switch.

**Three consequences,** which the maintainer worked through on 2026-10-10:

- **A later PB removes no check.** A check means "passed when it was
  played", the way a star means "was the PB when it was played". "I think
  that is a good rule." The cost: the chart's threshold line is drawn at the
  current PB, so an old run can carry a check and sit below today's line.
- **A change to the percentage re-marks every run, at once.** The percentage
  in force when an old run was played was never recorded. It lives only in
  the browser, and the watchdog, the thread that imports each new stats
  file, can't read it. "Sounds good." So checks are per browser, as toasts
  are.
- **No switch gates a mark.** An empty percentage is the one way to turn
  checks off.

One more thing re-marks runs, and it is not from that discussion: new
evidence about whether a run's version of the scenario is time-scored. It is
under **A past run's pace basis**.

**The maintainer's worked example.** The PB is 100. Runs A to E are played
in order at one sensitivity.

| Run | Score | Chasing | At 90% | At 99% |
|---|---|---|---|---|
| A | 85 | 100 | no check | no check |
| B | 95 | 100 | check | no check |
| C | 120 | 100 | check and star | check and star |
| D | 100 | 120 | no check | no check |
| E | 110 | 120 | check | no check |

Raising the percentage to 99 takes the check from B and E, and setting it
back returns both. C's new PB never touches B's check, because B is compared
with 100, not 120. The field has no maximum. Above 100 percent a run has to
beat the PB it was chasing by that margin, so every check then sits on a run
that is also a new PB: at 110 percent C keeps its check and no other run has
one.

**A past run's pace basis.** On a time-scored scenario the app compares
times and not scores, which is pace
([2026-10-05](2026-10-05-time-scored-scenarios-are-measured-by-pace.md)).
That entry lets a scenario's newest run name the version that every
comparison is judged under. That fits a toast, which only ever judges the
newest run. Applied as it stands to an old run, it would let a later run on
another version change the old run's check. An old run that missed by pace
would stop counting as a pace comparison, be judged by score, and pass, with
no change to the run, to the PB it was chasing, or to the percentage. So a
past run is judged under its own version:

- **The version is the run's own:** the one its stats file names in
  `Hash:`.
- **Whether that version is time-scored, and its constant, is one answer
  for the whole version,** taken from the newest performance file of that
  version that can answer. For the scenario's current version that is the
  2026-10-05 rule unchanged. The answer is not fixed: a later run of the
  same version can bring a file that answers differently.
- **The comparison is by pace** only when the PB the run was chasing was set
  on the same version and both times are positive. Otherwise it is by
  score.
- **A run is judged by score** when its file names no version, or when no
  performance file of its version can answer.

So a run on a later version changes no earlier check. What can still move
an old check is new evidence about its own version, in either direction:

- **The first performance file of a version that can answer** turns that
  version's earlier runs to pace.
- **A later file of the same version that answers differently** judges
  every run of that version again. A file that shows no countdown turns
  them back to score, as it turns the app's other pace surfaces back. So an
  old run that missed by pace can come to pass by score, and the reverse,
  with no change to the run, the PB it was chasing, or the percentage.

The app's other pace surfaces move at the same moments, because they read
the same answer. So a check holds to the PB the run was chasing when it was
played, and to the measure the app now uses for the run's version. The
latest run is judged as its toast was when it landed, because the newest
run names its own version and its own file is tried first. A later file of
that version can then move its check, as it can any other.

Two alternatives were set aside:

- **Keeping a version's first answer for good.** An old check would then
  disagree with the toast and the threshold line on a later run of the same
  version, and the design would have had to say when that first answer is
  set and when it is rebuilt.
- **Judging each run by what the app knew on the day it was played.** It
  would keep score verdicts on runs the app now knows were time-scored,
  beside pace verdicts on later runs of the same version, and it would
  parse one performance file per listed run.

A mutation was run on this rule in PR #371. With a past run judged under the
newest run's version, one test fails and only it: on real stats and
performance files, the run that missed by pace reads as a pass by score.

**Not judged.** Three kinds of run get no verdict, as the run toast already
had it:

- Every run, while the Score threshold percentage is empty.
- A scenario's first run, and the first run at a new sensitivity.
- A run compared by score whose PB before it was zero or less, which leaves
  no percentage to judge by.

That is about the threshold only. A star never depends on it: the first run
at a new sensitivity can be a new PB and carry one. A row with no verdict
has no check, and neither does a judged run that missed. The column shows
both as blank, and the cell's hover and accessible text give the one reason
that applies, taking the first that fits in the order above. The glance
answers "which runs passed", and the reason is one hover away. The card has
room, so it words a miss.

Every state together. The last column is the card's percentage of the PB
the run was chasing.

| The run | Check | Star | Card badge | Card percentage |
|---|---|---|---|---|
| Judged, and passed | check | if a new PB | New PB if one, else Threshold passed | shown |
| Judged, and missed | none, "Below threshold" | if a new PB | New PB if one, else Below threshold | shown |
| Any run while the percentage is empty | none, no percentage is set | if a new PB | New PB if one, else none | shown where one exists |
| A scenario's first run | none, a first run | never | none | none |
| The first run at a new sensitivity | none, a first run | if a new PB | New PB if one, else none | shown |
| Compared by score, with a PB before it of zero or less | none, no percentage to judge by | if a new PB | New PB if one, else none | none. A new PB names the previous best |

A judged miss can be a new PB only with the percentage above 100. A
comparison by pace needs only positive times, so a time-scored PB of zero or
less is still judged.

The three "Not judged" reasons each say why, because unknown isn't a miss.
The first-run reason names the threshold and not the personal best, because
such a run can still be a new PB and carry a star in the same cell.

**The percentage field sends on Enter or on leaving it.** It used to send
every keystroke, so typing 90 over 95 passed through 9, and every check on
the page would have flickered through it. The option was read in the
component's documentation and then checked in a browser by PR #371: typing
sends nothing, and on Enter the checks and the threshold line move together,
in Edge and Firefox. The field's help text lost its claim that only
notifications judge a run. Its last sentence reads `A run is judged against
the personal best you had before the run.` The Run toasts proposal words the
sentence the same way, so it is true whichever change lands first.

**One function judges.** The toast and the check call the same function, and
a past run's three facts, the PB it was chasing, whether it was the first at
its sensitivity, and its pace constant, are worked out from the run store
because no message carries them. Nothing about a mark is stored.

**Where a toast and a check can differ.** The toast judges a landed run
against the run store's high score when the run lands. The list's check and
the card's badge judge it against the PB before the run in play order. They
differ only for a run that lands older than the store's newest, such as a
stats file copied in. Such a run gets its toast and leaves the card alone,
since the card reports the newest run. PR #371's second reviewer asked for
this to be written down.

**The latest-run card.** The card reports the last run played, whatever
scenario is selected, and updates on every batch of new runs. "Latest-run
card" is the glossary's term. On screen the card has no title, and its first
line starts "Latest run".

- **It is worked out from the run store, never from the message a new run
  arrives in.** So the card is right on a page load with no new run, and a
  past run's check needs nothing that was not kept. The Run toasts proposal
  left that choice to this design. The same holds for the marks.
- **The first line** reads "Latest run", the run's time, and its scenario.
  "Latest" and not "Last", which reads as final. The time is a time of day
  for a run played today and carries the date otherwise.
- **The scenario's name is a button, where the proposal said a link.** While
  another scenario is selected, a click selects the run's scenario in place,
  under
  [the filter-clearing rule](2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md),
  and goes nowhere, which is what a button is. A link to the page's own
  address with the scenario in it would have Dash draw the whole page again,
  and a link to the address the page already holds does nothing, so a second
  click on the same run's name would be dead. It is drawn as the app draws a
  link, its accessible name is `Show {scenario}`, and a screen reader calls
  it a button. The button leaves the page once its scenario is selected,
  which dropped keyboard focus as PR #372 built it. Both review seats noted
  it, and the pull request that made the page public hands focus to the
  Selected scenario dropdown once the button has gone. It does so only after
  a press from the keyboard: a click with the mouse loses nothing by losing
  focus, and focus on a searchable dropdown opens its list.
- **One badge beside the score.** A new PB shows New PB, whether or not the
  run was judged. Otherwise a judged run shows Threshold passed or Below
  threshold, and an unjudged run shows no badge. The maintainer agreed the
  card keeps a worded "Below threshold": "Yes." The badges are words alone,
  yellow, green, and gray in that order. Yellow for a miss, as its toast is,
  would sit beside a yellow New PB.
- **The second line** gives the run's percentage of the PB it was chasing,
  and its accuracy. A new PB says how far it beat the previous best instead.
  The percentage is a fact about the run, so it shows whether or not the run
  was judged, and an empty threshold doesn't hide it. Two kinds of run have
  none, and show the accuracy alone: a scenario's first run, and a run that
  is not a new PB and is compared by score with a PB of zero or less. A new
  PB's previous best is formatted as the list formats a score, where the
  celebration toast prints two decimals.
- **The percentage follows the toast's rules:** the same PB, the same pace
  rule, and the same two display caps. The toast holds a miss one tenth
  under its goal as printed, and holds a run below the PB at 99.9%. A run
  nothing judges has no goal, so only the second applies to it.
- **The second line's wording is the toasts' own.** `{pct}% of PB` is the
  run toast's wording, and `of PB pace` adds the one word that says which
  measure was used. A new PB's `Up {pct}% on your previous best of
  {previous}`, its `{pct}% faster than your previous best of {previous}` by
  pace, and its `Your previous best was {previous}` over a previous best of
  zero or less are the celebration toast's sentences, as readout fragments.
- **The third line** gives which run of the scenario this is in its session,
  and the clock time spent on the scenario in that session. Once the session
  has ended the line says "last session", because "this session" would be
  untrue. The time is the sum of the scenario's visits in the session, each
  from its first run's start to its last run's end, so it includes the
  breaks between a visit's runs. A visit is consecutive runs on one scenario
  within a session.
- **Where that time can't be known, the line says so and keeps the run's
  number.** The time is unknown when the first run of any of those visits
  has no usable start. The sessions rules then count that visit from the
  run's end, so a visit of one long run would add nothing and the card would
  read `<1 min`. The card never shows a number in that case.
- **One height through every state,** so the page doesn't jump: 132 px. In
  its longest wording, a new PB by pace over a six-digit score, the second
  line takes two lines in a 385 px card, and the height is sized so that
  fits. With no run in the store the card says so, at the same height.
- **The server builds it, and the page load fills it.** The layout knows
  neither the selected scenario nor the stored percentage. Drawn at once,
  the card could show a verdict for a moment and then change it.

**The watchdog's per-run lines left the debug log.** The watchdog used to
log every run's distance from the PB and whether it passed a fixed 95%. The
run list is the record those lines stood in for, and they were removed when
the page went public.

**What this changes in older entries.** Each keeps its text and gains a
dated note.

- The 2026-10-05 pace entry: the watchdog's session lines leave its list of
  surfaces, the check and the card join it, and a past run is judged under
  its own version, not the newest run's. The pace rule stands.
- [2026-07-11, timestamps](2026-07-11-humanize-the-absolute-timestamp-format.md):
  the card's time drops the year while it is this year's. The format and
  its rules stand.

Proposed in
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
which merged as `a65f72d`. Shipped in
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371) and
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372),
hidden, and made public in
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373),
which removed the watchdog's lines. The proposal file,
`docs/proposals/run_history_proposal.md`, is deleted, and git history keeps
it.
