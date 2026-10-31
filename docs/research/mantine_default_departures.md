# Where the app departs from Mantine's defaults

Date: 2026-10-31
Author: claude-opus-5-5 · effort: xhigh
Source revision: `87fe0c64` on pull request #457's branch, plus the toast
settings that pull request added after it, with dash-mantine-components 3.0.0,
which bundles Mantine 9.7.4

This is a list of the places where the app's look and behavior depart from
Mantine 9's defaults, kept so the maintainer can revisit each one. It records the code on
the date above, and nothing keeps it current: check the code before acting on
an entry. Mantine's values were read from the CSS that dash-mantine-components
3.0.0 bundles, and the sizes and weights were measured in headless Edge on
Settings with the app's two stylesheets removed.

## App-wide departures

Each of these changes Mantine's look or behavior everywhere it applies.

| # | What the app does | Mantine 9's default | Where | Why |
| --- | --- | --- | --- | --- |
| 1 | Corners are 4 px (`defaultRadius: "sm"`) | `md`, 8 px | theme in `source/app_shell.py` | The maintainer's choice on 2026-10-31, when Mantine 9 changed the default (#457) |
| 2 | Text links are always underlined (`Anchor` `underline="always"`) | Underlined on hover | theme in `source/app_shell.py` | A link reads as a link without its color ([2026-10-22 entry](../decision_log/2026/2026-10-22-text-links-use-readable-colors-and-persistent-underlines.md)) |
| 3 | Text links are blue 9 in light mode (`--mantine-color-anchor`) | Blue 6 in light mode; blue 4 in dark, which the app keeps | `assets/stylesheet.css` | Blue 6 misses 4.5:1 contrast on white and on tinted notices ([2026-10-22 entry](../decision_log/2026/2026-10-22-text-links-use-readable-colors-and-persistent-underlines.md)) |
| 4 | Every field label is bold, 700 (`.mantine-InputWrapper-label`) | The "medium" weight, 600 (500 on Mantine 8) | `assets/stylesheet.css` | None recorded for the weight. `e7e0ac1d` (2026-08-03) made it one rule for every field label, so a new kind of field can't miss it |
| 5 | The chosen option in a dropdown list is also bold, on a light blue background (`.mantine-Select-option[data-checked]`, and the same for MultiSelect) | A check mark only | `assets/stylesheet.css` | None recorded. Added in `554c7164` (2025-10-26, "Update styling") |
| 6 | Dialog titles are bold and 1.6em (`.mantine-Modal-title`) | Regular weight, 400, at 16 px | `assets/stylesheet.css` | None recorded. Added in `f359c48a` (2025-11-10) with the old Settings dialog |
| 7 | Switch labels are 16 px (`.mantine-Switch-label`) | 14 px | `assets/stylesheet.css` | To make a switch's label "stand out slightly more" (`ca23aeb5`, 2025-11-14) |
| 8 | Navbar labels are 16 px (`.mantine-NavLink-label`) | 14 px | `assets/stylesheet.css` | "For better legibility" (`3fd3df27`, 2025-11-15) |
| 9 | Tooltips in dark mode are dark: dark 5 with gray 0 text, a 1 px dark 4 border and a shadow. AG Grid's tooltips are styled to match | Light in dark mode: gray 2 with black text, no border (gray 9 with white text in light mode, which the app keeps) | `assets/tooltips.css` | None recorded. Added in `f96a7c17` (2026-07-01, "Polish playlist last-played tooltips") |
| 10 | A toast can't be dragged or scrolled away sideways, and hovering a toast pauses only its own timer (`allowDragDismiss=False`, `allowScrollDismiss=False`, `pauseResetOnHover="notification"`) | A sideways drag or scroll dismisses a toast, and hovering any toast pauses them all | `NotificationContainer` in `source/app_shell.py` | Mantine 8's behavior, kept so a toast meant to stay until closed can't vanish on a stray trackpad scroll. Raised in review of #457; asked on 2026-10-31, the maintainer had no preference, and the pull request kept Mantine 8's behavior |

## Mantine 9 changes kept as shipped

These changed when the app moved to Mantine 9, and the app takes the new
default.

- **"Light" and "subtle" colors are solid, not translucent.** On this app's
  pages that shows on the navbar's active item, the ⓘ help icons (darker in
  light mode, brighter in dark), and the PB card's **Refresh** button (a darker
  blue in light mode, white instead of blue in dark). The maintainer kept them
  on 2026-10-31. Setting `useV8CssVariablesResolver=True` on the
  `MantineProvider` would bring back Mantine 8's colors, though Mantine calls
  it a migration aid.
- **The "medium" font weight is 600, up from 500.** It changed no text on the
  pages compared, because the app's field labels are bold anyway (entry 4).

## Adjustments in one place

These change one spot and leave Mantine's look elsewhere alone.

- **Stylesheet rules scoped to one element:** the layout of Run History's
  playlist and scenario fields, the Follow switch's label, the PB card's
  position tooltip, the scenario note's scroll area (a fade when the note is
  clipped, and a focus ring) and its text box, and the point color field's
  swatch, which shows the chart's default point color.
- **Props on single components:** `radius="xl"` makes the ⓘ help icons round,
  in Chart options and on the typical score; `fw=700` bolds the "Category:"
  and "Total runs:" labels in the scenario stats; and `checkIconPosition="right"`
  puts the check mark on the right in Run History's two dropdowns and the
  playlist selector, where Mantine puts it on the left.
- **12 `radius="sm"` props** now equal the theme's default and change nothing.
  They were equally redundant on Mantine 8, whose default was also `sm`.
