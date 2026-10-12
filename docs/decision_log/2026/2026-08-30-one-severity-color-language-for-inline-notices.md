# 2026-08-30: One Severity Color Language For Inline Notices

Status: Accepted (the orange rung widened by
[2026-09-19](#2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total) from
a failed follow-up write to any failed follow-up step)

The app's inline notices each picked their own look, so the surfaces that most
needed attention were the faintest things on the page. They now speak the same
severity colors the toasts already do, and every one of them carries a leading
icon. The first-run setup card is tinted like the rest instead of being a white
card on a white page, and the leftover-playlist-files notice became a plain
panel so screen readers are no longer told that a panel of buttons is an alert.
No wording changed anywhere.

Decision: one severity scale governs every notification surface, inline and
toast alike. Blue is informational and any action it offers is optional; yellow
is caution, an attention-worthy negative outcome or a state that needs the user
without anything having failed; red is an error, an operation that failed;
green is a positive outcome; orange is partial success, where the action
committed but a follow-up write did not. Green and orange stay toast-only:
no inline success or split-outcome panel exists, and none is added. Yellow
deliberately spans both configuration states and coaching outcomes such as a
below-threshold run, because a narrower warning-only reading would leave the
shipped threshold verdicts outside the scale.

Why: the severity information already existed in the code and did not reach the
eye. Three of the four alerts were `color="yellow"` with Mantine's `light`
variant, whose yellow tint is the palest token in the palette and reads as
near-white in light mode, and none of them had an icon; the fourth hard-coded
`#ff6b6b`, a red tint on a purely informational banner. The setup card, the
first notice a fresh install ever shows, was an untinted `dmc.Paper` on the
untinted page body. In a live render the icon, not the background, was the
dominant legibility fix.

The component rule: which component a notice uses follows its content model,
not its look. Mantine renders `Alert`'s root with `role="alert"` and the dmc
2.8.0 wrapper exposes no role override. Per
[WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/#alert) that role is an
assertive, atomic live region for important, usually time-sensitive messages,
and [MDN's guidance](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/alert_role)
draws the consequences this rule applies: the role is for text content rather
than interactive elements like links or buttons, and for content that appears
dynamically rather than with the page. So a text-only notice may be a
`dmc.Alert`, and a notice holding interactive controls is a `dmc.Paper` wearing
the alert anatomy through the shared `.alert-panel` classes in
`assets/stylesheet.css`. Should an interactive notice ever need announcing, the
shape is a separate polite status message, or an alert dialog for a workflow
that requires a response, never `role="alert"` around controls.

The five inline surfaces as shipped: the Settings store alert and the Playlists
visibility alert stay yellow `dmc.Alert`s and gain
`material-symbols:warning-outline`; the Aim Training Journey work-in-progress
banner becomes blue with `material-symbols:info-outline`, deleting the hex; the
Playlists leftover-files notice becomes a blue `dmc.Paper`, keeping its id, its
callbacks, and its hidden-class reveal; the Home setup card keeps its
`dmc.Paper` and takes the blue treatment for the identity offer and the yellow
one for the blocking stats-folder state, with the matching icon beside its
title. Both icons were already vendored, so no assets were added. Mantine
defines the `-light` tokens per color scheme, so dark mode needs no separate
rules.

Superseded in part by the
[2026-09-15 setup-hints entry](#2026-09-15-setup-hints-wear-the-notice-anatomy):
that sweep enumerated the notices by component and so never saw the three
plain-text messages about setup, which now wear the same anatomy. The
enumeration above is the five as shipped that day; there are seven, and the
two added carry no title. Everything else here stands, the scale included.

Rejected: one accent color for every inline notice, which is calmer and uniform
but makes "your saved choices are silently not applying" look identical to an
FYI and splits the app into two color vocabularies, one for toasts and another
for panels. Rejected for the setup card: one color for both states, which hides
that the first state blocks every plot on the page while the second is a
skippable offer. Rejected for the leftover-files notice: yellow, which keeps
housekeeping louder than the problem warrants and dilutes the two yellow alerts
that earn it. Rejected as variants: `filled`, far too loud for a persistent
panel and poorly contrasted in yellow, and `outline` or `default`, both whiter
than what shipped before. Rejected as a component: rebuilding the setup card as
a `dmc.Alert`, which would entrench the role mislabel permanently rather than
merely start from the wrong place. The `dmc.Paper` anatomy carries one ongoing
cost, accepted knowingly: it tracks Mantine's `Alert` look by hand across
upgrades.

Extends the toast layer specified by the
[2026-08-03 notification entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy),
which stays authoritative for toasts, including their white-card-with-icon
anatomy: an icon suppresses Mantine's colored side bar, so a toast's color is a
circle rather than a stripe, and nothing here changes that. Orange keeps the
meaning the
[2026-08-02 committed-side-effect entry](#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)
gave it and stays a distinct severity rather than folding into yellow.

Deferred: strengthening the pale yellow tint with a scoped CSS override. The
icons are expected to be enough, and the override is a one-line follow-up if
they are not.
