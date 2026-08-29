# Alert Color Language

Status: Proposed
Date: 2026-08-28

## TL;DR

The app has no shared color language for its inline notices. The first-run
setup card is a plain white panel that disappears into the page, and the
inline alerts are the palest yellow wash with no icons, so the surfaces that
most need attention are the easiest to miss. This proposal adopts one
severity scale — blue for information, yellow for warnings, red for errors —
rendered as a tinted background with a leading icon, and applies it to every
inline notice including the setup card. Toasts and all user-facing wording
stay exactly as they are.

## Decisions needed

Nothing below is ratified. D1 sets UI/UX direction for the whole app and is
the reason this is a proposal rather than a styling PR; reviewers are asked
for an independent position on it before reading the recommendation.

**D1 — Adopt a severity color language for inline notices.**
Status: Open. Recommended: yes — blue informational, yellow warning, red
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
yellow warning, blue information) and an icon, per
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
| Yellow | Warning: a choice is silently not applying, or a degraded state needs the user | Store alert, visibility alert, below-threshold verdict |
| Red | Error: an operation failed | Run-import failure, refresh failure, refused writes |
| Green | Success | Run verdicts, playlist action confirmations |

The toast layer already conforms; this proposal brings the inline layer to
the same scale. Green stays toast-only — no inline success panel exists, and
none is added.

### Surface-by-surface changes

- Every `dmc.Alert` gains an `icon`: `material-symbols:warning-outline` for
  yellow, `material-symbols:info-outline` for blue. Both are already
  vendored (toasts use the former, the Settings help tooltips the latter),
  so no new assets. In a live render the icon was the dominant legibility
  fix — more than any background change.
- The journey work-in-progress banner becomes `color="blue"` with the info
  icon, deleting the hard-coded hex.
- The leftover-files alert becomes blue per D3; the store alert and the
  visibility alert stay yellow. All keep the default `light` variant.
- The setup card keeps its `dmc.Paper` structure and gains its tint in
  `assets/stylesheet.css` on the existing `.setup-card` class: background
  `var(--mantine-color-blue-light)` plus a colored border accent echoing
  alert anatomy, with a modifier class switching the yellow tokens for the
  stats-folder state per D2. Mantine defines the `-light` tokens per color
  scheme, so dark mode needs no separate rules (verified in both schemes).

### Why the setup card keeps its Paper

Rebuilding the card as a `dmc.Alert` was considered and rejected. The card's
primary action is a link deliberately styled as a button through
`assets/stylesheet.css` because the dmc 2.8.0 wrapper does not expose
Mantine's `component=` escape hatch, and the Skip button's mounting is load
bearing for the skip callback (`allow_optional`). A rebuild would churn that
wiring and its tests for no visual gain over a few lines of CSS on the class
the card already has.

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
- PR 2 (after D1–D3 are ruled): the implementation — icons and recolors on
  the four alerts, the setup-card CSS, and the docs definition of done:
  update the two [specs/playlists.md](specs/playlists.md) statements that
  name alert colors, distill D1 into `decision_log.md` as the durable
  color-language entry with the specs linking it, and delete this file. No
  dependencies on other in-flight work. A kickoff prompt for the
  implementing agent is authored once the decisions are ruled.

## Testing

- This PR: docs gates only (`tests/test_docs.py` enforces the Status line,
  section order, and link integrity).
- PR 2: no behavior changes, so no new unit tests are expected; existing
  gates must stay green, and the visual result is verified by running the
  app in both color schemes and checking each surface (the trigger
  conditions for every notice are enumerated in the specs). The tint
  rendering itself was already validated during design with a standalone
  dmc 2.8.0 test bed in both schemes.
