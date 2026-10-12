# 2026-09-15: Setup Hints Wear The Notice Anatomy

Status: Accepted

Three messages telling the user the app needs something from them were still
plain text: the stats-folder line at the top of Scenario Performance, its
restart-pending twin, and the restart notice on the Settings page. They now
look like every other inline notice, a yellow panel with a warning icon
beside the sentence. Nothing they say changed, and no new message was added.

**The three surfaces.** The Home hint (`_stats_dir_hint()` in
`source/pages/home.py`) and the Settings restart notice (`_restart_notice()`
in `source/pages/settings.py`) are `dmc.Paper` elements wearing
`alert-panel alert-panel-caution` plus their own layout class, holding one
`dmc.Group` of `local_icon("material-symbols:warning-outline")` and a
`dmc.Text`. No title row: each sentence already names the action, and a
title over it would be new copy. The Home hint keeps its id, both branches,
and the selection logic that picks between them; the Settings notice keeps
its id, its `(children, class)` shape, its hidden-class reveal, and the two
`save_user_settings` outputs that drive it. The Home panels share the setup
card's width so the two match when they stack; the Settings panel is capped
at the form fields' width and ends where they do.

**The rulings** (proposal #281, all four ratified by the maintainer on
2026-09-15 after two full reviews):

- **D1**: the Position field's inline hints stay value qualifiers and are
  not promoted. Rejected: promoting them, which detaches the explanation
  from the value it qualifies and turns the post-Skip state into a permanent
  notice nagging about a choice the user made.
- **D2**: the restart-pending branch is yellow, like the unconfigured one. A
  pending restart needs the user and blocks every plot on the page. Rejected:
  blue, which reads the state as an FYI and costs a second class and icon
  pair on one id.
- **D3**: no title. Rejected: a title, which would be the only new copy in
  the change.
- **D4**: the Settings notice joins the same anatomy. Rejected: keeping the
  orange text as an accepted exception; blue on Settings with yellow on Home,
  which changes severity mid-flow on the first-run path; and yellow text,
  which the numbers below rule out.

**Why not yellow text.** Measured against the dmc 2.8.0 palette (WCAG 2.x,
page backgrounds `#ffffff` and `#242424`, tint alpha 0.1 light and 0.15
dark), no Mantine yellow reaches 4.5:1 as text on the light background:
yellow-9, the darkest, is 3.00:1 (5.18:1 dark). The shipped orange measured
2.57:1 light and 4.34:1 dark, and the dimmed Home hint 3.32:1 light. In the
panel the sentence stays at body text color, 19.66:1 light and 6.85:1 dark,
and the yellow is a cue on the icon and border (1.74:1 on the light tint,
8.70:1 dark) rather than the thing being read.

**`wrap="nowrap"` is load-bearing on both groups.** `dmc.Group` defaults to
`wrap="wrap"` and flexbox then sizes the `dmc.Text` at its one-line width, so
a sentence wider than the space beside the icon drops whole onto the row
under the icon instead of wrapping beside it; `align` does not prevent that.
Both sentences do exceed that space at a narrow window, and the Settings one
also did at the 32rem width the Home panels use. With `align="flex-start"`
the icon then pins to the top of a taller line box, so a CSS rule drops it by
half the leading onto the first line's middle.

**The co-render is reachable.** `bootstrap_stats_dir()` merges only
`stats_dir` into the store, so a detected folder that later vanishes leaves a
present-but-unusable `stats_dir` beside an absent `kovaaks_username` key:
the hint's case and the account offer's case at once. The page shows the
yellow hint above the blue card, each speaking for its own key, at the same
width. The restart branch has no such case, because the card stands aside
while a stats-folder change is pending.

Amends the
[2026-08-30 color-language entry](2026-08-30-one-severity-color-language-for-inline-notices.md),
whose enumeration of five inline surfaces becomes seven, and the
[2026-08-02 pinning entry](2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself.md),
which created the Settings notice without ruling its look. Out of scope, so
that the next sweep does not re-find them: the Settings save-status line,
which stays a red status line beside the button it answers, and the pale
yellow tint, deferred by the 2026-08-30 entry.

Provenance: `docs/proposals/setup_hints_become_notices_proposal.md`, proposed
in PR #281 and deleted in the shipping PR; git history holds its full text.
