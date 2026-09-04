# Vendored browser libraries

Third-party JavaScript the dashboard serves from `assets/`, copied into the
tree rather than fetched from a CDN so the local app works offline and every
byte it runs is reviewable in the diff. Files here are **not edited**: the only
change made to an upstream file is a provenance header comment.

| File | Package | Version | License | Source |
| --- | --- | --- | --- | --- |
| `canvas-confetti.js` | [canvas-confetti](https://github.com/catdad/canvas-confetti) | 1.9.4 | [ISC](canvas-confetti.LICENSE) | `dist/confetti.browser.js` from the npm package |

`canvas-confetti` renders the personal best celebration; the app-owned recipes
and guards that drive it are in `assets/pbCelebration.js`.

To update one of these, replace the file with the same build from the new
version, keep the header comment, refresh the version in the table above, and
copy the upstream `LICENSE` beside it if it changed. Pin an exact version — a
range would make the vendored bytes ambiguous.
