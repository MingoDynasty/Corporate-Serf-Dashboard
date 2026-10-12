# 2026-08-03: Home's Controls Row Measures The Content Area, Not The Window

Status: Accepted

Opening the navigation sidebar used to shove Home's row of controls onto a
second line, and closing it snapped them back. The sidebar takes 250px away
from the page, but the rules deciding how to lay the controls out were reading
the width of the whole browser window, which does not change when the sidebar
opens. Those rules now read the width of the area the controls actually get,
and the two wide dropdowns narrow a little before the row gives up and wraps.

Decision: Home's controls `dmc.Grid` sets `type="container"` and passes
`breakpoints`, and both wide playlist/scenario dropdowns swap a hard
`miw="min(400px, 100%)"` floor for `flex="1 1 200px"` under a
`maw="min(400px, 100%)"` cap and over a matching `miw` floor. The breakpoint
*values* are unchanged Mantine defaults; only the box they measure moves.

Why: `dmc.AppShellNavbar` is `position: fixed` with `width: 250px` and offsets
main's padding, so the content area shrinks by 250px while the viewport does
not. Mantine's default Grid emits `@media (min-width: …)` for responsive
`span` values, so Home's `span={"base": 12, "lg": 10}` crossed its threshold at
a 1200px *window* even when the content area was only ~900px. Both columns then
got a share of width the page did not have: the left column's controls wrapped
and the right column's radio labels were squeezed. The 400px `min-width` floor
compounded it, for the reason recorded below.

Consequences and constraints:

- **Line-breaking reads the hypothetical main size, not the shrunk size.** A
  flex item is collected onto a line at its flex-basis clamped by min/max
  width; `flex-shrink` only redistributes space *inside* a line that has
  already been collected. Anything pinning a dropdown's pre-wrap size at the
  400px target — the original `min-width: 400px`, and equally a
  `flex: 0 1 400px` basis — books 400px of the row before shrinking can run, so
  the row wraps at exactly the width it did before. The basis must therefore sit
  at the 200px *floor*, with `flex-grow` climbing back toward the 400px cap on a
  line that has room. `tests/test_home_layout.py` asserts the derived
  hypothetical size stays below the target rather than asserting the prop
  strings, because a prop-shaped test passes on all of the broken combinations.

- **`breakpoints` is not optional here.** Mantine renders the element carrying
  `container: mantine-grid / inline-size` only when a Grid passes *both*
  `type="container"` and `breakpoints`, while the `@container` queries
  themselves are emitted on `type` alone. Setting `type` without `breakpoints`
  produces queries with no container to match, silently collapsing every column
  to its `base` span. `tests/test_home_layout.py` pins both props together.
- **The threshold band moves.** Between roughly 1200px and 1480px of window
  width with the sidebar open, Home now stacks its two columns where it
  previously split them. That is the band where the split was crushing both
  columns, so the stack is the intended outcome rather than a regression.
- **Responsive *style props* have no container equivalent.** Mantine resolves
  those through theme media queries only, so this fix reaches responsive `span`
  values and nothing else. Nothing on Home relies on one today: the playlist
  filter's `ml={"base": 0, "lg": "xl"}` was the last, and PR #201 removed it
  outright for left-edge alignment — `tests/test_ui_presentation.py` now
  rejects any left offset on either playlist filter. A responsive margin or
  padding added elsewhere later would silently go back to measuring the window.
- **The sizing rule lives in `PLAYLIST_SELECTOR_PRESET`**, so the Aim Training
  Journey page's `dmc.MultiSelect` picks it up too. Both sit in wrapping rows
  and want the same behavior; splitting the rule to spare the second page would
  cost more than it saves. *(Renamed 2026-10-04: the rule is
  `PLAYLIST_SELECTOR_SIZING`, a second dict in the same module, so a page can
  put it on the column that holds its dropdown. Both pages still read the one
  rule.)*
