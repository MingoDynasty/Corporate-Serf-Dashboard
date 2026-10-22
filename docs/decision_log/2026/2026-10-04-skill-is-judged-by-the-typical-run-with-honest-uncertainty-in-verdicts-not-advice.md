# 2026-10-04: Skill Is Judged By The Typical Run, With Honest Uncertainty, In Verdicts Not Advice

Status: Accepted

The app's skill judgments are heading toward typical performance while a personal best remains an achievement.
A judgment the runs cannot support stays unknown, and the app states findings without prescribing training.
The shared score summary now gives later features one definition to build on.

**Superseded in part (2026-10-21).** The Terms passage's working name is now [Typical score](2026-10-15-typical-score-uses-the-last-twenty-runs-and-counts-every-version.md) on screen, in the glossary and in code. D1, D2 and D3 stand; defining the figure does not authorize a later judgment to use a dimmed value without choosing its evidence bar.

**Ruling.** Ruled (user) 2026-10-04, in chat, after both reviewers endorsed
each row:
[rows D1 to D5 of PR #327](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327#issuecomment-5986985763)
as recommended, with D3's evidence bar as amended in review. D5, what the
roadmap's Future list holds, is recorded in the roadmap alone.

The rules themselves are in the roadmap's
[Guiding principles](../../roadmap.md#guiding-principles). This entry holds what
the roadmap doesn't: the reasons, the evidence and its limits, and the
options set aside.

**D1, the typical run.** Judgments about skill, meaning where the player is
weak, where their level stands, and whether they're improving, move toward
the typical run. The personal best stays the achievement: KovaaK's ranks it,
the app celebrates it, and the shipped Rank, Next Rank, Position, and
Percentile columns keep reporting it. The two answer different questions, how
a scenario usually plays and what the player has reached, so the app keeps
both. Judging skill by the personal best alone was rejected. A personal best
is one run, so a lucky one can rank a consistent scenario as weaker than a
spiky one that usually plays worse. It also only rises, so it can't show a
decline, and after one lucky run it reads as a plateau when there isn't one.
What counts as the typical run (the window, the run count, the warm-up rule)
is the Run History proposal's to set. *(Moved 2026-10-11: Run History
neither defines nor shows the typical run, and its definition goes to a
proposal of its own, written before the first feature that judges by it. See
row S4 of
[A Session Ends After A Break Of More Than 30 Minutes](2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md).)*

**D1's evidence, and its limits.** The evidence is one player's history,
checked on 2026-09-27. Ordering scenarios against each other by the typical
run tracked the level the next time each scenario was played better than
ordering by personal best: a rank correlation of 0.62 against 0.51, over
eight sessions. Within one scenario the two tied, with an error spread of
5.5% against 5.6% over 267 predictions across 69 scenarios, one per scenario
per session. Neither comparison shows that practicing in that order causes
more learning. A re-check of the ordering is due around 2026-10-09, and the
columns that would rank weakness this way wait for it. The research on
learning and performance supports judging learning apart from the scores
during a session. It doesn't validate a particular window or warm-up rule for
this app.

**D2, honest uncertainty.** Unknown isn't weak. A judgment with too little
behind it says so, and a scenario isn't ranked weak or strong until it has
enough: unknown rows form a group of their own and are never ranked among the
known ones. A figure that can only be a minimum is labelled one wherever it's
shown, such as time spent in runs, which leaves out the time between runs and
any attempt that wrote no stats file. An estimate is shown no more precisely
than it's known. Under-sampling is the common case: on 2026-09-25, 23 of the
39 scenarios in the maintainer's benchmark had fewer than 10 lifetime runs.
How much is enough isn't set here, and it isn't only a run count: the runs
also have to be comparable, and the estimate's model has to hold.

**D3, verdicts, not advice.** The app states facts and verdicts: the typical
run, a trend, a rank-up chance, "unknown", and whether a bar the player set,
such as the score threshold, was met. A result measured against something the
player set is still a verdict. Telling the player what to play or when to
stop is advice, and the app doesn't give it. The rule covers training
decisions only, so a notice that asks for a setting isn't advice. Verdicts
only is the simplest option and the easiest to reverse: adding advice later
is cheap, and taking away advice people rely on is not. It keeps one player's
regimen from being imposed on every user, and it matches what the app shows
today with one exception, which it retires. The cost is accepted: a "leave
now or keep going" line shrinks to the facts the player's own rule reads.

**The line D3 retires.** A run that passes the score threshold without
placing gets a toast that ends "Ready to move on.", which tells the player
when to stop. The
[2026-09-14 copy entry](2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md)
kept that line under its D4, ruled 2026-09-12. By the bar set out here it's
a default rule the app vouches for, and no check came before it. Ruled
(user) 2026-10-04,
[in review](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327#discussion_r4179636701):
the line is retired. That toast ends at the fact, and the placed variant and
every other toast are unchanged. D3 supersedes that D4 in part: its other
half, which dropped "Keep grinding...", stands. The string changed in
PR #341,
[a PR of its own](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327#discussion_r4179646591),
as also ruled on 2026-10-04. That PR updated the notifications spec and the
pace proposal's Copy block with it, and added the supersession note to the
2026-09-14 entry.

Two options were set aside for now. Rules the player sets would add rule
semantics and a settings surface, and a default rule is advice by another
name. A built-in training method makes the strongest claim, and published
research supports general practice principles but no single aim-training
method.

**What would move D3.** Any move past verdicts takes a decision of its own.
What else it takes depends on what the app would be claiming.

- A rule the player writes, off until they write it and worded as theirs,
  claims nothing about training. It's an ordinary product decision: whether
  the convenience is worth a settings surface and the risk that it reads as
  the app's advice. The verdicts it reads ship first, and the player can
  override it and turn it off.
- A default rule or a built-in method is advice the app vouches for, so it
  takes strong evidence first. That means a check declared before its data
  comes in, measuring the benefit the rule claims, on results after the
  session rather than during it. A claim about learning needs retained
  performance, not a score from the same session.
- One player's results justify an opt-in experiment for that player. A method
  shipped to everyone needs evidence across players and tasks. The app
  collects none, so it would come from voluntary testing, results users
  supply, or published research.

**D4, Run history builds sessions first.** Sessions, and the visits inside
them, are built before either history view, as the foundation the views and
later features share. This reverses two durable decisions in the
[Run History proposal](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md): "raw timestamps
first; sessions are a later quality-of-life layer", and the view order that
followed from it. Both are marked superseded there, with their text kept.
Nearly every planned feature needs sessions, and splitting the runs into them
is one pure pass over runs the app already holds in time order. Which view
ships first is open, for the proposal's rewrite to decide. The roadmap
carries the milestone's reasons and the Future list, which is planned work in
no particular order.

**Terms.** Typical run, visit, and rank-up chance are working words here, not
[glossary](../../glossary.md) terms: nothing ships them yet. The proposal that
ships each one names and defines it in its Terms block, and may rename it.
*(2026-10-11: visit now has a [glossary entry](../../glossary.md#visit), under the
same word. See
[A Session Ends After A Break Of More Than 30 Minutes](2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md).)*
