# Run History

Run History charts one scenario's runs and typical score beside a session
list, with point tooltips naming each run's session, hover linking each chart
run to one list row and a separate latest-run highlight.
A click on any run, on the chart or in the list, opens it in the chart's
place, measured against the runs behind its typical score, until it is
closed.
Its top row puts the player's note beside the scenario selectors, followed
by adjacent cards for its typical score, personal best and latest run. The
page receives each new run once without a reload and can follow the
scenario just played.

Statements below describe what the app does today and link the
[decision log](../decision_log/README.md) entries that set them. Rationale
lives in those entries, not here. A statement with no link is an
implementation fact that no decision-log entry governs. Runtime structure is
mapped in [architecture.md](../architecture.md), the user-facing rationale in
[product.md](../product.md), and what the terms mean in the
[glossary](../glossary.md). What a session is, and when one is in progress,
is in [sessions.md](sessions.md). The Aim Training Journey page
(`/aim-training-journey`, reachable by URL only) is work in progress and out
of scope here, apart from its chart toolbar, noted under The chart.

## Identity

- The page is registered at `/run-history`
  ([2026-10-12][address]). Its name is "Run History": the navbar link, the
  page `name`, and the browser-tab title ([2026-10-12][name]).
- The navbar reads Home, Run History, Playlists, Settings. Its Run History
  link leads to the page with no parameters, where a reload changes nothing.
  The header title leads to [Home](home.md), not to this page
  ([2026-10-12][address]).
- The navbar marks the link of the open page. A link is marked when the
  address is its own or lies under it, with or without a trailing slash,
  and query parameters play no part. So this page's link is marked here
  whatever scenario the address names, and Playlists is marked on a
  playlist's scenario table as well as on the Playlists page. The marked
  link has a tinted background and a blue label, and carries
  `aria-current="page"`, which is what tells a screen reader. A page with
  no navbar entry, such as the Aim Training Journey page, marks nothing
  ([2026-10-13][navbar-mark]).
- The preference panel and its disclosure button are named "Chart options",
  and the controls inside carry the vocabulary the app's own chart
  annotations and the aim-training community already use, "PB score" and
  "Score threshold", rather than invented terms
  ([2026-08-09][naming]).
  Control labels, placeholders, tooltips, and toast titles are sentence case.
  The page title, the group headings, the run list's column headers, and the
  named chart modes "Score vs Run", "Score vs Time", and "Score vs
  Sensitivity" keep their capitals
  ([2026-09-14][copy]).
- Page copy says "Position" for leaderboard placement and reserves "Rank"
  for benchmark tiers, as in the "Rank thresholds" overlay. The rule lives in
  [scenario_rank.md](scenario_rank.md)
  ([2026-07-06][one-word]).
- With `show_version_in_title` enabled, the tab title is prefixed with the
  build's release label. The key is specified in
  [settings.md](settings.md#the-configuration-file).
- `?scenario=` and `?playlist_code=` query parameters select the two
  dropdowns, and the selection they make is remembered exactly like one made
  by hand: arriving from a scenario link in a playlist's table and then
  returning to the page shows that playlist and scenario, not an earlier one
  ([2026-09-19][query]).
  That holds for a hidden playlist too: `?playlist_code=` selects any loaded
  playlist, and the filter names it
  ([2026-10-12][hidden-filter]).
  A parameter the URL omits leaves its control on the remembered value. An
  unknown playlist code clears the filter. The parameters are applied on
  every load of that URL, so reloading a link applies it again over a later
  choice, and the selection it makes becomes the remembered one
  ([2026-09-19][query]).
- A scenario that the Playlist filter does not list is still selected, and
  the filter is cleared in the same step. That holds for a `?scenario=` link,
  for a run the page follows, and for a scenario's name pressed in the run
  list's All scenarios view
  ([2026-10-14][all-scenarios]).
  The scenario must have local runs: a link that names one with none leaves
  the filter alone and selects nothing. The filter empties in view with no
  toast, and the cleared filter is what the browser then remembers
  ([2026-10-12][clear-filter]).
- While a scenario note has unsaved changes, the navbar's links and the
  header title ask before they leave the page, and so do the browser's back
  and forward buttons ([The dialog](#the-dialog)).
- The page accepts query parameters it does not name and reads none of them.
  A run toast's link carries one, `run=` and the run's id, only so that
  each run's link is an address the page is not already at
  ([2026-10-13][run-toast]).

## The top row

The layout follows [T1, including the Follow switch ruling][top-row]. The
cards order and weight facts by their role in the player's next action,
keep facts needed at a glance on screen, and put supporting context after
them in a quieter readable style. Change frequency decides neither order
nor weight; ages read relative with exact times on hover and focus, while
times that name or order runs remain absolute ([T4][card-order]).

- The row takes two columns with the gap of the chart and the run list under
  it. The second column holds the latest-run card alone, at a width of its
  own ([2026-10-22][card-width]): 480px, the list's minimum
  ([2026-10-29][card-480]). With the default columns the list is also
  480px, so the card sits over it with matching edges at every zoom level.
  Adding columns can widen the list under the PB card, which doesn't change
  the top row ([2026-10-22][list-minimum]). The first holds,
  in DOM order, the dropdowns' column, the scenario note card
  ([below](#the-scenario-note-card)), then Scenario Stats and the PB card in
  one score pair at its right end, beside the latest-run card. Spare room
  sits before the score pair, never between its cards. Every card stretches
  to its line's height ([2026-10-21][score-strip]).
- Scenario Stats, the PB card and the latest-run card start their lines 12px
  below their top edge, 2px apart, in room the row already has: the 12px is
  never added to a card's height, so no card's content makes the row taller
  than it would be without it. Their first lines share one top and their
  large numbers another, and a card with fewer lines leaves its spare room at
  its bottom ([SC4][top-aligned]). The scenario note card starts its lines at
  the same offset, so its first line shares theirs whatever the note holds
  ([2026-10-28][note-aligned]).
- While the PB card's leaderboard line shows a hint, such as the one with no
  KovaaK's username, all three start their lines at their top edge instead,
  still lined up, and so does the note card ([SC4][top-aligned],
  [2026-10-28][note-aligned]). A long position with no hint, such as
  `Position: Unranked (123,456 players)` with a benchmark selected, can also
  wrap that line. Then the PB card's lines start up to about 10px higher than
  the other cards', by the maintainer's ruling of 2026-10-25
  ([SC4][top-aligned]).
- The dropdowns' column holds the "Playlist filter" select over the "Selected
  scenario" searchable select (placeholder "Select a scenario"), each the
  column's full width, and the "Follow newly played scenario" switch under
  the scenario select. The column joins a line at 260px and grows to 420px
  with the room the row has. It sets the row's height: 141px at 2560px.
- The "Open scenario table" link sits at the right end of the Playlist
  filter label's line while a playlist is selected. The Follow switch is
  small, its text at the dropdown labels' 14px with a 16px help icon, on a
  16px line. Neither is inside a label: each dropdown's accessible name is
  its label alone, and keyboard focus and a screen reader reach the link and
  the switch after their dropdown.
- The two dropdowns and the Follow switch persist in the browser. The Follow
  switch carries a help tooltip: "Automatically selects the scenario you just
  played when a new run is detected. If the **Playlist filter** doesn't list
  that scenario, the filter is cleared. It waits while a scenario note has
  unsaved changes."
  ([2026-10-12][clear-filter], [2026-10-18][note-unsaved]).
- Opening either dropdown's list keeps the selected name in the field and
  highlights it, so it can be copied, and the first keystroke replaces it
  with a search. The list shows every option until then. A drag on the field
  highlights only the part dragged over, and a second click while the list is
  open places a cursor. Every other way in highlights the whole name: a click
  on the label, a right-click, Tab, and focus returning to the page. After a
  pick or Escape, focus stays in the field with the list closed. An edit or
  an arrow key there highlights the name first, so typing still starts a
  fresh search, and a right-click there highlights it when the field shows
  only a cursor
  ([2026-10-12][highlight]).
- The Follow switch sits with the scenario selector, not in the panel: it
  governs selection, not presentation
  ([2026-08-09][panel]).
- The playlist filter lists the visible playlists
  ([playlists.md](playlists.md#the-overview)), plus the playlist it
  holds when that one is hidden. A hidden playlist becomes the selection
  through a `?playlist_code=` link, which every row of its scenario table
  carries, or by being hidden while it is selected. It is listed only while
  it is held: picking another playlist or clearing the filter takes it out of
  the list, and it can't be picked again until it is shown. Nothing in the
  list marks it as hidden. A playlist the URL names is in the list when the
  page paints. One the browser restored is added by the callback that lists
  the playlist's scenarios, so its name appears just after the page paints
  ([2026-10-12][hidden-filter]).
- While the playlist filter holds a loaded playlist, the "Open scenario
  table" link on its label's line leads to that playlist's scenario table at
  `/playlists/{code}`, which opens in playlist order
  ([playlists.md](playlists.md#routes-and-navigation)). There is no link, and
  no room held for one, while the filter is empty. The callback that lists the
  playlist's scenarios writes the link, so it arrives with that list just
  after the page paints, whether the selection was remembered, made by hand,
  or named by `?playlist_code=`.
- A remembered code that no playlist has does not stay in the filter. When
  the page loads, the filter drops it and is empty, with no clear button, and
  nothing is remembered: the list the filter is given has no such playlist,
  and the Select drops a value its new options lack
  ([2026-10-12][hidden-filter]).
- The first column wraps its pieces on its own width and never on the
  window's ([2026-08-03][content-area]).
  Where they don't fit on one line, Scenario Stats and the PB card move
  together to the next line's right end, then the scenario note card wraps.
  The score pair has the note card's 132px minimum height, so a quiet score
  state still holds room when the pair moves to its own line. Its height
  beyond that floor follows the cards. The pair itself can wrap if the
  column is too narrow to hold both cards, with each inner line packed to
  its right end ([2026-10-21][score-strip]).
  The latest-run card stays in the second column, as tall as the row.
- The scenario list comes from the selected playlist when one is chosen, and
  otherwise from the scenarios with at least one run loaded from the stats
  directory, named by each file's own `Scenario:` field
  ([2026-09-12][local-list]).
  Without a usable stats directory that local list is empty, while a selected
  playlist still lists its scenarios. The list is read again when a run
  lands, so a scenario whose first run has just landed is in it with no
  reload, whether or not the page follows that run.

## The scenario note card

The player's own plain-text note on the selected scenario, read in place and
edited with Save and Cancel ([2026-10-18][note-card]). What a note is and how
it is saved is in [2026-10-18][note-store].

- The card sits after the dropdowns and before the score pair, taking the
  room the row leaves, from 240px to 800px wide; past 800px the rest sits
  before the score pair. It is as tall as its line and never less than
  132px ([2026-10-21][score-strip], [2026-10-18][note-card]).
- What it shows while reading is out of the layout's flow, so its contents
  never set its height: a note, a long note, no note, a broken file and no
  scenario. Its minimum height and the other pieces on its line set its box
  ([2026-10-18][note-card]). A wrapped score line takes the score cards'
  height, with a 132px floor matching the note's, so its height can vary with
  no scenario selected or one that has no local runs. Stacking the score
  pair can make a selected row taller. At a page area of 900px or less the
  score-pair wrapper has no box, so its floor has no effect
  ([2026-10-21][score-strip]).
- While reading, its lines start 12px below its top edge, the score cards'
  offset, and at its top edge while they start theirs there. Its first line,
  or the **Add a scenario note** link, then shares the score cards' first
  lines' top whatever the note holds, and a short note leaves its spare room
  at the card's bottom. The editor keeps its own spacing
  ([2026-10-28][note-aligned]).
- With a note: a frame, the first line `Scenario note · edited {age}` in the
  other cards' quiet style with **Edit** at its right end, and the note under
  it at 14px, its line breaks kept, broken anywhere a word is too long. The
  text is selectable; only **Edit** opens the editor. **Edit**'s accessible
  name is `Edit scenario note` ([2026-10-18][note-card]).
- **Edit** takes clicks 5px either side of the word, 4px above it and 2px
  below, so its area is 30 × 24px where the word is 20 × 18px. Nothing moves
  for it, and the keyboard's focus ring frames that area.
- A note taller than the room under the first line scrolls inside the card,
  with a scrollbar this app draws at the card's right edge whenever there is
  more than fits, whatever the system's scrollbar setting. Its bottom line
  fades while more of the note is below and not at its end. The wheel, a
  trackpad and the scrollbar's thumb scroll it; while it can scroll it is a
  tab stop after **Edit**, a region named `Scenario note`, and the arrow
  keys, Page Up and Down, Home and End scroll it. Another scenario's note, or
  a note just saved, starts at its top. A scroll redraws nothing
  ([2026-10-19][long-note]).
- The age is relative and reworded every 30 seconds, as the PB card's is, with
  the exact time on hover and focus. It is the time the text last changed,
  which only a Save that changes the text moves ([2026-10-18][note-store]).
- With no note: the link **Add a scenario note** alone, at 14px, with no frame.
  With no scenario selected the room is empty and unframed
  ([2026-10-18][note-card]).
- A broken note file: a frame, `Scenario note` with **Edit**, and the schema
  machinery's message in place of the note, such as `The scenario note file
  isn't valid JSON. File: {path}`. **Edit** opens an empty editor, and its
  Save replaces the file after copying it aside. A file from a newer build
  shows its message and offers no **Edit**. The error shows on that card
  alone and in the log ([2026-10-18][note-store]).
- The card is drawn again only when the page's scenario changes and the rules
  below let the change through, by Save, and by the dialog's answers. A run
  that lands on any scenario, the 30-second tick, the date moving on, the
  Playlist filter, the Score threshold and a pick the dialog holds never
  redraw it, and the text box is never drawn again while it is typed into
  ([2026-10-18][note-unsaved]).

### Editing a note

- **Edit**, or **Add a scenario note**, turns the card into a text box over
  **Save** and **Cancel**, focus in the box with the cursor at the end of the
  text. The first line reads `Scenario note` alone. The box's accessible name
  is `Scenario note` and its placeholder `Note for this scenario`; Tab reaches
  **Save** and **Cancel** ([2026-10-18][note-card]).
- The text box never shows less than three lines, 69px, and scrolls inside
  itself. The editor keeps the row's height where that fits, and the card,
  with the row, grows only where the lines under the buttons need more room
  than the row leaves: the waiting line, the count and a save error, beside
  the buttons on a wide card and under them on a narrow one. At 2560px a
  waiting line or the count alone keeps the row's height
  ([2026-10-18][note-card]).
- A note holds at most 2,000 characters. The box stops typing there and cuts
  a paste there. From 1,800 characters a count shows: `1,850 of 2,000
  characters` ([2026-10-18][note-store]).
- **Save** writes the text to the scenario the editor opened on, closes the
  editor and shows the saved text, focus on **Edit**. Saving empty text, or
  only whitespace, deletes the note, and focus goes to **Add a scenario
  note**. Text equal to the note on disk writes nothing. **Cancel** closes the
  editor on the saved text, focus on **Edit** or the link
  ([2026-10-18][note-store]).
- A failed save keeps the editor open with its text and its error under the
  buttons. A file from a newer build refuses with the schema machinery's
  message; any other failure reads `Couldn't save the scenario note. See
  data/logs/debug.log.` ([2026-10-18][note-unsaved]).
- The note has unsaved changes while the box's text differs from the text it
  opened with. Typing a word and deleting it again leaves none
  ([2026-10-18][note-unsaved]).
- Escape does nothing in the editor ([2026-10-18][note-unsaved]).
- With no unsaved changes, the editor just closes when the scenario changes,
  by Follow or by hand, and the card shows the new scenario's note; the run
  toast's link and every link out of the page behave as they do with no
  editor open ([2026-10-18][note-unsaved]).
- While the note has unsaved changes, Follow waits. A run on another scenario
  leaves the page on the edited scenario, its toast shows as usual, and the
  line under the buttons reads `A run on {scenario} is waiting. Press
  **Save** or **Cancel** to show it.` The line is a polite live region,
  in the page from the moment the editor opens, so it is there before its
  text arrives. A newer run
  replaces the one named; a run on the edited scenario ends the wait, and so
  does turning Follow off. Turning it on again brings no run back. **Save**,
  **Cancel**, or undoing every change (which also closes the editor) moves the
  page once, to the newest waiting run's scenario, clearing a Playlist filter
  that doesn't list it. Meanwhile the chart, Scenario Stats, the PB card and
  the latest-run card stay on the edited scenario, and the run list adds the
  run ([2026-10-18][note-unsaved]).

### The dialog

- While the note has unsaved changes, each change of scenario the player
  makes and each departure the app can catch opens a dialog titled `Your
  scenario note isn't saved`, with **Keep editing**, **Discard** and **Save**
  and no close button. Focus starts on **Keep editing** and stays in the
  dialog. Escape and a click outside it mean Keep editing, which returns
  focus to the text box. **Discard** drops the text and goes where the player
  asked; **Save** saves, then goes. A failed save acts as Keep editing, with
  its error under the editor. Discard and Save drop a waiting run; Keep
  editing keeps it waiting ([2026-10-18][note-unsaved]).
- While the dialog is open its destination is fixed: a run that lands waits
  in the card, and the run toast's link does nothing
  ([2026-10-18][note-unsaved]).
- Its question, by route ([2026-10-18][note-unsaved]):
  - a pick in the Selected scenario dropdown, the run toast's link, a name in
    the run list's All scenarios view: `Save your changes to the note on
    {from} before you switch to {to}?`;
  - a Playlist filter change whose list lacks the edited scenario: `The
    **Selected scenario** list no longer holds {from}. Save your changes to
    its note first?`;
  - a navbar link, the header title, **Open scenario table**, and the
    browser's back and forward buttons: `Save your changes to the note on
    {from} before you leave the page?`.
- A pick, or a filter change that drops the edited scenario, has already
  happened when the dialog opens: the chart and the other cards redraw for it
  behind the dialog, and the note card does not. Keep editing writes the old
  scenario and filter back, and the browser remembers them, so a reload then
  opens on the edited scenario ([2026-10-18][note-unsaved]).
- The run toast's link is stopped before the page is drawn again. Save or
  Discard then selects its scenario in place, clearing a filter that doesn't
  list it, and the address stays as it was. A link to the edited scenario
  itself is stopped with no dialog, and nothing moves
  ([2026-10-18][note-unsaved]).
- A link that leaves the page is stopped, and Save or Discard then follows
  it. The back and forward buttons are kept from redrawing the page, the
  address goes back at once, and Save or Discard then moves through history
  again. A reload, closing the tab or going to another site gets the
  browser's own "Leave site?" prompt, set only while the note has unsaved
  changes; with none there is no prompt. A link that opens a new tab leaves
  the page as it is ([2026-10-18][note-unsaved]).

## The latest-run card

- The card reports the selected scenario's latest run: its last run in the
  newest session that holds one, in the order
  [sessions.md](sessions.md#sessions) sets, with the sessions split from
  every run in the store, as the run list splits them
  ([2026-10-18][follows]).
  It is worked out from the run store each time, never from the message a
  new run arrives in, so it is right on a page load with no new run
  ([2026-10-12][check]).
  During play with Follow on, the selected scenario is the one just played,
  so the card reports the run just played.
- Its first line reads `Latest run · {age}`, as the PB card's reads
  `PB · set {age}`. It doesn't name the scenario, which the Selected scenario
  field and the chart's title name ([SC2][first-line]). The age is how
  long ago the run ended, worded as the playlist tables' Last played words
  it, such as `just now` or `5 minutes ago`, and worded again every 30
  seconds, so during play it reads as the length of the break since the last
  run. Hovering or focusing the age shows the exact time, in the shared
  format with no seconds, such as `Oct 9, 2026, 5:24 PM`
  ([2026-07-11][timestamps], [T4][card-order]).
  The card has no control of its own apart from the age, which takes
  keyboard focus ([2026-10-18][follows]).
- The score is large, formatted as the playlist scenario table formats PB
  Score, with one badge beside it. A new PB shows "New PB", whether or not
  the run was judged. Otherwise a judged run shows "Threshold passed" or
  "Below threshold", and a run nothing judges shows no badge
  ([2026-10-12][check]).
  The badges are yellow, green, and gray in that order, drawn as the PB
  card's rank badge is: the page's text on a 20% tint of the badge's color,
  with a 1px solid border in that color, so each reads in both themes.
- Under the score are three lines: the comparison, the session line, and
  the run's sensitivity and accuracy ([SC3][card-lines]).
- The comparison line, at 13px, holds only comparisons: on a run that isn't
  a new PB, the typical phrase, then ` · `, then the run against the PB it
  was chasing, `3.6% above typical at session start · 85.8% of PB`. A part
  with nothing to say is left out, and with neither part the line is absent
  ([SC1][typical-start], [SC3][card-lines]).
- The PB part reads `{pct}% of PB`, or `{pct}% of PB pace`
  where the comparison is by pace. A new PB says how
  far it beat the previous best instead, with no typical phrase:
  `Up {pct}% on your previous best of {previous}`,
  `{pct}% faster than your previous best of {previous}` by pace, or
  `Your previous best was {previous}` over a previous best of zero or less.
  The percentage is a fact about the run, so it shows whether or not the run
  was judged, and an empty threshold doesn't hide it. Two kinds of run have
  none, and the line is absent: a scenario's first run, and a run that is
  not a new PB and is compared by score with a previous best of zero or less
  ([2026-10-12][check], [SC3][card-lines]).
  The percentage has one decimal and the two display caps
  ([Marks](#marks-the-check-and-the-star)): a run below the PB shows at
  most 99.9%, and a judged miss shows at most one tenth under its goal.
  The card is the one place a run's percentage of the PB is printed
  ([2026-10-13][run-toast]).
- The typical phrase measures the run against its scenario's typical score
  as it stood when the run's session began: the value after the scenario's
  last run before that session, from the same copy of the run store as the
  card's run ([typical_score.md](typical_score.md#api-and-snapshot-ownership)).
  Every run of a session meets the same value, and a later run in the
  session never moves it. With no run before the session, or an unknown
  value there, there is no phrase. A new PB has none, because it beats every
  earlier run and the phrase could only read above
  ([SC1][typical-start]).
  - By score: `(score − typical) / typical × 100` to one decimal,
    `{pct}% above typical at session start` or
    `{pct}% below typical at session start`, and
    `Matches typical at session start` where it rounds to 0.0. A typical
    score of zero or less has no phrase.
  - By pace, when every run behind the value is of the run's own version, a
    performance file answers for that version, and both times are positive,
    as the scenario table's Typical Rank decides it: the run toast's
    `percent_faster`, `{pct}% faster than typical at session start` or
    `{pct}% slower than typical at session start`, and `Matches …` at 0.0.
    That is decided apart from the PB part's measure, so one line can mix
    them, and the words name each ([SC1][typical-start],
    [2026-10-05][pace]).
  - A value that wasn't recent when the session began, judged then and not
    when the card is read, has the scenario table's 13px history clock after
    the phrase, hidden from a screen reader, which hears `, Not recent`
    instead ([SC1][typical-start], [2026-10-22][old-mark]).
  - The phrase is focusable, with the age's dotted underline, and hovering
    or focusing it, the clock included, shows
    `Typical score when this run's session began: {typical}`, the value
    formatted as the scenario table formats a typical score. On an old
    value a second paragraph follows: `Fewer than 10 of its runs were from
    the 30 days before the session began, so it may have been out of date.`
    The hover is at most 360px wide ([SC1][typical-start]).
- The session line names the run in its session, then ` · `, then the time
  spent on its scenario: `Run 7 this session · 9 min on this scenario`
  ([SC3][card-lines]). In the newest session the run reads
  `Run {n} this session` while the session is in progress, and
  `Run {n} last session` once it has ended. A run in an older session names
  the session as the run list names its row, by when it began, with the year
  where it is not this one: `Run 7 (Oct 16, 2:00 PM session)`,
  `Run 8 (Jul 20, 2020, 11:47 PM session)`. The year is judged against the
  app's own date. `{n}` counts the session's runs on the run's scenario
  ([2026-10-18][follows]).
  The time reads `{duration} on this scenario`, the time spent on the
  scenario in the run's session, as
  [sessions.md](sessions.md#where-sessions-show) defines it. Where that time
  can't be known it reads `Time on this scenario unknown`
  ([2026-10-12][check], [2026-10-18][follows]).
- The last line is the run's sensitivity and accuracy, worded as the PB
  card's last line words the PB run's: `{cm/360} cm/360 · Accuracy
  {accuracy}%`, or `Accuracy {accuracy}%` where the run's cm/360 is unknown
  ([SC3][card-lines], [2026-10-18][accuracy]).
- The session line and the last line are 12px, in the scenario table's
  readable grey for an old typical value, `#676d75` light and `#a6a6a6`
  dark, quieter than the comparison line and at least 4.5:1 in both themes.
  The first line keeps the theme's dimmed grey ([SC3][card-lines]).
- A measured time, here and in the run list, is rounded to the nearest
  minute, a half rounding up: `9 min`, `1 hr 6 min`
  ([2026-10-13][nearest-minute]).
  A time that rounds to zero reads `<1 min`, so that form means under 30
  seconds.
- The card is 480px wide, a width of its own that equals the run list's
  minimum, which is the list's width with the default columns
  ([2026-10-22][card-width], [2026-10-29][card-480]), and as tall as the
  top row. It is never less than its tallest state, so nothing that changes
  between runs changes its height, and the page doesn't jump. In the wide
  layout every line fits on one, and the floor is 135px. In a page area of
  900px or less, where the card can be 380px wide, the floor is 177px: the
  comparison by pace with an old value's clock on two lines, over the
  session line on two, with the top row's 12px above the first line and
  12px under the last. Its lines start from its top, as the other score
  cards' do ([SC4][top-aligned], [SC1][typical-start]).
- With no run to report, the card's first line reads `Latest run` alone, and
  the selection decides first, as on the PB card
  ([2026-10-18][follows]):
  - no scenario selected and no runs in the store: "No runs yet" over "Play a
    scenario in KovaaK's. Select it to see its latest run.";
  - no scenario selected, the store has runs: "No scenario selected";
  - the selected scenario has no runs, whether or not the store has any: "No
    runs yet" over "Play this scenario in KovaaK's and your latest run will
    show here."

  Each is at the same height.
- The card is rewritten when a run lands on any scenario, when the selected
  scenario changes, when the Score threshold percentage changes, when the
  newest session stops being in progress, and when the app's date moves on.
  Whether a late run reaches the card is decided by the selected scenario's
  latest run: a run on it newer than that run becomes the card's run, even
  when it is older than the store's newest, and one older leaves the card as
  it was ([2026-10-18][follows]).
- The card, the chart's ring and the run list's highlight identify the
  selected scenario's latest run, whether the selection comes from the
  dropdown, a scenario name in the list, a link or Follow. With Follow off,
  a run on another scenario leaves all three on the selection's run. With
  no scenario selected or no runs for it, neither highlight marks a run
  ([2026-10-23][latest-highlights]).

## The PB card

The card's lines, local-record scope and leaderboard presentation follow
[T3][pb-card]; their ordering and relative ages follow [T4][card-order].

- The card reports the selected scenario's personal best as this app
  records it, worked out from the run store each time, as the latest-run
  card is. The PB is the earliest run to reach the scenario's high score,
  the run the playlist scenario table's PB columns read
  ([2026-10-05][stars]).
- It is 300px wide, after Scenario Stats in the score pair at the first
  column's right end, beside the latest-run card, and as tall as its line
  ([2026-10-21][score-strip]). Its frame is the other cards', and its lines
  start 12px below its top, with no padding at its bottom
  ([SC4][top-aligned]).
- Its first line reads `PB · set {age}`: how long ago the PB run ended,
  worded as the playlist tables' Last played words it, such as `5 days ago`,
  and worded again
  every 30 seconds. Hovering or focusing the age shows the exact time, in the
  shared format with no seconds, such as `Oct 9, 2026, 5:24 PM`
  ([2026-07-11][timestamps]).
- The score is large, formatted as the playlist scenario table formats PB
  Score. Hovering or focusing it shows the line the latest-run card showed
  when this PB landed: `Up {pct}% on your previous best of {previous}`,
  `{pct}% faster than your previous best of {previous}` by pace, or
  `Your previous best was {previous}` over a previous best of zero or less
  ([2026-10-12][check]).
  A PB set by the scenario's first run beat nothing, so its score has no
  hover and no dotted underline.
  The PB run follows the store's order, which keeps runs ending in the same
  second as loaded. On a tie in that second, the hover instead describes the
  first run in play order to reach the score, preserving the comparison
  shown when that score landed ([T3][pb-card]).
- While the Playlist filter holds a benchmark that gives the scenario a
  ladder, a badge beside the score names the rank the PB has reached, as the
  benchmark table's Rank column does, in the page's text color on a tint of
  the rank's color with a border in that color, so a pale rank stays legible
  in both themes. There is no badge below the first threshold, with no
  benchmark selected, or for a scenario the benchmark has no ladder for.
- Under the score is the next rank: `{threshold} {rank} · {gap} · {points}
  to go`, such as `3,700 Lavender · +1.3% · 47 to go`, or `899 Lavender ·
  +2.8% faster · 2.83 to go` where the gap is by pace. A dot of the rank's
  color leads it, and the threshold, a score formatted as PB Score, is bold.
  The gap is the benchmark table's Next Rank figure and the points its
  tooltip's, both from the table's own walk of the ladder, with the pace
  constant chosen as the table chooses it
  ([2026-09-27][next-rank], [2026-10-05][pace]).
  Once every rank is reached the line reads `Top rank`. It is hidden with
  no benchmark selected, with no ladder, and wherever the table's Next Rank
  cell reads `N/A`.
- Under the next rank is the leaderboard line, the player's position on
  KovaaK's board, which [scenario_rank.md](scenario_rank.md) specifies in
  full: its states, its hints, its hover, and what **Refresh** answers.
  With a percentile it reads `{percentile}% percentile`, two decimals, and
  the position and the total are the first line of its hover. In every
  other state it reads `Position: {value}`, as the Scenario Stats card's
  Position field did. **Refresh** follows on the same line where it fits.
- The leaderboard line follows the local PB: a scenario with no local runs
  has no line, and nothing looks it up. KovaaK's places the best score its
  server holds, which can differ from the local PB, for example after runs
  on another computer, and the card shows both as they are.
- The last line is the PB run's sensitivity and accuracy, 12px in the
  latest-run card's readable grey, so the two cards' last lines read alike
  ([SC3][card-lines]): `{cm/360} cm/360 · Accuracy {accuracy}%`.
  The sensitivity is the scenario table's PB cm/360, trailing zeros dropped
  ([2026-09-27][trailing-zeros]), and the accuracy is the hit accuracy to two
  decimals, as the latest-run card shows a run's ([2026-10-18][accuracy]).
  Where the table's PB cm/360 is unknown the line reads
  `Accuracy {accuracy}%` alone.
- With no scenario selected the card reads `No scenario selected`, and for
  a scenario with no local runs `No local PB yet` over `Play this scenario
  to record one in this app.`. Its first line then reads `PB`, and it has no
  leaderboard line.
- The card is rebuilt by every run that lands on the selected scenario,
  whether or not it sets a new PB: whether the next rank's gap is by pace
  follows the scenario's newest version, so a run that beats nothing can
  change it. A new scenario rebuilds it, and the Playlist filter, which
  decides the badge and the next rank. A run on another scenario leaves it.
  The position's own reads write the leaderboard line.
- In every state that can change between runs, the card fits in the row the
  dropdowns' column sets: 141px at 2560px. With no KovaaK's username the
  line's hint takes two lines and the row is about 164px.
- The card is not a landmark or a button, and its first line is text. The
  dotted score, the percentile, and the age take keyboard focus and show
  their tooltips, as the latest-run card's age does.

## The chart

- The chart has three modes, chosen by a segmented control in the chart's
  header whose accessible name is "Chart mode": "Score vs Run", "Score vs
  Time", and "Score vs Sensitivity". It opens on Score vs Run
  ([2026-10-12][every-run]).
- Each mode plots every run of the scenario in its range as a point, legend
  "Run data point"
  ([2026-10-12][every-run]).
  Score vs Run and Score vs Time also draw the
  [typical score](../glossary.md#typical-score) over their runs, as a line
  inside two bands, below ([TS3][typical-chart], [TS4][typical-bands]).
  Score vs Sensitivity draws no summary line
  ([2026-10-12][every-run]).
- Score vs Run plots the runs in the order they were played, evenly spaced.
  The order is the one [sessions.md](sessions.md#sessions) sets, so the chart
  and the run list never disagree about which run came first. A run's place
  on the axis is its number in the scenario's whole history, so it keeps its
  place when the range changes. The axis title is "Run" and its labels are
  dates, one at the first plotted run of a day, in the form `Oct 12`, or
  `Dec 7, 2025` in another year than this one. The labels are thinned on the
  server for a plot 330px wide, from the newest back, so the day being played
  keeps its label
  ([2026-10-12][every-run]).
- Score vs Time plots each run at its own timestamp, on an axis titled
  "Date". Score vs Sensitivity plots each run at its sensitivity-and-scale
  string, on an axis titled "Sensitivity", with the sensitivities in sorted
  order
  ([2026-10-12][every-run]).
- The range is a select beside the mode control, with the accessible name
  "Range" and no visible label. Under Score vs Run it counts runs: "Last 50
  runs", "Last 100 runs", "Last 200 runs", or "All runs". Under the other two
  modes it counts days: "Last 7 days", "Last 14 days", "Last 30 days", "Last
  90 days", "Last 12 months", or "All time". The chart opens on the last 100
  runs, or the last 90 days. The mode and both ranges persist in the browser,
  one remembered range for runs and one for days: they are two selects, both
  always in the layout, and the one the mode does not use is hidden
  ([2026-10-12][every-run]).
- A range of N days is N calendar dates, counting today: it starts at local
  midnight N minus 1 days before today, so on October 11 the last 7 days are
  October 5 to 11. The last 12 months are 365 days, counted the same way. The
  date is the app's own, never the browser's. A chart left open past midnight
  is redrawn within 30 seconds of the date moving on
  ([2026-10-12][every-run]).
- The plot title is the scenario's name alone
  ([2026-10-12][every-run]).
- Score vs Run and Score vs Time mark each plotted run that set a
  [new PB](../glossary.md#new-pb) with a star: a second trace, legend "New
  PB", drawn over the run points. A new PB is a run whose score is strictly
  above every earlier run of its scenario, judged oldest first over the
  scenario's whole history, at every sensitivity and including runs the range
  leaves out. So a tie is not one, the earliest run to reach a score holds
  it, and the scenario's first run is not one. A star belongs to its run, not
  to a position on the chart. A new PB the range leaves off the chart gets no
  star and still counts in the comparison. With no new PB among its points
  the chart has no New PB trace and no legend entry, and Score vs Sensitivity
  never has one
  ([2026-10-05][stars],
  extended to Score vs Run by
  [2026-10-12][stars-run]).
  New PBs are judged in the order the runs were played, so a star sits on the
  same run of a same-second pair as the axis puts first.
- The selected scenario's latest run carries a ring when the range holds
  it, matching the Latest run card and the run list's highlight. The range
  is never widened to include it. A run on another scenario with Follow off
  leaves the ring and the chart's zoom as they are
  ([2026-10-23][latest-highlights]). The ring has no legend entry or hover
  of its own, and is drawn over a star. It is the app's blue, `#1c7ed6` on
  the light background and `#74c0fc` on the dark one
  ([2026-10-12][every-run]).
- Score vs Run draws the typical score, as
  [typical_score.md](typical_score.md) defines it: a line with a point at each
  plotted run whose value is known, legend "Typical score", and two bands
  around it, "Middle 50%" (P25 to P75) and the lighter "Middle 80%" (P10 to
  P90). A run before the scenario's first known value has no point. When the
  plotted range holds only one known value, as on the run that first makes
  it known, that value is drawn flat for half a run on either side of its
  run, so the line and the bands show. Every
  value is worked out over the scenario's whole history and only then is the
  range applied, so the value at the range's first run counts the runs the
  range leaves out, as the stars do. A value's sessions are split over every
  scenario's runs, taken from the same copy of the run store as the
  scenario's own
  ([TS1][typical-definition], [TS3][typical-chart], [TS4][typical-bands]).
- On Score vs Run a point is drawn at full strength when its value was recent
  at its run, and faded, at 35% opacity, when it wasn't. A faded stretch
  starts at the last full-strength point before it and ends at the first
  after it, so the line and the bands run on with no gap and no step. A
  point's strength never changes after its run. How recent the value is now
  is not the chart's to say
  ([TS6][typical-recency]).
- Score vs Time draws the same values, each worked out over the scenario's
  whole history, so the value at the range's first run counts the runs the
  range leaves out. Each value holds flat from its run to the next plotted
  run, with a step at each run, and the line ends at the newest plotted run,
  on that run's value: how recent the value is now is not the chart's to say
  here either. A value sits at its own run's time, so of two runs that ended
  in the same second, which the chart can draw in another order, the line
  holds the later-played run's value from that second on, and the earlier
  one's value, held for no time, has no point
  ([TS3][typical-chart]).
- A hold is at full strength while its value is recent, and faded, at 35%
  opacity, from the moment fewer than 10 of its runs are recent: when its
  10th-newest run turns 30 days old. It is still recent at that moment and
  faded after it. A value that wasn't recent at its run holds faded
  throughout. A faded part ends where the next run's value begins, and starts
  where the full-strength part before it ends, so the line and the bands run
  on with no gap
  ([TS6][typical-recency]).
- When the plotted range holds only one value to draw, as on the run that
  first makes a value known or in a range that holds one run, that value
  holds for no time. It is marked at its run instead: the line by a level
  stroke and each band by a bar from its bottom to its top, both 14px wide
  ([TS3][typical-chart]).
- The line and the bands draw under the run points, the stars and the ring,
  by plotly's `zorder` −1, although they come after them in the figure: the
  run trace stays first and keeps the template's first color. Among
  themselves the line draws over the bands, and full strength over faded.
  Each metric is one legend group, its entry after "New PB" in the order
  "Typical score", "Middle 50%", "Middle 80%". A faded stretch has no entry of
  its own, unless the figure holds only faded stretches of that metric.
  Clicking an entry hides the metric whole, faded stretches included. As with
  the stars the click is not remembered ([TS3][typical-chart]). The switches
  are in [Chart options panel](#chart-options-panel).
- They are gray in both themes, with no color setting. On the light
  background the line is `#343a40`, 2.5px wide, the middle 50% that gray at
  14% opacity, and the middle 80% at 7%. On the dark one they are `#dee2e6` at
  the same strengths. The figure is built with the light colors, and the
  presentation step recolors the traces by name with the theme, as it does
  the ring
  ([TS3][typical-chart], [TS4][typical-bands]).
- The line has a hover of its own at each point, its labels bold:
  `Typical score: {score}`, then `Runs: {n} in {s} sessions · {first} to
  {last}`, then `Recent: {k} of {n} in the 30 days up to this run`, then
  `Middle 50%: {p25} to {p75}` and `Middle 80%: {p10} to {p90}`, each band's
  line only while its switch is on. One session reads `1 session`, a span
  on one date reads `on {date}`, and a date carries its year only in another
  year than this one. Each figure is rounded as
  [typical_score.md](typical_score.md#display-rounding) says. The bands take
  no hover, and the run points' hover is unchanged
  ([TS3][typical-chart]).
- On Score vs Time a hold has a point at each end, both with its value's
  hover, the counts as they were at its run. On the faded part of a hold
  whose value was recent at its run, the Recent line reads
  `Recent: too few · last run {date}` instead, with the date of the value's
  newest run, since the count changes along the hold
  ([TS3][typical-chart], [TS6][typical-recency]).
- A run recorded under a game's own sensitivity scale is normalized to cm/360
  when its file is parsed, from the file's own `Sens Increment` and `DPI`
  fields, by `cm/360 = 360 x 2.54 / (0.07 x increment x DPI)`. A run whose
  file lacks either field, or carries one the conversion cannot use, keeps its
  recorded value and scale. Every consumer reads the normalized fields, so the
  normalized sensitivity-and-scale group is the unit for grouping, for run
  placement, and for first-sensitivity detection
  ([2026-09-11][normalize]).
  A cm/360 value, native or converted, is rounded to one decimal place, so a
  typed value and a converted one a few hundredths apart share a group. The
  buckets have hard edges: `40.849` and `40.851` land in `40.8` and `40.9`. A
  value on any other scale keeps exactly what its file recorded, so
  `0.32 Valorant` reads `0.32 Valorant`
  ([2026-09-27][precision]).
  A converted run also keeps the value, scale, and DPI its file recorded,
  unrounded, for its chart tooltip and the run list's Sensitivity tooltip
  ([2026-09-26][recorded]).
- Point hover has four lines, with no blank line after its timestamp.
  Its first line is the run's full absolute timestamp with seconds, as
  [the timestamp rule][timestamps] requires. In Score vs Run alone it adds
  ` · {n} runs ago`: the number of newer imported runs of that scenario in
  play order, across all sensitivities and versions, independently of range
  or zoom. One reads `1 run ago` and zero reads `Latest run`.
  The next lines are `Score: {score}`,
  `Session: {session_name} · run {session_number} of {session_total}` and
  `Sensitivity: {sensitivity}`. Labels are bold. The score uses the list's
  exact formatting, including thousands separators and up to two decimals
  with trailing zeroes dropped ([2026-10-24][compact-hover]).
- The session name exactly matches its Session row in the list, including
  the year when it differs from the app's current year. It names the whole
  play session, including play on other scenarios before this scenario.
  The numerator matches the run's `#` in the list; the denominator is the
  first count on its session's `12 of 47 runs` readout. Both count only
  this scenario, across versions, sensitivities and returning visits.
  The total includes runs after the hovered run and outside the chart range.
  During an ongoing session, the total so far and older points' run ages grow
  as more runs of that scenario are imported ([2026-10-24][compact-hover]).
- Sensitivity stays in every mode, including the converted run's original
  setting and DPI, such as `40.8 cm/360 (0.16 Valorant at 1600 DPI)`.
  Native and unconverted runs have no recorded-setting suffix
  ([2026-09-26][recorded]). Every point tooltip states the point's position on
  both axes; only Score vs Run needs a run-age readout because its Run-axis
  labels show dates. Accuracy is absent from the point tooltip and remains
  in the list ([2026-10-24][compact-hover]). A click on the point opens the
  run in [the run viewer](#the-run-viewer), which shows it.
  A star carries the same tooltip as its run point, including when ordinary
  dots are hidden through the legend ([2026-10-23][linked-hover]).
  Runs at one position share one hover, the one whose point comes last in the
  run trace. In Score vs Time that is runs that ended in the same second with
  the same score, and a new PB is ordered last among them, so the star's
  hover names the run that set the PB. Score vs Run gives every run its own
  position. Score vs Sensitivity still shares positions and has no stars
  ([2026-10-05][stars]).
- Three overlay families, all dashed labelled lines. "PB score ({value})"
  and "Score threshold ({value})" draw at the current personal best and at
  the configured percentage of it, while a run's verdict is judged against
  the PB the run was chasing
  ([2026-07-08][previous-pb]).
  On a [time-scored scenario](#time-scored-scenarios) whose PB can be
  measured by pace, the threshold line draws at the score that finishes at
  that percentage of the PB's pace, `C − (C − PB) × 100 / goal` for the
  scenario's constant `C`: a PB of 896.2 at 95% and a constant of 1,000
  draws at 890.74, where the score form would draw at 851.39. A goal above
  100% puts the line above the PB. The annotation is unchanged and still
  shows a score
  ([2026-10-05][pace]).
  "Rank thresholds" draws the selected playlist's rank lines, in ladder
  order and color: the ranks whose thresholds land inside the plotted score
  range plus every rank tied at the nearest threshold below and at the
  nearest above, or the whole ladder with "Show all ranks" on. No playlist
  selected means no rank lines, and an empty threshold percentage skips the
  threshold line. The rank lines redraw at once when the Playlist filter
  changes
  ([2026-10-12][every-run]).
- With "Accuracy targets" on, each drawn rank line gets its
  [accuracy target](../glossary.md#accuracy-target) just outside the plot's
  right edge, level with the line, in the theme's text color, such as
  `39.2%` beside `Saffron (2350)`, on all three modes. The lines, their
  labels and the chart's margins are unchanged: the figures sit in Plotly's
  default 80 px right margin, so the plot keeps its width. Only rank lines
  get one, not the PB or threshold line ([2026-10-30][at-margin]). A zoom
  drops the figure of a line it leaves out of view.
- A target is the rank's threshold over the scenario's score at 100%: the
  median of its runs' scores over their hit accuracy, over the runs of its
  newest run's version with an accuracy and a score above zero, when there
  are at least 5 such runs and at least 90% of them, counted in whole runs,
  land within 2% of that median. A version the app recognizes as
  [time-scored](#time-scored-scenarios) has none, whatever its runs. It is
  worked out on every build over the scenario's whole history, never the
  plotted range, and is an estimate for a run with the median run's shots
  and the fire button held throughout ([2026-10-30][at-rule]). It reads one
  decimal, rounded up to the next tenth (an exact 40% reads `40.0%`), a
  target above 100% gets no figure, and a threshold at or below zero reads
  `0.0%` ([2026-10-30][at-tenth]).
- With "Accuracy targets" on, a chart that draws rank lines but no figure
  shows one quiet note under the x axis's title, right-aligned, at 12 px and
  slightly faded, and its bottom margin grows from Plotly's 80 px to 112 px.
  The note names the first reason that applies: "This scenario has no
  accuracy targets, because it's scored by completion time.", "Accuracy
  targets need at least 5 runs of this scenario.", "Accuracy targets need at
  least 5 runs of this scenario since it was last updated.", "This scenario
  has no accuracy targets, because your scores here don't follow your
  accuracy closely enough.", or, when there is a score at 100% and every
  drawn rank is above 100%, "Every rank on the chart has an estimated
  accuracy target above 100%." With no rank line drawn there is neither
  figure nor note ([2026-10-30][at-note]).
- Zooming the x axis refits the score axis to what is in view: every
  visible trace's points inside the x window, padded by 5% of their span. The
  stars and the ring repeat run points, so they never change the fit. The
  typical score's line and bands take part, drawn as lines, a band as its
  outline: their points inside the window, and the part of each of their
  segments that crosses it, up to the window's edges. So the line and the
  bands stay in view, a Score vs Time hold that spans the whole window
  included ([TS3][typical-chart]). Overlay lines are not
  part of the fit, so a line beyond the fitted range is out of view while
  zoomed. A trace hidden from the legend is left out too, and showing or
  hiding one while zoomed refits. A window with none of these in it leaves
  the score axis as it was. Double-clicking the plot, "Reset axes", "Autoscale", and
  any new figure (a rebuild or an appearance change) return both axes to the
  full autorange. Double-clicking the x axis alone also returns a refit score
  axis to its full autorange, but leaves a score range the user dragged
  themselves.
- Until the first data callback resolves, the chart is a transparent,
  annotation-free placeholder. A result with nothing to plot gets an explicit
  empty state instead
  ([2026-07-16][pre-hydration]):
  "No scenario selected" / "Select a scenario to see your score history.",
  "No local runs found" / "Play this scenario once and the graph will fill
  in.", and, in the two modes that count days, "No runs in this range" /
  "Choose a longer range or play more runs.". An unexpected mode value gets
  "Unsupported graph option" / "Choose <b>Score vs Run</b>, <b>Score vs
  Time</b>, or <b>Score vs Sensitivity</b>.". A control named in an
  empty-state message is bold through `<b>` in the annotation string
  ([2026-09-14][copy]).
- The figure takes the Mantine light or dark template with the app theme.
  With no point color chosen the run points draw in the template's own blue,
  `#228be6` light and `#1971c2` dark
  ([2026-08-20][points]
  as amended by
  [2026-08-21][default-color]).
  A New PB star is plotly's `star` symbol, gold `#fab005` with a 1px
  `#5f3d00` outline, the same in both themes
  ([2026-10-05][stars]).
- "Point size" is a Small | Default | Large preset (Small 4px, Large 10px).
  Default leaves the generated size untouched rather than writing a pixel
  count. It sizes the New PB stars too: 9px on Small, 16px on Large, and the
  12px they are generated with on Default
  ([2026-10-05][stars]).
  It sizes the ring as well, 14px, 18px, and 22px, wide enough to clear a
  star at the same setting.
  "Point color" accepts eight curated swatches on one row, a picker,
  or a typed hex value. The empty value means Default (placeholder
  "Default"), a "Use default" button is the only way back to it, and
  anything unparseable falls back to the generated color. The empty field's
  preview swatch shows the color the graph is using in the current theme
  ([2026-08-20][points]
  as amended by
  [2026-08-21][default-color]).
- Color restyles only the run trace, and size restyles the run trace, the
  New PB trace, and the ring. Each is selected by its trace name in a cheap
  presentation callback applied after theming: the expensive chart rebuild
  never reruns for an appearance change, and placeholder and empty figures
  pass through untouched, as does a figure with no New PB trace. Nothing else
  on the chart is customizable, the stars' own color and shape included, and
  that boundary is deliberate
  ([2026-08-20][points],
  with the stars' size as its one exception, set by
  [2026-10-05][stars]).
- The stars have no control. Clicking "New PB" in the legend hides them and
  leaves every run point, and the choice is not remembered: the figure sets
  no `uirevision`, so the next figure draws them again, whether it comes from
  a new run on the scenario, a control that rebuilds the chart, or an
  appearance change
  ([2026-10-05][stars]).
- The chart keeps plotly.js's default modebar, which offers "Download plot as
  a PNG", a save to this PC, and "Share chart...". Pressing "Share chart..."
  opens plotly.js's confirmation naming Plotly Cloud, and nothing is sent
  before its Share button. Share opens Plotly Cloud in a new browser tab and
  hands that tab the figure only once Plotly Cloud reports the user signed in
  there. A blocked popup ends the flow with nothing sent. The figure is
  everything plotted: the title, each plotted run's timestamp, score,
  session name (its start time), run number and total within that session,
  run-age text, sensitivity with the setting a converted run was recorded
  at, and x value, the New PB stars and the ring, which repeat the position and
  score of runs already in it, the label and value of each overlay line
  drawn, and on Score vs Run and Score vs Time the typical score's line and
  bands with what the line's hover shows at each point
  ([TS3][typical-chart]). Run-age text is included even in Score vs Time and
  Score vs Sensitivity, whose hover does not show it. Accuracy is not included
  in the figure's run data. Neither the button nor the flow is app code: the
  graph passes no `config`, so both are plotly.js 4 defaults, kept on purpose.
  The Aim Training Journey graph passes no `config` either and carries the
  same toolbar and flow. Its figure is the playlist lines, their dates and
  progress percentages, and the aim-training-hours checkpoint labels
  ([2026-09-12][share]).

## The run list

- The list is a second column to the right of the chart, always shown
  ([2026-10-12][column]). It is as wide as its shown columns need, 19px for
  its borders and a classic scrollbar plus each shown column's width, never
  narrower than 480px. Its default columns need 407px, so it sits at that
  minimum; with Shots Fired on they need 489px, with Reloads or Avg FPS
  471px, with FOV 523px, and with every column 733px
  ([2026-10-29][marks-30]). Growth is capped so the chart keeps 480px where
  possible. In a narrow window, a list that needs up to 500px keeps it and
  the chart gives ([2026-10-22][list-minimum]). The page draws the list at
  its 480px minimum until the stored column choices load. Where the list is
  wider than its columns need, `#`, Time and Accuracy share the spare room
  in proportion to their widths, and none narrows below its own width;
  every other column, the marks included, keeps one width
  ([2026-10-29][marks-30]). Past the chart's floor the
  list scrolls sideways inside its own box, and its session rows, scenario
  rows and other full-width rows stay whole in view while the run rows
  scroll under them ([2026-10-22][list-width]). It has two views, This
  scenario and All scenarios ([2026-10-14][all-scenarios]).
- Its header is one line: a switch between the two views at the left, with
  the "Expand all" button and the "Columns" menu at the right. The switch is
  a segmented control whose accessible name is `Run list view`. The list
  starts on This scenario, the browser remembers the switch, and pressing it
  shows the other view from its top with keyboard focus left on the switch.
  At the list's 480px minimum the switch and both buttons share one line,
  including the wider "Collapse all" label. In a narrower stacked page the
  buttons wrap under the switch ([2026-10-14][all-scenarios],
  [2026-10-18][heading-line], [2026-10-22][list-minimum]).
- The header also holds a heading line, before the switch, for screen
  readers only: it is hidden from view in both views, and it is a line of
  text, not an HTML heading ([2026-10-18][heading-line]). On screen the
  Selected scenario field and the chart's title name the scenario
  ([SC2][first-line]).
  Under This scenario the line reads `{scenario} · {n} runs`, or `1 run`,
  where `{n}` counts every run of the scenario in the run store, the figure
  Scenario Stats shows as Total runs. Under All scenarios it reads
  `All scenarios · {n} runs`, where `{n}` counts every run in the store
  ([2026-10-14][all-scenarios]).

### This scenario

- The list shows the selected scenario's runs on two levels: sessions, newest
  first, and under each the scenario's runs in that session, newest first.
  Only sessions that hold a run of the scenario are listed, with one
  exception: the newest session is always the first row, in progress or not,
  even when the scenario was not played in it
  ([2026-10-12][column]).
- A session row is named by when the session started: `Oct 4, 9:45 PM`, or
  `Dec 30, 2025, 9:45 PM` in an earlier year. Its right side reads how many
  of the session's runs were on this scenario, such as `7 of 47 runs` or
  `1 of 1 run`. The first row carries an "In progress" badge while its
  session is in progress. No session row in this view gives its length;
  every session's length is available in All scenarios
  ([2026-10-23][inline-summaries]). With the selected scenario not played in
  the first row's session, the row reads `0 of 47 runs` and, opened, "Not
  played in this session"
  ([2026-10-12][column]).
- The count on every session row is a button drawn as a link, `0 of 47 runs`
  included. Its hover reads "Show the whole session". A click on it does not
  open or close the row: it switches the list to All scenarios, opens that
  session and every scenario row of the selected scenario in it, scrolls the
  session's row to just under the first row, and puts keyboard focus on that
  row. Rows already open in the tree stay open. All scenarios then loads as
  far back as the session if it had loaded fewer sessions, and the session is
  the last one listed. The switch moves with the jump, so a reload afterwards
  opens on All scenarios. A tree that does not hold the session shows from its
  top, with focus on its first row ([2026-10-14][count-link]).
- A run row has six columns by default and up to ten: `#`, the run's
  number among this scenario's runs in its session, counted in the order they
  were played, "Time", a time of day with no seconds, "Score", the marks,
  "Accuracy" to two decimals with trailing zeros kept, such as `82.31%` or
  `100.00%` ([2026-10-18][accuracy]), "Shots Fired", "Reloads",
  "Sensitivity", "FOV", and "Avg FPS". Shots Fired, Reloads, FOV and Avg FPS
  are hidden until turned on in the Columns menu ([2026-10-22][new-columns],
  [2026-10-29][shots-hidden]). The marks column is 30px, has no visible
  header, and its accessible name is "Marks" ([2026-10-29][marks-30]). Shots
  Fired is shown on every scenario and counts the shots of the first weapon
  the stats file lists. Sensitivity is the run's normalized
  sensitivity-and-scale string, as on the chart's axis. Columns don't sort
  ([2026-10-12][column]).
- A converted run's Sensitivity cell has a native tooltip with its normalized
  value followed by its original game setting and DPI, such as
  `40.8 cm/360 (0.16 Valorant at 1600 DPI)`. Original values stay unrounded,
  and whole values drop trailing zeroes. Native and unconverted runs have no
  extra tooltip. This applies in both list views ([2026-10-24][compact-hover]).
- Reloads is the stats file's count, such as `0` or `12`. FOV is the FOV the
  run was played at, the number with trailing zeros dropped, then its scale,
  such as `103 Overwatch`, or the number alone where the file names no scale.
  A scale too long for the column is cut after the number, and the cell's
  native hover gives its whole text. Nothing is converted. Avg FPS is rounded
  to a whole number, such as `676` or `1,024`. A field the file lacks or
  can't be read shows an empty cell, never a zero ([2026-10-22][new-columns]).
- A divider marks where the scenario was left and returned to within a
  session, and counts what was played between: `10 runs on 3 other
  scenarios`, or `1 run on 1 other scenario`.
- A date header names the date of any listed run that is not on the date its
  session started: `Oct 12`, or `Jan 1, 2027` in another year than this one.
  A run's date is the date it ended on. Where any of a session's runs of the
  scenario has another date than the session's start, each date among those
  runs gets a header, the start date included. Two cases have one date among
  the listed runs and still get its header: a scenario played only after
  midnight in a session that started before it, and a single run that started
  before midnight and ended after it. Where a header and a divider fall
  between the same two runs, the divider comes first.
- The selected scenario's latest run is highlighted, matching the Latest
  run card. Its row keeps the highlight even when the chart's range leaves
  its point off the chart. A selection change does not open rows or scroll
  the list to reach it. The highlight is a look alone and tells a screen
  reader nothing ([2026-10-23][latest-highlights]).
- With runs and no scenario selected, this view reads "No scenario selected"
  with the switch still above it, and "Expand all" and "Columns" out of view.
  A selected scenario with no local runs lists the newest session alone
  ([2026-10-14][all-scenarios]), and the latest-run card above it reads "No
  runs yet". The hidden heading line reads `{scenario} · 0 runs`
  ([2026-10-18][heading-line]).
- The grid's accessible name is `Runs of {scenario}, by session`.

### All scenarios

- The list shows every session, newest first, whatever the Playlist filter
  holds, on three levels: sessions, the scenarios played in each, and each
  one's runs. The newest session is the first row
  ([2026-10-14][all-scenarios]).
- A session row reads its name, the "In progress" badge on the first row
  while its session is in progress, then `{length} · {n} runs · {k}
  scenarios`, such as `1 hr 6 min · 47 runs · 7 scenarios`, singular where a
  count is one. `{k}` counts scenarios, not rows. Every session row gives its
  length, and only the first row's length has the hover.
- Under a session is a scenario row per visit, so a scenario that was left
  and returned to has a second row. The rows are numbered in the order they
  were played and listed newest first. A scenario row reads
  `{number}. {scenario}`, its run count, such as `2 runs`, and a star where a
  new PB was set in that visit, whose hover and accessible name are "New PB".
  The name is cut short with an ellipsis before the count is, and the hover
  on the part around it gives the whole name ([2026-10-14][all-scenarios]).
- A scenario's name is a button drawn as a link, whose accessible name is
  `Show {scenario}`. A click on it selects that scenario for the whole page,
  clearing a Playlist filter that does not list it, and the view stays on All
  scenarios. The row does not open or close, and the list does not scroll. A
  press on the selected scenario's own name changes nothing. The live region
  says `Selected scenario: {scenario}`, and keyboard focus stays on the
  name's button ([2026-10-14][all-scenarios]).
- Under a scenario row are its runs, newest first, in the columns of This
  scenario with the same marks. `#` is the run's number among its
  scenario's runs in the session and carries on into a second visit, so a run
  has the same number in both views. Every listed scenario's runs are marked
  ([2026-10-14][all-scenarios]).
- There are no dividers. A date header under a scenario row follows This
  scenario's rule asked of that row alone: once any of its runs is on another
  date than the session began, each date among its runs gets a header. A
  closed scenario row shows no date.
- The selected scenario's rows carry a band down their left edge, its
  scenario rows and the runs under them, and its names' buttons carry
  `aria-current`. With no scenario selected, or one with no run in the listed
  sessions, nothing is marked. The tree never scrolls to the selected
  scenario or loads older sessions to reach it. The band is a look alone. The
  selected scenario's latest run carries the same highlight as under This
  scenario, so that row can carry both. Clicking a scenario name in an older
  visit still highlights its latest run wherever it is listed, leaving open
  rows and the scroll position as they are
  ([2026-10-14][all-scenarios], [2026-10-23][latest-highlights]).
- An open session row carries a "Show all runs" button at the end of its
  facts. It opens every scenario row of that session and reads "Hide all
  runs" once they are all open, which closes them and leaves the session open.
  A closed session row has none ([2026-10-14][count-link]).
- With no scenario selected, this view lists every session and marks nothing.
- The grid's accessible name is `Runs of all scenarios, by session`.

### Both views

- A session row and a scenario row open and close on a click, with no request
  to the server. Each starts with a gray chevron, the app's own icon at 16px,
  that points right while the row is closed and down while it is open
  ([2026-10-18][figure-columns]). On arrival the first session is open, and under All
  scenarios so is the scenario row of the last run played, unless the tree
  first arrives for a session's count, when only what its jump opens is
  open ([2026-10-14][count-link]). Each view keeps its own open rows, and
  which rows are open is never remembered. A scenario
  row keeps its state while its session is closed
  ([2026-10-14][all-scenarios]).
- "Expand all" opens every loaded session of the view on screen, down to its
  scenario rows under All scenarios, and reads "Collapse all" once they are
  all open. It opens no runs, and "Collapse all" leaves the scenario rows'
  own state alone. Both buttons read what a press would do, following every
  way a row can open or close.
- The "Columns" menu shows or hides, in table order, Shots Fired, Reloads,
  Sensitivity, FOV and Avg FPS ([2026-10-05][columns-menu]). Sensitivity is
  shown to start, and the other four are off ([2026-10-22][new-columns],
  [2026-10-29][shots-hidden]). After them it has a "Median and best"
  checkbox, off to start. The browser remembers each
  ([2026-10-14][median-best]).
- With "Median and best" on, a scenario row under All scenarios and a session
  row under This scenario show the median and best of the runs under the row,
  `Median {median}` and `Best {best}`, or `Score {score}` over one run, and
  nothing over none. The median is the middle score, or the mean of the two
  middle scores. Both count every run under the row at any sensitivity, are
  formatted as a score is, and show whether the row is open or closed. A
  session row under All scenarios has none. Turning the checkbox on or off
  makes no request ([2026-10-14][median-best]).
- The figures sit in the row's own line, just before its count, including
  the first row under This scenario. No row's height changes when the
  checkbox turns on or off ([2026-10-23][inline-summaries]).
- A scenario row reads `Median {median} · Best {best} · 4 runs`, or `Score
  {score} · 1 run` ([2026-10-18][figures-line]).
- Under This scenario, a session row's Median, Best, and count line up in
  columns down the list, 16px apart with no dot between them. Each label is
  on every row, right-aligned
  against its value. Every value lines up on its decimal point: whole numbers
  end at one place, and decimals stick out to the right. A one-run session
  reads `Score {score}` in Best's column, with Median's column blank and
  silent to a screen reader ([2026-10-18][figure-columns]). Every session
  row's count, including the newest, contributes to the count column's width
  ([2026-10-23][inline-summaries]). Each column is as wide as its widest value
  in any session of the scenario, loaded or not, so Show older sessions
  never moves a column ([2026-10-18][figure-columns]).
- Each view loads 30 sessions and counts its own. A "Show older sessions"
  button at the end adds 30 to the view it is pressed in. A change of
  scenario keeps both counts, and a reload starts both from 30
  ([2026-10-14][all-scenarios]).
- The list is rebuilt from the run store, never from a batch of new runs,
  when a run lands on any scenario, when the view or the selected scenario
  changes, when the Score threshold percentage changes, when older sessions
  are asked for, when the date moves on, and when the newest session stops
  being in progress. So its "In progress" badge clears within 30 seconds of
  the session ending, with no run landing
  ([sessions.md](sessions.md#in-progress)).
- A run that lands shows as a new row with nothing lost: opened rows stay
  open, and keyboard focus stays on the same run, and on the same button of
  the same row. With Follow on, the list scrolls back to the top
  ([2026-10-12][column]).
- Each view opens the rows of every run newer than the newest run whose rows
  it has opened: under This scenario the first row, and under All scenarios
  each run's session row and scenario row. So a batch with runs on two
  scenarios opens both scenario rows, and runs that land while the other view
  is on screen open their rows when the view is next shown. The first time a
  view's rows arrive in a visit, the rows of the run the visit began with
  open too, unless they arrive for a session's count. A row the player
  closed stays closed until a newer run lands in it. A run on a new scenario
  adds a scenario row at the top of its session, with the next number
  ([2026-10-14][all-scenarios]).
- With no run in the store the list reads "No runs yet" in either view, with
  no controls.
- The list is the grid the app's other tables use, in its free edition, made
  to read as a tree: a session row and a scenario row are full-width rows
  drawn by the app's own script, and opening one is a filter over the rows.
  The rows reach the grid as data, never as Dash components
  ([2026-10-12][grid]).
- On a session row or a scenario row, Enter and Space open or close it, Right
  opens it, and Left closes it. A key that changes a row writes "Expanded" or
  "Collapsed" to a live region, and so do "Expand all", "Show all runs", and
  "Hide all runs". Tab from a group row walks its buttons: a session row's
  toggle, whose accessible name is "Session", then its count or "Show all
  runs"; a scenario row's toggle, "Scenario", then its name. A row's depth is
  never announced. What NVDA says of the list, and what still does not work
  well, is recorded in
  [run_history_list_nvda_walk.md](../research/run_history_list_nvda_walk.md)
  ([2026-10-12][grid], [2026-10-14][all-scenarios]).
- A click on a Run row, or Enter or Space on a focused one, opens its run in
  [the run viewer](#the-run-viewer). A key pressed on a button inside a group
  row stays that button's own.
- The grid draws only the rows in view, so a browser's find-in-page reaches
  only those.

### Linked hover

- Hovering a run point or PB star targets one list row. When its Run row is
  exposed by expansion, that row is outlined. Under All scenarios, a collapsed
  visit uses its exact Scenario row instead. A collapsed Session uses its
  Session row, including the pinned current session. The **This scenario**
  view falls directly from Run to Session
  ([2026-10-23][linked-hover], [2026-10-23][one-row-hover]).
- Expansion state chooses the most specific target. A Run in an expanded
  visit remains the target when off-screen, even when its Scenario header is on-screen.
  An off-screen or unloaded target produces no visible cross-highlight.
  Repeated visits to the same scenario are identified separately by visit ID
  ([2026-10-23][one-row-hover]).
- Hovering a visible run row emphasizes its dot or star in the current chart.
  A run outside the selected scenario, plotted range, zoom, or visible traces
  has no visible counterpart. Session and Scenario rows do not highlight
  whole sets of runs.
- Temporary links use a grape outline, separate from the blue latest-run
  highlight and selected-scenario band. Hover preserves point preferences,
  stars, the latest-run ring, scroll position, chart axes, expanded groups,
  keyboard focus, selections, and the number of sessions loaded.
  A linked PB star retains its gold fill.
- The emphasis appears immediately and clears on unhover. A list scroll,
  model or expansion change, chart redraw, or page departure clears it too.
  Hover runs entirely in the browser and never loads older sessions. A click
  is no part of it: a click on a run point, a PB star or a Run row opens the
  run in [the run viewer](#the-run-viewer), and opening or closing a run
  clears the emphasis ([RV1][rv-open]).

## The run viewer

The run viewer shows one run in the chart's place, with the run list beside
it.

### Opening and closing

- A click on a Run row, in either view of the run list, or on a run point
  or a PB star of the chart, in any mode, opens that run. Enter or Space on a
  focused Run row opens it too. A position several runs share opens the run
  its tooltip names. Over a run point or a star the pointer is a hand. A
  Session or Scenario row keeps its own click and keys ([RV1][rv-open]).
- The run takes the place of everything in the chart's column: the chart,
  its header, and Chart options. The chart is hidden, not rebuilt, so
  closing the run shows it as it was left: its mode, zoom, ranges, hidden
  traces and Chart options. A chart drawn again while hidden, as when a run
  lands, comes back at its column's width ([RV1][rv-open]).
- A click on another Run row switches to that run, which starts from its
  top. Points can't be clicked while a run is open, since the chart is
  hidden ([RV1][rv-open]).
- The open run's row carries a blue outline, in either view, and keeps it
  when the list is rebuilt. The outline is a look alone.
- **Close** sits at the header's right with an `Esc` key hint, and its
  accessible name is `Close`. Esc closes the run too, except while a text
  field has focus or a dialog, menu or dropdown is open, such as the note
  dialog, a Select's list or the Columns menu: Esc then does only what that
  control does with it ([RV1][rv-open]).
- Focus goes to **Close** when a run opens, and stays on the row pressed
  when a run is switched from the list. When the run closes, by Close or
  Esc, focus goes back to the Run row that opened it, scrolled into view, or
  to the chart's mode control when a point or a star did. A row no longer in
  the view on screen, or under a closed group, sends focus to the mode
  control too ([RV1][rv-open]).
- A change of the selected scenario closes the run, made by the player or by
  Follow, and leaves focus where it is. The scenario written again with the
  value it already holds, as when a run lands with Follow on, changes
  nothing ([RV1][rv-open]).
- A Run row of another scenario, under All scenarios, opens without
  changing the selection. The header names its scenario, and Close returns
  the selected scenario's chart ([RV1][rv-open]).
- A run that lands while one is open joins the list and the hidden chart,
  and the open run stays ([RV1][rv-open]).
- The open run isn't written to the address and adds no history entry, so
  the browser's Back leaves the page, and a reload shows the chart
  ([RV1][rv-open]).

### What it shows

- From the top: the header, the score line, a line naming the run's typical
  runs, the tiles, By Bot when the run names two bots or more, Settings,
  then Everything Recorded, closed ([RV1][rv-open]).
- The header's first line reads `{scenario} · ended {date}`, in the absolute
  format with seconds, such as `Aug 6, 2026, 10:56:36 PM`. Its title reads
  `Run {n} · {session} session`: the run's number among its scenario's runs
  in its session, as the list numbers it, and the session named as the list
  names its row, such as `Run 2 · Aug 6, 10:23 PM session`.
- A run whose stats file can't be read shows the header and `This run's file
  couldn't be read. See data/logs/debug.log.`, and nothing under it.
- The score line is the score, the latest-run card's badge, and the card's
  comparison, worked out the same way for any run: judged against the PB the
  run was chasing, under its own version, with the page's Score threshold
  percentage, and measured against the typical score when its session began
  ([The latest-run card](#the-latest-run-card)).
- A run's typical runs are the runs behind its scenario's typical score when
  the run's session began, up to 20, while that value is known. The line
  under the score names them: `Typical comes from your {N} runs before this
  session, played on {date}.`, or `played from {date} to {date}.` when they
  ended on more than one date, each date with its year only in another year
  than this one. With none it says why: `This is the scenario's first
  session, so there's no typical run to compare with yet.`, or `There's no
  typical run for this run's session yet: it had {N} runs before it, and a
  typical score needs 10 runs across 2 or more sessions, or 20 in one
  session.`, with `1 run` for one. Every Typical and Difference figure is
  then left out, and no setting is marked ([RV2][rv-typical]).
- Every figure the viewer compares, on a tile, a card or By Bot, is compared
  with the run's typical runs, and there is no other choice of runs to
  compare with ([RV2][rv-typical]).

### The tiles

- Score, Accuracy, Shots fired and Reloads, in that order, then Time on a
  run whose own version the app recognizes as
  [time-scored](#time-scored-scenarios) ([RV3][rv-tiles]).
- Each tile shows the run's value over `Typical {value} · {difference}`.
  The typical is the median of the figure over the typical runs that have
  it, and the hover reads `Median of {n} of your {N} typical runs`, or
  `Median of your {N} typical runs` when every one has it. The difference
  is the run's value less the typical, worked from the two values as shown,
  so the three add up on screen, with `+` or `−` before it and none on zero
  ([RV2][rv-typical], [RV3][rv-tiles]).
- Score is formatted as everywhere else, and its typical to its typical
  runs' precision, as Scenario Stats shows the typical score. Accuracy is
  KovaaK's hits over shots to two decimals, and its difference reads in
  percentage points, such as `+1.82 pts`. Shots fired and Reloads read as
  counts, and a typical between two runs keeps its half, such as `5,776.5`
  ([RV3][rv-tiles]).
- Time is the clock's constant less the score, read as `m:ss.s`, such as
  `1:54.3`, with its difference in seconds, such as `−2.4 s`. It has a
  typical only when every typical run is of the run's own version, and a
  time of zero or less is none ([RV3][rv-tiles]).
- A higher Score or Accuracy is green and a lower one red, fewer Reloads
  and a faster Time are green and the reverse red, and Shots fired is
  uncolored. A difference that reads zero is uncolored ([RV3][rv-tiles]).
- A figure the run's file lacks, such as Reloads in the oldest files, reads
  `Not recorded` ([RV3][rv-tiles]).

### By Bot

- A run whose kill table names two bots or more shows `By Bot`, one row per
  bot. A run that names one bot, or whose kill table is empty, shows none
  ([RV4][rv-by-bot]).
- What it shows follows the run's kind. When any bot has two kills or more,
  even if another has one: Kills, Time per Kill and Accuracy. When each bot
  is one kill and the run's own version is
  [time-scored](#time-scored-scenarios): Time, the bot's split, and
  Accuracy. When each bot is one kill on any other run: Accuracy alone
  ([RV4][rv-by-bot]).
- A bot's accuracy is its kill rows' hits over their shots. Its time is the
  sum of its kills' gaps since the kill before, the first kill's from the
  run's start, and its time per kill is that over its kills. A kill time is
  a time of day: a gap more than 12 hours below zero crossed midnight, and
  any other gap below zero means the times disagree ([RV4][rv-by-bot]).
- With typical runs, each figure shows This Run, Typical and Difference
  under its name. A bot's typical is the median of the figure over the
  typical runs that name the bot and have the figure, its hover worded as a
  tile's, and a bot no typical run names has empty Typical and Difference
  cells. With no typical runs, each figure is one column
  ([RV2][rv-typical], [RV4][rv-by-bot]).
- Times read in seconds to two decimals, such as `1.11 s`, accuracy as a
  run's accuracy, such as `59.26%`. A difference is worked from the two
  values as shown and signed as a tile's, in ` s` or ` pts`. A faster time
  or a higher accuracy is green, the reverse red, and a difference that
  reads zero is dimmed ([RV4][rv-by-bot]).
- The subtitle is the kind's line, then `Listed in the order the run plays
  them.` where each bot is one kill, then `Typical is each bot's median over
  your typical runs. Difference is this run minus typical, in percentage
  points (pts) for accuracy.` when there are typical runs. The kinds' lines
  are `Each kill's time runs from the kill before it, so it includes finding
  the bot.`, `Each bot is one kill, in a set order, so these are the run's
  splits. A kill's time runs from the kill before it.`, and `Each bot is one
  kill, so its time is shown only when the app knows this run was scored by
  completion time.` ([RV4][rv-by-bot]).
- A run's times are unknown when its file has no usable `Challenge Start:`,
  when its times disagree, or when it was paused. It keeps its kills and
  accuracy, every time cell is empty, its typical's included, and a line
  under the subtitle says why: `Times aren't shown because this run's file
  has no start time.`, `Times aren't shown because this run's file has times
  out of order.`, or `Times aren't shown because this run was paused, and
  its file doesn't say when.` A run that shows accuracy alone has no such
  line. A typical run with unknown times counts toward each bot's typical
  accuracy and not toward its times ([RV4][rv-by-bot]).
- Rows start in play order where each bot is one kill, and in name order
  otherwise, numbers read as numbers, so `Fly Bot 2` comes before `Fly Bot
  10` ([RV4][rv-by-bot]).
- Each column header sorts ascending, then descending, then back to the
  starting order, on a click or on Enter while it has focus, and the sorted
  header carries `aria-sort`. An empty cell goes last both ways, rows that
  tie keep their starting order, and Bot sorts in name order. Each run, the
  one switched to included, starts in its own order. The row under the
  pointer is marked ([RV4][rv-by-bot]).
- The table is as wide as its columns, each sized to its contents, and
  scrolls sideways in its own box where it is wider than the viewer.

### Settings

- Eleven cards on every run, six to a row: Sensitivity, Vertical
  sensitivity, DPI, FOV, Crosshair and Crosshair scale, then Hide gun,
  Resolution, Resolution scale, Frame cap and Input lag. Sensitivity is the
  run list's Sensitivity text with a converted run's recorded setting, FOV
  is the list's FOV text, Crosshair drops its `.png`, Vertical sensitivity
  reads `Same as horizontal` when the two are equal, else its value and
  scale, Hide gun reads `Yes` or `No`, Resolution scale is a percentage, and
  Frame cap drops a trailing `.0`. DPI, Crosshair scale, Resolution and
  Input lag are as the file writes them ([RV5][rv-settings]).
- A card whose value differs from its most common value over the typical
  runs is tinted yellow and shows `Typical {value}` under its own, so the
  change isn't carried by color alone. A tie goes to the value the latest
  typical run used. Its hover is the value, then `Typical {value} · on {n}
  of your {N} typical runs`, where an unmarked card's hover is its value,
  so a value cut short can be read whole ([RV5][rv-settings]).
- A setting the file doesn't have reads `Not recorded`, with the hover `The
  run file doesn't have this setting. Older versions of KovaaK's didn't
  record it.`, and is never marked ([RV5][rv-settings]).
- There is no card for the crosshair's color, which the game writes wrong.
  The value is in Everything Recorded as written ([RV5][rv-settings]).

### Everything Recorded

- A closed section at the bottom, `Everything Recorded`, under it `The run
  file as KovaaK's wrote it, grouped by kind.`, holding the stats file's
  fields under their own names, as written. It is closed each time a run
  opens, and stays open or closed as it was while another run is switched to
  from the list, whether or not either run has a By Bot table
  ([RV6][rv-recorded]).
- The fields are grouped as Result, Other Counters, Run and Settings, each
  in a fixed order, then Other for any field none of those names, in file
  order, so a game update never hides one. A group with no field in the
  file is left out ([RV6][rv-recorded]).
- A group folds to one line, `All zero: {field names}`, only when every
  field it names is in the file and reads zero. A field the file doesn't
  have, or has with no value, isn't zero, so its group stays open
  ([RV6][rv-recorded]).
- Files names the run file and reads `Found` or `None` for the run's
  performance file. Weapons shows the weapon rows, and Kills the kill table
  with every column the file has, in file order, or `This run's file
  records no kills.` Both tables scroll sideways in their own box where they
  are wider than the viewer ([RV6][rv-recorded]).
- The tables are handed to the page as data and drawn by Mantine, never as
  one Dash component per cell: a kill table can run to hundreds of rows
  ([RV6][rv-recorded]).

## Marks: the check and the star

- Two facts about a run are drawn beside its score in the run list, and
  worded as the latest-run card's badge. A check says the run met the score
  threshold. A star says the run was a
  [new PB](../glossary.md#new-pb), by the rule the chart's stars use, and a
  run can carry both. The check's hover and accessible name are "Threshold
  passed", and the star's are "New PB"
  ([2026-10-12][check]).
- A run is judged against the PB it was chasing: the scenario's best score
  before it, at any sensitivity
  ([2026-07-08][previous-pb]).
  So a later PB removes no check: a check means "passed when it was played".
  The chart's threshold line is drawn at the current PB, so an old run can
  carry a check and sit below today's line
  ([2026-10-12][check]).
- A session row shows one star after its count when any run in its scope
  set a new PB, whether the row is open or closed. Under This scenario only
  the selected scenario's runs count, so a session with none has no star.
  Under All scenarios every run in the session counts, regardless of the
  selected scenario or Playlist filter. Multiple PBs still produce one star.
- A session star's hover and accessible name are "A new PB for this scenario
  was set in this session." under This scenario and "A new PB was set in
  this session." under All scenarios. Unstarred session rows keep the star's
  room, so Median, Best and count stay aligned across rows.
- Session stars aggregate the runs' historical PB marks. A later PB doesn't
  remove an older session's star, ties don't count and a scenario's first
  run only sets the baseline. The score threshold percentage doesn't affect
  stars.
- The percentage is the Score threshold percentage as it is set now, for
  every run. A change to it marks every run again, at once, because the
  percentage in force when an old run was played was never recorded. It lives
  only in the browser, so checks are per browser. The field sends its value
  on Enter or on losing focus, never per keystroke, and the threshold line
  moves with it
  ([2026-10-12][check]).
- No switch gates a mark. An empty percentage is the one way to turn checks
  off, and it removes no star
  ([2026-10-12][check]).
- Three kinds of run are not judged: every run while the percentage is
  empty, a scenario's first run and the first run at a new sensitivity, and a
  run compared by score whose PB before it was zero or less. A star never
  depends on the threshold: the first run at a new sensitivity can be a new
  PB and carry one. A run with no verdict has no check, and neither does a
  judged run that missed. The cell's hover and accessible text give the one
  reason that applies, the first that fits in that order: "Not judged. No
  score threshold percentage is set.", "Not judged. A scenario's first run,
  and the first run at a new sensitivity, aren't judged against the score
  threshold.", "Not judged. Your personal best before this run was zero or
  less, so there is no percentage to judge by.", or, for a judged miss,
  "Below threshold"
  ([2026-10-12][check]).
- A judged run passes when `score × 100 >= PB × goal`, where `PB` is the PB
  it was chasing and `goal` is the percentage. The two sides are compared
  as decimals, so a run exactly at the goal passes: in floats
  `20.6 × 95 / 100` is `19.570000000000004`, which would fail a 19.57 run
  sitting exactly at 95% of a 20.60 PB
  ([2026-07-08][previous-pb]).
  The percentage a surface prints is `score / PB × 100`.
- Compared by pace, with `C` the scenario's constant, a run passes when
  `(C − PB) × 100 >= goal × (C − score)`, compared as decimals in the same
  way, and the percentage is `(C − PB) / (C − score) × 100`. Pace needs
  positive times only, so a time-scored PB of zero or less is still
  judged. Where a time is zero or less the run is compared by score
  ([2026-10-05][pace]).
- Two display caps keep a printed percentage from contradicting the
  verdict beside it. A judged miss prints at most one tenth below the goal
  as printed, so a 94.98% miss of a 95% goal reads `94.9%`, never `95.0%`.
  A run below the PB prints at most `99.9%` whether it passed or not, so a
  run 0.03% short reads `99.9%`, never `100.0%`. Both hold by pace too,
  since a run's pace is below the PB's exactly when its score is
  ([2026-10-12][check]).
- Nothing else judges a run. The run toast carries no verdict, and no
  surface says where a run placed among the runs at its sensitivity
  ([2026-10-13][run-toast],
  [2026-10-13][retired]).
- A past run is judged by pace under its own version of the scenario, the
  one its stats file names in `Hash:`, where the app measures pace on that
  version. Whether a version is time-scored, and its constant, is one answer
  for the whole version, taken from the newest performance file of that
  version that can answer. The comparison is by pace only when the PB the run
  was chasing was set on the same version and both times are positive.
  Otherwise it is by score, as it is for a run whose file names no version
  and where no performance file of its version can answer. So a run on a
  later version changes no earlier check. New evidence about a run's own
  version can: the first performance file of a version that can answer turns
  that version's earlier runs to pace, and a later file of the same version
  that answers differently judges every run of that version again
  ([2026-10-12][check]).
- The personal best celebration compares a landed run with the run store's
  high score when the run lands. The star and the card's badge compare it
  with the PB before the run in the order the runs were played. The two
  differ only for a run that lands older than the store's newest, such as
  a stats file copied into the folder.

## Time-scored scenarios

- A time-scored scenario scores the time left on a clock that counts down
  from a constant when the task is done, so a score of `s` took `C − s`
  seconds. Wherever the app can measure pace on one, these surfaces divide
  times instead of scores: the Next Rank gap
  ([playlists.md](playlists.md#the-per-playlist-scenario-table)), the Score
  threshold line (The chart), the New personal best toast
  ([notifications.md](notifications.md#run-notifications)), and the check
  and the latest-run card's badge and percentage
  ([Marks](#marks-the-check-and-the-star)), and the card's typical phrase
  ([The latest-run card](#the-latest-run-card)).
  Anything that orders or places scores is unchanged, because a higher score
  is always a faster finish: the chart's points and axis, the PB score line,
  the rank lines, and the Rank column. No completion time is shown anywhere
  but the run viewer's Time tile and By Bot's splits, which the pace entry's
  note of 2026-10-30 names ([2026-10-05][pace], [RV3][rv-tiles],
  [RV4][rv-by-bot]; [The tiles](#the-tiles), [By Bot](#by-bot)).
  The typical score's line and bands are among them: a median and its
  percentiles order scores, so they divide no times
  ([TS1][typical-definition]).
- Pace applies to a comparison only when three things hold: the scenario is
  recognized as time-scored, every score in the comparison is eligible, and
  both times are positive. Otherwise the surface behaves exactly as it does
  on any other scenario, with its own `N/A` and unjudged rules. A
  time-scored PB of zero or less still gets a pace percentage, because only
  the times have to be positive
  ([2026-10-05][pace]).
- A scenario is recognized from a performance file, the file KovaaK's writes
  beside each run's stats file. The file is time-scored when it has at least
  two score events and, after every one, the running score is within 0.5 of
  `time_limit − timescale × timestamp`. Then the constant is the file's
  `time_limit`, and the scenario version is its `scenario_hash`. Any other
  file that can answer says the scenario is not time-scored. A file can't
  answer when its bytes do not parse, when its `schema_version` is not 1, or
  when its header lacks a scenario hash, or a time limit or a timescale
  that is a positive, finite number. A run paused partway through is
  recognized like any other, because the file's timestamps leave paused
  time out
  ([2026-10-05][pace]).
- For the surfaces that judge the scenario as it stands, the scenario's
  newest run names the version. That run and the older runs with the same
  stats-file `Hash:` are tried newest first, and the first whose performance
  file can answer decides. A file that can't be read or can't answer is
  skipped. A file that answers "not time-scored" decides, and no older file
  is read. The app can't tell, and every surface keeps its score math, when
  no file of that version can answer, when none of the scenario's runs has a
  performance file, when the newest run has no `Hash:`, or when the stats
  folder has no `performances` folder beside it. A scenario's first run on a
  game build that writes these files therefore turns it to pace, and its
  numbers move then
  ([2026-10-05][pace]).
  A past run's check is the exception: it is judged under the run's own
  version ([Marks](#marks-the-check-and-the-star)).
- A score is eligible for a pace comparison only when its run's `Hash:`
  equals the deciding file's `scenario_hash`. A rank threshold counts as
  eligible. A run whose stats file has no `Hash:` still loads, and its score
  is never eligible. So a PB set on an older version of the scenario keeps
  the score math, on the table and the chart, until a run on the current
  version beats it
  ([2026-10-05][pace]).
- A run's performance file is found by name: the stats file's name with
  ` Stats.csv` replaced by ` Performance.perf`, in the `performances` folder
  beside the stats folder
  ([settings.md](settings.md#restart-scope-and-pinning)). Startup lists that
  folder once and parses nothing. A run that lands adds its file to the
  listing, so the table and the chart see the file the watchdog judged the
  run by, with no restart. A file is parsed only when a surface asks about
  its scenario, and its answer is remembered by file name for the life of
  the process. A file that can't be read is not remembered, so the next look
  tries again. A missing, unreadable, or malformed performance file costs
  only the detection, never the run
  ([2026-10-05][pace]).
  The first time a file is parsed, the debug log records its answer. For a
  file that can answer, the line also carries its time limit, its score
  event count, and its largest distance from the countdown.

## Chart options panel

- The panel is an in-flow column beside the chart, between the chart and the
  run list, disclosed by the "Chart options" button in the chart's header. It
  starts closed on every visit, its open state is never persisted, and
  collapsing hides the controls with `display: none` while keeping them
  mounted and feeding their callbacks
  ([2026-08-09][panel]).
  When the chart's own area, the page less the navbar and the run list,
  drops to 48em, the same panel stacks above the chart
  ([2026-10-12][column]).
- Three groups in order, holding eleven controls: **Overlays** ("Rank
  thresholds" on, "Show all ranks" off, "Accuracy targets" off, "PB score"
  on), **Run Data
  Points** ("Point size" Default, "Point color" empty), and **Score
  Threshold** ("Score threshold overlay" on, "Score threshold percentage"
  95, minimum 1, placeholder "Percentage")
  ([2026-08-09][panel],
  [2026-08-20][points],
  [2026-10-13][retired];
  label casing as amended by [2026-09-14][copy]).
  Overlays ends with the typical score's three switches, after "PB score":
  "Typical score", "Middle 50%" and "Middle 80%", all on
  ([TS7][typical-switches]).
  A help text that names another control renders the name bold: "Needs
  **Rank thresholds** turned on."
  ([2026-09-14][copy]).
- "Accuracy targets" is an input of the chart rebuild, as "Show all ranks"
  is, with the id `run-history-accuracy-targets-switch`. Like every
  remembered control's, its id and its default, off, never change. Off, or
  with "Rank thresholds" off, it changes nothing. Its help text: "Shows
  beside each rank line an estimate of the accuracy that rank needs when you
  hold the fire button for the whole run. It's calculated from your runs, on
  scenarios where your score follows your accuracy, such as tracking. Needs
  **Rank thresholds** turned on." ([2026-10-30][at-switch]).
- Each of the typical score's switches shows or hides its metric on Score vs
  Run and Score vs Time, faded stretches included, and a band's switch also
  its line in the line's hover. A band can show without the line. They are
  inputs of the chart rebuild, as "PB score" is, and change nothing on Score
  vs Sensitivity. Their ids are `run-history-typical-score-overlay-switch`,
  `run-history-middle-50-overlay-switch` and
  `run-history-middle-80-overlay-switch`, and like every remembered control's
  their ids and defaults never change. Each help text names the mode that
  doesn't show its metric ([TS7][typical-switches]): "Draws your typical
  score: the median of your
  last 20 runs, or of all your runs if you have fewer. It's faded where too
  few of them are recent. **Score vs Sensitivity** doesn't show the line or
  bands.", "Shades the middle 50% of the runs behind your typical score. A
  narrower band means more consistent scores. **Score vs Sensitivity**
  doesn't show this band.", and "Shades the middle 80% of the runs behind
  your typical score, in a lighter shade than the middle 50%. **Score vs
  Sensitivity** doesn't show this band."
- The Score threshold percentage help text reads the same on every scenario:
  "Sets the score goal as a percentage of your personal best. On a scenario
  scored by completion time, it's a percentage of your personal best's pace
  instead, when the app can measure pace reliably. Otherwise, it stays a
  percentage of your score. The overlay line tracks your current personal
  best. A run is judged against the personal best you had before the run."
  ([2026-10-05][pace];
  the last sentence as set by
  [2026-10-12][check]).
- Every control in the panel persists via Dash persistence in the browser's
  local storage, so preferences are per browser and per origin, which is why
  every human-facing URL says `localhost`
  ([2026-08-09][localhost]).
- The panel holds no notification control. The Run notifications switch is
  on the Settings page ([settings.md](settings.md#notifications)), because
  the run toast shows on every page
  ([2026-10-13][run-setting]).
  The Score threshold verdict switch is retired with the verdict it gated,
  so an empty percentage is the one way to stop runs being judged
  ([2026-10-13][retired]).
  The values a browser stored for the two old switches are left behind,
  unused.

## Scenario Stats

- A card in the top row, framed as the latest-run card is, in the theme's
  tokens. Its first line is plain text, "Typical score", and is not a heading
  ([TS8][typical-card-lead], [2026-10-18][stats-last-played]). A help icon
  named "About the typical score" follows it, and its lead is the typical
  score in the same large-number style as the PB and latest-run cards, with
  a dotted underline and a hover ([TS8][typical-card-lead]). Category and
  Total runs follow at one weight ([TS8][typical-card-lead]). The personal best and the
  leaderboard position are [the PB card's](#the-pb-card), and when the
  scenario was last played is [the latest-run card's](#the-latest-run-card)
  ([2026-10-18][stats-last-played]).
- The lead is the value after the scenario's newest run, built by the same
  function as the chart's last point from one snapshot of the whole run
  store. Recency is judged against the app's own clock as of now, and a
  value that isn't recent is dimmed in the theme's dimmed color
  ([TS5][typical-card-value]).
- Whenever some supporting runs are older than 30 days, the first line adds
  ` · {k} of {n} recent runs`, including zero, whether the lead is dimmed or
  at full strength. It adds no readout when every supporting run is recent
  ([TS6][typical-recency]).
- The lead's hover gives the median's supporting count, the run and session
  counts and short dates, the number from the last 30 days, and both the
  middle 50% and middle 80%. A single date reads `on {date}`, and only a
  date outside the current year shows its year. Chart switches change
  neither this hover nor the card
  ([TS5][typical-card-value]).
- With no scenario selected, the card reads "No scenario selected" under its
  first line, in the PB card's empty-title style, in place of the lead,
  Category and Total runs. A scenario with no local runs reads "No runs yet"
  over `Total runs: 0`. Below the existence minimum the lead reads "Too few
  runs", whose hover gives the minimum and the scenario's run and session
  counts, with singular wording for one
  ([TS8][typical-card-lead]).
- The first line's help explains the median, both bands and their switches,
  the dimming, and why the card's recency can differ from the chart's last
  point. The help icon and the hovered lead accept keyboard focus
  ([TS8][typical-card-lead]).
- A selected-scenario run, a scenario change, and the page's 30-second
  relative-time tick update the lead and readout. The tick dims a value
  within 30 seconds of its recency test failing. Unchanged rendered content
  returns `no_update` so a held tooltip stays mounted across ticks. The
  card builds no interval of its own
  ([TS5][typical-card-value]).
- Category is `{category} · {subcategory}`, or `{category}` with one level,
  using the selected benchmark table's own group labels and length guard.
  It is shown only while the Playlist filter holds a benchmark with groups
  that lists the selected scenario. No filter, an ordinary playlist, an
  unknown code, no matching scenario, absent or mismatched groups, or a
  benchmark on the grouping exclusion list hides the entire row with no
  placeholder. A scenario or filter change rewrites it, including a filter
  change alone ([T2][category]).
- Its frame is 270px wide. Its lines start 12px below its top, 2px apart,
  with no padding at its bottom, and it fits in the row the dropdowns'
  column sets ([SC4][top-aligned]).

## Run delivery

- A successfully imported run CSV appears once in the stores and run lists.
  Duplicate create events and deletion/recreation of that filename during
  the same app session do not add runs or increase scenario counts. The
  filename identity and retry rules are in
  [notifications.md](notifications.md#run-notifications).
- The app shell drains the run-event deque, on its own interval and on every
  page, and publishes one batch per tick. This page's `forward_run_events`
  consumes that batch store as its only `Input` and writes two stores in one
  answer: a summary of the batch for the scenario the page shows, which is
  the scenario last played when the Follow switch is on, and the id of the
  batch's newest run, written for every batch. The Follow switch and the
  scenario dropdown are `State` there, so flipping either forwards nothing on
  its own. The supported usage model is one active tab
  ([2026-07-06][coalesce]).
  The drain, and the run toast it sends on every page, are specified in
  [notifications.md](notifications.md#run-notifications). The page builds
  no toast for a run.
- One callback writes both dropdowns' values, with plain outputs. It reads
  the summary and lands on the scenario just played when Follow is on,
  clearing a Playlist filter that does not list it, and it is the callback
  that applies a link's parameters, a scenario's name pressed in the run
  list's tree, and the scenario note card's answers. Which input called is
  read from what triggered the call ([2026-10-12][clear-filter],
  [2026-10-14][all-scenarios], [2026-10-18][follows]).
  With Follow off the page stays on the selected scenario.
- While a scenario note has unsaved changes the same callback moves nothing
  on its own: it holds a run in a store of its own, which the note card
  names, and holds a name pressed in the list for the note card's dialog. The
  Follow switch is one of its inputs, so turning Follow off ends a wait at
  once. The note card's editor runs in the browser and decides there whether
  a change of scenario asks, when the change lands
  ([2026-10-18][note-unsaved]).
- The chart rebuild consumes the summary, so a batch of several runs becomes
  one rebuild and one change of scenario rather than a replay
  ([2026-07-06][coalesce]).
  Its other rebuild triggers are a scenario change, the Playlist filter, the
  chart mode, the two ranges, the date moving on, and any Chart options
  control that feeds it
  ([2026-10-12][every-run]).
- The run list, the latest-run card, the scenario dropdown's list, and the
  check for a session in progress take the second store, so each is brought
  up to date for a run on any scenario, once per batch.
- The page polls on `polling_interval` (default 1000 ms) for two callbacks:
  the run-import failure flush and the rank read. The shell's drain is a
  third poll, on its own interval, and it runs on every page. Waitress's 8
  worker threads absorb the burst, and both intervals keep ticking while the
  tab is hidden
  ([2026-07-17][threads]).
- Two background queues reach the screen here and on [Home](home.md),
  whichever of the two is open: run-import failures on the next poll tick,
  and the startup playlist warnings on a one-shot interval 250 ms after
  mount. The page that is open empties the queue
  ([2026-10-12][address]).
  Both toast families are specified in
  [notifications.md](notifications.md#background-threads-and-diagnostics).

## Narrow windows

- Both rules measure the page's own boxes and never the window, because the
  navbar takes 225px without changing the window's width
  ([2026-08-03][content-area]).
- When the page area is 900px or narrower, the run list goes above the chart
  at up to 600px tall, and the page scrolls. The order is then the top row,
  the list, and the chart
  ([2026-10-12][column]).
  The top row is then one wrapping line packed from its start, in DOM
  order: the dropdowns' column, the scenario note card, at least 240px wide,
  Scenario Stats, the PB card, and the latest-run card, which joins a line at
  380px and takes the room left on it. The score pair's wrapper has no box
  there ([2026-10-21][score-strip]). The latest-run card's floor there is
  177px ([SC4][top-aligned], [SC1][typical-start]).
- Chart options sits beside the chart only while the chart's own area is
  wider than 48em. At that width or less it stacks above the chart, with its
  groups side by side
  ([2026-10-12][column]).
- There is no phone design. At phone width the list scrolls sideways
  ([2026-10-12][column]), with its full-width rows held in view
  ([2026-10-22][list-width]).
- In a stacked page the list is the page's full width and holds every column
  shown, and scrolls sideways only where the page is narrower than their need
  ([2026-10-22][list-width]).

## What the page keeps and forgets

- Runs are files: every run is a CSV in the stats directory, the in-memory
  stores are rebuilt from them at startup, and every view on this page is
  therefore recomputable at any time: the chart, the run list, the marks, and
  the card
  ([2026-08-08][rank-history]).
- Leaderboard positions are not history: only the latest position per
  scenario is cached, past positions are overwritten and cannot be
  reconstructed, and capture stays unbuilt until a position-over-time
  feature is designed, whose first deliverable must be that capture
  ([2026-08-08][rank-history]).
- The browser remembers the Playlist filter, the Selected scenario, the
  Follow switch, the chart mode, the two ranges, the Chart options controls,
  the run list's switch, and the Columns menu's six checkboxes, each under
  the control's own id. It does not remember whether Chart options is open,
  which rows of the list are open in either view, or how many sessions either
  view has loaded
  ([2026-10-12][own-ids], [2026-10-14][all-scenarios]).
- The chart-appearance preferences live only in the browser's local
  storage. Nothing the panel sets is written server-side
  ([2026-08-20][points]).
- Scenario notes are the one thing on this page a player writes and nothing
  can rebuild. Each is a file under `data/scenario_notes/`, read when its
  scenario is selected and never held in memory
  ([2026-10-18][note-store]). Text that isn't saved yet lives only in the
  open page: nothing keeps a draft, so only a crash or a killed browser loses
  it without a question ([2026-10-18][note-unsaved]).
- Nothing about a mark is stored. A check and a star are worked out again
  each time something asks, from the runs, the percentage, and what the
  performance files say now
  ([2026-10-12][check]).
- The run open in [the run viewer](#the-run-viewer) is held by the open page
  alone: it is not in the address, and a reload or a visit to another page
  and back shows the chart. Nothing about a run is stored either: its
  figures are worked out each time it opens, from its stats file and its
  typical runs' files, and the stats folder and the performances folder are
  only ever read.

## Setup surfaces

- With no runs to read, the page says why in place, above its top row. It
  shows the stats-folder hint, and the setup card's two yellow states, "Your
  settings can't be read" and "Finish setting up". Each reads and looks as
  it does on Home, where [home.md](home.md#setup-surfaces) specifies them.
  The card here has no Skip and never offers the account: that state is
  Home's alone
  ([2026-10-12][address]).
- The chart, the run list, and the card keep their ordinary empty states
  beneath them.

[name]: ../decision_log/2026/2026-10-12-the-chart-page-is-named-run-history.md
[address]: ../decision_log/2026/2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md
[navbar-mark]: ../decision_log/2026/2026-10-13-the-navbar-marks-the-open-page.md
[column]: ../decision_log/2026/2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md
[grid]: ../decision_log/2026/2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md
[every-run]: ../decision_log/2026/2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md
[at-rule]: ../decision_log/2026/2026-10-30-accuracy-targets-are-estimated-from-the-players-own-runs-where-at-least-5-agree.md
[at-tenth]: ../decision_log/2026/2026-10-30-an-accuracy-target-shows-a-tenth-of-a-percent-rounded-up.md
[at-margin]: ../decision_log/2026/2026-10-30-accuracy-targets-sit-beside-the-rank-lines-in-the-charts-right-margin.md
[at-switch]: ../decision_log/2026/2026-10-30-an-accuracy-targets-switch-in-chart-options-starts-off.md
[at-note]: ../decision_log/2026/2026-10-30-with-accuracy-targets-on-a-chart-with-none-says-why.md
[stars-run]: ../decision_log/2026/2026-10-12-score-vs-run-stars-each-new-pb.md
[clear-filter]: ../decision_log/2026/2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md
[check]: ../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md
[own-ids]: ../decision_log/2026/2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md
[nearest-minute]: ../decision_log/2026/2026-10-13-a-measured-time-rounds-to-the-nearest-minute.md
[naming]: ../decision_log/2026/2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options.md
[panel]: ../decision_log/2026/2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph.md
[localhost]: ../decision_log/2026/2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001.md
[copy]: ../decision_log/2026/2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md
[one-word]: ../decision_log/2026/2026-07-06-one-word-per-concept-in-leaderboard-verbiage.md
[query]: ../decision_log/2026/2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md
[hidden-filter]: ../decision_log/2026/2026-10-12-the-playlist-filter-lists-the-hidden-playlist-it-holds.md
[highlight]: ../decision_log/2026/2026-10-12-opening-a-scenario-performance-dropdown-highlights-its-name.md
[content-area]: ../decision_log/2026/2026-08-03-homes-controls-row-measures-the-content-area-not-the-window.md
[local-list]: ../decision_log/2026/2026-09-12-the-local-scenario-list-comes-from-the-run-store.md
[stars]: ../decision_log/2026/2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star.md
[pace]: ../decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md
[normalize]: ../decision_log/2026/2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi.md
[precision]: ../decision_log/2026/2026-09-27-sensitivity-precision-is-fixed-per-scale-and-its-config-knob-is-retired.md
[recorded]: ../decision_log/2026/2026-09-26-a-converted-run-keeps-the-setting-it-was-recorded-at-for-display-only.md
[timestamps]: ../decision_log/2026/2026-07-11-humanize-the-absolute-timestamp-format.md
[next-rank]: ../decision_log/2026/2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one.md
[trailing-zeros]: ../decision_log/2026/2026-09-27-the-scenario-table-drops-trailing-zeros-from-pb-score-and-pb-cm360.md
[previous-pb]: ../decision_log/2026/2026-07-08-judge-score-threshold-notifications-against-the-previous-pb.md
[pre-hydration]: ../decision_log/2026/2026-07-16-keep-pre-hydration-states-honest.md
[points]: ../decision_log/2026/2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there.md
[default-color]: ../decision_log/2026/2026-08-21-the-empty-point-color-is-called-default-and-the-points-follow-the-theme.md
[run-toast]: ../decision_log/2026/2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md
[retired]: ../decision_log/2026/2026-10-13-top-n-placement-and-the-score-threshold-verdict-switch-are-retired.md
[run-setting]: ../decision_log/2026/2026-10-13-run-notifications-is-a-browser-local-setting-on-the-settings-page.md
[share]: ../decision_log/2026/2026-09-12-charts-keep-plotlyjs-4s-share-chart-button.md
[columns-menu]: ../decision_log/2026/2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones.md
[all-scenarios]: ../decision_log/2026/2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md
[count-link]: ../decision_log/2026/2026-10-14-a-sessions-count-jumps-to-it-in-the-tree-and-an-open-session-row-has-show-all-runs.md
[median-best]: ../decision_log/2026/2026-10-14-the-run-lists-columns-menu-offers-median-and-best-off-to-start.md
[new-columns]: ../decision_log/2026/2026-10-22-the-run-lists-columns-menu-offers-reloads-fov-and-avg-fps-off-to-start.md
[list-width]: ../decision_log/2026/2026-10-22-the-run-list-grows-to-fit-the-columns-it-shows.md
[list-minimum]: ../decision_log/2026/2026-10-22-the-run-list-can-shrink-to-480px-when-columns-are-hidden.md
[card-width]: ../decision_log/2026/2026-10-22-the-latest-run-card-keeps-a-500px-width-of-its-own.md
[marks-30]: ../decision_log/2026/2026-10-29-the-run-lists-marks-column-is-30px-and-three-columns-share-its-spare-room.md
[shots-hidden]: ../decision_log/2026/2026-10-29-the-run-lists-shots-fired-column-starts-hidden.md
[card-480]: ../decision_log/2026/2026-10-29-the-latest-run-card-is-as-wide-as-the-run-lists-minimum.md
[figures-line]: ../decision_log/2026/2026-10-18-median-and-best-sit-in-the-rows-own-line-ahead-of-its-count.md
[figure-columns]: ../decision_log/2026/2026-10-18-the-run-list-draws-a-chevron-and-this-scenario-lines-its-figures-up-in-columns.md
[inline-summaries]: ../decision_log/2026/2026-10-23-this-scenario-session-rows-keep-their-score-summaries-inline.md
[coalesce]: ../decision_log/2026/2026-07-06-coalesce-pending-home-run-events.md
[threads]: ../decision_log/2026/2026-07-17-absorb-poll-tick-bursts-with-threads-not-visibility-gating.md
[rank-history]: ../decision_log/2026/2026-08-08-rank-history-capture-is-deferred-until-a-position-over-time-feature-is-designed.md
[top-row]: ../decision_log/2026/2026-10-14-run-historys-top-row-has-one-card-per-kind-of-information.md
[category]: ../decision_log/2026/2026-10-14-scenario-stats-names-the-selected-benchmarks-category.md
[pb-card]: ../decision_log/2026/2026-10-14-the-pb-card-shows-the-local-record-and-next-rank.md
[card-order]: ../decision_log/2026/2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md
[accuracy]: ../decision_log/2026/2026-10-18-a-runs-accuracy-shows-two-decimals.md
[follows]: ../decision_log/2026/2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md
[first-line]: ../decision_log/2026/2026-10-25-the-latest-run-cards-first-line-drops-the-scenarios-name.md
[card-lines]: ../decision_log/2026/2026-10-25-the-latest-run-card-ends-with-the-runs-cm360-and-accuracy.md
[top-aligned]: ../decision_log/2026/2026-10-25-run-historys-three-score-cards-line-up-from-the-top.md
[typical-start]: ../decision_log/2026/2026-10-25-the-latest-run-card-measures-the-run-against-the-typical-score-at-session-start.md
[old-mark]: ../decision_log/2026/2026-10-22-an-old-typical-value-on-the-table-is-marked-with-a-clock-in-a-readable-grey.md
[stats-last-played]: ../decision_log/2026/2026-10-18-last-played-leaves-scenario-stats-and-its-first-line-is-plain-text.md
[heading-line]: ../decision_log/2026/2026-10-18-the-run-lists-heading-line-is-for-screen-readers-only.md
[note-store]: ../decision_log/2026/2026-10-18-a-scenario-note-is-one-plain-text-note-per-scenario-in-a-file-of-its-own.md
[note-card]: ../decision_log/2026/2026-10-18-run-historys-top-row-shows-the-selected-scenarios-note.md
[long-note]: ../decision_log/2026/2026-10-19-a-long-scenario-note-scrolls-in-its-card.md
[note-aligned]: ../decision_log/2026/2026-10-28-the-scenario-note-lines-up-with-the-score-cards.md
[note-unsaved]: ../decision_log/2026/2026-10-18-unsaved-note-text-is-never-lost-to-a-change-of-scenario-or-page.md

[typical-definition]: ../decision_log/2026/2026-10-15-typical-score-uses-the-last-twenty-runs-and-counts-every-version.md

[typical-chart]: ../decision_log/2026/2026-10-18-the-typical-score-is-drawn-after-each-run.md

[typical-bands]: ../decision_log/2026/2026-10-18-two-percentile-bands-show-the-typical-scores-spread.md

[typical-card-value]: ../decision_log/2026/2026-10-18-scenario-stats-shows-the-newest-typical-score-at-any-age.md

[typical-recency]: ../decision_log/2026/2026-10-20-a-typical-score-is-recent-with-ten-runs-from-the-last-thirty-days.md

[typical-switches]: ../decision_log/2026/2026-10-20-the-typical-score-and-both-bands-have-independent-switches.md

[typical-card-lead]: ../decision_log/2026/2026-10-20-scenario-stats-leads-with-the-typical-score.md

[score-strip]: ../decision_log/2026/2026-10-21-run-historys-score-cards-stay-together-after-the-note.md

[latest-highlights]: ../decision_log/2026/2026-10-23-run-history-highlights-the-selected-scenarios-latest-run.md

[linked-hover]: ../decision_log/2026/2026-10-23-run-history-links-chart-and-list-runs-on-hover.md

[one-row-hover]: ../decision_log/2026/2026-10-23-run-history-hover-outlines-one-list-row.md

[compact-hover]: ../decision_log/2026/2026-10-24-chart-point-tooltips-show-score-time-and-run-numbers.md

[rv-open]: ../decision_log/2026/2026-10-30-a-run-opens-in-the-charts-place-and-close-or-esc-closes-it.md

[rv-typical]: ../decision_log/2026/2026-10-30-the-run-viewer-measures-a-run-against-its-typical-runs.md

[rv-tiles]: ../decision_log/2026/2026-10-30-the-run-viewers-tiles-are-score-accuracy-shots-fired-reloads-and-time.md

[rv-by-bot]: ../decision_log/2026/2026-10-30-by-bot-measures-each-bot-against-its-own-typical-and-names-no-bot.md

[rv-settings]: ../decision_log/2026/2026-10-30-the-run-viewer-shows-eleven-settings-and-marks-a-changed-one.md

[rv-recorded]: ../decision_log/2026/2026-10-30-everything-recorded-shows-the-whole-stats-file-closed-and-grouped.md
