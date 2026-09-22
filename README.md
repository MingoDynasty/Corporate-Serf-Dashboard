# Corporate Serf Dashboard

Your KovaaK's runs, plotted as you play, on your own PC.

[Install](#install) · [Features](#features) · [User guide](docs/user_guide.md) · [Troubleshooting](#troubleshooting)

Corporate Serf Dashboard watches your KovaaK's stats folder while you train. Each run you
finish lands on the Scenario Performance page as it happens: the plots and stats update, a
notification says how the run went, and your leaderboard position refreshes when you set a
new personal best. It runs on your own PC and opens in your browser.

It turns the runs you already play into answers to three questions: am I improving, where am
I weak, and what should I work on next?

The name of this app is in honor of [Corporate Serf](https://www.youtube.com/watch?v=a-MShVYe3kY).

![Corporate Serf Dashboard example](docs/example.png "Corporate Serf Dashboard example")

## Features

- **Scenario plots** — Score vs Sensitivity and Score vs Time per scenario, with PB, score-threshold,
  and benchmark-rank overlays.
- **Run notifications** — a toast when a run earns a verdict against your personal best or the top N.
- **Personal best celebration** — confetti, fireworks, cannons, or stars when a run beats your
  scenario best.
- **Leaderboard standing** — your global position and percentile per scenario, refreshed after a new
  personal best.
- **Playlist scenarios table** — every scenario in a playlist with position, percentile, and
  personal-best stats; sort by percentile to pick what to train.
- **Benchmarks** — a bundled benchmark library, Voltaic and Viscose on by default, plus import of any
  playlist by share code; see [Playlists and Benchmarks](docs/user_guide.md#playlists-and-benchmarks).

The rationale behind each feature lives in [docs/product.md](docs/product.md); what's next in
[docs/roadmap.md](docs/roadmap.md).

## Install

Windows only. You do not need Python, uv, or git — the installer brings its own copy of
everything.

1. Paste this into PowerShell:

   ```powershell
   irm https://raw.githubusercontent.com/MingoDynasty/Corporate-Serf-Dashboard/main/get.ps1 | iex
   ```

2. Double-click the **Corporate Serf Dashboard** shortcut the installer put on your desktop. A
   console window opens, the dashboard starts, and your browser opens it at
   <http://localhost:8050/>. **Closing that console window stops the dashboard** — that is how
   you shut it down. Double-clicking the shortcut while it is already running opens another
   browser tab; it will not start a second copy.

3. Look at the Scenario Performance page. On its first start the dashboard finds your KovaaK's
   stats folder itself, through Steam. If it could not, a card on that page says so and points
   at the Settings page. Once the folder is known, the card instead offers the one thing the
   first start cannot work out for itself: your KovaaK's account, which turns leaderboard
   positions and percentiles on. Skip it and those features stay off; the dashboard does not
   ask again.

The installer asks you nothing. Everything lands under
`%LOCALAPPDATA%\CorporateSerfDashboard` — its own uv, its own Python, its own package cache, a
starter `config.toml`, and each version of the app it has installed — so nothing else on your
machine is used or disturbed: no registry keys, no machine-wide Python or uv, nothing on `PATH`.

**Immutable GitHub releases · SHA-256 digests for the app zip and `release.json`.** Every
release is cut by CI from a commit that passed the test suite, and it is never changed after it
is published. GitHub lists the SHA-256 digest of each file it uploaded on the release page;
`Get-FileHash <file>` in PowerShell prints the same digest for your copy. If you would rather
not pipe a script from the internet, see [Manual install](docs/user_guide.md#manual-install).

### Updates

**Each launch checks for a new release and updates itself** before starting, so you stay current
without doing anything. If that check fails — offline, GitHub unreachable — it simply runs the
version you already have. A new version only becomes the recorded install after it has actually
started successfully; one that fails to start is discarded and the previous version runs instead.
Updates never touch your `config.toml` or your `data` folder.

### Other ways to install

[Manual install](docs/user_guide.md#manual-install) installs from a release you have inspected
yourself, and covers rolling back to, and pinning, an older release.
[Run From Source](#run-from-source) is for development, or for managing the toolchain
yourself.

### Uninstall

Delete the `%LOCALAPPDATA%\CorporateSerfDashboard` folder and the desktop
shortcut. Nothing else on the machine was modified — no registry keys, no
machine-wide Python or uv, nothing on `PATH`.

<details>
<summary>One loose end: the installer script left in <code>%TEMP%</code></summary>

The easy install downloads the installer to `%TEMP%\csd-install-<tag>.ps1` and
leaves it there. It is inert once the install finishes — nothing reads it again
— and Windows clears `%TEMP%` eventually, but you can delete it yourself:

```powershell
Remove-Item "$env:TEMP\csd-install-*.ps1"
```

</details>

## What it talks to

The dashboard does not collect or send usage or crash analytics. Your runs, settings, and
caches stay on your PC unless you share a chart yourself. Three things reach the network:
installing and updating it, leaderboard lookups once a KovaaK's username is set, and the
actions you click (detecting your accounts, importing a playlist, sharing a chart).
[What it talks to](docs/user_guide.md#what-it-talks-to) in the user guide lists every service
and what makes the app reach it.

## Troubleshooting

[Troubleshooting](docs/user_guide.md#troubleshooting) in the user guide lists problems by what
you see, such as a port already in use, a stats folder that was not found, a missing
leaderboard position, or a slow first start. An installed copy keeps its logs in
`%LOCALAPPDATA%\CorporateSerfDashboard\data\logs`; a source checkout keeps them in its own
`data\logs`.

## Found a bug?

Open an issue from the
[issue chooser](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/issues/new/choose)
— there is a form for bug reports and one for feature requests. The bug form
asks for your app version and your `debug.log`, which is what makes a failure
on a machine no one else can see diagnosable; it also spells out what the log
contains before you attach it.

Easiest route: the **Settings** page has a "Report a bug" link that opens the
form with your version already filled in, and shows the folder your logs are
in.

## Configuration

Most settings live on the dashboard's own **Settings** page: where your KovaaK's stats live,
and who you are on the leaderboards. Boot settings such as `port` live in `config.toml`
(installed: `%LOCALAPPDATA%\CorporateSerfDashboard\config.toml`), which updates never touch.
[Configuration](docs/user_guide.md#configuration) in the user guide covers both.

## Run From Source

Run from a git checkout if you develop the app, or if you would rather manage the toolchain
yourself. You need git and [uv](https://docs.astral.sh/uv/):

```shell
git clone https://github.com/MingoDynasty/Corporate-Serf-Dashboard.git
cd Corporate-Serf-Dashboard
uv sync
```

Copy `example.toml` to `config.toml`, then start the app:

```shell
uv run python source/app.py
```

The stats folder is detected on the first start, and the Settings page covers whatever it
missed. A checkout does not update itself: `git pull` is the update path.

## Development

The app is Python + [Dash](https://dash.plotly.com/) (Plotly, Dash Mantine Components);
[docs/architecture.md](docs/architecture.md) has the module map.

Development uses AI coding agents. Every change is reviewed and must pass the
project's test suite and CI gates (ruff, mypy, pytest) before it merges; the
reasoning behind the durable choices is public in the
[decision log](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/blob/main/docs/decision_log.md).

## License

Copyright (C) 2025-2026 MingoDynasty

Corporate Serf Dashboard is free software under the
[GNU Affero General Public License](LICENSE), version 3 or (at your option)
any later version. Derivatives stay free and open source on the same terms.
