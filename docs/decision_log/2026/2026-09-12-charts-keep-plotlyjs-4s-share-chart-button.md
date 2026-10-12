# 2026-09-12: Charts Keep plotly.js 4's Share Chart Button

Status: Accepted

Upgrading plotly put a "Share chart..." button on both of the app's charts,
because the new plotly.js turns that button on by default. The button stays
rather than being hidden. Sharing happens only when a user presses it,
confirms a dialog that names Plotly Cloud, and is signed in there, so it is
an export the user chooses and not data the app sends on its own. Users see it
beside the existing PNG download, and the user guide lists Plotly Cloud among
the services the app can reach.

**What changed.** plotly 7.0.0 bundles plotly.js 4.0.0, and Dash serves
plotly.js from the plotly package (`package_data/plotly.min.js`), so the
upgrade changes the browser runtime and not only the Python API. plotly.js
4.0.0 changed the `showSendToCloud` config default from `false` to `true`.
Neither `dcc.Graph` passes `config` (`graph-content` in
`source/pages/home.py`, `aim-training-journey-graph` in
`source/pages/aim_training_journey.py`), so both render the button. Ruled on
2026-09-12 (PR #283): ship it, do not suppress it. There is no config line to
carry this reason beside the code, because the behavior is a library default;
this entry is the only record that it is deliberate.

**What pressing it does**, verified against the bundled plotly.js 4.0.0. The
button opens plotly.js's own dialog naming Plotly Cloud, with Cancel and
Share; nothing is sent before Share. Share runs `sendDataToCloud`: it
serializes the figure with `graphJson` (data arrays and layout), opens
`plotlyServerURL` (default `https://cloud.plotly.com/newchart`; Dash sets no
`PLOTLYENV.BASE_URL`) in a new tab with the dashboard's
`window.location.origin` as an `origin` query parameter, and listens for a
`CHART_AUTH_SUCCESS` message from that origin, which Plotly Cloud sends once
the user is signed in there (the dialog offers account creation to anyone
without one). Only then does it `postMessage` the figure to that tab. Whether
an existing Plotly Cloud session skips the sign-in step is Plotly Cloud's
behavior, not visible in plotly.js. The app makes no request itself, and a
blocked popup ends the flow with nothing sent. The figure carries, on
Scenario Performance: the scenario
name and render time in the title; every plotted run's timestamp, score, and
accuracy, and its x value (sensitivity or date); the average-score line; and
the label and value of any rank, PB score, or score-threshold overlay shown.
On Aim Training Journey: playlist names, dates, progress percentages, and the
aim-training-hours checkpoint labels.

**Why it stays.** The flow is user-initiated, gated by a dialog that names
its destination, and completes in a Plotly Cloud tab the user can see, which
makes it an export in the same class as saving the PNG. That is what
separates it from crash telemetry, which the
[2026-08-10 bug-reports entry](2026-08-10-bug-reports-land-on-github-issues-with-the-log-attached-unredacted-and-disclosed.md)
rejects as privacy-hostile for a local tool. The user guide's
outside-services table carries a Plotly row as the disclosure.

**Rejected alternative.** `config={"showSendToCloud": False}` on both graphs,
holding the plotly.js 3 default. PR #283 shipped that hold first and backed it
out on the ruling: it guarded against a hidden data flow that does not exist,
and the one real gap, the README's list of services, was cheaper to close by
updating the README.

**Reversing it.** Pass `config={"showSendToCloud": False}` to every
`dcc.Graph`, including any added later (a layout test that walks all graphs,
rather than naming ids, is the guard that holds), and remove the Plotly row
from the user guide's What it talks to table and "sharing a chart" from the
README's summary. **Revisit trigger:** plotly.js changing the flow so data
leaves before the dialog or without the Plotly Cloud tab, or changing the
default `plotlyServerURL`; or a user report of the button being mistaken for
a local save.
