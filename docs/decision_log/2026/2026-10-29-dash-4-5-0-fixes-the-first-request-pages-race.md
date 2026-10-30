# 2026-10-29: Dash 4.5.0 Fixes The First-Request Pages Race

Status: Accepted

Dash 4.5.0 fixed the race that left the first page load after a server start
without one of Dash's scripts and filled the browser console with errors. The
app now requires that version, so the noise is gone and nothing in the app has
to work around it. A console no longer needs a reload before it is judged
clean.

**Ruling.** Ruled (user) 2026-10-29, in chat, on
[#446](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/446), the
dependency refresh that moved dash from 4.4.1 to 4.5.0. Asked whether to
retire the first-load race note in AGENTS.md and the 2026-07-18 entry in that
PR, the maintainer answered "Yes, add it here." It supersedes the
[2026-07-18 entry](2026-07-18-accept-dashs-first-request-pages-race-instead-of-warming-the-app.md).

**What changed upstream.**
[plotly/dash#3980](https://github.com/plotly/dash/pull/3980), released in dash
4.5.0, runs the three `before_request` setup hooks (`Dash._setup_server` and
the pages `router_sync` and `router_async`) under a lock, and sets each hook's
"already done" flag only after its work has finished. That is the mechanism
the 2026-07-18 entry diagnosed: the pages hook set its flag first, so a
concurrent early request skipped the setup and served an index page missing
Dash's own `document.title` script, while `validation_layout` was still
empty.

**Measured.** On 2026-10-29, with the 2026-07-18 entry's eight-way test: the
app started on a fresh state root with real runs, the port polled over TCP so
no HTTP request ran the hooks first, then eight concurrent `GET /`, each
body's inline clientside script text compared with a render fetched
afterwards. Four fresh starts per version. On dash 4.4.1, 26 of 32 first
renders lacked inline script text the later render carried; on dash 4.5.0,
0 of 32 did.

**The browser re-check does not discriminate.** The 2026-07-18 entry
suggested re-checking after a Dash upgrade by loading the app once and
reading the console. A single headless Edge load as the first request after a
fresh start showed no console errors and the page's own title on dash 4.4.1
as well as on 4.5.0, four starts each: the page's request finishes the setup
hook before the browser asks for anything else, so nothing overlaps it. To
test for the race, use the eight-way test.

**What holds it.** The `dash>=4.5.0` floor in `pyproject.toml`, so a resolver
cannot hand back a version that races. The primed-request mitigation the
2026-07-18 entry validated stays unapplied, since nothing needs it.

**What is left as it was.** AGENTS.md no longer lists the race among the
console messages that are upstream noise. The screenshot script and the
linked-hover browser test still load their page once and reload before they
measure, a step added for this race; it costs a page load and does no harm,
so it stays. The decision-log entries that cite the 2026-07-18 entry record
what was true on their dates and are unchanged.
