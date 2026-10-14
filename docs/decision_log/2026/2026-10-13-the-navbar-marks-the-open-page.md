# 2026-10-13: The Navbar Marks The Open Page, And Tells A Screen Reader Which

Status: Accepted

The navbar now marks the link of the page that is open, with a tinted
background and a blue label. A link is also marked on every page under its
address, so Playlists stays marked on a playlist's scenario table. A screen
reader is told the same thing, because the one attribute that names the
current page is also what draws the mark.

**Rulings.** By the maintainer, 2026-10-13, recorded on
[PR #377](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/377):
"I ratify all 4 decisions." The four are N1 to N4 below, as they were put.
The rules as the app applies them are in
[run_history.md](../../specs/run_history.md),
[home.md](../../specs/home.md), and
[playlists.md](../../specs/playlists.md). This entry holds the reasons, what
was measured, and what was set aside.

**Supersedes in part** the
[2026-10-12 address entry](2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md):
its note that the navbar marks no page, and that marking one was left to a
later change. This is that change.

**N1, the navbar marks the open page.** Before this, the navbar's links
looked the same whichever page was open. Nothing said where the user was but
the page's own content and the browser tab's title, and Run History has no
heading of its own.

**N2, a link is marked when the address is its own or lies under it.**

- **One rule covers every link.** Playlists is marked at `/playlists` and at
  `/playlists/{code}`, a playlist's scenario table, which is reached from
  the Playlists page and belongs to it.
- **Query parameters play no part.** Run History is marked whatever
  scenario the address names.
- **Home needs no exception.** Its address is `/`. "Under it" means the
  link's address followed by `/` and more, and no page's address starts
  with `//`, so Home is marked only on Home.
- **A trailing slash names the same page,** as it does for the router, so
  `/settings/` marks Settings.
- **A page with no navbar entry marks nothing.** The Aim Training Journey
  page (`/aim-training-journey`) is the one such page, and nothing marked is
  the right answer for it.
- **Set aside: marking a link only at its exact address.** A playlist's
  scenario table, and any nested address added later, would then show a
  navbar with nothing marked, which is how every page looked before.

**N3, the mark is Mantine's default look for an active link, unchanged.**
The link gets a tinted background and its label turns blue. No `variant` is
set.

- **Set aside: the filled look.** The navbar's icons are outlined boxes in
  the theme's blue. On a filled blue row the icon is drawn in the color of
  its background and disappears in the light theme.
- **Set aside: the subtle look.** It changes only the label's color, and
  blue text is how the app draws a link that can be clicked.
- **The marked label's contrast is low in the light theme, and that is
  accepted.** Measured from the rendered colors:

  | Theme | Label | Background | Contrast |
  | --- | --- | --- | --- |
  | Light, not marked | `rgb(0, 0, 0)` | `rgb(255, 255, 255)` | 21.00:1 |
  | Light, marked | `rgb(34, 139, 230)` | `rgb(232, 243, 252)` | 3.17:1 |
  | Dark, not marked | `rgb(201, 201, 201)` | `rgb(36, 36, 36)` | 9.37:1 |
  | Dark, marked | `rgb(116, 192, 252)` | `rgb(35, 51, 64)` | 6.58:1 |

  WCAG AA asks 4.5:1 of text this size. The app's ordinary links are the
  same blue on white, at 3.56:1, and the tint carries the mark, not the
  label's color. If the label ever has to pass, Mantine's `--nl-color`
  variable on the marked link sets it to the body text color, about 18.7:1,
  and the label then stops matching the icon's blue. Not applied.

**N4, the marked link carries `aria-current="page"`, and that attribute
draws the mark.**

- **A fixed prop cannot do it.** The shell is one component tree, built
  once when the app starts and shared by every page. A prop set on a link
  in that tree is the same on every page.
- **The component can match the address itself, but tells nobody.**
  `dmc.NavLink` in dash-mantine-components 2.8.0 takes `active="exact"` or
  `active="partial"` and compares the address with its link. It keeps the
  result in its own state. It never renders `aria-current`, and it writes
  nothing back that a callback could read.
- **One clientside callback writes the attribute.** It reads the address
  and writes `aria-current="page"` on the link that N2 names, and nothing
  on the others.
- **Mantine draws a link that carries the attribute as an active one.** Its
  NavLink documentation says so for a router's links, and the bundled
  stylesheet has one rule for both:
  `:where([data-active], [aria-current='page'])`. A test pins that rule, so
  an upgrade that drops it fails there and not on screen.
- **The component's `active` is left unset on purpose.** With it set, two
  matchers run: the component's draws the mark and the callback's writes
  the attribute. The attribute could then stop being written while the mark
  stayed, and nobody looking at the screen would see it. Drawn from the
  attribute, a callback that stops working removes the mark from every page
  at once.
- **The callback holds no address.** It reads each link's own `href`. A
  second copy of an address could go stale when a link moved, and
  `tests/test_run_history_page.py` counts the copies of Run History's.
- **It follows a location of the shell's own,** a `dcc.Location` that
  nothing writes to. Dash Pages has one already, under a private id that an
  upgrade is free to rename.
- **Set aside: a server-side callback.** Its matching would be Python that
  a test can run. It costs a request, and a beat of lag, on every
  navigation. The matching runs in the browser instead, where no test here
  runs; the tests pin what it hangs on and the checks below cover what it
  does.

**Measured, 2026-10-13,** in headless Edge 155 and headless Firefox 157, in
the light and the dark theme, on this change's build:

- Each of Home, Run History, Playlists, and Settings marked its own link
  and no other.
- A playlist's scenario table marked Playlists, and `/aim-training-journey`
  marked nothing.
- `/home` and `/index` landed on `/` and marked Home.
- A scenario address with parameters marked Run History, typed in and
  reached through a scenario link in a playlist's table.
- `/settings/` and `/playlists/{code}/` marked as their pages do.
- A click on each navbar link, then Back, Back, and Forward, moved the mark
  with no reload.
- The mark landed 7 to 17 ms after the navbar's links on a fresh load.
- In Edge, the first page load after a server start marked Home. The
  [first-request race](2026-07-18-accept-dashs-first-request-pages-race-instead-of-warming-the-app.md)
  did not fire on that load. That entry measured that the race drops only
  Dash's own title setter, never one of the app's callbacks.

**Not run:** NVDA, or any screen reader. That a screen reader announces
`aria-current="page"` on a link as the current page is from the ARIA
specification, not observed here.
