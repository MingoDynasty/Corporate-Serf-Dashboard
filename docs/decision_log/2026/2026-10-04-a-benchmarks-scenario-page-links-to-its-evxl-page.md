# 2026-10-04: A Benchmark's Scenario Page Links To Its Evxl Page

Status: Accepted

A benchmark's scenario page now carries a View on Evxl link that opens the
same benchmark on Evxl in a new browser tab. Evxl shows what this app doesn't,
such as the overall rank a benchmark awards, and getting there used to mean
finding the benchmark on Evxl by hand. With a Steam ID set the link opens the
player's own sheet, and without one it opens the page where Evxl asks for a
profile. The app builds the address and requests nothing from Evxl itself.

**Agreed before the PR.** In chat on 2026-10-04 the maintainer agreed to the
placement, the header of the per-playlist scenario page, and asked for the
build. The rest of this entry is the author's, open to review: where the names
come from, the page a missing Steam ID falls back to, and the label "View on
Evxl".

**Addresses.** `https://evxl.app/u/{Steam ID}/{benchmark}/{difficulty}` with a
Steam ID, and `https://evxl.app/benchmarks/{benchmark}` without one. Both
names are Evxl's own, matched exactly and case-sensitively, and each is
percent-encoded as one path segment, so a `/` inside a name travels as `%2F`.
Neither address carries a query: Evxl appends `?tab=` from the visitor's
remembered tab, and a link that set one would override that choice. The
measurements are in
[kovaaks_api_notes.md](../../kovaaks_api_notes.md#evxl-benchmark-pages-linked-never-fetched).

**Where the names come from.** A bundled file carries the KovaaK's playlist
name, which is not Evxl's: "Viscose Benchmark S2 - Medium" is "Viscose
Benchmarks S2" and "Medium" there. `source/kovaaks/evxl_links.py` reads both
names from `resources/evxl/benchmarks.json`, the snapshot the importer
generates the bundled library from, once per process, keyed by playlist code.
The file already ships in the release zip, and the release's archive contract
names it, so a release that would ship without it fails its draft instead of
silently losing every link. Rejected: having the importer write
the names into each bundled file. That is the tidier data model, but it bumps
the generated schema and regenerates all 261 files against live KovaaK's
data, and the diff would carry whatever thresholds KovaaK's had changed since
the last refresh. The cost accepted
instead is that the running app now reads a file only the importer read
before. A snapshot that is missing or in another shape logs one warning and
removes the link, and nothing else. The importer refreshes the snapshot before
it generates, so the names move at the corpus's own cadence, and a benchmark
Evxl renames is a 404 until the next refresh.

**Matching a code.** Codes compare case-folded, because the snapshot has
carried a code in different letter case from the bundled file's. A code the
snapshot lists twice keeps its first listing, the one the importer generates
the file from.

**Which pages get it.** A benchmark's page, by the test that adds the Rank and
Next Rank columns, when the snapshot lists its code. A playlist's page never
gets it, whatever Evxl lists: the link goes with the rank columns.

**No Steam ID.** The profile-less page is the fallback rather than no link, so
the link doesn't silently vanish for a user who skipped the account setup, and
that address holds nothing personal. Evxl's profile-less page answers 404 for
a benchmark name holding `+`, `/`, `&`, or `:`, so those benchmarks show no
link until a Steam ID is set, which was 25 of the 261 bundled files on the day
it was measured. The code excludes the wider set JavaScript's `decodeURI`
leaves encoded, the likely cause, so that the unmeasured characters fail
toward no link instead of a broken one.

**A plain anchor.** The link is `html.A` with its own stylesheet class, not
`dmc.Anchor`. dash-mantine-components 2.8.0 bundles `@braintree/sanitize-url`,
which runs `decodeURIComponent` over an href and rebuilds it through `URL`, so
`%2F` reached the DOM as `/` and split "NRS 360 / Macro Benchmarks" into two
segments. Dash 4.4.1's `html.A` passes an href through
`dash_clientside.clean_url`, which returns it unchanged unless its scheme is
dangerous.

**Disclosure.** The user guide's What it talks to section names the link
beside the app's other browser-opened links and says its address holds the
Steam ID. It is not a row in that section's table, which lists what the app
itself reaches.

**Rejected.** A link in each row of the Playlists overview: the link is about
one benchmark, and the overview would carry the control on every row of a
library most of which a user doesn't play. The profile-less page for everyone:
it keeps the Steam ID out of the address, but drops the difficulty and costs a
click on every visit.

**Amended 2026-10-05: the link is Evxl's logo.** The link now shows Evxl's
logo and no text. "View on Evxl" stays, as the link's tooltip and its
accessible name. The addresses, the pages that get the link, and the new tab
are as this entry describes them.

- **Agreed in chat, not ruled.** On 2026-10-05 the maintainer chose the logo
  alone with a tooltip, after the app header's GitHub and Discord links. The
  author had recommended the logo in front of the text, because a logo alone
  means nothing to someone who doesn't know Evxl. The maintainer's answer was
  that Evxl is well known among aim trainers. The size, the placement, the
  tooltip on keyboard focus, and the wording of the permission record are the
  author's.
- **Permission.** Evxl's owner told the maintainer in a direct message that
  the app may use the logo, with no conditions. The logo stays its owner's
  and is under no open license, and `assets/icons/README.md` holds the
  record. The file is the site's 721×679 icon scaled down to 102×96 and
  otherwise untouched.
- **Bundled, never loaded from Evxl.** The logo is served from
  `assets/icons/` through `local_icon`. Loading it from evxl.app would make
  every benchmark page contact Evxl, and would break this entry's statement
  that the app requests nothing from Evxl.
- **Its name.** The logo is hidden from assistive technology, so an
  `aria-label` names the link. The tooltip opens on keyboard focus as well as
  on hover, which the header's two icon links don't do: it is the only place
  a sighted keyboard user can read where the link goes.
- **Focus ring.** The plain anchor had the browser's own ring, which in Edge
  is `rgb(16, 16, 16)`: 1.23:1 against the dark theme's page. The link now
  carries Mantine's `mantine-focus-auto` class, the ring `dmc.Anchor` brings.
  Measured in headless Edge on 2026-10-05 it is 3.56:1 on the light theme and
  3.09:1 on the dark one, against a floor of 3:1. Firefox was not measured.
- **Known cost.** The logo is cyan and can't be recolored without its owner's
  say. Rendered at its 24-pixel height it measures 2.0:1 against the light
  theme's page and 6.82:1 against the dark one's.
