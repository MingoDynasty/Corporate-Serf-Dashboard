# 2026-08-20: Run Points Get A Size Preset And A Color, And The Chart Stops There

Status: Accepted

The Scenario Performance chart now lets you change how the raw run points look:
a Small, Default, or Large point size, and a point color chosen from eight
curated swatches, a picker, or a typed hex value. Both live in a new **Run Data
Points** group in Chart options and persist in your browser like the overlays
beside them. Leaving the size on Default and the color empty keeps exactly the
chart the app drew before. Nothing else on the chart became customizable, and
that boundary is the decision as much as the two controls are.

Decision: the inspector gains one **Run Data Points** group between *Overlays*
and *Score Threshold*, holding a full-width `Small | Default | Large` segmented
control (`point-size`) and a `dmc.ColorInput` (`point-color`). Both carry
`persistence=True`, the same browser-local model as their siblings; nothing is
written to `data/settings.json` or `config.toml`. A **Use automatic** button
beside the color field is the reset.

**The product rule.** A chart control has to answer a recognizable user goal,
not expose a Plotly property. Size and color earn their place because two goals
are demonstrable: make the points easier to see, and pick a color that reads
better for you. The interface keeps three levels — a strong Automatic or
Default appearance for most users, a small set of controls for the primary data
marks, and nothing else until a real workflow demands it. The promotion rule
follows from that: reconsider opacity only if overlapping points are shown to
hide useful density, reconsider marker symbols only if the graph ever carries
multiple semantic point categories, and if a visual-object group would exceed
roughly three controls, revisit presets or design an advanced mode rather than
appending another property.

**Default is semantic, not a number.** Selecting Default leaves `marker.size`
completely unmodified rather than writing the pixel count the chart happens to
use today. Two consequences: the generated appearance and any future template
change flow through untouched, and the layout default of a persisted control
never has to move — changing one silently discards every value the browser
already stored under that id.

**Automatic is the empty value.** An empty `point-color` means Automatic and the
field says so through its placeholder. Cleared dmc inputs send `""`, never
`None`, so the guard is truthiness, never `is not None`. Hex is the only
accepted format, which keeps alpha out of the feature; anything unparseable
falls back to the generated color rather than erroring.

**The eight swatches, and how they were chosen.** One hex value has to work on
both real plot backgrounds — `#ffffff` light and `#242424` dark — so the shade
was selected per family against both, rather than taking one Mantine shade index
across the board. All eight clear 3:1 on both:

| Family | Hex | Light | Dark |
|---|---|---:|---:|
| blue-7 | `#1c7ed6` | 4.20:1 | 3.70:1 |
| cyan-8 | `#0c8599` | 4.35:1 | 3.57:1 |
| teal-8 | `#099268` | 3.95:1 | 3.93:1 |
| green-9 | `#2b8a3e` | 4.37:1 | 3.55:1 |
| orange-9 | `#d9480f` | 4.30:1 | 3.61:1 |
| red-7 | `#f03e3e` | 3.84:1 | 4.04:1 |
| grape-6 | `#be4bdb` | 4.02:1 | 3.86:1 |
| pink-6 | `#e64980` | 3.73:1 | 4.16:1 |

`swatchesPerRow` is set to 8 explicitly; the component's own default is 7, which
would strand the eighth swatch on a row of its own.

**The exclusions are v1 curation under the current themes, not permanent bans.**
Yellow is out because no Mantine yellow shade reaches 3:1 on both backgrounds.
Lime is out because green already covers that family and only its deepest shade
passes, so it would add a weakly differentiated choice. Gray is out because it
collides with the grid lines. Dark is out because it disappears against the dark
plot. Re-audit all four if the chart backgrounds change. Contrast was only an
eligibility screen — small rendered points were checked in both themes before
shipping — and an arbitrary custom color carries no such guarantee, which is why
the graph updates immediately and **Use automatic** is an obvious,
keyboard-reachable way back.

**Appearance applies after theming, and never touches `generate_graph`.** Both
controls are Inputs to `apply_graph_appearance` (formerly
`apply_light_dark_theme_to_graph`), which deserializes `cached-plot`, applies the
light or dark template, and only then calls
`plot_service.apply_point_appearance`. The expensive callback that writes
`cached-plot` keeps its inputs unchanged, so changing a size or a color cannot
reread scenario data, rebuild overlays, or fire a notification. That split is
asserted against the callback registry, not just documented. The raw-run trace is
selected **by name** (`RUN_DATA_POINT_TRACE_NAME`), never by index: placeholder
figures, empty-state figures, figures without a run trace, and any future
reordering fall back untouched, and *Average Score*, the overlays, the axes, and
the hover labels are never restyled. Both graph modes are covered by
construction, and preferences survive scenario switches.

Alternatives rejected: **improving the default for everyone** — a larger
universal marker or a size that adapts to point count — because no universal
default satisfies personal color preference, and adaptive sizing makes the same
data look different as its point count grows; rendered evidence may still improve
the Automatic size later, but a better default is not a substitute for
personalization. **Palette-only** (governable but weakens personalization) and
**picker-only** (flexible but makes everyone solve color selection from scratch
and hides the safe choices). **Five presets or a continuous slider**, which
elevate rendering precision into a product concept and make the default harder to
recognize and restore. **Ten swatches**, adding indigo-5 (`#5c7cfa`) and violet-5
(`#845ef7`): finer blue-to-purple choice at the cost of two more neighboring
options the picker already covers. **The 14-color DMC example list**, which is a
component demonstration rather than a palette curated for these backgrounds, and
several of whose values fail the contrast target.

Out of scope and staying there: opacity, marker symbols, borders and outlines,
Average Score line styling, rank/PB/threshold overlay styling, axes, grid lines,
fonts, plot backgrounds, hover-label styling, per-scenario or per-playlist
appearance profiles, import/export of appearance preferences, and any generic
Plotly-property editor.

Design in [#238](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/238),
implementation in [#241](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/241).
The panel this group joined is the
[2026-08-09 chart options entry](#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph).
The Automatic wording, the generated color, and the empty field's white
preview swatch were revised the next day; see the
[2026-08-21 entry](#2026-08-21-the-empty-point-color-is-called-default-and-the-points-follow-the-theme).

**Superseded in part, for copy (2026-09-14).** The chart's legend entries are
"Run data point" and "Average score", so `RUN_DATA_POINT_TRACE_NAME`, the
handle this entry selects the run trace by, now holds "Run data point". The
point preferences are unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

**Superseded in part (2026-10-05).** Point size now sizes the New PB stars on
the Score vs Time chart as well as the run points, so "Nothing else on the
chart became customizable" has one exception. The set of controls is
unchanged, Point color still restyles only the run trace, and the rest of this
entry stands. See [The Score vs Time Chart Marks Each New PB With A Star](#2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star).
