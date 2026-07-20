# Corporate Serf Dashboard

The name of this app is in honor of [Corporate Serf](https://www.youtube.com/watch?v=a-MShVYe3kY).

This app watches your KovaaK's stats directory and turns your runs into training insight. As you keep
playing and generating new scores, the home page's plots, stats, and notifications update
automatically in the background.

## Features

- **Scenario plots** — Sensitivity vs Score and score-over-time plots per scenario, with optional
  high-score, score-threshold, and benchmark-rank overlays.
- **Run notifications** — toasts as each run lands: top-N placements for the current scenario, and
  score-threshold pass/fail against your high score.
- **Leaderboard standing** — your global rank and percentile for the selected scenario, e.g.
  `Rank: 11,290 of 63,892 (82.33% Percentile)`, with a bounded background refresh after a new
  personal best and a manual Refresh button for when the leaderboard lags.
- **Playlist scenarios table** — every scenario in a playlist with rank, percentile, last played,
  runs, high score, and personal-best stats; sort by percentile to build a training priority list.

The rationale behind each feature lives in [docs/product.md](docs/product.md); what's next in
[docs/roadmap.md](docs/roadmap.md).

## Tech Stack

1. Python
2. Dash
    1. Plotly.js
    2. Dash Mantine Components
    3. React
    4. Flask

## Install

Windows only. You do not need Python, uv, or git — the installer brings its own
copy of everything.

### Easy install

Paste this into PowerShell:

```powershell
irm https://raw.githubusercontent.com/MingoDynasty/Corporate-Serf-Dashboard/main/get.ps1 | iex
```

Everything lands under `%LOCALAPPDATA%\CorporateSerfDashboard` — its own uv, its
own Python, its own package cache — so nothing else on your machine is used or
disturbed. Along the way the installer:

- finds your KovaaK's stats folder (from Steam's install path and library
  folders) and asks you to confirm it;
- writes a starter `config.toml` beside the install;
- creates a **Corporate Serf Dashboard** desktop shortcut.

Launch it from that shortcut, which opens the dashboard in your browser. A
console window stays open while the dashboard is running — **closing it stops
the dashboard**, which is how you shut it down. Double-clicking the shortcut
again while it is already running just opens another browser tab; it will not
start a second copy.

**Each launch checks for a new release and updates itself** before starting, so
you stay current without doing anything. If that check fails — offline, GitHub
unreachable — it simply runs the version you already have. A new version only
becomes the recorded install after it has actually started successfully; one
that fails to start is discarded and the previous version runs instead.

### Manual install

If you would rather not pipe a script from the internet, install from a release
you have inspected yourself:

1. Download the latest release zip from the
   [Releases page](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/releases/latest).
2. Extract it and read `install.ps1` — it is the same installer the one-liner
   runs.
3. Open PowerShell in the extracted folder and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

That explicit command is required: double-clicking a `.ps1` file deliberately
does not execute it on Windows. `-ExecutionPolicy Bypass` relaxes only the
per-process default for this one script — it does not, and cannot, override
enterprise Group Policy or AppLocker. Home machines are the audience here; on a
machine someone else administers, ask them first.

### Rollback

Every release is kept and immutable, so going back is a matter of naming a tag.
Pick one from the
[Releases page](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/releases),
then paste this into PowerShell, editing the first line:

```powershell
$tag = 'v2026.07.19.4'
$installer = "$env:TEMP\csd-install-$tag.ps1"
Invoke-WebRequest -UseBasicParsing -OutFile $installer `
  -Uri "https://raw.githubusercontent.com/MingoDynasty/Corporate-Serf-Dashboard/$tag/install.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer -Tag $tag
Remove-Item $installer
```

Each release ships its own installer, so this deliberately fetches the one
belonging to the release you are rolling back to.

`-Tag` also **pins** the install: it stays on that version and stops
auto-updating. Without the pin, the next launch would immediately reinstall the
release you just rolled back from, making the rollback a no-op. To resume
automatic updates, run the [easy install](#easy-install) one-liner again.

Releases published before the installer existed cannot be rolled back to;
`v2026.07.19.4` is the earliest that can.

Rolling back has a config floor too. Because `config.toml` is written once at
first install and never rewritten, an install first set up by a release that
omits `polling_interval` and `sens_round_decimal_places` (they now default in
code) cannot roll back to an older release that still requires them — the
install stops with a "cannot load config.toml" error. Add those two keys from
`example.toml`, or delete `config.toml` so the older installer regenerates its
own, then re-run.

### Uninstall

Delete the `%LOCALAPPDATA%\CorporateSerfDashboard` folder and the desktop
shortcut. Nothing else on the machine was modified — no registry keys, no
machine-wide Python or uv, nothing on `PATH`.

One loose end: the easy install downloads the installer to
`%TEMP%\csd-install-<tag>.ps1` and leaves it there. It is inert once the
install finishes — nothing reads it again — and Windows clears `%TEMP%`
eventually, but you can delete it yourself:

```powershell
Remove-Item "$env:TEMP\csd-install-*.ps1"
```

## Configuration

Settings live in `config.toml`:

- **Installed:** `%LOCALAPPDATA%\CorporateSerfDashboard\config.toml`, written on
  first install. Updates never touch it.
- **From source:** copy `example.toml` to `config.toml` in your checkout.

The installer fills in `stats_dir` for you. `example.toml` documents every
setting; two are worth knowing about:

- `kovaaks_username` — set this to enable the leaderboard rank and percentile
  features (and optionally `steam_id`, which makes player matching exact when
  usernames are ambiguous). Leave it empty to run fully offline.
- `port` — change this if something else on your machine already uses 8050. The
  dashboard says so at startup rather than failing mysteriously.

## Usage

Launch from the desktop shortcut, or run it yourself from a source checkout
(below), then open <http://localhost:8050/> — or your configured port.

Use one active Home tab at a time. Additional Home tabs are crash-safe, but they
share one in-memory run-event queue and are not synchronized with each other.

## Run From Source

For development, or if you would rather manage the toolchain yourself. Requires
git and [uv](https://docs.astral.sh/uv/):

```shell
git clone https://github.com/MingoDynasty/Corporate-Serf-Dashboard.git
cd Corporate-Serf-Dashboard
uv sync
uv run python source/app.py
```

Copy `example.toml` to `config.toml` and set `stats_dir` before the first run
(see [Configuration](#configuration)). A source checkout does not auto-update;
`git pull` is the update path.

## Example

![Corporate Serf Dashboard example](docs/example.png "Corporate Serf Dashboard example")

## Rank Data

In essence, "benchmarks" are basically just "playlists" but with rank data attached. With the help of
the <http://Evxl.app>'s author, I combined his benchmarks data with playlist data from KovaaK's API, for most of the
common benchmarks. These files are in `resources/benchmarks` and the app loads all of them at startup. The most
popular ones (Voltaic, Viscose) are visible by default; to enable any other benchmark, toggle "Show hidden" on the
Playlists page and unhide it — no file copying needed.

Playlist JSON must include a non-blank `code` field. The app uses that code as the playlist identity for routes,
selectors, imports, and filenames; playlist names are only display labels.

## Import Playlist

In the `Settings` modal, there is an option to import a playlist via share code. The app queries the
KovaaK's API with your input share code to retrieve the playlist data.

Note that by importing playlists this way, the playlist will not include rank data. If you want to include rank data for
the rank overlays, then see the **Rank Data** section. Imported playlists are saved under `data/playlists`.
