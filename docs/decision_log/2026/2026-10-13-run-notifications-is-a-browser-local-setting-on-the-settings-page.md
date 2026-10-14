# 2026-10-13: Run Notifications Is A Browser-Local Setting, On The Settings Page

Status: Accepted

The switch that turns run toasts off has moved from the chart's options to
the Settings page, into a Notifications section of its own above
Celebrations. The run toast shows on every page now, so its switch no
longer belongs to one page's chart. It takes effect the moment it is
flipped, and the browser remembers it. A browser that had turned run toasts
off under the old switch starts with them on again, once.

**The store is the setting.** `dcc.Store(id="run-notifications",
storage_type="local")` in the app shell holds one string, `"on"` or
`"off"`, and starts on. Only the exact `"off"` silences the run toast.
Anything else shows it, a value this build does not know and a store the
browser has lost included, which is the direction browser-local storage
should fail in. The drain reads the store as `State`, so flipping the
setting sends nothing. The store's id and its off value are what a browser
holds: changing either turns run toasts back on for everyone who had turned
them off.

**The switch is a view of it.** "Run notifications" sits on the Settings
page in a Notifications section, directly above Celebrations and outside
the Save form. It carries no Dash persistence of its own, so the store and
the switch can never be two remembered values that disagree. Off means no
plain toast, on any page. It does not reach the celebration, the
failed-import toast, or any other toast.

**Why the Settings page.** The maintainer chose it on 2026-10-11. The
[celebration setting](2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page.md)
went there because "The behavior is app-wide, so the Chart options
inspector on one page is the wrong home", and the run toast is app-wide
too: it shows on Playlists and on Settings. It was also the smaller build,
since the page already had the tick described below.

What it costs: the switch leaves the page where most toasts are seen. The
celebration setting accepted the same cost.

**It reuses the Settings page's tick, and the tick is load-bearing here
too.** The store as an input to the switch and the switch as an input to
the store would be a dependency cycle, which the Dash renderer refuses in
the browser. So the page's one-shot interval fills the switch from the
store, read as `State`, and the same tick's count gates the write. The gate
matters for the reason the celebration entry records: mounting the page
fires the write callback with the switch's layout default, which is on,
despite `prevent_initial_call` and with the switch itself as the triggering
id. Without the gate, every visit to Settings would turn run toasts back
on. A stored value other than `"off"` leaves the switch on its default and
writes nothing back, so a value a later build wrote stays as that build
left it.

**It stays browser-local.** A key in `data/settings.json` was rejected for
the celebration on cost, because it forces that file's first schema
migration, and the reasoning holds here.

**A stored "off" is lost once.** The old switch's value is kept by Dash's
persistence under the old control's id, and the store does not read it. So
a browser that had turned run toasts off starts on again when this lands,
and shows them until the switch on Settings is turned off. The Run History
page went public first
([its reset](2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md)),
so this is a second reset, for this one switch. The maintainer accepted it
with the proposal. The values a browser stored for the two old switches are
left behind, unused, and nothing clears them.

**Alternatives rejected.**

- **Keeping the switch in Chart options.** It stays where players have
  found it, on the page where most toasts show. It also leaves an app-wide
  setting in one page's chart panel, and puts a second copy of the store's
  wiring and its hazard on that page.
- **A mirror store beside a persisted switch.** The switch would keep
  Dash's persistence and copy its value into a shell store. Then two stored
  values can disagree: after an upgrade, a browser whose switch says off has
  a store that still says on, until the page is next opened. The switch
  would read off while toasts showed.
- **Reading Dash's persistence keys from the browser.** It depends on the
  renderer's private key format, which the
  [2026-09-19 entry](2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)
  already declined to rely on.

What the toast is and when a run earns one is in
[its entry](2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md).

Shipped in PR #376; proposal and rulings in #354. Distilled from
`docs/proposals/run_toasts_proposal.md`, deleted in the shipping PR.
