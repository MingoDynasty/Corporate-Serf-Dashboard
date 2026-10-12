# 2026-08-21: The Empty Point Color Is Called Default, And The Points Follow The Theme

Status: Accepted

The Point color field's empty state now reads Default instead of Automatic,
and its reset button reads Use default. Automatic suggested a Manual mode that
never existed, and Default is the word the Point size control beside it
already uses. The run points with no color chosen used to be the same indigo
in both themes; they now take the theme's own blue, a little deeper in dark
mode. The small preview swatch beside an empty field used to be plain white;
it now shows the color the graph is using in the current theme.

Decision: the first change is copy only. The stored value is unchanged: an
empty `point-color` still means the generated color, under the same persisted
id, so nothing a browser already saved is discarded. `POINT_COLOR_AUTOMATIC`
became `POINT_COLOR_DEFAULT`, and the reset button's id `point-color-default`.

**The run points take the theme template's colorway.** The 2026-08-20 entry
says an empty color keeps whatever Plotly and the Mantine template give it.
Until now the Mantine template's colorway never reached the run points:
`px.scatter` writes the first colorway entry of Plotly's default template,
`#636efa`, into the trace's `marker.color` when the figure is generated, and
the `update_layout(template=...)` applied afterwards never overrides a
property the trace already sets, so the points were `#636efa` in both themes.
The generator now clears that baked color (`marker_color=None`), so the run
trace carries no color of its own and Plotly draws it in the first colorway
entry of whichever template the theme applies: `#228be6` (blue-6) under
`mantine_light`, `#1971c2` (blue-7) under `mantine_dark`. First entry because
the run trace is the figure's first trace; colorway assignment is by index in
Plotly, and that ordering is pinned by test. `plot_service.generated_point_color`
reads the same entry for a scheme, and is the single source for the preview.

**How the swatch shows it.** Mantine's `ColorInput` renders its preview as a
`ColorSwatch` whose color is the value when valid and a hardcoded `#fff`
otherwise, as an inline style. Home sets `--point-color-default-light` and
`--point-color-default-dark` on the field from `generated_point_color`, and
two stylesheet rules scoped to `.point-color-field:has(input:placeholder-shown)`
(the second under `:root[data-mantine-color-scheme="dark"]`) repaint the
swatch's color overlay from the active one with `!important`, the only way
past an inline style. A typed or picked color hides the placeholder, and the
rules with it, so Mantine's own preview of that color takes over. Alternatives
rejected: **keeping the baked `#636efa` and previewing it as a constant**,
which leaves the theme template decorative for the primary data mark;
**storing a hex as the layout value**, which moves a persisted default
(discarding stored values) and turns the generated color into a chosen one;
**replacing the preview through `leftSection`** with a swatch kept in sync by
a callback, a round trip per keystroke to do what two CSS rules do.

Not changed: the Average Score line, which `px.line` bakes in the same
`#636efa` and which now sits beside blue points. Clearing its color would hand
it the colorway's second entry (red) rather than the points' color. Ruled
2026-08-22: the line gets a user setting of its own in a later PR, not a
colorway change here.

**Superseded in part, for copy (2026-09-14).** The line this entry calls
Average Score is labelled "Average score" in the legend and its hover label.
The color decision is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md).
