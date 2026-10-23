# 2026-10-22: Text Links Use Readable Colors And Persistent Underlines

Status: Accepted

Text links use a darker blue in light mode so they remain readable on the page and on tinted notices. Ordinary text links stay underlined so their action can be recognized without color. The same text-link colors apply to the playlist grids and the run toast, while link-styled buttons keep their existing hover-only underlines.

## Contract

- The shared anchor color is Mantine blue 9 in light mode and the existing blue 4 in dark mode. Filled controls keep their existing colors.
- Ordinary Mantine anchors default to an always-visible underline. The app wordmark and the setup card's button-shaped action retain their explicit exceptions. Icon-only links have no text to underline.
- Link-styled buttons that change the current view or open the scenario-note editor receive the shared color but keep their existing hover-only underline. Their underline treatment is outside this navigation-link change.
- The run toast's plain Dash link is underlined at rest. Playlist and scenario grid names use the shared anchor color, including on hover and after visiting; their existing underlines stay in place.
- Link text clears 4.5:1 against the default page and the blue and yellow notice backgrounds in both themes. This is separate from the visual cue that identifies a link.

## Evidence

The stats-folder hint inherited Mantine's default light anchor blue, which measured 3.34:1 on its yellow tint and 3.56:1 on white. The shortfall predated the caution-panel treatment in PR #298. Blue 8 still gives only 4.48:1 on the blue notice tint; blue 9 clears all three backgrounds.

[WCAG's text contrast criterion](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) sets 4.5:1 for ordinary text. [Its inline-link guidance](https://www.w3.org/WAI/WCAG22/Techniques/general/G183) distinguishes recognizing a link from reading its text. An underline supplies the former and does not replace the contrast requirement.

Regression tests calculate contrast from the installed Mantine palette and the shared CSS override. Browser checks cover the actual hint, notice tints, grid links, hover, keyboard focus, and explicit underline exceptions.
