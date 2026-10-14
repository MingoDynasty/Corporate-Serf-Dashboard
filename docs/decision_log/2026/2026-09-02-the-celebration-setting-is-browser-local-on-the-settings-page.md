# 2026-09-02: The Celebration Setting Is Browser-Local, On The Settings Page

Status: Accepted

The control that chooses how a personal best celebrates lives on the Settings
page, in its own Celebrations section, with a Preview button beside it. It
offers Off and four animation styles, and takes effect the moment one is
chosen rather than waiting for Save. The browser remembers the choice instead
of the app's settings file, so a different browser, or one whose site data has
been cleared, celebrates by default.

**The store is the setting.** `dcc.Store(id="pb-celebration-style",
storage_type="local")` in the app shell holds one string: `"off"` or a style
name, defaulting to `"confetti"`. The value was a style name from the start
even though version one shipped a switch, so the follow-up that turned the
switch into a style select only added values to a contract that already
existed and kept whatever was saved. The control initializes from the store
and writes back to it and carries no Dash persistence of its own, so a
switch's boolean
and a select's string never become two competing persisted values. The drain
reads the store as `State`, and so does the clientside animation: changing the
setting must not replay a batch already delivered.

**Why the Settings page.** The behavior is app-wide, so the Chart options
inspector on one page is the wrong home — undiscoverable, and a control there
describes itself as a chart option. This departs from the placement rule the
[point customization](2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there.md)
and [master switch](2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed.md)
entries both state, that the inspector owns browser-persisted presentation
preferences. The departure is deliberate and narrow: that rule governs
preferences about the chart, and this one is about the app. It is also the
first browser-persisted control on the Settings page, beside a form whose
three fields are written to disk behind Save. The section is visibly separate,
its control applies instantly, and it touches neither the restart notice nor
the store alert, both of which speak for the form's three keys, so the form's
contract is untouched.

**Why not `data/settings.json`.** Rejected on cost, not principle. Settings v1
is a closed set of three string keys, so a new key is settings v2: a
validator, a version bump, the stamp script becoming a real migration under
the documented ordering contract, the launcher's trial-run window to be solved
for the first migrating release, and an older build refusing the v2 file on
rollback
([2026-08-11](2026-08-11-durable-json-stores-carry-a-schema_version-stamp.md)).
A cosmetic preference should not be what forces that. When a setting that
deserves v2 arrives, this one joins it; only the store's backing would change.

**Instant apply needs one tick, and the tick is load-bearing.** The obvious
callback pair — the store as `Input` to the switch, the switch as `Input` to
the store — is a dependency cycle the Dash renderer refuses, so the switch is
initialized by a one-shot `dcc.Interval` that reads the store as `State`. That
tick is also the gate on the write direction, and this is the part worth
remembering: mounting the page fires the write callback with the switch's
*layout default* despite `prevent_initial_call`, with the switch itself as
`ctx.triggered_id` — so the repo's usual triggering-id guard does not catch
it, and without the gate, opening Settings wrote the on value over a stored
off. Ordering makes the gate safe rather than lucky: once the tick has landed
the switch already holds the stored value, so the worst a late mount-fire can
write is the value that was there. Any future browser-local control on a page
layout has the same hazard.

**Accepted costs.** Browser persistence is per origin and is cleared with site
data. Both fail towards "celebrations came back", never towards silence, which
is why only the exact `"off"` value silences the family: a style name a later
build wrote, or a store this build cannot read, still celebrates. The layout
default is not a third cost: a `dcc.Store` writes it to storage only when
nothing is stored yet and otherwise takes the stored value, so changing the
default later resets nobody's setting. That is the opposite of Dash
`persistence`, which keys the stored value on the layout default and drops it
when that default moves (the
[2026-08-20 point-customization entry](2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there.md)
records the controls that pay it), and the distinction matters when the
follow-up changes the default style. One more, inherited rather
than introduced: `message_queue` is process-wide and each drain's payload
reaches one client, so with two tabs open a batch lands in whichever drain
runs first. That is the single-consumer shape the page's drain already had,
and the supported usage model stays one active tab.

**Preview, and the styles that follow.** Preview plays the currently selected
style through the same clientside path a real celebration takes, so it obeys
the reduced-motion guard; it shows no toast, because the toast reports a run
and there is no run. It ships in version one because it is the only way to see
the effect without setting a personal best. The follow-up converted the switch
to a select over Off, Confetti, Fireworks, Cannons, and Stars — curated
presets only, no duration, particle, or color knobs, no custom style, and no
Random option. Since the proposal file is deleted, its specification of that
step is recorded here: Confetti is the upstream Realistic Look recipe
unchanged (five bursts from one origin, about 200 particles, about three
seconds); Fireworks is the upstream Fireworks recipe cut from 15 s to about
3 s; Cannons is School Pride cut to about 2.5 s with the app's accent colors
in place of the demo's red and white; Stars is the upstream Stars recipe
unchanged (three volleys, star and circle shapes, no gravity). Snow is
ambient rather than a celebration and is excluded. `confetti.reset()` clears
particles but does not stop a `setInterval` or animation-frame loop, so the
two loop-based recipes must not be taken from the demo verbatim — each style
is bounded to about three seconds and must cancel cleanly.

**What that step settled when it shipped.** Cancellation is centralized rather
than repeated per style: every style returns a cancel closure, the animation
module holds exactly one, and it is invoked before any new play. That way a
style's whole leak surface is its own one-line closure, and a style that
schedules nothing returns nothing. Cannons uses Mantine's primary blue
(`#228be6`, the filled-button color) and white, which is the reading of "the
app's accent colors" this repository can point at. Preview is `disabled` while
Off is selected, replacing the earlier behavior of a click that produced
nothing: the section applies instantly, so the committed value is the only
sensible preview target, and previewing a merely highlighted option would be a
different product. A Python test parses the animation's style registry and
asserts it matches the select's options, because a name offered with no entry
falls back to Confetti — a wrong answer rather than a visible failure. A
JavaScript test harness was considered again here and again declined; the
centralized cancellation is what shrinks the surface one would have covered.

**Superseded in part (2026-10-13).** The celebration select is no longer the
only browser-local control on the Settings page. A Notifications section sits
directly above this one, with the Run notifications switch, held in a second
shell-hosted store and filled by the same tick. This entry's reason for the
Settings page now covers both. See
[Run Notifications Is A Browser-Local Setting, On The Settings Page](2026-10-13-run-notifications-is-a-browser-local-setting-on-the-settings-page.md).

Shipped in PR #268, and the style select in #272; ruled on #248.
