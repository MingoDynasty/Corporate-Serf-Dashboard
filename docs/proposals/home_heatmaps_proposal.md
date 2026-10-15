# Home Heatmaps Proposal

Status: Proposed
Date: 2026-10-15

## TL;DR

Home, the page the app opens on, shows first-time setup and one line of
counts, and nothing about when or how much the player has played. This
proposal adds an Activity card under that line with two heatmaps: a calendar
of days shaded by time in runs, and a grid of the hours of the week. One
dropdown picks the period for both, either the last 12 months or a year with
runs. Nothing here is ratified, and the shading rule is left for the
reviewers to debate, as the maintainer asked.

## Decisions needed

Six rows, HM1 to HM6. **Nothing in this proposal is ratified.** Each row
quotes the maintainer's lean with its date, argues it, recommends an answer,
and says what choosing otherwise would cost. A lean is not a ruling, and
reviewers are asked to challenge every row, every author-owned choice in
[Design](#design), and the [Copy](#copy) block. The card as a player meets it
is at the top of Design, in [What the player sees](#what-the-player-sees);
reading it first makes the rows concrete.

The scope is the maintainer's direction of 2026-10-15: "I would like to focus
this chat session on heatmaps for the Home page, and save the other ideas for
a separate proposal." The other ideas are listed in
[Out of scope](#out-of-scope), and none is designed here.

Three things are ratified already, and this proposal builds on them without
reopening them:

- **Home at `/`, its setup surfaces, and its stats line**
  ([2026-10-12](../decision_log/2026/2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md)).
  The card goes under them.
- **The 30-minute session rule**
  ([2026-10-11](../decision_log/2026/2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md)).
  Nothing here changes what a session is.
- **Run History's day ranges** ([the chart](../specs/run_history.md#the-chart)):
  a range of N days is N calendar dates counting today, from local midnight.
  The card's "Last 12 months" is that same range.

### HM1. Home gets an Activity card with both heatmaps under one period dropdown

Status: Open. The maintainer's lean, 2026-10-14, on the first mockup: "I
think the 12 weeks bar chart looks ugly. I do like both the Year calendar and
the Hour x weekday heatmaps." The calendar "should probably have some
controls to change the year, for people who have years of data." Then
2026-10-15: "I'm thinking a dropdown might be better since eventually a
player will have so many years accumulated that we will run out of space to
have dedicated buttons per year."

The material consequence: Home gains its first content beyond setup and the
stats line, and its first control.

**Recommendation: an Activity card directly under the stats line, as wide as
the page. Its title row holds `Activity` and a Range dropdown, which offers
`Last 12 months` and then every calendar year that has runs, newest first,
the current year included. The card opens on `Last 12 months` at every load,
and the browser doesn't remember the choice. A summary line for the period
sits under the title. Under it are the calendar of days and the grid of the
hours of the week, side by side where the card is wide enough and stacked
where it isn't. Both heatmaps and the summary follow the dropdown.**

- **Under the stats line.** The setup surfaces and the stats line are Home's
  ratified opening, so the card comes after them. It is the first thing on
  the page that changes with play.
- **One dropdown for both heatmaps.** The maintainer asked for a dropdown,
  and a player with years of history would run out of room for buttons. An
  hour grid with a period of its own would need a second control and could
  show a different period from the calendar beside it. No product the
  research found gives an hour grid its own picker.
- **The summary follows the dropdown.** LeetCode and Monkeytype work their
  summaries out again for the period picked. Codeforces doesn't, and its
  summary stops matching the calendar under it.
- **"Last 12 months" means what it means on Run History.** It is the 365
  dates that end today, the range Run History's `Last 12 months` covers. The
  mockup drew the 52 weeks back to a Sunday instead, which on 2026-10-15 was
  four more days: 4,929 runs on 87 days, against 4,748 runs on 85.
- **The current year is listed as well.** LeetCode lists only "Current" and
  earlier years. Monkeytype offers the last 12 months and the years back to
  the account's creation, and GitHub lists every year. A year answers "how is
  this year going", which the rolling window doesn't: in October the two
  differ by more than two months of play. The cost is one more entry.
- **Only years with runs are listed,** as LeetCode does. On 2026-10-15 the
  maintainer's dropdown would read `Last 12 months`, `2026`, `2025`, `2024`,
  `2021`, `2020`, `2019`: they recorded no runs in 2022 or 2023.
- **It opens on the last 12 months, and forgets.** The maintainer looks at
  Home "primarily at app start, sometimes after a session" (2026-10-13). A
  remembered 2020 would open the app on old history. Home's spec already
  says the page has no control the browser remembers, and this keeps it so.
  Run History remembers its range because it is a working view.
- **What the card answers.** It answers "how much have I played, and when",
  as facts. That is not one of the product's three questions (am I
  improving, where am I weak, what next), and
  [Answer the question, don't just show the data](../roadmap.md#guiding-principles)
  is the app's first principle. It is the roadmap's planned "An overview —
  time spent and activity across all scenarios", and context for the look
  back between sessions that [product.md](../product.md#when-they-ask-them)
  describes.
- **The counter-position.** In the ideas consult `claude-fable-5-1` left the
  hour grid out as "static trivia, interesting once" and put the calendar
  later. `gpt-6.1-sol` put both later, the hour grid as "occasional habit
  curiosity, weak everyday value". Both warned that an activity chart can
  turn into a consistency score. The maintainer chose both heatmaps after seeing them
  drawn from their own stats. The design answers the warning with facts
  only: no streak, no goal, no count of days missed, and no line that
  compares one period with another. A reviewer who still judges the hour
  grid not worth its place can contest it here.

Choosing otherwise:

- **Buttons per year** run out of room as the history grows.
- **A period for each heatmap** costs a second control, and lets the two
  heatmaps on one card show different periods.
- **Leaving the current year out** saves one entry. A player who wants this
  year has to read it out of the rolling window.
- **Remembering the choice** stores a value, and can open the app on an old
  year.
- **The calendar alone** drops the hour grid and its layout work.

Rejected in the design discussion: weekly bars (the maintainer: "ugly"), and
the consult's 12-week strip.

### HM2. What a shade measures

Status: Open. The maintainer, 2026-10-14, on the order of a related list,
the scenarios played lately: "'By time in runs' makes more sense than 'By
runs', since some scenarios have longer durations." They have given no lean
on the heatmaps' measure itself. One part of this recommendation departs
from the design note this proposal starts from, which shaded the hour grid
by runs; see below.

The material consequence: the card puts the app's first time-in-runs figure
on screen, so this row decides what that figure means and what it is called.
No page shows time in runs today. Run History shows a session's length,
which counts the breaks between runs, and the latest-run card shows the time
on a scenario in a session, which runs from a visit's first run's start to
its last run's end
([sessions.md](../specs/sessions.md#where-sessions-show)).

**Recommendation: both heatmaps shade by time in runs: the sum of the
[run lengths](../glossary.md#run-length) of the runs in a day, or in an hour
of the week. A run counts toward the date and the hour it ended in. The
summary line gives the period's runs, its days with runs, and its time in
runs. When any run in the period has no run length, the whole card counts
runs instead: both heatmaps shade by runs, the summary leaves the time out,
and a line under it says why.**

- **Time, not a count, for the maintainer's reason.** A day of two-minute
  scenarios is twice the play of the same number of one-minute runs. On the
  maintainer's last 12 months the two measures barely differ: 4,494 of the
  4,748 runs measure between 30 and 60 seconds, and in the hour grid only 5
  of the 112 hours with runs would take a different shade by runs, none by
  more than one step. A player whose scenarios vary more in length would see
  more difference, and time is right for them for the same reason.
- **Time in runs, not session time.** A session's length counts the time
  between runs: results screens, menus, restarts, and breaks of up to 30
  minutes. It runs about twice the time in runs: runs fill 53% of the
  maintainer's session length overall, and 48% in 2026. Time in runs is the
  practice itself. Session time does one thing better: it is known for 2019
  to 2021, when run lengths mostly aren't.
- **What the figure is.** Time in runs is exact for what it counts: the runs
  the stats folder records, each from its start to its end less its pauses.
  It reads about half a second short per run, about 1%, because a run's end
  is written to the whole second. It is not the time played. It leaves out
  the time between runs, and any attempt that wrote no stats file, such as a
  restart. The card writes it as `{time} in runs`, and a hover on the
  summary's time says what it leaves out.
- **How this reads the ratified minimum rule.** The guiding principle
  [Be honest about uncertainty](../roadmap.md#guiding-principles) says "A
  figure that can only be a minimum is labelled one, such as time spent in
  runs, which leaves out the time between runs and any attempt that wrote no
  stats file." This proposal reads it as met by a name that says what is
  counted, "in runs", and a hover that says what is not. By the glossary a
  run is an attempt that wrote a stats file, so the figure is exact for runs
  and a minimum only of the time played. The literal reading puts "at least"
  before every time on the card, down to each day's hover. If reviewers read
  the rule that way, only the copy changes. The cost would be a hedge on
  every number, including the ones that are exact for their label.
- **The whole card switches, never one day.** The mockup switched to runs
  only when a day with runs had no time at all. That keeps the maintainer's
  2021 shaded by time, although 46 of its 87 runs have no run length,
  because every one of its seven days has at least one run with a length.
  Three of its days would be shaded by part of their runs. Switching on any
  run without a length never shades by a partial time. It switches three of
  the maintainer's periods: 2019, where 12 of 12 runs have no run length,
  2020 (451 of 471), and 2021 (46 of 87). Every run since 2024 has one.
- **What the switch costs.** A single run without a length switches the whole
  period. That is now rare. A run loses its length when its file gives no
  usable start or pause, or when the length falls outside 1 to 1,800
  seconds, such as a run across a clock change or a file that looks like a
  reset ([sessions.md](../specs/sessions.md#run-start-and-run-length)). No
  run of the maintainer's since 2021 has lost its length. Another player may
  see it more often. The alternative is a share: shade by
  time while no more than 1% of the period's runs lack a length, and write
  the times as minimums. It is a second rule and a constant to defend, so it
  is not recommended.
- **The hour grid shades by time too.** The design note had it shaded by
  runs. With both heatmaps on one measure, the card has one unit, both
  legends read in minutes, and the switch moves both heatmaps together.
  Shading the hour grid by runs is exact by construction, since every run
  has an end, and never needs the switch. Its cost is two measures on one
  card, minutes in one legend and runs in the other, and it loses the
  duration effect the maintainer named.
- **The Backlog's "Time definitions across the app."** On 2026-10-14 the
  maintainer deferred a scenario's time played on Run History so that "the
  concept of time stays consistent throughout the app", noting that Home
  faces the same question. This row decides only the heatmaps' measure, and
  names it time in runs, a figure distinct from a time played. If the
  maintainer would rather settle the app-wide definition first, the
  alternative is to ship the heatmaps shaded by runs and revisit them then.

Choosing otherwise:

- **By runs:** always known, with no switch. A four-minute scenario weighs
  the same as a 30-second one.
- **By session time:** known in every year. It counts breaks as play, a
  session across midnight has to be split between two dates, and it means
  something different from time in runs.
- **Switching per day, as the mockup did:** shades the maintainer's 2021 by
  part of its runs.
- **"At least" on every time:** honest under the literal reading of the
  minimum rule, and a hedge on every figure.

### HM3. The shading rule

Status: Open. The maintainer, 2026-10-15: "I don't have any strong lean on
shading. Perhaps leave it up for Fable/Sol/Astra to debate." The author
recommends one rule below, and each reviewer is asked for a stance of their
own.

The material consequence: what a shade means. Either the same shade means
the same amount in every period and for every player, or it means "among
your bigger days in this period".

**Recommendation: quartiles of the days with runs in the period, with each
shade's range written in the legend. The hour grid uses the same rule over
its hours with runs.**

The rule, exactly:

- **The values.** Each day's time in runs in whole minutes, rounded as its
  hover writes it, so a day's hover and its shade's range never disagree. On
  a period that counts runs, each day's runs.
- **Who counts.** A day with no runs takes the empty tile and is not
  counted. A day with runs always takes a shade, even one that rounds to
  `<1 min`.
- **The cut points,** by nearest rank: the values at positions ⌈n/4⌉, ⌈n/2⌉
  and ⌈3n/4⌉ of the n days with runs, smallest first. A day at or under the
  first cut takes the palest shade, and so on up; a day over the third takes
  the darkest. Equal values always share a shade.
- **Fewer than four days with runs** can't be split into quarters, so every
  day with runs takes the second shade.
- **The legend** gives each shade's range, from the least to the most a day
  in it holds, and `none` for a shade that holds no day.

The four rules the mockup compares, on the maintainer's last 12 months: 85
days with runs, 78 hr 12 min in runs, from 1 minute to 3 hr 10 min a day.

| Rule | Where the shades end | Days per shade, palest first |
|---|---|---|
| Quartiles of the days with runs (KovaaK's, Refleks) | 26 min, 44 min, 1 hr 16 min | 22, 21, 21, 21 |
| Fixed minutes | 15 min, 30 min, 1 hr | 11, 14, 27, 33 |
| Relative to a 10%-trimmed mean, at half, once and one and a half times it (Monkeytype) | 25 min, 50 min, 1 hr 16 min | 21, 26, 17, 21 |
| An even split of the range (Mantine's Heatmap default) | 48 min, 1 hr 36 min, 2 hr 23 min | 46, 29, 6, 4 |

How each reads across the dropdown, as days per shade, palest first. 2019 to
2021 count runs (HM2), so fixed minutes become fixed runs there, at 15, 30
and 60:

| Period | Days | Quartiles | Fixed | Relative to the mean | Even split |
|---|---|---|---|---|---|
| Last 12 months | 85 | 22, 21, 21, 21 | 11, 14, 27, 33 | 21, 26, 17, 21 | 46, 29, 6, 4 |
| 2026 | 64 | 16, 16, 17, 15 | 9, 10, 21, 24 | 16, 20, 11, 17 | 32, 23, 7, 2 |
| 2025 | 78 | 20, 20, 19, 19 | 12, 11, 22, 33 | 22, 22, 13, 21 | 40, 23, 11, 4 |
| 2024 | 1 | 0, 1, 0, 0 | 0, 0, 1, 0 | 0, 1, 0, 0 | 1, 0, 0, 0 |
| 2021, by runs | 7 | 2, 2, 2, 1 | 5, 1, 1, 0 | 2, 3, 0, 2 | 5, 1, 0, 1 |
| 2020, by runs | 24 | 7, 5, 6, 6 | 14, 5, 3, 2 | 9, 6, 3, 6 | 17, 3, 1, 3 |
| 2019, by runs | 3 | 0, 3, 0, 0 | 3, 0, 0, 0 | 1, 0, 2, 0 | 1, 0, 0, 2 |

- **Quartiles** fill every shade evenly in every period with enough days, so
  every shade tells the player something: which days were the big ones, and
  how the period was spread. They adapt to every player with no number to
  defend, and one rule serves both heatmaps and both measures. The cost is
  that color doesn't compare periods: a light year looks as dark as a heavy
  one, and only the legend's ranges and the summary tell them apart. On this
  history 2025 and 2026 look alike and are alike, with median days of 51 and
  45 minutes.
- **Fixed minutes** mean one amount everywhere. Years compare at a glance and
  the legend never changes. On the last 12 months they put 60 of 85 days in
  the two darkest shades. A player who plays two hours a day would see nearly
  every day darkest, and one who plays ten minutes nearly every day palest.
  The 15, 30 and 60 are one player's scale, and the app would have to defend
  them. A period that counts runs needs fixed run counts as well, which put
  14 of 2020's 24 days in the palest shade. The rule can't serve the hour
  grid: a cell adds up a whole period, so its values grow with the period's
  length. The busiest hour holds 2 hr 15 min over the last 12 months and 29
  minutes in 2024.
- **Relative to the mean** behaves much as quartiles do, with uneven shades
  and one empty in 2021. Its cuts have a meaning, half your usual day and so
  on, but the trimmed mean behind them needs explaining.
- **An even split** lets a few long days push most days into the palest two
  shades: 75 of 85 over the last 12 months. It is Mantine's default, which is
  one reason not to take its Heatmap as is.

Why quartiles over fixed minutes, the strongest alternative:

- **The calendar's first job is the shape of the period:** which days had
  play and which were the big ones. Quartiles use all four shades for that in
  every period; fixed minutes use mostly two on this history.
- **No constant to defend.** Fixed minutes fit players near the maintainer's
  scale, and the app ships to others.
- **One rule for the whole card.** Fixed minutes would need a second rule for
  the hour grid, and fixed run counts for the years without lengths.
- **Precedent and evidence.** KovaaK's, the game this app reads, shades its
  own overview by quartiles of the days with runs (measured from a
  screenshot), and Refleks does in its source. GitHub's staff describe
  per-user quartiles after removing outliers. In map-reading tasks quantile
  classes were read most accurately (Brewer and Pickle, 2002), on
  choropleths rather than calendars.
- **The numbers stay on screen.** The legend gives each shade's range in
  minutes, and the summary gives the period's totals, so a year compares
  with another by its numbers.

**A fifth rule, not mocked: quartiles of every day in the player's history.**
One set of cut points serves every period, so years compare by color, and
the scale still adapts to the player. On this history the cut points are 22
minutes, 44 minutes and 1 hr 19 min, over the 150 days whose runs all have a
length. The last 12 months would read 17, 26, 24 and 18 days per shade, and
2025 18, 18, 19 and 23. Its costs: the cut points move as the history grows, so an old year
can change its look, and the years that count runs need a lifetime scale of
their own. The author leans against it for those costs, and offers it for
the debate.

Choosing otherwise:

- **Fixed minutes:** years compare by color, at the cost of most days in two
  shades on this history, a constant to defend, and a second rule for the
  hour grid.
- **Relative to the mean:** much as quartiles, with uneven shades and a rule
  that needs explaining.
- **An even split:** most days in the two palest shades.
- **Lifetime quartiles:** years compare by color, at the cost of cut points
  that drift and a second scale for the years that count runs.

### HM4. Green

Status: Open. The maintainer's lean, 2026-10-15: "I'm actually leaning
toward green. It follows Anki, Github, Leetcode, and probably some other
apps. Unless other colors are more popular with calendar heatmaps in other
apps."

The material consequence: the card's color. It is the app's first green
outside a notification or the run list's check.

**Recommendation: one green ramp, an empty tile plus four steps. More is
darker in light mode and brighter in dark mode, as in every product
surveyed. The steps are tuned for even lightness on the app's own
surfaces:**

| Theme | Card | Empty tile | Steps, least to most |
|---|---|---|---|
| Light | `#ffffff` | `--mantine-color-gray-1`, `#f1f3f5` | `#6fdd8b`, `#2da44e`, `#1a7f37`, `#044f1e` |
| Dark | `#242424` (`--mantine-color-dark-7`) | `--mantine-color-dark-6`, `#2e2e2e` | `#0f5323`, `#238636`, `#3fb950`, `#7ee787` |

Contrast, by the WCAG formula:

| | Faintest step against the empty tile | Each step against the one before |
|---|---|---|
| Proposed, light | 1.52:1 | 1.52, 1.90, 1.58, 1.93 |
| Proposed, dark | 1.48:1 | 1.48, 1.99, 1.82, 1.65 |
| GitHub's chart steps, light, on this app | 1.20:1 | 1.20, 1.70, 1.41, 2.30 |
| GitHub's chart steps, dark, on this app | 1.05:1 | 1.05, 1.99, 1.93, 1.75 |
| GitHub's chart steps, dark, on GitHub | 1.34:1 | 1.34, 1.99, 1.93, 1.75 |

- **Green is the most common hue among the calendars surveyed:** GitHub,
  LeetCode, Codeforces, Anki's heatmap add-on, and WakaTime's
  GitHub-matching option. GitLab and Gitea are blue, KovaaK's and Refleks
  orange, and Monkeytype and keybr use the user's theme color. The
  maintainer's condition, that no other color be more popular, holds.
- **GitHub's dark steps can't be used as they are.** They are tuned for
  GitHub's `#0d1117` page. On this app's dark card their first step is
  1.05:1 against the empty tile, which makes a day with runs look like a day
  without. Against a lighter empty tile, `#3b3b3b`, it is darker than the
  tile. So both themes are tuned, as the palette research tuned the app's
  blue. The steps are picked in GitHub's green family. Apart from `#2da44e`,
  they are not GitHub's chart steps.
- **The faintest step is stronger than GitHub's** because under quartiles a
  quarter of the days with runs take it: 22 days in the last 12 months. A
  faint first step makes a quarter of the days played look unplayed. It is
  still under the 3:1 that WCAG 1.4.11 asks of graphics needed to understand
  content. Each day's hover and accessible name carry its value, and no
  product surveyed clears 3:1.
- **Green means a positive outcome in the app's notices.** The
  [2026-08-30 entry](../decision_log/2026/2026-08-30-one-severity-color-language-for-inline-notices.md)
  gives green that meaning on notification surfaces: the new personal best
  toast is green, as is the run list's threshold check
  (`--mantine-color-green-7` in light). A chart is not a notification
  surface, so no ratified rule is broken. The risk is in the reading: greener
  as better, a calendar of good days, which is the consistency-score worry
  both seats raised. The legend says `Less` and `More`, never better, and the
  card states facts only.
- **The neutral alternative is the app's blue,** the informational color of
  its notices, mocked as the default of the second mockup and tuned there to
  even steps. It is less familiar on a calendar, where only GitLab and Gitea
  use blue.
- **Color vision.** Lightness carries the order, which reads under the common
  color-vision deficiencies. Datawrapper's guidance is that any colors work
  "as long as they vary by lightness", and each step here differs from the
  one before by at least 1.48:1.

Choosing otherwise:

- **GitHub's chart steps as they are:** familiar in light mode, with a
  faintest step close to the empty tile, and broken in dark mode.
- **Blue:** neutral in the app's color language, and less familiar for a
  calendar.
- **Orange,** KovaaK's own: orange is the app's partial-success color.
- **Red** is the app's error color, and **yellow** washes into an empty day
  in light mode (the third mockup).

### HM5. Weeks start on Sunday

Status: Open. The maintainer's lean, 2026-10-15: "I agree with Sunday." The
author had moved its own lean from Monday to Sunday on the research.

The material consequence: where a week begins in both heatmaps.

**Recommendation: both heatmaps put Sunday first. The calendar's columns are
weeks that run Sunday to Saturday, top to bottom, and the hour grid's rows
run Sunday to Saturday. The calendar labels Mon, Wed and Fri, as GitHub does;
the hour grid labels every row.**

- **The precedents.** GitHub, KovaaK's, LeetCode and Codeforces start weeks on
  Sunday. Mantine's Heatmap default, Strava, ActivityWatch, CodeChef and
  keybr start on Monday. GitLab and Anki let the user choose, and Umami
  follows the browser's locale.
- **The app already writes dates the US way:** `Oct 4, 9:45 PM`, on a
  12-hour clock. US calendars start on Sunday.
- **The cost:** the weekend splits. Saturday ends one column of the calendar
  and Sunday opens the next, and in the hour grid Saturday is the last row and
  Sunday the first.

Choosing otherwise:

- **Monday,** the ISO week: the weekend sits together at the end.
- **The browser's locale:** the page is built on the server, the app
  localizes no dates anywhere else, and two players' screenshots would
  differ.
- **A setting:** a control for a small gain.

### HM6. A day starts at midnight, local time

Status: Open. The maintainer's lean, 2026-10-15: "I'm leaning toward 12 AM
because Github is a good example to follow, and because it would otherwise
complicate things with multiple definitions of day start." The author had
recommended 4 AM in the design discussion, and recommends the lean here.

The material consequence: which date a late-night run belongs to.

**Recommendation: a day is a calendar date in the app's local time, from
midnight to midnight, the date Run History's day ranges use. A run belongs to
the date and the hour of its end, the time in its stats file's name. The hour
grid's first column is 12 AM.**

- **One meaning of a day.** Run History's ranges are calendar dates from local
  midnight. A 4 AM day on Home alone would make Home's last 12 months and Run
  History's disagree at both ends, and give a date two meanings.
- **The precedents.** GitHub, GitLab, keybr and freeCodeCamp use local
  midnight. LeetCode and Monkeytype use UTC and say so beside the chart. Only
  Anki and ActivityWatch start the day at 4 AM, each with a setting; Anki's
  manual gives the reason, so that studying around midnight doesn't count as
  two days.
- **The cost, measured.** 22 of the maintainer's 325 sessions span midnight,
  and 480 runs land on the date after their session began. 68 sessions start
  between midnight and 5 AM. Each such session shows as two days in the
  calendar. In the hour grid, its runs after midnight land on the next
  weekday's row, at the left edge, apart from the evening they continue. The
  maintainer's hour grid has its evening band from about 1 PM to 3 AM. A 4 AM
  day would split 6 sessions, and a 6 AM day 3.
- **Sessions are unaffected.** They are cut by breaks, not by dates, so a
  session that crosses midnight stays one session on Run History.

Choosing otherwise:

- **A 4 AM day,** as Anki and ActivityWatch: late play counts toward the
  evening it began, and a day means two things in the app.
- **A setting:** a control, and still two meanings of a day.

## Problem

### What Home shows today

Home is the page the app opens on ([home.md](../specs/home.md)). It shows the
stats-folder hint and the setup card when either applies, and one line that
counts the runs and the scenarios in the stats folder. Its spec calls it a
stand-in for an Overview page that is planned and not designed. The roadmap's
Future list has that page as "An overview — time spent and activity across
all scenarios", and says Home holds its place.

No page shows when or how much the player has played. Run History shows one
scenario's runs, grouped by session, and its All scenarios view shows each
session whole. Neither shows a day, a week, or a year at a glance.

### What the maintainer said

Their words in the Home design discussion, 2026-10-13 to 15. All are leans.

- **When Home is looked at:** "primarily at app start, sometimes after a
  session" (2026-10-13).
- **Both heatmaps,** 2026-10-14: "I think the 12 weeks bar chart looks ugly.
  I do like both the Year calendar and the Hour x weekday heatmaps." The
  calendar "should probably have some controls to change the year, for
  people who have years of data."
- **Time in runs,** 2026-10-14, of a list of scenarios: "'By time in runs'
  makes more sense than 'By runs', since some scenarios have longer
  durations."
- **A dropdown,** 2026-10-15: "I'm thinking a dropdown might be better since
  eventually a player will have so many years accumulated that we will run
  out of space to have dedicated buttons per year."
- **Sunday,** 2026-10-15: "I agree with Sunday."
- **Green,** 2026-10-15: "I'm actually leaning toward green. It follows Anki,
  Github, Leetcode, and probably some other apps. Unless other colors are
  more popular with calendar heatmaps in other apps."
- **Midnight,** 2026-10-15: "I'm leaning toward 12 AM because Github is a good
  example to follow, and because it would otherwise complicate things with
  multiple definitions of day start."
- **Shading,** 2026-10-15: "I don't have any strong lean on shading. Perhaps
  leave it up for Fable/Sol/Astra to debate."
- **Updates while the page is open,** 2026-10-13: "ideally every page in the
  app automatically updates while open, similar to the Run History page. But
  for simplicity I can accept no automatic updates; i.e. each page load pulls
  the latest data, and that's it."
- **Scope,** 2026-10-15: "I would like to focus this chat session on heatmaps
  for the Home page, and save the other ideas for a separate proposal."

### How the design was worked out

- **An ideas consult,** 2026-10-13 and 14, answered by `claude-fable-5-1` and
  `gpt-6.1-sol`, each writing its own list before seeing the candidates.
  Neither put the heatmaps first (HM1).
- **Four versions of a full-size mockup,** built from the maintainer's stats
  with the app's own parser and session rule, in light and dark, with
  switches for the colors, the shading rule and the day start. The
  maintainer judged the heatmaps on it. The mockups are local scratch, not in
  the repo.
- **Three research passes** by research subagents, on palettes, on heatmap
  UX, and on calendar and week heatmaps in other apps, plus a check of
  LeetCode's calendar in a browser. Each report marks what was read at a
  primary source and what is secondhand, and the design session checked a
  sample of each. The findings this proposal cites are summarized in its
  rows.

### Verified facts

Measured on 2026-10-15 at `1799df0`, over the maintainer's stats folder,
with the app's own parser (`extract_data_from_file`) and session rule
(`split_into_play_sessions`), unless a line says otherwise.

- **The history:** 9,135 runs on 866 scenarios in 325 sessions, from
  2019-07-14 to 2026-10-09, on 177 days. Years with runs: 2019, 2020, 2021,
  2024, 2025, 2026.
- **Run lengths:** 509 runs have none, all from 2019 to 2021: 12 of 2019's
  12, 451 of 2020's 471, and 46 of 2021's 87. Every run since 2024 has one.
  A length reads about half a second short per run, about 1% of the total,
  because a run's end is written to the whole second (the design
  discussion's probe).
- **The last 12 months,** October 16, 2025 to October 15, 2026: 4,748 runs on
  85 days, 78 hr 12 min in runs. The median day is 44 minutes and the longest
  3 hr 10 min. 4,494 of the runs measure 30 to 60 seconds.
- **The hour grid over the last 12 months:** 112 of the 168 hours of the week
  hold runs. The busiest is Sunday 4 PM to 5 PM, with 137 runs and 2 hr 15
  min. Little is played between 5 AM and 11 AM.
- **Runs fill 53% of session length** overall, and 48% in 2026 (the design
  discussion's probe).
- **Midnight:** 22 of 325 sessions span it, and 480 runs land on the date
  after their session began. 68 sessions start between midnight and 5 AM. A
  4 AM day would split 6 sessions, a 6 AM day 3. 13 runs start on one date
  and end on the next.
- **Clock changes:** the only clock change with runs in its skipped or
  repeated hour was 2025-11-02, when 17 of the night's 192 runs ended in the
  repeated 1 AM hour.
- **The building block on hand:** dash-mantine-components 2.8.0, the app's
  locked version and floor, has a calendar `Heatmap` that takes `colors`,
  `domain`, `firstDayOfWeek`, `getTooltipLabel`, `splitMonths` and
  `clickData`. It has no legend prop, sets no role or label on its squares,
  and draws dates only, so it can't draw the hour grid. Its default shading
  is an even split.
- **Green in the app:** the run list's threshold check is
  `--mantine-color-green-7` in light and `--mantine-color-green-4` in dark
  (`.run-list-check` in `assets/stylesheet.css`), and the new personal best
  toast is green.
- **The app's dark card** is `--mantine-color-body`, `#242424`, and its light
  card `#ffffff` (Mantine 8, from the installed bundle).

### Not checked

- **Other players' histories.** Every figure is one player's. How often a run
  lacks a length in another player's recent years is not known (HM2).
- **The proposed greens on screen.** The fourth mockup draws GitHub's chart
  steps. The tuned steps in HM4 are computed, not yet seen.
- **The fifth shading rule** in HM3 is computed, not mocked.
- **Firefox,** which the maintainer reads the app in. The mockups were
  checked in headless Edge.
- **A screen reader,** on anything: nothing is built.

## Design

### What the player sees

At 2560 px, the maintainer's width, on 2026-10-15:

```
Found 9,135 runs across 866 scenarios in your stats folder.

+-- Activity ------------------------------------------------------------------------------- [ Last 12 months  v ] --+
| Last 12 months · 4,748 runs on 85 days · 78 hr 12 min in runs                                                       |
|                                                                                                                      |
| By day                                                              By hour of the week                              |
|      Oct  Nov  Dec  Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct     12 AM   3 AM   6 AM ...  6 PM   9 PM       |
|      . . # . . . . . . . . . . . . . . . . . # # . . . . . . . . . .  Sun  # # # .  . . . ...  # # # # # #          |
| Mon  # . . . . # . . . . . . . . . . . . . . # . . . . . . . . # .   Mon  # # # .  . . . ...  # # # # # #          |
|      ...                                                             ...                                             |
| Fri  . # . . . . . . . . . . . . . . . . . . . # . . . . . . . . .   Sat  # # # .  . . . ...  # # # # # #          |
|                                                  Less [][][][][] More                         Less [][][][][] More   |
|   Shades: 1 to 26 min · 27 to 44 min · 46 min to 1 hr 16 min ·        Shades: 1 to 19 min · 21 to 38 min ·          |
|           1 hr 18 min to 3 hr 10 min                                   39 to 59 min · 1 hr 1 min to 2 hr 15 min      |
+----------------------------------------------------------------------------------------------------------------------+
```

How a player meets it:

- **At app start,** the moment Home is looked at most, the card opens on the
  last 12 months. The calendar shows which days had play and which were the
  big ones. The hour grid shows when in the week the player plays. The
  summary line gives the totals.
- **Looking back at a year,** the player picks `2025` in the Range dropdown.
  Both heatmaps and the summary redraw at once, with no wait on the server.
- **Reading a day,** they hover over a square, or move onto it with the
  keyboard: `Sun, Oct 12, 2025 · 41 runs · 52 min in runs`.
- **Reading an hour,** the same: `Sundays, 4 PM to 5 PM · 137 runs · 2 hr 15
  min in runs`.
- **An old year whose runs have no length,** such as 2020, shades by runs,
  and a line under the summary says why.
- **A new player** sees the card from their first run, with every day they
  played in one shade until they have played on four days.
- **A player back from a break of over a year** sees the last 12 months
  empty, with `Last 12 months · No runs`, and their years in the dropdown.

### The card

- **Where.** Directly under the stats line, at the page's full width. Like
  the stats line, it is drawn only while the app has a usable stats folder,
  and only once the run store holds a run. Without either, the setup
  surfaces or the stats line already say why there is nothing to show.
- **The title row.** `Activity` at the left, a section heading. The Range
  dropdown at the right: a `dmc.Select` like Run History's range select, with
  the accessible name `Range` and no visible label, its options carrying
  their own meaning. It does not persist.
- **The summary line** under the title, a readout:
  `{period} · {runs} runs on {days} days · {time} in runs`. On a period that
  counts runs it leaves the time out, and a second line says why. On a period
  with no runs it reads `{period} · No runs`. The time's hover says what time
  in runs leaves out.
- **The calendar.** One square per date, 13 px with a 3 px gap, in weeks of
  columns, Sunday at the top. The last 12 months take 53 columns; a calendar
  year takes 53, or 54 in a leap year that starts on a Saturday. The first
  and last columns can be partial weeks: a date outside the period has no
  square. In the current year, the dates after today have no square either,
  and their columns are kept, so a year is always as wide as a full year.
  Month names sit over the column where each month begins; weekday names
  label the Mon, Wed and Fri rows.
- **The hour grid.** Seven rows, Sunday first, each labelled. 24 columns,
  each one hour from 12 AM, labelled every three hours: `12 AM`, `3 AM`,
  through `9 PM`. Squares of 24 px with a 3 px gap.
- **The legend,** under each heatmap at its right: `Less`, the empty tile and
  the four steps, `More`. Under it, the ranges line, one range per shade,
  palest first.
- **No click.** Clicking a day lists that day's records in GitHub, GitLab and
  Anki. This app has no address that opens a day or a session, so a square
  does nothing on click (see [Out of scope](#out-of-scope)).

### What is counted

- **A run belongs to the date and the hour it ended,** as written in its stats
  file's name, in local wall-clock time. 13 runs in the history began before
  midnight and ended after it; each counts wholly on the date it ended.
- **A day's time** is the sum of its runs' lengths, rounded to the whole
  minute as the app rounds a measured time
  ([2026-10-13](../decision_log/2026/2026-10-13-a-measured-time-rounds-to-the-nearest-minute.md)).
  The summary's total is the sum of the period's run lengths, rounded once.
- **An hour of the week** adds up every run that ended in that hour, on that
  weekday, across the period.
- **Whether the period counts time or runs** is HM2's switch: time when every
  run in the period has a run length, runs otherwise. It holds for the whole
  card.

### Empty and sparse periods

| State | What the card shows |
|---|---|
| No usable stats folder, or no runs at all | No card. The setup surfaces or the stats line say why. |
| A period with no runs, such as the last 12 months after a long break | Both heatmaps as empty tiles, `{period} · No runs`, the legend with no ranges line. The dropdown still lists the years with runs. |
| Fewer than four days with runs, such as 2024's one day | Every day with runs in the second shade, and the ranges line gives that shade's range alone: `Shades: none · 36 min · none · none`. The hour grid follows the same rule over its hours. |
| A period whose runs lack lengths, such as 2019 to 2021 | Shaded by runs, the summary without a time, and `Shaded by runs, because {n} of these runs have no run length.` under it. |
| A player with ten runs: the maintainer's first ten, on two days of 2019, none with a length | Shaded by runs. Both days in the second shade. The hour grid's four hours with runs split into quarters. |

### Daylight saving days

Every time in a stats file is local wall-clock time, and the card uses it as
written, as the session rule does
([sessions.md](../specs/sessions.md#clock-changes)).

- **When the clock goes back,** the repeated hour's runs from both passes land
  in one square of the hour grid: on 2025-11-02, 17 runs in Sunday's 1 AM
  square.
- **When it goes forward,** the skipped hour holds no runs that night.
- **The calendar is unaffected:** a day of 23 or 25 hours is still one date,
  and its time is the sum of its runs. A run across the change has no length,
  because its length falls outside the trusted range
  ([sessions.md](../specs/sessions.md#run-start-and-run-length)), so its
  period counts runs (HM2).
- **The cost** is at most one hour a year counted twice, and one missing, in
  the hour grid. No product the research found documents its handling.

### Data and updates

- **Built at page load,** from a copy of the run store, as the stats line is.
  The card doesn't change while the page is open, as the maintainer accepted;
  a run that lands shows on the next load. "Today" is the app's own date at
  load, never the browser's, as on Run History.
- **Every period is sent with the page,** so the dropdown switches in the
  browser and the whole card stays one snapshot. For the maintainer's seven
  periods that is about 2,500 calendar squares and 1,200 hour squares, each
  with its shade and its text.
- **The cost** is one pass over the runs to group them by date and by hour,
  per page load.

### The building block

**Recommendation: draw both heatmaps in the browser from data the server
builds, as the run list does.** A Python function works out every square's
shade and text, the summary, and the legends, for every period. A script in
`assets/` draws the two tables from that data and holds no copy of its own,
as `assets/runHistoryList.js` holds none
([2026-10-12](../decision_log/2026/2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md)).
The shading rule lives in Python, where it is tested.

Rejected:

- **dmc's `Heatmap`.** It draws the calendar only, so the hour grid would need
  a second building block and a second look. It has no legend, no label on a
  square, and a tooltip on the pointer only. Its shading is an even split, so
  quartiles would have to be smuggled in as shade numbers through `domain`.
- **plotly's `go.Heatmap`,** in a `dcc.Graph`. It draws both grids, but it
  offers no accessible layer, carries the plotly toolbar, and hovers on the
  pointer only.
- **One Dash component per square.** The two heatmaps hold about 540 squares
  before their labels, and every change of period would redraw them. The
  run list's entry rules this out: Dash draws components at a cost that
  doubles per component each time their number doubles.

### Keyboard and screen reader

- **Each heatmap is a table:** its caption names it and the period, its rows
  are headed by the full weekday names, and each square is a cell whose
  accessible name is its hover text, empty squares included.
- **One tab stop per heatmap.** The arrow keys move between squares, and Home
  and End go to the ends of a row. A focused square shows its hover text, as
  GitHub's calendar has done since 2023.
- **The summary line and the ranges line are text,** read in place, so the
  totals and what each shade means don't depend on a hover. The summary's
  time takes focus and shows its hover, as Run History's hovers do.
- **The legend's swatches are hidden from screen readers.** The ranges line
  says what they say.
- **NVDA is run on the built heatmaps** and what it says is recorded, as on
  the run list.

### Narrow windows

The page area is the window's width less 257 px, the navbar and the padding.
The calendar needs about 890 px and the hour grid about 680 px, so the two sit
side by side from a card of about 1,650 px.

| Window | Page area | Layout |
|---|---|---|
| 3840 px | 3,583 px | Side by side, at their natural size, with room to spare |
| 2560 px, the design width | 2,303 px | Side by side |
| 1920 px | 1,663 px | Side by side, with about 20 px to spare |
| 1536 px | 1,279 px | Stacked, the calendar first |

- **The squares keep their size;** the heatmaps never stretch to fill a wide
  card, and never shrink in a narrow one.
- **Below about 1,180 px of window,** the calendar no longer fits the card. It
  scrolls sideways inside the card, as GitHub's does, and the page itself
  never scrolls sideways.

### Light and dark

The card, its text and its borders use the theme's tokens, as the other cards
do. The empty tile is a theme token in each theme. The four steps are the
only fixed colors, set per theme by HM4 in `assets/stylesheet.css`.

### Copy

Every string this proposal adds. They follow the nine copy rules in
[AGENTS.md](../../AGENTS.md#styling-conventions). Counts take thousands
separators and the singular where a count is one (`1 run`, `1 day`), as the
stats line does. Times are written as the app writes a measured time: `<1
min`, `9 min`, `1 hr`, `1 hr 6 min`. Dates are written as Run History writes
them: `Oct 12` in the current year, `Oct 12, 2025` in an earlier one.

| Where | String | Why |
|---|---|---|
| Card title | `Activity` | A section heading, so Title Case under rule 3. The roadmap's word for the overview, "time spent and activity". |
| Range dropdown, accessible name | `Range` | Run History's name for its select that offers the same `Last 12 months`. |
| Range dropdown, options | `Last 12 months`, then `{year}`, such as `2025` | The same label as Run History's, for the same 365 dates. |
| Summary, a period counting time | `{period} · {runs} runs on {days} days · {time} in runs`, such as `Last 12 months · 4,748 runs on 85 days · 78 hr 12 min in runs` | A readout chained with ` · `, so no period (rules 1 and 2). "In runs" says what the time counts (HM2). |
| Summary, a period counting runs | `{period} · {runs} runs on {days} days` | The same readout with no time, since the time is unknown. |
| Summary, a period with no runs | `{period} · No runs` | A readout. A fragment after ` · ` starts with a capital, as the latest-run card's `Time on this scenario unknown` does. |
| Summary's time, hover and focus | `Time in runs counts each run from its start to its end, less its pauses. It leaves out the time between runs and any attempt that wrote no stats file, such as a restart.` | Says what the figure is and what it leaves out, as Run History's session length hover does. "Stats file" is the app's term. |
| Under the summary, a period counting runs | `Shaded by runs, because {n} of these runs have no run length.`, or `Shaded by runs, because 1 of these runs has no run length.` | What happened, then why, in one sentence. "Run length" is the glossary's term. |
| Caption over the calendar | `By day` | A chart caption, sentence case. Short, and true of both measures. |
| Caption over the hour grid | `By hour of the week` | Says the grid adds weeks together, which "by hour" alone doesn't. |
| Calendar, weekday labels | `Mon`, `Wed`, `Fri` | GitHub's three labels; the app's short weekday names. |
| Calendar, month labels | `Jan` to `Dec` | The app's short month names. |
| Hour grid, weekday labels | `Sun` to `Sat` | Every row labelled; seven rows have room. |
| Hour grid, hour labels | `12 AM`, `3 AM`, `6 AM`, `9 AM`, `12 PM`, `3 PM`, `6 PM`, `9 PM` | The app's 12-hour clock, every third hour so the labels fit 24 px columns. |
| Legend | `Less`, `More` | The convention of GitHub, GitLab, KovaaK's and Monkeytype. Never "better". |
| Legend, ranges line | `Shades: {range} · {range} · {range} · {range}`, palest first. A range is `{least} to {most}`, one value when they are equal, `none` for a shade that holds no day. A unit shared by both ends is written once. Such as `Shades: 1 to 26 min · 27 to 44 min · 46 min to 1 hr 16 min · 1 hr 18 min to 3 hr 10 min`, or by runs `Shades: 1 to 4 runs · 5 to 10 runs · 12 to 23 runs · 27 to 78 runs` | A readout. Each range is exact, because the shades are worked out on the values as written. |
| Calendar square, hover and accessible name | `{weekday}, {date} · {runs} runs · {time} in runs`, such as `Sun, Oct 12, 2025 · 41 runs · 52 min in runs`. Counting runs: `{weekday}, {date} · {runs} runs`. No runs: `{weekday}, {date} · No runs` | The date first, then the facts, as a readout. The weekday because only three rows are labelled. |
| Hour square, hover and accessible name | `{weekday}s, {hour} to {next hour} · {runs} runs · {time} in runs`, such as `Sundays, 4 PM to 5 PM · 137 runs · 2 hr 15 min in runs`, and `Saturdays, 11 PM to 12 AM` for the last hour. Counting runs, the time is left out. No runs: `Sundays, 6 AM to 7 AM · No runs` | The plural says the square adds up every such hour in the period. |
| Calendar, accessible caption | `By day, {period}`, such as `By day, last 12 months` or `By day, 2025` | The visible caption with the period, so a screen reader names the table it enters. |
| Hour grid, accessible caption | `By hour of the week, {period}` | As the calendar's. |
| Rows' accessible headers, both heatmaps | `Sunday` to `Saturday` | Full names for a screen reader; the visible labels are short. |

### Terms

Each entry is written as [docs/glossary.md](../glossary.md) would hold it.
The shipping PR moves them in.

- **Time in runs**, under "Play", after Run length. The sum of the run
  lengths of a set of runs: how long they took to play, pauses left out. It
  leaves out the time between runs and any attempt that wrote no stats file,
  such as a restart, so it is less than the time played. It is unknown when
  any of the runs has no run length. How the Activity card uses it is in
  `home.md`.
  - On screen: `{time} in runs`.
  - Not session length, which counts the time between runs, and not the
    latest-run card's time on a scenario, which runs from a visit's first
    run to its last.
- **Activity card**, under a new section "Home". The card on Home with two
  heatmaps of when and how much the player played, for a period they pick:
  the last 12 months, or a year with runs.
  - On screen its title is `Activity`.

The glossary's Run History entry already says it is "Not Home, the page the
app opens on." No other entry becomes untrue.

### Decisions this changes

The shipping PR keeps each entry and adds a dated note. It erases nothing.

- [2026-10-12, Run History's address and Home](../decision_log/2026/2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md)
  set what Home holds: setup, then one line of stats. The card extends that
  list and changes none of it. The entry gets a dated note that points to
  the heatmap entries.
- [2026-08-30, the severity colors](../decision_log/2026/2026-08-30-one-severity-color-language-for-inline-notices.md)
  is not changed: it governs notification surfaces, and a chart is not one
  (HM4).

## Delivery plan

Two implementation PRs. This is intent, not a contract: a boundary that moves
is noted in that PR's description. Home is public, so each PR changes a public
page in its release. Neither starts before the rows it builds are ratified.

1. **The Activity card with the calendar** (HM1 for the card, the dropdown and
   the summary; HM2, HM3, HM4, HM5 and HM6 for the calendar). The pure
   function that builds every period's data, the script that draws the
   calendar, the legend, the accessible table and its keyboard path, the
   greens in both themes, the narrow-window rules, the NVDA walk, and the
   `home.md` statements and glossary entries for what it ships.
2. **The hour grid** (HM1's second heatmap, with HM2 to HM6 applied to it).
   It adds the grid to the same function, script and card, and the
   side-by-side layout. As the last PR, it ships the proposal by the
   [Shipping a proposal](../../AGENTS.md#shipping-a-proposal-docs-definition-of-done)
   checklist: a decision-log entry per row, the note in
   [Decisions this changes](#decisions-this-changes), `home.md`, the
   glossary, the roadmap, `product.md`, `architecture.md`, and this file
   deleted.

PR 2 needs PR 1. **Recommended:** `claude-opus-5-5`, at xhigh for PR 1, whose
script and keyboard path are new, and at high for PR 2. The maintainer looks at
each in their own Firefox before it merges.

### Fallbacks

- **PR 1 grows too large:** land the pure function and its tests first, with
  nothing on screen, then the card.

## Out of scope

- **The other Home ideas,** waiting for a separate proposal on the
  maintainer's direction of 2026-10-15: the record line (the stats line and
  what it might grow into), Recently Played (the last 10 sessions or 30 days,
  ordered by time in runs), the latest session (the maintainer: "I still have
  to think more about this"), the page's name (Claude, Fable and Sol all
  recommend Home), the lifetime time figure and its name, and links to a
  scenario's history.
- **Clicking a square.** It needs an address that opens a day or a session on
  Run History, which doesn't exist.
- **Updates while the page is open.** The maintainer accepted load-only.
- **A setting for the week's first day, or for the day's start.**
- **Time definitions across the app** (Backlog). This proposal names and uses
  time in runs for the card alone (HM2).
- **Detecting restarts** (Backlog). Time in runs leaves them out.
- **Anything that judges:** a streak, a goal, a count of days missed, a
  comparison with the previous period, PB marks on the calendar, or a score
  by hour, which would show how well rather than how much.

## Testing

- **Unit, the pure function,** through a table of cases: the periods listed,
  newest first, with no year that has no runs; the last 12 months equal to
  Run History's 365 dates; each summary form; the switch to runs on one run
  without a length; nearest-rank cut points, ties, and fewer than four days;
  a day that rounds to `<1 min` still shaded; each range equal to the values
  its hovers write, and `none` for an empty shade; a run counted on the date
  and hour it ended, including one that crossed midnight; two runs in a
  repeated hour landing in one square; the current year with no squares
  after today; a leap year starting on a Saturday taking 54 columns; Sunday
  in the first row.
- **The script holds no copy:** a test that every string it shows comes from
  Python, as the run list's does.
- **Callbacks:** the card is drawn only with a usable stats folder and a run;
  the dropdown switches periods without a server request.
- **Live, each PR:** headless Edge at 3840, 2560, 1920 and 1536 px, in light
  and dark, on the maintainer's stats, a period with no runs, a year that
  counts runs, and a player with ten runs. Keyboard: the arrow keys, Home and
  End, and focus showing the text. NVDA walked and recorded. The maintainer's
  look in Firefox.
- **Docs:** `tests/test_docs.py` for the links, and the gates in AGENTS.md.
