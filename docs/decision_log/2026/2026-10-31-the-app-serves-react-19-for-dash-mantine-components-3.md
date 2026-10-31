# 2026-10-31: The App Serves React 19 For Dash Mantine Components 3

Status: Accepted

Dash Mantine Components 3, the release built on Mantine 9, shows a blank page
under React 18, so the app now asks Dash for React 19. Dash ships React 19 in
its own package but still serves React 18 unless asked, and calls React 19
experimental. The app's other browser libraries keep working on React 19
through a compatibility layer that Dash loads. The page still loads entirely
from the app, and the switch itself changes nothing a user sees.

**Decision.** `source/app.py` calls
`dash._dash_renderer._set_react_version("19.2.4")` before it creates the
`DashProxy`. Dash reads the setting each time it builds the index page's
script list (`Dash._generate_scripts_html`), so the call has to run before the
first page is served. Every way the app starts imports `source.app` first: the
launcher and a source run, the startup and browser tests, and the screenshot
script.

**Why.** dash-mantine-components 3.0.0, released 2026-10-30, requires Dash 4.5
or later and React 19.2.4. Under React 18 its components throw "Dash Mantine
Components v3 requires React 19. Detected React 18.3.1." as they render. A
one-button dmc 3 app loaded in headless Edge on 2026-10-31 showed an empty
page and that error; with the call above it drew its button. Dash 4.5.0 added
React 19 as an experimental opt-in
([plotly/dash#3880](https://github.com/plotly/dash/pull/3880)): the default
stays 18.3.1, and an app opts in with this call or the `REACT_VERSION`
environment variable. Dash serves React 19 from the `umd-react` builds and
loads a shim right after react-dom, so component libraries built for React 18,
such as dash-ag-grid, dash-extensions and Dash's own, keep working.

**Offline.** React 19.2.4, react-dom 19.2.4 and the shim ship inside the dash
wheel, under `dash/deps/` and `dash/dash-renderer/build/`. With Dash's default
`serve_locally`, the index loads them from `/_dash-component-suites/`. The CDN
addresses that `_set_react_version` also records are used only by an app that
serves from a CDN, which this one does not, so
[What it talks to](../../user_guide.md#what-it-talks-to) is unchanged.

**Alternatives rejected.**

- **The `REACT_VERSION` environment variable.** The launcher, a source run, and
  every test that starts the app would each have to set it, and Dash prints an
  "EXPERIMENTAL" line on every start.
- **Holding dash-mantine-components below 3.** It keeps React 18 and Mantine 8,
  but only defers the move, and a refresh takes the newest version of
  everything
  ([2026-10-05 entry](2026-10-05-a-refresh-takes-the-newest-version-of-everything.md)).

**Checked on React 19,** on 2026-10-31 with dash 4.5.0, dash-ag-grid 35.3.0,
dash-extensions 2.0.6 and plotly 7.1.0: the full pytest suite; the linked-hover
and run viewer browser regressions in Edge, 54 tests; every page, light and
dark, screenshotted beside `main` in headless Edge, with no console message
beyond the known AG Grid `columnSizeOptions` warning; the playlist filter's two
checks from the dependency refresh playbook; and a run toast replaced in place
with a fresh lifetime.

**What holds it.** `tests/test_app_version.py::test_app_serves_react_19` fails
if the served page stops loading React 19. `_set_react_version` is private,
and it asserts the version against Dash's `_available_react_versions`: a Dash
release that renames it or drops 19.2.4 fails the import of `source.app`, and
every startup test with it. When a Dash release makes React 19 its default,
the call can go.

**An earlier entry's premise.** The
[2026-10-12 run list entry](2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md)
weighed libraries partly on running on "the app's React 18.3". AG Grid now
runs on React 19 through Dash's shim, and the run list's browser regressions
pass, so that decision stands.
