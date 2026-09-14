# Setup Hints Become Notices

Status: Proposed
Date: 2026-09-12

## TL;DR

Three messages that tell the user something is blocking the app are still
plain text: the stats-folder line at the top of Scenario Performance, its
restart-pending twin, and the restart notice on the Settings page. The
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
repeats the sentence in fewer words. The title-less anatomy is shipped, and no
title means no new string: the proposal changes no copy at all, which keeps
it clear of PR #247's Copy block and lets the implementation land on either
side of #247's implementation PR.

Choosing differently: a title ("Restart needed", "Stats folder not set") is
new user-facing copy. It would join a Copy block in this proposal, go through
copy review, and be the one thing the two arcs would then contend over.

### D4 — The Settings restart notice joins the same anatomy

Status: Open. Maintainer lean (2026-09-12): promote it to the same yellow
panel, non-binding until ruled.

The Settings page shows "Restart the app to apply. This app is still running
on the settings it started with." under the Save button while any
restart-scoped change is pending. It is plain text colored orange, a color the
severity scale reserves for partial success and marks toast-only. No decision
ruled that color; the
[2026-08-02 entry](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)
that created the notice says nothing about its look. It is the same condition
as the Home restart branch, one page over, on the exact path the user walks
(Save, then back to Home). This is a scope addition beyond the Scenario
Performance question that prompted the proposal.

**Recommendation: the same yellow panel.** Same condition, same anatomy, one
look on both pages. Yellow text is not an option: the
[2026-08-20 point-color entry](../decision_log.md#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
measured every Mantine yellow shade and none clears 3:1 on either page
background. The panel anatomy is precisely the shape that carries yellow
legibly, on the icon and the border rather than the text. The cost is a
component change in the settings page, the notice callback returning a
children list instead of a string, and the settings tests walking for the
text instead of comparing it.

Choosing differently: leaving it as orange text costs nothing in code, but
the notifications spec's statement that no inline surface uses orange stays
false, the proposal ships one condition as a yellow panel on Home and orange
text on Settings, and the decision log needs an explicit accepted-exception
note so the next sweep does not re-find it. Recoloring to yellow text is
rejected on contrast and is not offered as an option.

## Problem

### The inventory

Verified against `main` at `5be84bf` (2026-09-12). Three bare `dmc.Text`
messages tell the user a blocking condition exists. None carries a tint or an
icon, and none is among the five inline surfaces the
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
`tests/test_home_setup_card.py` is the only test asserting the
`.alert-panel` classes and is the model for the promoted surfaces.
`tests/test_ui_presentation.py` touches none of these.

## Design

### The Home hint

`_stats_dir_hint()` returns a `dmc.Paper` instead of a `dmc.Text`, keeping
`id="stats-dir-hint"` and the two branches' selection logic untouched.
Anatomy, the setup card's minus the title row: `withBorder=True`; className
`alert-panel alert-panel-caution stats-dir-hint`; children a `dmc.Group` (gap
`xs`, aligned to the top so a wrapped sentence does not float the icon) of
`local_icon("material-symbols:warning-outline", className="alert-panel-icon")`
and a `dmc.Text` holding today's children verbatim: the restart sentence, or
the unconfigured sentence with its
`dmc.Anchor("Settings", href="/settings", refresh=False)`.

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
`Group` anatomy as the Home hint (warning icon beside the sentence).
`_restart_notice()` returns a children list and a class instead of a string
and a class: an empty list with `RESTART_NOTICE_HIDDEN_CLASS` when nothing is
pending, the group with `RESTART_NOTICE_CLASS` when something is. The
`save_user_settings` callback's two outputs on that id keep their shape, and
the hidden-class reveal (`display: none` on the modifier class) is untouched.
`RESTART_NOTICE_CLASS` becomes
`alert-panel alert-panel-caution app-settings-restart-notice`; the
`.app-settings-restart-notice` rule drops its orange color and small size and
keeps only what layout needs (a `max-width` matching the Home panels if the
form's Stack would otherwise run the panel full width; author's call at
implementation).

The notice covers identity changes as well as the stats folder. Those need a
restart too, so the same yellow applies; nothing in the notice's trigger
logic changes.

If D4 is ruled out of scope, the settings page is untouched, and the shipping
PR's decision-log entry records the orange notice as an accepted exception to
the toast-only rule, with contrast as the reason, so the next sweep does not
re-find it.

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
  rule, rejected above: two components in one slot.
- **Yellow text for the Settings notice.** No Mantine yellow shade clears 3:1
  on either page background (measured in the 2026-08-20 point-color entry);
  the panel carries yellow on the icon and border for exactly this reason.
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
- Strengthening the pale yellow panel tint, deferred by the 2026-08-30 entry.
- The configured-but-wrong username case, deferred by the 2026-08-09 entry.
- Any new notice surface. This proposal changes the look of three messages
  that exist.

## Testing

- `tests/test_home_stats_dir_hint.py`: the two assertions on `hint.children`
  become walks of the panel for the sentence and, on the unconfigured branch,
  the `dmc.Anchor`; every case also asserts `hint.className` against the
  alert-panel classes, on `tests/test_home_setup_card.py`'s model. The
  co-render case (vanished folder, absent username key) is added, asserting
  that both the hint and a non-empty setup card box render, hint first.
  Assertions are tightened, never loosened.
- `tests/test_settings_page.py` (D4 only): the three `notice == RESTART_NOTICE`
  assertions walk the children for the sentence; the class assertions stay on
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
  app runs). Deleting `settings.json` does not reach the hint: the bootstrap
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
