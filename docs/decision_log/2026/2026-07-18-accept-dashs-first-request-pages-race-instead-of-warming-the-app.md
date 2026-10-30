# 2026-07-18: Accept Dash's First-Request Pages Race Instead of Warming the App

Status: Superseded by the
[2026-10-29 entry](2026-10-29-dash-4-5-0-fixes-the-first-request-pages-race.md):
dash 4.5.0 fixed the race upstream, and the app requires that version

Decision: The browser-console noise on the first page load after a server
start — a `TypeError: Cannot read properties of undefined (reading 'apply')`
from `handleClientside`, plus a flood of ~86 "ID not found in layout" entries
in the dev-tools overlay — is a known upstream Dash defect. We accept it and
do not work around it. Treat it as expected baseline noise during browser
checks; reload the page before judging whether the console is clean.

Why: Dash's `enable_pages()` registers its page router as a `before_request`
hook (`dash/dash.py`, in `router_sync`/`router_async`). The hook sets its
`_got_first_request["pages"]` guard flag *before* it finishes its work, and
takes no lock:

```python
if self._got_first_request["pages"]:
    return
self._got_first_request["pages"] = True
...   # builds validation_layout, registers the document.title clientside callback
```

Inline clientside function bodies are injected into the index HTML at render
time. Under a threaded server — Waitress with `threads=8` in production,
Flask's threaded dev server when `debug = true` — a concurrent early request
sees the flag already set, returns immediately, and serves an index page whose
script block is missing, while `/_dash-dependencies` still advertises the
callback. The renderer looks the function up, gets `undefined`, and calls
`.apply` on it. `validation_layout` is populated in the same unfinished hook
body, which is why the "ID not found in layout" flood appears alongside: one
root cause, two symptoms.

Measured 2026-07-18 on dash 4.4.0: eight simultaneous first requests produced
**seven of eight** renders missing the script; every later render has it. A
browser triggers it because it opens several connections at startup.

The missing function is Dash's own `_pages_dummy` `document.title` setter, not
application code — all six of our clientside callbacks register correctly every
time. It is not a dash-extensions defect either: `DashProxy._setup_server`
correctly takes a `setup_server_lock`, and plain `dash.Dash` races identically
(measured: 7/8 for both, in a minimal app with no dash-extensions involved).
It reproduces on dash 4.3.0 and 4.4.0 alike, so it is not a regression from the
PR #146 dependency upgrade.

## Reproducing it requires a wide enough race window

Two conditions must both hold, which is why a casual minimal repro shows
nothing and reports "works fine":

1. **`suppress_callback_exceptions` must be at its default `False`.** When it
   is `True`, Dash skips the whole `validation_layout` block inside the pages
   router (`dash/dash.py`, the `if not self.config.suppress_callback_exceptions:`
   guard) — which is the slow part of the hook. The window collapses to
   near-zero and the race effectively never fires. This app leaves the setting
   at its default.
2. **Page layouts must be expensive enough to matter.** That block calls every
   registered page's layout function to build `validation_layout`. The window
   is as wide as those calls take. A `html.Div("hi")` page closes it instantly;
   this app's real page layouts hold it open long enough to lose 7 of 8 races.
   A minimal repro reproduces once a page layout is given real work to do
   (a 0.4s sleep was sufficient).

Practical consequence: **do not expect an upstream fix to arrive on its own.**
Most small Dash apps and most upstream tests satisfy neither condition, so the
bug is invisible in exactly the places that would catch it. Absent someone
filing it (not done as of 2026-07-18), assume it survives future Dash releases
rather than treating a version bump as a likely cure. Re-check cheaply after a
Dash upgrade: load the app once, reload, and see whether the first-load console
noise is gone.

Impact is cosmetic and self-healing: on an affected load `document.title` shows
the app-level title instead of the page title, and any reload fixes it. A
workaround for someone else's bug is not worth carrying for that.

"No feature is affected" is measured, not assumed. Exercised on a load
confirmed to have lost the race — six of seven clientside functions registered,
86 "ID not found in layout" entries, the app-level title — the Home page still
rendered fully, the Plotly graph mounted (a beat later than usual), server
callbacks fired and returned 200, and toggling the x-axis radio round-tripped
end to end and updated the figure. The only observable defect was
`document.title`. The "ID not found in layout" flood is the renderer reporting
a transient state it recovers from, not callbacks being dropped.

Validated mitigation, should this ever become worth fixing: prime the app with
one synchronous in-process request before serving — `with
app.server.test_client() as c: c.get("/")` in `main()`, ahead of `serve(...)` /
`app.run(...)`. Measured under the same eight-way concurrency test, this took
seven-of-eight failures down to zero. Deliberately not applied.
