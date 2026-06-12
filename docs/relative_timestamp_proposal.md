# Relative ("Humanized") Timestamp Proposal

## Goal

Display the Scenario Stats "Last played" timestamp as a relative, self-updating
string ("5 minutes ago") instead of a static absolute string
("2026-05-16 01:23:45 PM"). The displayed value should stay current over time
without the user reloading or re-selecting the scenario.

Current display is produced server-side in `get_scenario_num_runs`
(`source/pages/home.py`): it returns `"{days_ago} days ago"` into the
`scenario_datetime_last_played` `dmc.Text`, with the full `strftime` string in
the `last-played-tooltip` label. It only refreshes when `do_update` or the
scenario selection changes.

## Constraint

Dash Mantine Components render `dmc.Text` as a plain string container. There is
no native DMC relative-time / self-updating component, so the "keep it current"
behaviour must be added separately.

## Chosen Approach: clientside callback + browser-side `dcc.Interval`

- The server callback sends the raw timestamp to the browser **once** (into a
  `dcc.Store`); it no longer formats the relative string itself.
- A dedicated `dcc.Interval` (e.g. 30s) ticks **in the browser only**.
- A Dash `clientside_callback` (plain JS) recomputes the "X ago" string on each
  tick and on each Store change, and writes it into the `dmc.Text` `children`.

### Why this is efficient

A `dcc.Interval` driving a **clientside** callback is not server polling. It is
a pure browser `setInterval` timer. The backend transmits the timestamp exactly
once; every tick after that is a few lines of JS updating one DOM node — no
network traffic, no server CPU. The perceived "polling overhead" does not exist
in any meaningful sense.

### Alternative considered: self-updating web component

A web component such as `@github/relative-time-element` (MIT) renders
`<relative-time datetime="...">` once and manages its own adaptive updates
(frequent when recent, rare when old) — no `dcc.Interval` or clientside callback
needed.

Rejected for now because:

- Dash has no `<relative-time>` component, so it requires shipping a JS file in
  `assets/` and emitting the custom tag (e.g. via `html.Time` upgraded by the
  asset script).
- Dash callbacks **replace** DOM nodes when the server re-renders this text, so
  the asset script needs a `MutationObserver` to re-apply itself — otherwise a
  new timestamp from the backend would never get humanized.

Worth revisiting only if we want adaptive cadence or humanized timestamps in
many places across the app.

## Data format: send epoch milliseconds, not an ISO string

Store an epoch timestamp in the `dcc.Store`, not an ISO string.

- **No parsing ambiguity.** Epoch is an absolute instant; `new Date(ms)` is
  fully deterministic. A naive ISO string (no offset) parses inconsistently —
  date+time as *local*, date-only as *UTC* — which is a latent footgun.
- **JSON-native** — just a number.
- ISO's only advantage was readability when inspecting the Store; not needed,
  because the human-readable string already lives in the tooltip as a separate
  output.

### Conversion catches

- **Units.** Python's `datetime.timestamp()` returns *seconds* (float); JS
  `Date` expects *milliseconds*. Multiply by 1000 on the way out.
- `datetime.now()` is naive local time; `.timestamp()` correctly interprets a
  naive datetime as local and converts to POSIX epoch, so the conversion is
  sound.

## Edge cases

### Null timestamp (scenario never played)

This is the case that must be handled deliberately. With epoch, `new Date(null)`
is treated as `new Date(0)` → **1970-01-01**, so a never-played scenario would
silently render *"55 years ago"* rather than visibly breaking. (With an ISO
string `new Date(null)` gives `Invalid Date` instead — still wrong, just more
obvious.)

Required: the clientside callback must check for null/empty **before**
constructing the `Date` and short-circuit to a chosen sentinel ("N/A" /
"Never"). The tooltip label needs the same guard. This moves the `"N/A"`
decision that the server currently makes into the JS (or keeps a sentinel value
in the Store that the JS recognizes).

### Same timestamp across scenarios

Not a problem, but worth knowing why. Dash dedupes Store updates: if the new
scenario's timestamp is byte-identical, the `Store → clientside callback` link
does not re-fire. This is harmless because the displayed text is already correct
(same timestamp → same relative string) and the `dcc.Interval` keeps ticking
independently. It would only matter if the `dcc.Interval` were dropped and
refresh relied solely on Store changes.

### Duplicate output / render race

Do **not** let both the server callback and the clientside callback write
`children` of the same `dmc.Text` — that is a duplicate-output conflict and a
render race. Clean split:

- Server callback writes only the **Store** (raw epoch) and the **tooltip
  label**.
- Clientside callback owns `children` exclusively, driven by `[Store, Interval]`.

## Implementation sketch

1. Add a `dcc.Store` (e.g. `id="last-played-ts"`) and a dedicated
   `dcc.Interval` (e.g. `id="relative-time-interval"`, 30s) to the home layout.
2. Change `get_scenario_num_runs` so the `scenario_datetime_last_played` slot is
   no longer set server-side; instead output `date_last_played.timestamp() *
   1000` (or `None`) into the new Store. Keep the `strftime` string going to the
   tooltip label.
3. Add a `clientside_callback`:
   - Inputs: the Store `data` and the Interval `n_intervals`.
   - Output: `scenario_datetime_last_played.children`.
   - Logic: if Store value is null/empty → return sentinel; else
     `new Date(ms)`, diff against `Date.now()`, format with
     `Intl.RelativeTimeFormat` (or ~15 lines hand-rolled).
4. No new dependency required.
