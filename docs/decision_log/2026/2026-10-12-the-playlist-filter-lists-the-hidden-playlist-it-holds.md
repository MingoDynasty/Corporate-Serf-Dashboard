# 2026-10-12: The Playlist Filter Lists The Hidden Playlist It Holds

Status: Accepted

The playlist filter on Scenario Performance now names a hidden playlist when
that playlist is the one selected. Before, arriving from a hidden playlist's
scenario table left the filter blank or showing the previous playlist's name,
while the scenarios and the rank lines on the page belonged to the hidden one.
A hidden playlist is in the dropdown only while it is selected, so picking
another playlist takes it out of the list again.

**Ruling.** By the maintainer, 2026-10-12, after trying the current behavior
and two options side by side in a prototype: "Yes I choose option 1. Notably,
with option 1, if the user selects a different playlist, then tries to select
"negative benchmarks" again from the dropdown, that item no longer exists. So
it still manages to keep in the spirit of the "Hide playlists" feature, which
hides playlists from dropdown menus to help keep dropdown menus tidier."
Option 1 is the rule below. Option 2 is under "The option set aside". The
build is
[PR #363](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/363).

**The defect.** The filter's options were the visible playlists, while a
selection was accepted for any loaded playlist. A `?playlist_code=` link
selects one, and every row of a playlist's scenario table carries that link
whether the playlist is visible or not. So does a value the browser restored.
A hidden playlist is loaded and not visible, so the filter could hold a value
that none of its options had. The installed Select (dash-mantine-components
2.8.0) then does one of two things, both read in its bundle and seen in a
browser. Mounted with such a value, it keeps the value and shows no text.
Given one by a callback, it keeps the previous option's text until it loses
focus. The rest of the page followed the held playlist all along: its
scenarios, the link to its table, and its rank lines on the chart. A fresh
install hides 247 of the 261 bundled benchmarks, so the state was a few
clicks away. Reproduced at `685d16a` in headless Edge.

**The rule.** `playlist_filter_options()` in
`source/components/scenario_selection.py` returns the visible playlists, plus
the held playlist when it is loaded and hidden, in the full list's own order.
It has two callers:

- `select_playlist` writes it as the filter's `data`, for the filter's
  value, on every mount and every change. This is the half a restored
  selection needs, because the server never sees a restored value. Its name
  appears one round trip after the page paints.
- The layout builds it for `?playlist_code=`. A linked playlist is in the
  list when the page paints, so its name shows as soon as `apply_deep_link`
  sets the value.

The held playlist leaves the list on the next pick or clear, because the list
is built again for the new value.

**What this changes in the 2026-07-11 entry.** One sentence of
[The Playlist Overview Is The Playlist Management Surface](2026-07-11-the-playlist-overview-is-the-playlist-management-surface.md):
"`get_visible_playlist_selector_options()` is the single visibility filter
every option list consumes (Home filter, Journey picker, overview), so they
cannot disagree." The function is still the only place that decides what is
visible, and the three lists still agree on that. What changed is that the
Scenario Performance filter's list is that list plus one playlist. The
sentence after it is unchanged: hidden playlists "still load, their
`/playlists/{code}` routes still resolve, and rank overlays still draw". Rank
lines for a hidden playlist were already drawn, under a filter that named
another playlist or none, and this entry makes the filter agree with the
chart. The older entry is marked amended, not superseded, because nothing it
decided is reversed.

**The option set aside.** Treat a hidden playlist like an unknown code on
this page, so the filter clears. Run as a prototype, it did four things the
chosen rule does not:

- It drew no rank lines and gave no link back for a user who had opened a
  hidden playlist's table on purpose, which reverses the sentence quoted
  above.
- It dropped a linked scenario with no local runs, leaving "No scenario
  selected".
- It forgot the selection for good when the held playlist was hidden, where
  the chosen rule keeps it through a hide and a show.
- It was not the smaller change. Hiding the held playlist involves no link,
  so clearing the filter needs the same write to the filter's options.

**A remembered code no playlist has.** The filter used to keep such a code.
It looked empty but had a clear button, and the code stayed stored. Writing
the filter's options makes the Select drop a value they lack, so the filter
is now empty and nothing is remembered. The cost is that a playlist missing
on one visit does not come back as the selection later: a deleted playlist
imported again, or a file that failed to load once. This rides on the fix and
changes a state the spec described, so the maintainer was asked whether to
keep it or guard against it, with keeping it recommended. The answer,
2026-10-12: "let's go with your recommendation." The guard set aside was to
write no options for a code that does not resolve, which would have left that
state as it was.

**Costs accepted.**

- Nothing in the dropdown marks the held entry as hidden. Marking it is copy,
  and no copy was decided.
- The Journey picker has the same exposure and is left alone, since its page
  is shelved.
- A restored hidden selection shows an empty filter for one round trip: 151
  to 236 ms in the four returns measured in Edge, and 228 to 288 ms in
  Firefox. A link arrival shows the previous playlist's name for one round
  trip, 46 and 47 ms in the two measured in Edge and 112 and 125 ms in
  Firefox, which is the cost
  [2026-09-19](2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)
  already accepts. The Firefox runs shared the machine with a test run.
- The rule leans on two behaviors of the installed Select that no unit test
  can hold: a value its options have is named, and a value its new options
  lack is dropped. An upgrade of dash-mantine-components repeats the browser
  check, as a step in [dependency_refresh.md](../../dependency_refresh.md#packages-that-ship-browser-code).

**What it keeps.** The filter's layout `value` is `None` on every visit, and
`data` is not a prop the browser stores, so the 2026-09-19 rule about a
remembered control's layout default holds. `select_playlist` keeps its second
Input. No component id changed. No callback reads the filter's `data`, so the
new output adds no round of callbacks, except the one that follows a dropped
code.

**A second page.** The callback half lives in the shared registration, so a
page that calls `register_scenario_selection()` gets it. The layout half is a
call the page makes, as it already makes `initial_scenario_options()`.
