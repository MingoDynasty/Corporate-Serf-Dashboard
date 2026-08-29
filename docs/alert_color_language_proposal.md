# Alert Color Language

Status: Proposed
Date: 2026-08-28

## TL;DR

The app has no shared color language for its inline notices. The first-run
setup card is a plain white panel that disappears into the page, and the
inline alerts are the palest yellow wash with no icons, so the surfaces that
most need attention are the easiest to miss. This proposal adopts one
severity scale — blue for information, yellow for caution, red for errors —
rendered as a tinted background with a leading icon, and applies it to every
inline notice including the setup card. The one notice that today holds a
button inside an alert component becomes a plain card with the same look, so
screen readers stop being told a panel of controls is an alert. Toasts and
all user-facing wording stay exactly as they are.

## Decisions needed

Nothing below is ratified. D1 sets UI/UX direction for the whole app and is
the reason this is a proposal rather than a styling PR; reviewers are asked
for an independent position on it before reading the recommendation.

**D1 — Adopt a severity color language for inline notices.**
Status: Open. Recommended: yes — blue informational, yellow caution, red
error, the same scale the toast layer already speaks per outcome. The
alternative raised during design was one accent color (light blue) for every
notice: calmer and uniform, but it makes "your saved choices are silently not
applying" look identical to an FYI, and it splits the app into two color
vocabularies, one for toasts and another for panels.

**D2 — Setup card: color per state, or one color for both states.**
Status: Open. Recommended: per state — yellow for "Finish setting up" (the
app cannot plot anything and the card is not dismissible), blue for "Add your
KovaaK's account" (optional and skippable). One blue for both reads calmer on
a first run, at the cost of hiding that the first state is blocking while the
second is an offer.

**D3 — "Leftover playlist files" alert: blue or yellow.**
Status: Open. Recommended: blue. The bundled copy of the playlist already
won and the app behaves correctly; the alert is a cleanup offer, not a
malfunction, and yellow keeps housekeeping louder than the problem warrants.
Low stakes either way; listed because it re-colors a shipped surface.

## Problem

The app's message surfaces split into two layers. Toasts are consistent:
every payload already carries an outcome color (red failure, green success,
orange partial success, yellow warning, blue information) and an icon, per
[specs/notifications.md](specs/notifications.md). Inline notices are not:
each one chose its look ad hoc, and the result is uniformly faint. The
current inventory, verified by rendering every surface live with dmc 2.8.0 in
both color schemes:

- The Home setup card (`_setup_card` in `source/pages/home.py`) is a
  `dmc.Paper(withBorder=True)` with no background tint: a pure white card on
  the pure white page body (`--mantine-color-body`). It is the first notice a
  fresh install ever shows and the most prominent call to action in the app,
  and it is the surface that prompted this proposal.
- Three of the four `dmc.Alert`s — the Settings store alert, the Playlists
  visibility alert, and the Playlists leftover-files alert — are
  `color="yellow"` with Mantine's default `light` variant. That variant is a
  translucent tint, and yellow's is the palest token in the palette: legible
  in dark mode, near-white in light mode. None of the three has an icon, so
  nothing anchors them visually as alerts.
- The fourth, the Aim Training Journey work-in-progress banner, hard-codes
  `color="#ff6b6b"` — a red tint on a purely informational notice, and the
  only raw hex in any alert.
- Toast anatomy is white by design: every payload passes an icon, and an
  icon suppresses Mantine's colored side bar, leaving a white card with a
  colored icon circle
  ([2026-08-03](decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  That layer is specified, deliberate, and not the problem.

So severity information exists in the code (the colors are already mostly
semantic) but does not reach the eye, and the one surface users report as
"white" — the setup card — carries no severity styling at all.

## Design

### The color language

One scale for every notice, inline and toast alike:

| Color | Meaning | Already used by |
| --- | --- | --- |
| Blue | Informational; any action is optional | Backlog digest, unset-username Refresh answer |
| Yellow | Caution: an attention-worthy negative outcome or a state that needs the user, but not an error | Store alert, visibility alert, below-threshold verdict |
| Red | Error: an operation failed | Run-import failure, refresh failure, refused writes |
| Green | A positive outcome | Run verdicts, playlist action confirmations |
| Orange | Partial success: the action committed but a follow-up write failed | The "Playlist imported — not shown" split outcome |

The toast layer already speaks this scale, orange included: the one orange
toast is the committed-side-effect split outcome, deliberately neither a
plain success nor a warning about the import itself
([2026-08-02](decision_log.md#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)),
and it stays a distinct severity rather than being folded into yellow. This
proposal brings the inline layer to the same scale. Green and orange stay
toast-only — no inline success or split-outcome panel exists, and none is
added.

Yellow deliberately spans two kinds of caution — a configuration or store
state that needs the user, and a coaching outcome like a below-threshold
run. Both are "worth attention, nothing failed"; a narrower warning-only
definition would leave the shipped threshold verdicts outside the scale.
Green is "a positive outcome" rather than "success" for the mirror-image
reason: a threshold pass is not an operation succeeding.

### Surface-by-surface changes

- Every inline notice gains a leading `icon`:
  `material-symbols:warning-outline` for yellow,
  `material-symbols:info-outline` for blue. Both are already vendored
  (toasts use the former, the Settings help tooltips the latter), so no
  new assets. In a live render the icon was the dominant legibility fix —
  more than any background change.
- The journey work-in-progress banner becomes `color="blue"` with the info
  icon, deleting the hard-coded hex.
- The leftover-files surface becomes blue per D3 — and changes component:
  it is a persistent notice holding a focusable button ("Delete leftover
  files"), which the component rule below reserves for `dmc.Paper`. It
  adopts the same blue anatomy classes as the setup card, keeping its ids,
  callbacks, and hidden-class reveal mechanism verbatim, so its existing
  behavior coverage carries over unchanged. The store alert and the
  visibility alert stay yellow `dmc.Alert`s with the default `light`
  variant.
- The setup card keeps its `dmc.Paper` structure and gets the full alert
  anatomy: its tint lands in `assets/stylesheet.css` on the existing
  `.setup-card` class — background `var(--mantine-color-blue-light)` plus a
  colored border accent — with a modifier class switching the yellow tokens
  for the stats-folder state per D2, and a leading icon beside the title
  matched to the state the same way (warning for "Finish setting up", info
  for "Add your KovaaK's account"). The title is a plain `dmc.Text` in a
  Stack, so an icon-and-title row accommodates the icon without touching
  the card's actions or wiring. Mantine defines the `-light` tokens per
  color scheme, so dark mode needs no separate rules (verified in both
  schemes).

### The component rule

Which component a notice uses follows its content model, not its look. The
constraint is semantic: Mantine renders `Alert`'s root with `role="alert"`
(verified live on dmc 2.8.0; `Paper` carries no role), an assertive ARIA
live region meant for brief, time-sensitive messages, and the ARIA
Authoring Practices direct that an alert must not contain interactive
elements. So:

- A notice that is plain text — a message worth interrupting the user for
  when it appears — is a `dmc.Alert`. The store alert, the visibility
  alert, and the journey banner qualify: none holds a control, and for the
  two that callbacks reveal, the assertive announcement is the point.
- A notice that holds interactive controls or persists as a call to action
  is a `dmc.Paper` wearing the alert anatomy through CSS. The setup card
  qualifies (two controls, persistent), and so does the leftover-files
  surface — today a `dmc.Alert` with a focusable delete button inside
  `role="alert"`, an existing mismatch this proposal corrects rather than
  repaints.

Rebuilding the setup card as a `dmc.Alert` was considered and rejected
under the same rule: a component whose semantics we would immediately have
to strip is the wrong starting point. The secondary cost is churn — the
existing `.setup-card` styling and its structural tests
(`tests/test_home_setup_card.py`) assume the Paper layout, and a rebuild
would rework both for no visual gain over CSS on the class the card
already has. The card's action wiring itself (the CSS-styled CTA anchor,
Skip's `allow_optional` mounting) would transfer into an Alert's children
unchanged, so it is deliberately not the argument here.

### Copy

No user-facing strings are added or edited, so this proposal carries no Copy
block. Colors and icons only. This also keeps the change fully independent
of the in-flight app-wide messaging sweep.

### Alternatives rejected

- One accent color for all inline notices: see D1.
- `filled` variant: far too loud for persistent panels, and yellow-filled
  has poor text contrast.
- `outline` or `default` variants: whiter than today; they move in the wrong
  direction.
- Strengthening the pale yellow tint with a scoped CSS override: deferred.
  The icons are expected to be enough, and the override is a one-line
  follow-up if they are not.

## Out of scope

- Toasts, including their white-card-with-icon anatomy. Specified in
  [specs/notifications.md](specs/notifications.md) and unchanged.
- Any wording change anywhere; the messaging sweep owns app-wide copy.
- Structural redesign of the setup card, and any new notice surfaces.
- The tint-strengthening knob above.

## Delivery plan

- PR 1: this proposal.
- PR 2 (after D1–D3 are ruled): the implementation — icons and recolors
  across the five inline notices, the leftover-files conversion to the
  shared Paper anatomy, the setup-card CSS and per-state icon, and the
  docs definition of done across every affected spec:
  - Distill D1 into `decision_log.md` as the durable color-language entry.
  - State the shared scale in [specs/notifications.md](specs/notifications.md)
    (already the messaging-layer spec: it carries the routing policy and the
    toast color inventory), linking the new entry.
  - Update the two [specs/playlists.md](specs/playlists.md) statements that
    name alert colors.
  - Add the new presentation to the statements that describe the recolored
    surfaces where their owning specs already describe them: the store
    alert in [specs/settings.md](specs/settings.md) and the setup card in
    [specs/scenario_performance.md](specs/scenario_performance.md).
  - The Aim Training Journey page is explicitly work in progress and has no
    capability spec, so its banner is recorded only by the shared-scale
    section until that page ships.
  - Delete this file.

  No dependencies on other in-flight work. A kickoff prompt for the
  implementing agent is authored once the decisions are ruled.

## Testing

- This PR: docs gates only (`tests/test_docs.py` enforces the Status line,
  section order, and link integrity).
- PR 2: two new tests, one per semantic contract this proposal
  introduces. First, the setup card's state-to-treatment mapping
  (stats-folder state gets the yellow modifier and warning icon, identity
  state the blue treatment and info icon), asserted over
  `_setup_card_children()` alongside the structural tests that already
  cover the card. Second, the leftover-files conversion: a structural
  assertion that the `playlists-superseded-alert` layout node is a
  `dmc.Paper` and not a `dmc.Alert` while still holding the delete
  button — the existing playlist tests exercise the callbacks and cleanup
  flow but never the component type, so without this an implementation
  that skipped the conversion (and the `role="alert"` fix it carries)
  would pass every planned test. The alerts' static colors and icons
  deliberately get no prop-echo assertions — a test that restates a
  literal only fails when the literal is edited on purpose — and are
  covered instead by the visual pass and the spec statements. Existing gates must stay green, and
  the visual result is verified by running the app in both color schemes
  and checking each surface (the trigger conditions for every notice are
  enumerated in the specs). The tint rendering itself was already
  validated during design with a standalone dmc 2.8.0 test bed in both
  schemes.
