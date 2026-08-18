# Scenario Performance Data Point Customization

Status: Proposed
Date: 2026-08-13

## TL;DR

Scenario Performance's raw run points can be difficult to read when a chart is
unusually dense or when someone needs stronger visual prominence. This proposal
adds browser-persisted point-size and point-color controls to Chart options while
leaving every other chart element opinionated and consistent. The current
recommendation uses three size presets and an Automatic-first color input with
curated swatches and a custom picker.

## Decisions needed

### D1 — Which point customization belongs in the first version?

Status: Ratified (2026-08-17)

**Decision: size and color only.** They answer the two direct user goals:
make points easier to see and choose a personally readable color. Opacity,
symbol, borders, hover styling, and styling for other chart elements remain out
of scope.

Adding more properties now would turn a focused visibility feature into the
start of a general Plotly editor. Choosing a narrower palette-only feature would
reduce complexity further, but would leave point visibility unaddressed.

### D2 — How much size choice should the control expose?

Status: Ratified (2026-08-17)

**Decision: three named presets: Small, Default, and Large.** Three stops
express the meaningful trade-off between density and visibility without implying
that a precise pixel diameter is analytically important. Default preserves the
current Plotly appearance instead of hard-coding its present effective size.

Five presets would offer finer adjustment at the cost of a wider or more crowded
control whose neighboring values may be hard to distinguish. A continuous
slider would provide maximum control, but would elevate rendering precision into
a product concept and make the default harder to recognize and restore.

### D3 — How should point color be selected?

Status: Open

**Current recommendation: Automatic plus eight curated, dual-theme swatches and
an integrated custom picker.** Automatic preserves the chart's existing
generated appearance. Swatches make common, graph-readable choices fast, while
the picker and hex input avoid arbitrarily preventing a color a person finds
easier to see.

A palette-only control would guarantee a smaller and more governable choice set,
but would weaken the personalization goal. A picker-only control would be
flexible but make every user solve color selection from scratch and make the
safe choices harder to find.

Within D3, the newly surfaced palette choice is the curated count. Eight keeps
one compact set of distinct color families; ten adds indigo and violet for finer
blue-to-purple choice at the cost of two more neighboring options. The 14-color
DMC example is not recommended because it is a component demonstration rather
than a palette curated for these chart backgrounds, and several values fail the
proposal's contrast target. The current preference for eight is deliberately
open to the maintainer's ruling.

### D4 — Where should this work sit on the roadmap?

Status: Ratified (2026-08-15)

**Decision: Upcoming as a small pre-launch item that does not displace Run
history and sessions.** The feature is small enough to ship before public launch
and has a bounded single implementation PR. Keeping Run history first and
explicitly naming this as parallel work preserves the roadmap's current
depth-first priority.

Future was rejected because it would understate the feature's readiness and the
maintainer's intent to ship it before launch. Giving it equal prominence with or
placing it ahead of Run history was rejected because this is parallel polish,
not a replacement for the next declared milestone.

D1, D2, and D4 record maintainer rulings. D3 remains open, including the curated
color count; proposal review is still expected to challenge its interaction,
palette, or any other open choice where a better product direction is available.

## Problem

The Scenario Performance graph combines a raw-run scatter trace with an average
line. Plotly currently chooses the raw points' size and color, and the page gives
the user no way to change either. Small points can be difficult to pick out,
while larger points can overwhelm a dense history; the default blue may also be
less readable or less comfortable for a particular person.

The existing Chart options inspector is the right interaction surface. Its
controls are contextual, update the live graph, and persist in the browser. The
durable Settings page has a deliberate Save model and owns app configuration,
not presentation preferences.

The larger product risk is uncontrolled option growth. Plotly exposes many
styling properties, but exposing them one by one would increase decision load,
testing surface, accessibility risk, and panel height without necessarily
helping someone understand performance. This feature therefore needs both useful
controls and an explicit boundary.

## Design

### Product rule

Expose recognizable user goals, not rendering-library properties. A new chart
customization should earn a control by solving a demonstrated reading or
analysis problem; the mere existence of a Plotly property is not sufficient.

The interface keeps three levels:

1. A strong Automatic or Default appearance for most users.
2. A small set of high-value controls for the graph's primary data marks.
3. Additional or advanced controls only after a real workflow demonstrates the
   need.

### Alternative considered: improve the default for everyone

A slightly larger universal marker or a size that adapts to point count could
reduce density and visibility problems without adding controls. The current
recommendation does not use that as the whole solution because no universal
default satisfies personal color preference, while adaptive sizing makes the
same data look different as its point count changes and adds behavior that is
harder to predict and test. Rendered evidence may still improve the Automatic
size during implementation, but a better default does not replace the proposed
personalization.

### Inspector organization

Add one **Run Data Points** group to the existing Chart options inspector. It
contains Point size followed by Point color. It does not add another disclosure
layer or change the inspector width.

The group appears after Overlays and before Score Threshold. Overlays determine
which reference information is present, Run Data Points controls the primary
marks, and Score Threshold keeps its existing goal and notification controls
together.

### Point size

Use a full-width segmented control with Small, Default, and Large values. The
initial implementation should test approximately 4 px for Small and 10 px for
Large against representative dense and sparse scenarios. Those diameters are
mechanical starting points, not product decisions, and may move based on
rendered evidence.

Default is a semantic value, not a stored pixel count. It leaves marker size
unmodified so the graph's existing appearance is unchanged and future template
improvements can flow through without migrating a persisted value.

### Point color

Use the installed Dash Mantine Components `ColorInput` with a visible **Point
color** label. An empty value represents Automatic and the field displays that
word when no override is active. Opening it provides:

- the curated swatch set selected by D3;
- the component's integrated color picker; and
- a hexadecimal text input.

The current eight-swatch candidate uses per-family shades selected against both
real plot backgrounds rather than taking one shade index across every Mantine
family:

| Family | Hex | Contrast on light | Contrast on dark |
|---|---|---:|---:|
| blue-7 | `#1c7ed6` | 4.20:1 | 3.70:1 |
| cyan-8 | `#0c8599` | 4.35:1 | 3.57:1 |
| teal-8 | `#099268` | 3.95:1 | 3.93:1 |
| green-9 | `#2b8a3e` | 4.37:1 | 3.55:1 |
| orange-9 | `#d9480f` | 4.30:1 | 3.61:1 |
| red-7 | `#f03e3e` | 3.84:1 | 4.04:1 |
| grape-6 | `#be4bdb` | 4.02:1 | 3.86:1 |
| pink-6 | `#e64980` | 3.73:1 | 4.16:1 |

If D3 selects ten, add indigo-5 (`#5c7cfa`, 3.67:1 / 4.23:1) and
violet-5 (`#845ef7`, 4.26:1 / 3.64:1). With eight, set
`swatchesPerRow=8` explicitly rather than inheriting the component's default of
seven; validate the real popover before treating the single-row layout as final.

For the current themes, omit yellow because no Mantine yellow shade reaches 3:1
on both backgrounds. Omit lime because green already covers that family and only
the deepest lime shade passes, adding a weakly differentiated choice. Omit gray
because it collides with grid lines, and dark because it disappears against the
dark plot. These are v1 curation choices under the current themes, not permanent
bans; re-audit them if the chart backgrounds change.

A nearby **Use automatic** action clears an explicit value. The control uses
hex rather than alpha-enabled color formats, so opacity does not enter this
feature indirectly. The eyedropper is omitted in the first version.

Contrast is an eligibility screen, not a substitute for rendering small points
in representative charts. Treat the candidate values as implementation starting
points and validate them in both themes, targeting at least 3:1 graphical
contrast. An arbitrary custom color cannot carry that guarantee, so the graph
updates immediately and Automatic remains an obvious, keyboard-accessible
recovery path.

### Application and persistence

Both controls affect only the raw-run scatter trace named **Run Data Point**.
They do not restyle Average Score, rank thresholds, PB, the score-threshold
overlay, axes, grid lines, or hover labels.

The preferences apply to Score vs Sensitivity and Score vs Time, and remain the
same while switching scenarios. They use the same browser-local Dash persistence
model as the existing Chart options inputs; they are not written to
`data/settings.json` or `config.toml`.

Apply the appearance preferences after loading the cached base figure and its
light or dark template. Changing a picker value must not reread scenario data,
rebuild overlays, or trigger notification logic. Automatic leaves the generated
trace untouched. Unknown size values, empty or invalid colors, placeholder
figures, and figures without a run trace fall back safely without breaking the
graph.

### Accessibility and responsive behavior

The controls keep visible text labels and keyboard-operable reset behavior; the
color interaction never relies on unlabeled swatches as its only input. Point
shape, hover data, and trace names remain unchanged, so color is not introduced
as the only carrier of analytical meaning.

Validate the third inspector group in both supported layouts: the 20rem side
panel and the panel stacked above the graph below its container-query threshold.
The inspector's existing independent scroll is the overflow fallback on short
wide screens.

### Promotion rule for future options

Reconsider opacity if overlapping points are shown to obscure useful density or
selection. Reconsider marker symbols if the graph later represents multiple
semantic point categories. If a visual-object group would exceed roughly three
controls, revisit presets or a deliberately designed advanced mode instead of
continuing to append properties to the inspector.

## Delivery plan

Ship the feature in one implementation PR after D3 is ratified. That PR adds
both inspector controls and their browser persistence, applies appearance after
the cached figure is themed, covers both graph modes and fallback states, and
performs the proposal-shipping documentation cleanup. There is no hard technical
dependency on other in-flight work; roadmap ordering governs priority rather
than code sequencing.

## Out of scope

- point opacity, marker symbols, borders, and outlines;
- Average Score line width, color, dash style, or smoothing;
- rank, PB, and score-threshold overlay styling;
- axes, grid lines, fonts, plot backgrounds, and hover-label styling;
- per-scenario, per-axis, or per-playlist appearance profiles;
- import, export, or sharing of chart appearance preferences; and
- a generic advanced or Plotly-property editor.

## Testing

Automated coverage should prove:

- the existing graph output is unchanged under Default and Automatic;
- Small and Large set only the raw-run marker size in both graph modes;
- a valid custom color sets only the raw-run marker color in both graph modes;
- invalid or cleared values fall back to the unmodified base trace;
- changing appearance does not invoke scenario-data or notification work;
- both inputs are mounted in the Run Data Points group with their intended
  defaults and browser persistence;
- placeholder and no-data figures tolerate every persisted preference; and
- light and dark theme changes preserve explicit preferences while Automatic
  continues to use the base figure appearance.

Manual validation should compare representative dense and sparse scenarios in
both themes, exercise swatches, hex entry, the picker, and Use automatic by
mouse and keyboard, and inspect the side-by-side and stacked panel layouts.
