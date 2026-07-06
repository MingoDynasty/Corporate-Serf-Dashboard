# Proposal: sticky column headers on the playlist scenarios grid

Status: Proposed (not yet implemented)

## Context

TODO Playlist Page item 7: on playlists with many scenarios, scrolling down
loses the column headers. The diagnosis is confirmed in code — the grid in
[playlist_scenarios.py](../source/pages/playlist_scenarios.py) sets
`"domLayout": "autoHeight"` in `dashGridOptions`, which makes AG Grid grow to
fit every row. The grid therefore never has its own vertical scrollbar; the
*page* scrolls, and the header (sticky only within the grid viewport) scrolls
away with it. Fix: give the grid a bounded height so it owns the vertical
scroll. Effort S, single file.

## Changes (single file: `source/pages/playlist_scenarios.py`)

1. **Remove `"domLayout": "autoHeight"`** from `dashGridOptions`. The default
   `normal` layout scrolls rows inside the grid viewport with the header
   pinned. Row virtualization also kicks back in — a side benefit on
   100+-scenario playlists.

2. **Size the page to the content viewport so the grid fills the remaining
   space** (no magic pixel offsets):
   - On the page's root `dmc.Stack`, set
     `style={"height": "calc(100dvh - var(--app-shell-header-offset, 0rem) - 2*var(--app-shell-padding, 1rem))"}`.
     Mantine's `AppShell` ([app_shell.py](../source/app_shell.py)) defines
     exactly these CSS variables, and `AppShellMain`'s padding is built from
     them, so this tracks the real chrome height (header `4em` + `md` padding)
     without hardcoding.
   - On the `dcc.Loading` wrapper, set
     `parent_style={"flex": 1, "minHeight": 0, "display": "flex", "flexDirection": "column"}`
     so the grid slot absorbs the leftover Stack height (Dash 4.3's
     `dcc.Loading` supports `parent_style`).
   - On the `dag.AgGrid`, change `style` to
     `{"height": "100%", "width": "100%", "minHeight": 300}` (the `minHeight`
     keeps the grid usable on very short windows; the page then scrolls, which
     is acceptable).

   Fallback if the `dcc.Loading` wrapper fights the flex sizing (spinner
   overlay or an extra inner div): put the `calc(...)` height directly on the
   AgGrid `style` and skip the Stack/Loading styling. Decide during
   verification.

No CSS file changes expected; the existing `.playlist-scenarios-grid` theming
in `assets/stylesheet.css` is orthogonal. No test updates: nothing in `tests/`
references the grid layout.

## Accepted trade-offs

- **Short playlists**: the grid frame now fills the viewport, so a 5-scenario
  playlist shows empty grid body below the last row. Standard grid look;
  conditional autoHeight for small playlists was rejected as needless
  complexity.
- **`columnSize="autoSize"`** will now measure only rendered (virtualized)
  rows instead of all rows; `minWidth` on every column guards against
  truncation. Verify visually.

## Verification (no commits)

1. **Reproduce first**: create a gitignored `config.toml` in the worktree
   (copy from the main checkout if present, else adapt `example.toml`; avoid
   port 8080 — Steam). Run the app and open a large bundled playlist, e.g.
   "TSK Ultimate Benchmarks - All Scenarios" (`resources/playlists/` ships
   with the repo, so playlists load without any Kovaak's data). Confirm the
   page scrolls and `.ag-header` leaves the viewport.
2. **Apply the fix**, reload, and verify: the page body no longer scrolls,
   scrolling inside the grid keeps `.ag-header` on screen, and the Scenario
   column isn't truncated after scrolling deep.
3. **Spot-check**: a small playlist, the no-playlist status message, dark
   mode, and a narrow window (horizontal scroll stays inside the grid).
4. **Gates**: `uv run ruff format --check .`, `uv run ruff check`,
   `uv run mypy source`, `uv run python -m compileall source`,
   `uv run pytest`.
5. Leave everything uncommitted; report the diff summary.

## Shipping

When this ships, distill into a `decision_log.md` entry (if the sizing
approach is worth recording) and delete this file in the shipping PR, per
AGENTS.md "Shipping a proposal".
