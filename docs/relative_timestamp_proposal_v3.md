# Relative ("Humanized") Timestamp Proposal — v3

## What changed since v2

- **Tail resolved.** Old dates (>30 days) render as an **absolute date** — no
  longer a lean (was open at v2's "Still open"). See
  [the ladder](#relative-time-formatting).
- **Prior-art framing corrected.** v2 implied a flat "consensus" and mislisted
  AWS Cloudscape as backing the absolute tail. Reality: consensus exists on the
  *mechanics* (single-unit, floor, "just now", tooltip, no prefix), but the
  *tail* diverges — Primer (~30d) and Atlassian (7d) switch to absolute, while
  **Cloudscape stays relative** into weeks/months/years. Reworded as "tool-UI
  precedent," not "consensus." See [Prior art](#prior-art).
- **Tooltip accessibility consciously waived** for this local single-user app,
  recorded as a decision rather than an omission. See
  [Accessibility](#accessibility-tooltip-only).
- **JS helper test plan.** The formatter holds the risky logic and pytest can't
  reach it. Added a **manual QA checklist** as the acceptance bar and a
  pure-function design (injectable `now`) so a Node smoke test is a drop-in
  later. See [Testing impact](#testing-impact).

## Goal

Display "Last played" as a relative, humanized string ("5 minutes ago") instead
of a static absolute string, in **both** places it appears, with a hover tooltip
showing the full absolute timestamp. The home-page value should stay current
over time without a reload; the grid value should at minimum be correct on
render (auto-refresh is a separate decision — see Location 2).

## Locations in scope

| | Location 1 — Home "Scenario Stats" | Location 2 — Playlists "Last Played" column |
|---|---|---|
| File | [`source/pages/home.py`](../source/pages/home.py) | [`source/pages/playlist_scenarios.py`](../source/pages/playlist_scenarios.py) |
| Render path | `dmc.Text` node inside a `dmc.Tooltip` (home.py:509-517) | AG Grid cell via JS `valueFormatter` (playlist_scenarios.py:45-52) |
| Current cell value | server string `"{days_ago} days ago"` (home.py:122-125) | `last_played_sort` = epoch **seconds** for sort; `last_played_display` = `"YYYY-MM-DD"` string for the cell (playlist_scenarios_service.py:114-117) |
| Tooltip today | yes — `last-played-tooltip` label, full `strftime` (home.py:126) | none |
| Self-update today | only when `do_update` fires or selection changes | only on row reload (page nav) |
| Self-update needed | yes (live stat you watch during a session) | low value — see decision below |

The two share exactly one thing: **the relative-time formatting logic**. That
belongs in a single JS helper so the two render paths stay consistent.

## Shared design

### One JS helper in `assets/`

Dash auto-loads every `assets/*.js`. There is already
[`assets/dashAgGridFunctions.js`](../assets/dashAgGridFunctions.js) registering
`dagfuncs.nullsLastComparator`. Add the formatters there (or a sibling
`assets/relativeTime.js`) and expose them two ways:

- `dagfuncs.relativeTime(seconds, sentinel)` / `dagfuncs.absoluteTime(seconds,
  sentinel)` — for the AG Grid `valueFormatter` / `tooltipValueGetter`.
- The same functions are reachable as `window.*` globals, so the home page's
  inline `clientside_callback` string can call them too (the existing color-mode
  clientside callback in `app_shell.py:173` is also a plain inline string, so
  this matches the current style).

Two functions, both **pure** (no DOM access) and both taking an optional `now`
argument defaulting to `Date.now()` so they are deterministically testable:

- `relativeTime(seconds, sentinel, now?)` → `"5 minutes ago"` / absolute date for
  old values / `sentinel` for null.
- `absoluteTime(seconds, sentinel)` → full timestamp for tooltips, formatted to
  match the home page's existing `"%Y-%m-%d %I:%M:%S %p"` so both pages read
  identically.

### Relative-time formatting

**Hand-roll the strings; don't use `Intl.RelativeTimeFormat` (decided).** Intl
buys i18n + pluralization, but this app is English-only, you still pick the unit
yourself, and Intl can't do the "switch to an absolute date past a threshold"
branch we want (below) — so that logic is hand-written regardless. ~15 lines of
plain JS in one place is simpler to read and fully controls the edges. Revisit
Intl only if real i18n ever lands.

**The ladder.** Always a **single rounded unit — never compound** ("2 months and
15 days ago" reads too heavy, gives precision nobody acts on, and breaks the
convention users know). Relative while recent, **absolute date once old** — the
exact instant always lives in the tooltip, so the relative string only needs the
gist.

```
≤ 60s        → "just now"      (also catches zero/negative diffs — see below)
< 60 min     → "N minutes ago"
< 24 h       → "N hours ago"
≤ 30 days    → "N days ago"
> 30 days    → absolute date, e.g. "2026-05-16"
```

Minutes is the floor (never "seconds ago" — too fast to read, and it would force
a 1s tick). The "just now" bucket also absorbs the **future/negative-diff** case
(a run timestamped slightly ahead due to clock quirks; the current home code
hides this with `abs()`, home.py:122), so any diff ≤ 0 renders "just now".

**Tail (>30 days): absolute date (decided).** Past the cutover the cell shows the
real date (`absoluteTime` without the time-of-day, e.g. `2026-05-16`) rather than
continuing into "N months/years ago". Rationale:

- This app is a stats dashboard, not a social feed. The tool-UI precedent (GitHub
  Primer ~30d, Atlassian 7d) switches to absolute; the pure-relative-forever
  pattern is the feed convention (YouTube, Reddit). See [Prior art](#prior-art).
- It dissolves the rounding-imprecision worry entirely: past a month you show the
  exact date, so there's no "1 year = 12-23 months" ambiguity and no need for
  qualifier words.

The **30-day cutover** is the decided default (precedent spans 7-30 days); trivial
to tune after seeing it live.

**No "over"/"about" prefix (decided).** Flooring is silent, per universal
convention — bare "1 year ago" is understood as approximate. "over 1 year ago" is
verbose, infects every floored bucket ("over 1 hour ago") if applied honestly,
and only half-fixes precision anyway. The real fix for coarse-end precision is
the absolute tail above, not a prefix word.

**Absolute format (decided).** `absoluteTime` (tooltips) uses
`"%Y-%m-%d %I:%M:%S %p"` — matching the home tooltip today — not
`toLocaleString()`. A tooltip must show the exact instant unambiguously;
`toLocaleString()` is locale-dependent and `M/D/Y`-ambiguous. ISO-style date is
unambiguous and already what the app shows. The >30-day cell tail uses the same
formatter truncated to the date (`%Y-%m-%d`). ~10 lines of JS padding / 12h
conversion.

### Data format: epoch seconds

Store/emit an epoch number, not an ISO string.

- **No parse ambiguity.** `new Date(ms)` is deterministic; a naive ISO string
  parses inconsistently (date+time as local, date-only as UTC).
- **Use seconds, not milliseconds.** The grid already carries seconds
  (`date_last_played.timestamp()`), and a test asserts that
  (`test_playlist_scenarios_service.py:103`). Keeping seconds everywhere means
  one convention and no test churn; the JS helper multiplies by 1000 internally
  for `new Date`. (This reversed v1's "send milliseconds" call.)
- **Timezone is sound.** `date_last_played` is naive *local* time — it is parsed
  from the Kovaak's filename via `datetime.strptime(..., "%Y.%m.%d-%H.%M.%S")`
  (data_service.py:385). `.timestamp()` interprets a naive datetime as local and
  yields POSIX epoch; `new Date(s*1000)` renders back in browser-local, which on
  a localhost app is the same clock. No cross-machine skew.

## Location 1 — Home "Scenario Stats"

**Approach: clientside callback + a browser-side `dcc.Interval`.**

- The server callback `get_scenario_num_runs` (home.py:111) stops formatting the
  relative string. It writes the raw epoch (or `None`) into a new `dcc.Store`
  and keeps writing the absolute string to the tooltip label (it already returns
  `"N/A"` for no-selection / not-in-DB, so the tooltip guard is already covered).
- A `dcc.Interval` ticks in the browser; a `clientside_callback` recomputes the
  string on each tick and on each Store change, writing `children` of
  `scenario_datetime_last_played`.

**Interval — dedicated, 30s (decided).** There is already an `interval-component`
(home.py:432, default 1s from `polling_interval`), and reusing it would need no
new component. But with **minute** granularity the text changes at most once a
minute, so the 1s cadence is wasted, and reuse would couple display-refresh
cadence to a config knob that means something unrelated ("how often to poll for
new Kovaak's data"). A future bump to `polling_interval` would then silently
change how often the timestamp re-renders. A **dedicated `dcc.Interval` at 30s**
decouples the two and is right-sized (the displayed minute is never more than
~30s stale at rollover), for the cost of one trivial component.

**Duplicate-output split (unchanged from v1, still required):** the server
callback must not also write `children` — that is a render race. Server owns
Store + tooltip; clientside owns `children`.

## Location 2 — Playlists "Last Played" column

The grid already runs JS client-side via `valueFormatter`, so "send epoch not
ISO" is moot here — `last_played_sort` is already epoch seconds. The work is:

1. **Cell text** — change the column's `valueFormatter` from
   `params.data.last_played_display` to
   `dagfuncs.relativeTime(params.value, "Never")` (`params.value` is
   `last_played_sort`, in seconds). `relativeTime` returns the sentinel when the
   value is null, so `nullsLastComparator` sorting is unaffected (it sorts on the
   raw number, not the formatted text).
2. **Tooltip** — add `tooltipValueGetter`:
   `dagfuncs.absoluteTime(params.value, "Never")` (full timestamp). This replaces
   the need for the `"YYYY-MM-DD"` `last_played_display` string entirely.
3. **`last_played_display` — dropped (decided).** Remove it from the row dict and
   let `absoluteTime` format the tooltip, so both pages share one JS formatter
   and there is no second source of truth. This changes
   `test_playlist_scenarios_service.py` assertions on `last_played_display`
   (lines 102, 129, 162, 307, 313) — a deliberate test update, called out in
   [Testing impact](#testing-impact).

**Self-update — Phase 1 renders fresh, live ticking is Phase 2 (decided).** AG
Grid does not re-run `valueFormatter` on a timer; it re-runs on data load, sort,
or an explicit `refreshCells()`. In **Phase 1** the cell is correct on render and
re-rendered on every navigation to the page (`load_playlist_scenario_rows` fires
off the layout store), so with minute granularity drift while the table is open
is negligible — good enough without any ticking. **Phase 2** adds live ticking:
a dedicated `dcc.Interval` plus a small clientside callback —
`getApiAsync('playlist-scenarios-grid')` then
`refreshCells({force: true, columns: ['last_played_sort']})` (both available in
the installed `dash_ag_grid` 35.2.0). Est. ~30-45 min. See [Phasing](#phasing).

## Edge cases

### Null / sentinel (the real cases)

The null cases are **no scenario selected** and **scenario not in database**
(home, already returning `"N/A"`), and **scenario in playlist but never played**
(grid, `date_last_played is None`). They are *not* "never played" on the home
page — a scenario in the DB always has a `date_last_played` (set on first load,
data_service.py:311).

`new Date(null)` → epoch 0 → **1970**, so a missing value would silently render
"55 years ago". The helper must check for null/empty **before** constructing the
`Date` and return a sentinel.

**Sentinel wording differs by meaning (decided).** The two null states are not
the same thing, so they don't get the same word:

- Grid, scenario in playlist but **never played** → **"Never"** (accurate).
- Home, **no selection / not in DB** → keep **"N/A"** ("Never" reads wrong for an
  unselected scenario, and the rest of the Scenario Stats block already shows
  "N/A" in those states).

**Not blank.** A blank value after the bold "Last played:" label reads as
broken / still-loading — indistinguishable from the initial-render-flash state.
"N/A" is unambiguously intentional. ("—" em-dash dimmed is a slightly more
polished "no value" glyph, but only worth it applied to the whole Scenario Stats
block — out of scope here; noted as optional polish.)

The shared helpers take the sentinel as a parameter: `relativeTime(seconds,
sentinel)` / `absoluteTime(seconds, sentinel)`. The grid passes `"Never"`, the
home page passes `"N/A"`.

### Future / negative diffs

The current home code uses `abs(...)` (home.py:122), which hides the case where
`date_last_played` is slightly in the future (a run recorded moments ago, FS
clock quirks). With a signed diff, `Date.now() - ts` goes negative and a naive
formatter would say **"in 5 minutes."** Handled by the "just now" floor: any diff
under 60s, including ≤ 0, renders "just now".

### Initial-render flash

Between first paint and the first clientside fire, `scenario_datetime_last_played`
`children` is empty. Set an initial placeholder (e.g. the sentinel) so it does
not flash blank.

### Cadence vs. smallest unit

The tick interval bounds staleness to one interval. With minutes as the floor,
the dedicated **30s** interval keeps the displayed minute at most ~30s stale at
rollover — comfortably enough.

### Same timestamp across scenarios (home)

Dash dedupes Store updates: a byte-identical new timestamp won't re-fire the
Store→clientside link. Harmless — same timestamp means same string, and the
interval keeps ticking. Only matters if the interval were removed.

### Accessibility (tooltip-only) — consciously waived

The exact timestamp is reachable only on **hover** — the `dmc.Tooltip` target
(`dmc.Text`) isn't focusable, and AG Grid's `tooltipValueGetter` shows on mouse
hover only. So keyboard / screen-reader users can't surface the exact instant.
UX guidance (UX Movement) flags tooltip-only timestamps as needing a non-hover
cue.

**Decision: waive for now.** This is a local, single-user, personal desktop
dashboard the developer runs for themselves; there is no broader audience for
whom keyboard/SR access to the precise timestamp is a real need, and gold-plating
a11y here is disproportionate. If that ever changes, the fix is small: make the
text focusable (`tabindex=0`) so the Mantine tooltip opens on focus, and/or
render the absolute string into an `aria-label` / visible-on-focus element.

## Alternatives considered

### Server-side refresh (the simplest thing, and why not)

Keep formatting in Python and just refresh it. Two sub-problems make this worse,
not better:

- `get_scenario_num_runs` only re-fires on `do_update` (set true *only when new
  data arrives*, check_for_new_data, home.py:85-101) or selection change — so it
  freezes between runs. To refresh on a timer you must add the interval's
  `n_intervals` as a direct input, which re-runs the *entire* callback (runs +
  tooltip + the queue-coupled path) every tick just to re-render one string.
- The cost argument is a wash on localhost, so it doesn't rescue the approach.

The clientside split is preferred for **isolation** — re-rendering the relative
string never touches the server data path — not for saving CPU.

### Self-updating web component (`@github/relative-time-element`)

Rejected as in v1: Dash has no `<relative-time>` element, so it needs a shipped
asset plus a `MutationObserver` to survive Dash replacing the DOM node on
re-render. Worth revisiting only if we want adaptive cadence across many places.

## Testing impact

The relative/absolute formatting lives in JS and is **not** reachable by pytest,
yet it holds the risky logic: null sentinels, the future/≤0 clamp, unit selection
+ pluralization, the 30-day relative→absolute boundary, and 12-hour absolute
formatting. Two-part plan:

1. **Manual QA checklist (acceptance bar for Phase 1).** Verify each branch:
   - `≤ 60s`, exactly `0`, and a **future** timestamp → "just now".
   - `1` vs `2` minutes (pluralization); the `59 min` and `60 min` boundaries
     (latter → "1 hour ago").
   - hours pluralization; `23h59m` vs `24h` (latter → "1 day ago").
   - days; the `30 days` vs `31 days` boundary (latter → absolute date).
   - absolute format: zero-padding, 12-hour clock incl. **12:00 AM** (midnight)
     and **12:00 PM** (noon); renders in local time.
   - null → correct sentinel: **"Never"** in the grid, **"N/A"** on home.
2. **Keep the helpers pure with an injectable `now`** so a Node smoke test
   (`node --test`) is a drop-in if/when we add a JS runner. Not standing up a
   Node toolchain now — disproportionate for ~30 lines in a pure-Python project.

Also: dropping `last_played_display` (Location 2, step 3) requires updating the
assertions in `test_playlist_scenarios_service.py` (lines 102, 129, 162, 307,
313). `last_played_sort` is unchanged, so sort tests (`test_playlist_pages.py:74-83`)
stay green.

## Implementation sketch

**Shared:**

1. Add `relativeTime(seconds, sentinel, now?)` and `absoluteTime(seconds,
   sentinel)` to `assets/dashAgGridFunctions.js` (or `assets/relativeTime.js`),
   registered on `dagfuncs` and reachable as `window` globals. Both guard null →
   sentinel. `relativeTime` implements the single-unit ladder (just now →
   minutes → hours → days → absolute date past 30 days; any diff ≤ 0 → "just
   now"; never compound). `absoluteTime` formats `"%Y-%m-%d %I:%M:%S %p"`.

**Location 1 (home):**

2. Add a `dcc.Store` (e.g. `last-played-ts`) and a dedicated `dcc.Interval`
   (e.g. `relative-time-interval`, 30s) to the home layout.
3. Change `get_scenario_num_runs` to output epoch seconds (or `None`) into the
   Store and the absolute string into the tooltip label; **remove** its
   `scenario_datetime_last_played.children` output.
4. Add a `clientside_callback`: inputs `[Store.data, relative-time-interval.n_intervals]`,
   output `scenario_datetime_last_played.children`, body calls
   `window.relativeTime(value, "N/A")`. Seed `children` with an initial sentinel
   to avoid a blank flash before the first fire.

**Location 2 (playlists):**

5. Column `valueFormatter` → `dagfuncs.relativeTime(params.value, "Never")`; add
   `tooltipValueGetter` → `dagfuncs.absoluteTime(params.value, "Never")`.
6. Drop `last_played_display` from `format_playlist_scenario_rank_row` and update
   the affected service tests. (No grid auto-refresh — that's Phase 2.)

No new Python dependency.

## Phasing

- **Phase 1** — Steps 1-6 above. Shared helper; home self-updates via the 30s
  interval; both pages show relative text + an absolute-timestamp tooltip; the
  grid renders fresh on each navigation (no live ticking).
- **Phase 2** — Grid live ticking: a dedicated `dcc.Interval` + a clientside
  callback calling `getApiAsync('playlist-scenarios-grid')` →
  `refreshCells({force: true, columns: ['last_played_sort']})`. ~30-45 min, no
  server changes. Self-contained, ships independently of Phase 1.

## Resolved decisions

1. **Home interval:** dedicated `dcc.Interval` at 30s (not reusing
   `interval-component`) — decouples from `polling_interval` and right-sized for
   minute granularity.
2. **Grid auto-refresh:** deferred to **Phase 2** (rows already rebuild on
   navigation, so Phase 1 is fresh-on-render).
3. **`last_played_display`:** dropped; tooltip formatted by `absoluteTime`.
4. **Sentinel:** "Never" on the grid (never-played), "N/A" on home
   (no-selection / not-in-DB), via a sentinel parameter on the shared helpers.
   Not blank (reads as broken). "—" block-wide is optional future polish.
5. **Granularity:** hand-rolled ladder, **single unit always (never compound)** —
   just now (≤ 60s, incl. ≤ 0) → N minutes → N hours → N days → absolute date.
   No Intl dependency. No "over"/"about" prefix.
6. **Absolute format:** `"%Y-%m-%d %I:%M:%S %p"` (matches today), not
   `toLocaleString()`.
7. **Tail (>30 days):** absolute date (not "N months/years ago"). 30-day cutover
   is the default; tunable.
8. **Accessibility:** tooltip-only (hover) access to the exact timestamp,
   consciously waived for this local single-user app.

## Tunable later

- The 30-day cutover (precedent spans 7-30 days) — one-line change after seeing
  it live.
- Optional polish: switch the whole Scenario Stats block from "N/A" to a dimmed
  "—" placeholder (separate change, not part of this proposal).

## Prior art

Market scan of how relative timestamps are handled, June 2026.

**Consensus on the mechanics:**

- **Single unit, never compound** — universal (GitHub Primer, AWS Cloudscape,
  Atlassian, the `Intl.RelativeTimeFormat` API).
- **Floor / round down** to the largest unit — Atlassian states it explicitly;
  this is why "1 year ago" is approximate.
- **"just now" / "Now" under 60s.**
- **Always expose the exact timestamp on hover** (e.g. Cloudscape sets the
  `<time title>`; Atlassian "always provide a way to see the actual timestamp").
- **No "about"/"over" prefixes** in any major system.

**The tail diverges — tool-UI precedent favors absolute, but it is not
universal:**

- **Switch to an absolute date** — Atlassian after **7 days**; GitHub Primer
  after **~1 month** (then `on MMM D`, then a full date with year). Supports tail
  option (A).
- **Stay relative into weeks/months/years** — **AWS Cloudscape** defines no
  switch threshold and continues relative units; the social-feed pattern
  (YouTube, Reddit) does the same. This is the counterexample to (A).
- A contrarian view (Smykowski, "Stop using relative date and time") argues for
  absolute-only on accessibility/ambiguity grounds — reinforces keeping a real
  date available (tooltip + the absolute tail).

We chose the absolute tail because this is a stats tool (Primer/Atlassian
precedent) and it removes coarse-end rounding ambiguity.

Sources: [GitHub Primer — RelativeTime guidelines](https://primer.style/product/components/relative-time/guidelines/),
[AWS Cloudscape — Timestamps](https://cloudscape.design/patterns/general/timestamps/),
[Atlassian — Date & time](https://atlassian.design/foundations/content/date-time),
[UX Movement — Absolute vs. Relative Timestamps](https://uxmovement.com/content/absolute-vs-relative-timestamps-when-to-use-which/),
[Smykowski — Stop using relative date and time](https://tomaszs2.medium.com/stop-using-relative-date-and-time-87c52ba816d3).
