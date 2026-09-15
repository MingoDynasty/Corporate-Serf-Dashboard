# Setup Hints Become Notices

Status: Proposed
Date: 2026-09-12

## TL;DR

Three messages that tell the user the app needs something from them are
still plain text: the stats-folder line at the top of Scenario Performance,
its restart-pending twin, and the restart notice on the Settings page. The
color-language sweep that gave every other notice a tint and an icon never
reached them, so the faintest lines on the page are the ones the user most
needs to see. This proposal moves them onto the panel anatomy the setup card
already wears and changes no wording. The Position field's inline hints stay
as they are, because they qualify a value rather than announce a condition.

## Decisions needed

Four product rulings. Each carries the author's recommendation, adopted by
the maintainer as a non-binding lean on 2026-09-12 pending the co-design
review. Everything else in this proposal is author-owned and reversible.

### D1 — The Position hints stay value qualifiers

Status: Open. Maintainer lean (2026-09-12): keep them as they are,
non-binding until ruled.

The Position field on Scenario Performance appends a dimmed fragment to its
value in three states (username unset, lookup failed, served from cache). The
question that prompted this proposal asked whether every plain-text message
on the page should be removed or converted to a notice component; these three
are the other candidates.

**Recommendation: leave the component alone.** The hint is the second half of
a sentence whose first half is the field's value, and the manual Refresh
callback relies on that: with no username configured it returns `no_update`
for the value because the field already explains itself. Promoted to a panel,
the explanation detaches from the value it qualifies and the loudest element
on the page lands under a stat tile. The decisive case is Skip: declining the
identity offer on the setup card writes an empty username, after which the
field reads "N/A — set your KovaaK's username in Settings" on every visit for
good. As a quiet qualifier beside a stat that is correct, and the card's fine
print already said rank lookups would be off. As a panel it is a permanent
notice nagging about a choice the user made, on the page whose card they just
dismissed. The
[messaging-consistency proposal](app_messaging_consistency_proposal.md)'s
D1 (PR #247, ratified 2026-09-14) also trims these hints to bare
fragments, which is the opposite direction from a notice.

Choosing differently: promoting them puts a third panel on the page (beside
the setup card and the promoted stats-folder hint) and needs an answer for
the post-Skip state. Removing them leaves "N/A" with no explanation, which
the
[2026-08-09 in-place ruling](../decision_log.md#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)
forbids, and leaves a cached position indistinguishable from a fresh one.

### D2 — The restart-pending branch is yellow

Status: Open. Maintainer lean (2026-09-12): yellow, non-binding until ruled.

While a saved stats-folder change awaits a restart, the Home hint reads
"Restart the app to apply your saved settings." and the setup card stands
aside. The unconfigured branch is yellow without debate: it matches the setup
card's blocking state. The restart branch is the judgment call.

**Recommendation: yellow.** The severity scale defines yellow as a state that
needs the user without anything having failed, and blue as informational with
any offered action optional. A pending restart needs the user, and restarting
is not optional: nothing plots until it happens. The setup card's own reason
for its yellow state is that it blocks every plot on the page, and the restart
state blocks every plot too. Both branches yellow also keeps the hint one
color, one class, and one test shape.

Choosing differently: blue reads the state as "nothing failed and the user
already acted", which is true but is not a criterion on the scale, and it
makes the completion step of first-run setup quieter than the yellow card
that preceded it. It also costs a second class and icon pair on one id.

### D3 — The promoted hint has no title

Status: Open. Maintainer lean (2026-09-12): no title, non-binding until
ruled.

The setup card and the leftover-files notice carry a bold title above their
body. The Aim Training Journey banner does not: icon and one sentence.

**Recommendation: no title.** Each hint is one sentence that already names
the action ("Restart the app…", "…set it in Settings"). A title over it
repeats the sentence in fewer words. The title-less shape is shipped (the
journey banner, a `dmc.Alert`); as a Paper it needs one Group prop, specified
in Design. No title means no new string: the proposal changes no copy at all,
which keeps
it clear of PR #247's Copy block and lets the implementation land on either
side of #247's implementation PR.

Choosing differently: a title ("Restart needed", "Stats folder not set") is
new user-facing copy. It would join a Copy block in this proposal, go through
copy review, and be the one thing the two arcs would then contend over.

### D4 — The Settings restart notice joins the same anatomy

Status: Open. Maintainer lean (2026-09-12): promote it to the same yellow
panel, non-binding until ruled.

The Settings page shows "Restart the app to apply. This app is still running
on the settings it started with." under the Save button whenever
`is_restart_pending()` holds: the stored stats folder differs from the pinned
one (moved, cleared, or set while none was usable), or a frozen identity pin
differs from the stored username or Steam ID. So it shows after a username
fix or a folder move on an install that works, as well as on the first-run
path. The Home restart branch is the subset of that condition where no usable
pin exists and nothing plots; in the working-install states Home shows no
hint at all. The notice is plain text colored orange, a color the severity
scale reserves for partial success and marks toast-only. No decision ruled
that color; the
[2026-08-02 entry](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)
that created the notice says nothing about its look. This is a scope addition
beyond the Scenario Performance question that prompted the proposal.

**Recommendation: the same yellow panel.** One anatomy for the restart
condition on both pages, and one severity in every state the notice has.
Yellow in the working-install states comes from the scale's own words: a
saved change that is not in effect until the user restarts is "a state that
needs the user without anything having failed", and the restart is optional
only if the user does not want the change they saved. The 2026-08-30 entry
rejected a single accent color for exactly this case, because it would make
"your saved choices are silently not applying" look like an FYI. On the
first-run path the same yellow then carries from Settings to the Home restart
branch (D2) with no change of severity mid-flow.

Yellow text is not an option. Measured against the dmc 2.8.0 palette (WCAG
2.x ratios, page backgrounds `#ffffff` and `#242424`), no Mantine yellow
reaches 4.5:1 as text on the light background: the darkest, yellow-9, is
3.00:1, while every shade clears 3:1 on dark. The
[2026-08-20 point-color entry](../decision_log.md#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
found the same for plot points, where no shade reaches 3:1 on both plot
backgrounds. The panel is legible because its sentence stays at body text
color (19.66:1 light, 6.85:1 dark); the yellow is a cue on the icon and
border (1.74:1 against the light tint), never the thing being read. The cost
is a component change in the settings page, the notice callback returning
the panel's children for the pending state, and three settings-test
assertions walking for the sentence instead of comparing it.

Choosing differently. Leaving the orange text costs nothing in code, but
orange-filled measures 2.57:1 on white and 4.34:1 on dark, the least legible
of the three messages (the dimmed Home hint is 3.32:1 on white); the
notifications spec's statement that no inline surface uses orange stays
false; and the decision log needs an explicit accepted-exception note so the
next sweep does not re-find it. Blue on Settings with yellow on Home is
quieter after a routine identity fix, but on the first-run path one pending
restart would show blue on Settings and then yellow on Home. Recoloring to
yellow text is rejected on the numbers and is not offered as an option.

## Problem

### The inventory

Verified against `main` at `5be84bf` (2026-09-12) and re-checked at
`fcc94e9` (2026-09-14). Three bare `dmc.Text` messages tell the user the app
needs something from them: a usable stats folder, or a restart to apply what
they saved. None carries a tint or an icon, and none is among the five inline
surfaces the
[2026-08-30 color-language entry](../decision_log.md#2026-08-30-one-severity-color-language-for-inline-notices)
enumerated.

| Surface | Function | Copy | Look today |
| --- | --- | --- | --- |
| Home, stats folder unconfigured | `_stats_dir_hint()` in `source/pages/home.py` | `No stats directory configured — set it in [Settings]` | dimmed, `sm`, no icon (`.stats-dir-hint`) |
| Home, restart pending | same function, same id | `Restart the app to apply your saved settings.` | same |
| Settings, restart pending | `_restart_notice()` in `source/pages/settings.py` | `Restart the app to apply. This app is still running on the settings it started with.` | orange (`--mantine-color-orange-filled`), `sm`, no icon (`.app-settings-restart-notice`) |

The Position field's three inline hints (`_rank_hint_children()`, class
`.scenario-rank-hint`, dimmed `xs`) are the other plain-text messages on
Scenario Performance. They are value qualifiers, not notices, and D1 proposes
leaving them.

Everything else on the page is already on a sanctioned surface: the setup
card is a `dmc.Paper` wearing `.alert-panel`; the five empty-state
title/message pairs render inside the Plotly figure, not the DOM; toasts are
governed by the routing policy.

### Why it matters

The 2026-08-30 entry's own diagnosis was that "the surfaces that most needed
attention were the faintest things on the page". The Home hint is the
faintest thing on a page that is otherwise empty when it shows: the scenario
list is empty, nothing plots, and one dimmed line explains why.

The restart branch is mainline, not an edge case. When startup detection
finds no KovaaK's folder, the hint is the completion message of first-run
setup: setup card (stats-folder state), then Settings, then Save, then back
to Home, then this line. All three of these hold in `_stats_dir_hint()`: the
process pin from `resolve_stats_dir()` is `None`; `is_stats_dir_change_pending()`
is true; and the stored `stats_dir` is non-empty (clearing the field is also a
pending change, but falls through to the unconfigured branch).

The Settings notice is off the scale. The 2026-08-30 entry: "orange is
partial success, where the action committed but a follow-up write did not.
Green and orange stay toast-only". The
[notifications spec](../specs/notifications.md#the-severity-scale) restates
it: "no inline surface uses either." The notice's orange predates that entry
and was not swept because it is a `dmc.Text`, not an alert.

Both messages sit below WCAG's 4.5:1 for normal text in both color schemes,
and the panel body they would move to does not. Measured against the dmc
2.8.0 palette with WCAG 2.x relative luminance; page backgrounds `#ffffff`
(light) and `#242424` (dark); tint alpha 0.1 light and 0.15 dark:

| Text | Light | Dark |
| --- | --- | --- |
| Home hint today (`dimmed`) | 3.32:1 | 4.04:1 |
| Settings notice today (`orange-filled`: orange-6 light, orange-8 dark) | 2.57:1 | 4.34:1 |
| Caution panel body text on its tint | 19.66:1 | 6.85:1 |
| Caution panel icon and border on its tint (`yellow-light-color`) | 1.74:1 | 8.70:1 |
| yellow-9, the darkest yellow, as text on the page | 3.00:1 | 5.18:1 |

### The co-render, and why it is reachable

The unconfigured hint and the setup card's identity state can show together.
`bootstrap_stats_dir()` writes the detected folder merged over whatever is
stored, never all three keys, so a fresh install with a detectable KovaaK's
folder has `stats_dir` present and `kovaaks_username` absent: that is the
identity card's normal path. If that folder later vanishes before the user
visits Settings, the next boot has a present-but-unusable `stats_dir` beside
an absent username key, and both surfaces render. The
[2026-08-11 setup-card entry](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)
called mixed presence "unreachable through the app"; that holds for
`stats_dir: ""` (every Save writes all three keys) but not for the
vanished-path variant. Narrow, but real, and the design answers it. The
restart branch has no such case: the card stands aside entirely while a
change is pending.

### What pins the current shape

`tests/test_home_stats_dir_hint.py` asserts both Home branches by exact
string and by id, and asserts `hint.children` directly.
`tests/test_settings_page.py` asserts the Settings notice's
`children == RESTART_NOTICE` and its class constant, never its color.
`tests/test_home_setup_card.py` asserts the `.alert-panel` classes on the
setup card and is the model for the Home hint; `tests/test_playlist_pages.py`
asserts the leftover-files Paper's `SUPERSEDED_NOTICE_CLASS` and its hidden
twin, the closer model for a hidden-class panel like the Settings notice.
`tests/test_ui_presentation.py` touches none of these.

## Design

### The Home hint

`_stats_dir_hint()` returns a list holding a `dmc.Paper` instead of a
`dmc.Text` (the layout splats the list), keeping `id="stats-dir-hint"` and
the two branches' selection logic untouched. Anatomy, the setup card's minus
the title row: `withBorder=True`; className
`alert-panel alert-panel-caution stats-dir-hint`; children a `dmc.Group` with
`wrap="nowrap"`, gap `xs`, and `align="flex-start"`, holding
`local_icon("material-symbols:warning-outline", className="alert-panel-icon")`
and a `dmc.Text` with today's children verbatim: the restart sentence, or the
unconfigured sentence with its
`dmc.Anchor("Settings", href="/settings", refresh=False)`.

`wrap="nowrap"` is load-bearing. `dmc.Group` defaults to `wrap="wrap"`, and
flexbox sizes the `dmc.Text` at its one-line width, so a sentence wider than
the space beside the icon drops whole onto the next row, under the icon,
instead of wrapping beside it; `align` alone does not prevent that. A render
probe during review (dmc 2.8.0, Chromium, the app's stylesheet and vendored
icon) showed the Settings sentence dropping at the 32rem width and both Home
sentences dropping in a 343px window; with `wrap="nowrap"` they wrap beside
the icon. `_settings_help_label()` in `home.py` already uses the prop for the
same reason. With nowrap the 16px icon sits about 4px above the center of the
first 25px line box; whether to nudge it, as Mantine's own Alert does, is the
author's call at implementation.

`dmc.Paper`, not `dmc.Alert`, for both branches. The unconfigured branch
holds a link, and the 2026-08-30 component rule sends a notice with
interactive content to the panel anatomy. The restart branch is text-only and
the rule would permit `dmc.Alert` there, but the two branches share one slot,
one id, one class, and one test file; splitting the component across them
buys nothing and costs a second anatomy to keep in step.

`.stats-dir-hint` drops its dimmed color, small size, and bottom padding and
becomes a layout class only, joining the setup card's width and spacing rule
as a second selector on the same declaration (`margin-bottom` at the `md`
step, `max-width: 32rem`), so the two panels are the same width when they
stack. The `.alert-panel` and `.alert-panel-caution` rules are untouched.

Under D2 both branches are yellow with the warning icon. If D2 goes blue for
the restart branch, that branch drops `alert-panel-caution` and takes
`material-symbols:info-outline`; the id stays, and the class assertion in the
test splits per branch.

Under D3 there is no title row. If D3 goes titled, the title takes
`.alert-panel-title` in a leading `dmc.Group` with the icon, exactly as the
setup card lays it out, and the titles join the Copy block below.

### Co-render and ordering

Layout order is unchanged: the hint renders above the setup card's `dmc.Box`.
In the reachable co-render (vanished folder beside a never-asked identity)
the page shows a yellow blocker above a blue offer, each about a different
thing, and the setup card's key-absence logic is untouched. The card still
stands aside while a stats-folder change is pending, so the restart branch
never stacks with it; the 2026-08-11 entry's "the restart hint owns that
moment" stays true.

### The Settings restart notice (D4)

Under the lean, the `dmc.Text` with `id="app-settings-restart-notice"`
becomes a `dmc.Paper` with the same id, `withBorder=True`, and the same
`Group` anatomy as the Home hint (`wrap="nowrap"`, warning icon beside the
sentence). `_restart_notice()` keeps its `(children, class)` shape: `""` with
`RESTART_NOTICE_HIDDEN_CLASS` when nothing is pending, exactly as today, and
the group with `RESTART_NOTICE_CLASS` when something is. The
`save_user_settings` callback's two outputs on that id keep their shape, and
the hidden-class reveal (`display: none` on the modifier class) is untouched.
`RESTART_NOTICE_CLASS` becomes
`alert-panel alert-panel-caution app-settings-restart-notice`; the
`.app-settings-restart-notice` rule drops its orange color and small size and
keeps only what layout needs (a `max-width` matching the Home panels if the
form's Stack would otherwise run the panel full width; author's call at
implementation).

The notice's trigger logic does not change: it shows for every restart-scoped
change, identity or folder, on a working install or a first-run one, and D4
gives every one of those states the same yellow.

If D4 is ruled out of scope, the settings page is untouched, and the shipping
PR's decision-log entry records the orange notice as an accepted exception to
the toast-only rule, naming the trade actually accepted: an off-scale color
at 2.57:1 in light mode, kept on purpose, so the next sweep does not re-find
it.

### Copy

No string is added or changed. Every string this proposal touches is carried
verbatim:

- Home, unconfigured: `No stats directory configured — set it in [Settings]`
  (the anchor is a separate child). PR #247's ratified Copy block rewrites this line
  to `No stats folder configured. Set it in [Settings].`; whichever
  implementation lands second rebases the one test string.
- Home, restart pending: `Restart the app to apply your saved settings.`
- Settings, restart pending: `Restart the app to apply. This app is still
  running on the settings it started with.`

If D3 is ruled titled, the titles are new strings and join this block before
implementation.

### Alternatives rejected

- **Removing either Home branch.** Each is the only thing explaining why the
  page beside it is empty; without it the page is blank and silent.
- **`dmc.Alert` for the restart branch alone.** Permitted by the component
  rule, rejected above: two components in one slot. The Home hint also only
  ever renders with the layout, never dynamically, which is the other half of
  the rule's reading of `role="alert"`.
- **`dmc.Alert` for the Settings notice.** The strongest alternative under
  D4: the notice is text-only and appears after a Save, the store alert on
  the same page already is one, and `_restart_notice()` would keep returning
  a string so no settings test would change. Rejected because Mantine's
  light-variant Alert has a transparent border, 14px body text, and a 20px
  icon column: it would not look like the Home panel the user sees next, and
  one look on both pages is the case for D4.
- **Yellow text for the Settings notice.** No Mantine yellow reaches 4.5:1 as
  text on the light background (yellow-9 is 3.00:1); the panel keeps its
  sentence at body color, so its legibility never depends on the yellow.
- **Folding the promotion into PR #247's implementation PR.** The
  maintainer's standing rule keeps copy changes and other changes in separate
  PRs; this is the same rule seen from the other side.
- **A shared "setup panel" builder for the card, the hint, and the notice.**
  Three call sites with two anatomies (titled and not) do not yet justify an
  abstraction; the shared thing is the CSS, which already exists.

### Blast radius

`source/pages/home.py` (`_stats_dir_hint()` only), `source/pages/settings.py`
(`_restart_notice()`, `RESTART_NOTICE_CLASS`, the layout's notice element;
D4 only), `assets/stylesheet.css` (`.stats-dir-hint`, the `.setup-card`
selector list, `.app-settings-restart-notice`), and the tests and docs named
below. No callback signature, id, or settings-service behavior changes.

## Out of scope

- The Position hints' wording and separator: PR #247's D1.
- The unconfigured hint's wording: PR #247's Copy block.
- The five empty-state messages drawn inside the Plotly figure, and every
  toast.
- The Settings store alert and the Playlists alerts, already on the scale.
- The Settings save-status line (`.app-settings-save-status-failed`: red
  text, no icon, for the failed and the refused save). It stays a status
  line: a readout beside the button it answers, not a standing notice, which
  is how the settings spec classes save outcomes. Named so the next sweep
  does not re-find it; once this ships it is the only bare text in the app
  colored with a severity token.
- The unconfigured line's accuracy in the vanished-folder state, where it
  says nothing is configured while the Settings field shows the stored path.
  A copy question for the messaging arc, not this PR.
- Strengthening the pale yellow panel tint, deferred by the 2026-08-30 entry.
- The configured-but-wrong username case, deferred by the 2026-08-09 entry.
- Any new notice surface. This proposal changes the look of three messages
  that exist.

## Testing

- `tests/test_home_stats_dir_hint.py`: the two assertions on `hint.children`
  become walks of the panel for the sentence and, on the unconfigured branch,
  the `dmc.Anchor`; every case also asserts `hint.className` against the
  alert-panel classes, on the models named under What pins the current
  shape. The
  co-render case (vanished folder, absent username key) is added, asserting
  that both the hint and a non-empty setup card box render, hint first.
  Assertions are tightened, never loosened.
- `tests/test_settings_page.py` (D4 only): the three `notice == RESTART_NOTICE`
  assertions walk the children for the sentence. The two hidden-state
  assertions (`notice == ""` and `notice.children == ""`) stay as they are
  because the hidden children stay `""`, and the class assertions stay on
  the constants. `FORM_OUTPUT_IDS` is unchanged because the id is.
- `tests/test_home_rank_format.py` is untouched under D1.
- Gates: `uv run pytest tests`, `uv run ruff format --check .`,
  `uv run ruff check`, `uv run mypy source`,
  `uv run python -m compileall source tests`.
- Manual, at the running app in both color schemes: the unconfigured branch
  (stop the app, set `stats_dir` in `data/settings.json` to a path that does
  not exist, start); the restart branch (from that state, Save a real folder
  in Settings, then open Home without restarting); the co-render (the
  unconfigured state with the `kovaaks_username` key deleted from the file);
  and the Settings notice (any Save of a changed folder or identity while the
  app runs). Two of these at a width where the sentence needs a second line,
  the Settings notice at the form's width and the Home hint in a narrow
  window, checking that the sentence wraps beside the icon and never under
  it. Deleting `settings.json` does not reach the hint: the bootstrap
  detects and writes a real folder before the pin is taken.

## Delivery plan

1. **This PR: the proposal.** Default lane: the connector, one full Codex
   review in co-design mode, the maintainer's deep read. Nothing ships until
   D1 to D4 are ruled.
2. **One implementation PR** (Opus 5 at high, from a kickoff prompt that
   names the rulings), in three commits: the Home hint with its tests; the
   Settings notice with its tests (D4); the docs. It is independent of PR
   #247's implementation PR: whichever lands second rebases one test string
   on the unconfigured hint.
3. **Docs definition of done**, in the implementation PR: a decision-log
   entry that amends the 2026-08-30 entry's five-surface enumeration (a
   superseded-in-part note there, the enumeration erased nowhere) and, if D4
   is adopted, the 2026-08-02 entry for the Settings notice's look;
   [`specs/scenario_performance.md`](../specs/scenario_performance.md#hosted-setup-surfaces)
   (Hosted setup surfaces),
   [`specs/settings.md`](../specs/settings.md#the-setup-card) (The setup
   card, and The Settings page under D4), and
   [`specs/notifications.md`](../specs/notifications.md#the-severity-scale)
   (the five-notice enumeration and the toast-only statement about orange);
   `docs/product.md`'s color-language inventory entry; `docs/roadmap.md`;
   the proposal file deleted; the kickoff prompt moved to
   `ignore/prompts/done/`.
