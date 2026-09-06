# Corporate Serf Dashboard

The name of this app is in honor of [Corporate Serf](https://www.youtube.com/watch?v=a-MShVYe3kY).

Corporate Serf Dashboard watches your KovaaK's stats folder while you train. Each run you
finish lands on the Scenario Performance page as it happens: the plots and stats update, a
notification says how the run went, and your leaderboard position refreshes when you set a
new personal best. It runs on your own PC and opens in your browser.

![Corporate Serf Dashboard example](docs/example.png "Corporate Serf Dashboard example")

## Features

- **Scenario plots** — Sensitivity vs Score and score-over-time plots per scenario, with optional
  PB-score, score-threshold, and benchmark-rank overlays. Chart options also set the run points'
  size and color, so a dense or a faint chart can be made readable; both preferences stay in your
  browser.
- **Run notifications** — one toast as each run lands, titled with its verdict: score-threshold
  pass/fail against your personal best, or the top-N placement it earned. Playing again replaces
  it rather than stacking a second one beside it, and a run that earns neither says nothing. One
  Chart options switch, Run Notifications, turns these off, leaving the chart to update silently.
- **Personal best celebration** — a run that beats your scenario best gets a short burst of
  confetti and its own toast, on whatever page you have open, and the toast stays until you
  dismiss it so the news survives a fullscreen session. If the window was covered when the run
  landed, the animation waits until you come back to it. A Settings control picks the animation,
  Confetti, Fireworks, Cannons, or Stars, or turns the whole thing off, with a Preview button
  beside it, and it is its own family, so Run Notifications does not silence it.
  A reduced-motion preference keeps the toast and drops the animation.
- **Leaderboard standing** — your global position and percentile for the selected scenario, e.g.
  `Position: 11,290 of 63,892 (82.33% Percentile)`, with a bounded background refresh after a new
  personal best and a manual Refresh button for when the leaderboard lags.
- **Playlist scenarios table** — every scenario in a playlist with position, percentile, last
  played, runs, and personal-best stats (PB Score, PB Date, PB cm/360, PB Accuracy); sort by
  percentile to build a training priority list.

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
not pipe a script from the internet, see [Manual install](#manual-install).

### Updates

**Each launch checks for a new release and updates itself** before starting, so you stay current
without doing anything. If that check fails — offline, GitHub unreachable — it simply runs the
version you already have. A new version only becomes the recorded install after it has actually
started successfully; one that fails to start is discarded and the previous version runs instead.
Updates never touch your `config.toml` or your `data` folder.

### Manual install

If you would rather not pipe a script from the internet, install from a release you have
inspected yourself:

1. Download the app zip (`Corporate-Serf-Dashboard-<tag>.zip`) from the
   [Releases page](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/releases/latest).
   Its SHA-256 digest is listed beside it; GitHub's own "Source code" downloads carry no digest.
2. Extract it and read `install.ps1` — it is the same installer the one-liner runs.
3. Open PowerShell in the extracted folder and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

That explicit command is required: double-clicking a `.ps1` file deliberately does not execute it
on Windows. `-ExecutionPolicy Bypass` relaxes only the per-process default for this one script —
it does not, and cannot, override enterprise Group Policy or AppLocker. Home machines are the
audience here; on a machine someone else administers, ask them first.

<details>
<summary><strong>Rollback</strong> — go back to (and pin) an older release</summary>

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
automatic updates, run the install one-liner again.

Releases published before the installer existed cannot be rolled back to;
`v2026.07.19.4` is the earliest that can.

Rolling back has a config floor too. Because `config.toml` is written once at
first install and never rewritten, an install first set up by a release that
omits `polling_interval` and `sens_round_decimal_places` (they now default in
code) cannot roll back to an older release that still requires them — the
install stops with a "cannot load config.toml" error. Add those two keys from
`example.toml`, or delete `config.toml` so the older installer regenerates its
own, then re-run.

</details>

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
caches stay on your PC. This is every network connection the app or its launcher makes:

| When | What | Where |
|---|---|---|
| You run the install one-liner | Fetches `get.ps1`, then the release's own `install.ps1` | `raw.githubusercontent.com` |
| Every launch from the shortcut, unless the install is pinned | Asks whether a newer release exists | `api.github.com` |
| Installing or updating | Downloads the release zip, and, when they are not already present, uv, a Python build, and the app's packages | `github.com`, `astral.sh`, `pypi.org`, `files.pythonhosted.org` |
| While running, only with a KovaaK's username set | Looks up your leaderboard position, percentile, and the player total; slowly fills the playlist percentile cache in the background (`percentile_warmup_enabled` in `config.toml` turns that off) | `kovaaks.com` |
| You click **Detect my accounts** or **Import** on a page | Checks the Steam accounts on this machine against KovaaK's; fetches a playlist by share code, asking Evxl when KovaaK's has no record of it | `kovaaks.com`, `api.evxl.app` |

With no KovaaK's username set, the running app makes no network requests on its own. Requests to
KovaaK's identify themselves with the app's name, its version, and this repository's address.
The GitHub, Discord, and **Report a bug** links in the app open in your browser; the app itself
does not contact those sites. Without a connection, the launcher starts the version you already
have, and a leaderboard position shows its cached value or says the lookup failed.

## Troubleshooting

Each entry starts with what you see. The logs are the last one.

**The console says the dashboard failed to start, and the app error output includes "port 8050
is already in use".** Another program holds the port — a second copy of the dashboard is the usual
one; Steam uses 8080. Close that program, or set a different `port` in `config.toml` (see
[Configuration](#configuration)) and launch again.

**The Scenario Performance page is empty, and a card says "No KovaaK's stats folder was found".**
Steam detection missed — KovaaK's installed somewhere unusual, or not yet. Open Settings: the
stats folder box suggests each Steam library it found, and the folder is normally
`<Steam library>\steamapps\common\FPSAimTrainer\FPSAimTrainer\stats`. Save, and restart the
dashboard when the page says so.

**Position shows "set your KovaaK's username in Settings" instead of a number.** Leaderboard
features are off until the dashboard knows who you are. On the Settings page, **Detect my
accounts** fills in the account it can prove is yours, or lists what it found for you to pick
from; then press Save. Leaving the username empty is a supported choice — the dashboard then
runs fully offline.

**The console keeps printing "Still starting Corporate Serf Dashboard ... N seconds elapsed."**
The first start reads every run file in your stats folder before the page can open, and a large
folder on a slow disk takes a while. The launcher waits up to 120 seconds. If it gives up
("failed to start (timeout)"), launch again; if that keeps happening, report it with the launcher
logs (below).

**A card says "Your settings can't be read", and the Settings page says `settings.json` has no
`"schema_version"` line.** Installs made before `v2026.08.11.5` wrote their settings without a
format stamp, and newer versions refuse to guess. Nothing was deleted or changed. Close the
dashboard, then either add the line `"schema_version": 1` to
`%LOCALAPPDATA%\CorporateSerfDashboard\data\settings.json` (and to `data\playlist_visibility.json`
and each file under `data\playlists\`), or run `scripts\stamp_schema_version.py` from the
installed version folder with its own `.venv\Scripts\python.exe` — the script's header carries
the exact commands. Then launch again.

**The browser did not open, or the console says a post-start step failed.** The dashboard is
running anyway. Open <http://localhost:8050/> yourself — the console's "Dashboard running at"
line names the exact address, including a configured port.

**Notifications sometimes do not appear.** Keep one Scenario Performance tab open at a time.
Extra tabs are crash-safe, but a new run's notification goes to whichever tab asks first.

**Where the logs are.** `%LOCALAPPDATA%\CorporateSerfDashboard\data\logs`. `debug.log` is the
app's own log; `launcher-app-stderr.log` and `launcher-app-stdout.log` are what the launcher
captured when the dashboard would not start. The Settings page shows this folder. Running from
source, it is `data\logs` in your checkout.

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

Two files sit side by side. `config.toml` holds boot settings and is yours to
edit:

- **Installed:** `%LOCALAPPDATA%\CorporateSerfDashboard\config.toml`, written on
  first install. Updates never touch it.
- **From source:** copy `example.toml` to `config.toml` in your checkout.

`example.toml` documents every setting (an installed copy keeps it at
`%LOCALAPPDATA%\CorporateSerfDashboard\versions\<tag>\example.toml`); two are worth knowing
about:

- `port` — change this if something else on your machine already uses 8050. The
  dashboard says so at startup rather than failing mysteriously.
- `host` — the address the dashboard listens on. The default, `127.0.0.1`,
  serves this machine only. Set it to `0.0.0.0` to also open the dashboard from
  a phone or another PC on your network, at `http://<this-machine's-IP>:8050/`.
  It has to be an IP address rather than a name, so `localhost` and an empty
  value are both refused with an error naming the setting.
  On Windows you will also need an inbound firewall rule for the port; a bind
  alone is not enough. **The dashboard has no login,** so anything that can
  reach that address can read your stats and change your settings — only do
  this on a network you trust.

Everything else you might want to change lives on the dashboard's own
**Settings** page: where your KovaaK's stats live, and who you are on the
leaderboards. The stats folder is usually filled in for you on the first start
— the dashboard finds it through Steam — so the page is mostly there for the
cases it could not, and for turning the leaderboard features on. If you have
KovaaK's in more than one Steam library, the stats folder box suggests each one
it found, so picking the right copy is a click rather than a hunt through
Explorer. For the username and Steam ID, **Detect my accounts** checks the
Steam accounts on this machine against KovaaK's and fills in the one it can
prove is yours — or lists what it found, for you to choose from, when it
cannot be sure of exactly one. Nothing detected is kept until you press Save.

The page writes `data/settings.json`, the app-owned file beside `config.toml`
(installed: `%LOCALAPPDATA%\CorporateSerfDashboard\data\settings.json`). You
can write it by hand instead:

```json
{
  "schema_version": 1,
  "stats_dir": "S:/SteamLibrary/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats",
  "kovaaks_username": "YourKovaaksName",
  "steam_id": ""
}
```

- `schema_version` — which format this file is in. Required, and it must be the
  whole number `1`. It is how a future version of the dashboard will know how to
  read a file this one wrote. A file without it, or with a key not listed here,
  is not used: the dashboard leaves it exactly as it is, starts with no settings
  configured, and says so on the Settings page. Saving from that page rewrites
  the file and keeps a copy of the old one beside it.
- `stats_dir` — the folder KovaaK's writes its run files into, usually
  `<Steam library>/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats`. Without
  it the dashboard still starts, but it has no runs to show and says so on the
  Scenario Performance page. Left empty on purpose, it stays empty: the startup
  detection only fills the value in when it has never been set.
- `kovaaks_username` — enables the leaderboard position and percentile features;
  leave it out to run fully offline. `steam_id` is optional and makes player
  matching exact when usernames are ambiguous.

Edit this file only while the dashboard is stopped — it is read once per run.
Saving from the Settings page while it runs is fine; the page tells you when a
change needs a restart before it takes effect.

One setting on that page is in neither file: the **Celebrations** choice, which
picks the personal best celebration's animation or turns it off. It is
remembered by the browser rather than written to disk, applies the moment you
choose, and is not part of Save. A different browser, or one whose site data you
have cleared, starts on Confetti.

## Playlists and Benchmarks

Benchmarks are playlists with rank data attached. The app ships with a bundled
benchmark library in `resources/benchmarks` — built with the help of
[Evxl.app](https://evxl.app)'s author by combining his benchmark rank data with
playlist data from the KovaaK's API — and loads all of it at startup. The most
popular benchmarks (Voltaic, Viscose) are visible by default; to enable any
other, toggle "Show hidden" on the Playlists page and unhide it — no file
copying needed.

You can also import any playlist by share code: on the Playlists page, click
**Import** and enter the code, and the app fetches the playlist from the
KovaaK's API and saves it under `data/playlists`. Playlists imported this way
carry no rank data — the benchmark-rank overlays come only from the bundled
library.

## Run From Source

For development, or if you would rather manage the toolchain yourself. The app
is Python + [Dash](https://dash.plotly.com/) (Plotly, Dash Mantine Components);
[docs/architecture.md](docs/architecture.md) has the module map. Requires git
and [uv](https://docs.astral.sh/uv/):

```shell
git clone https://github.com/MingoDynasty/Corporate-Serf-Dashboard.git
cd Corporate-Serf-Dashboard
uv sync
```

Copy `example.toml` to `config.toml`, then start the app — the stats folder is
detected on the first start, and the Settings page covers whatever it missed
(see [Configuration](#configuration)):

```shell
uv run python source/app.py
```

A source checkout does not auto-update; `git pull` is the update path.

## Development

Development uses AI coding agents. Every change is reviewed and must pass the
project's test suite and CI gates (ruff, mypy, pytest) before it merges; the
reasoning behind the durable choices is public in the
[decision log](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/blob/main/docs/decision_log.md).

## License

Corporate Serf Dashboard is free software under the
[GNU Affero General Public License v3.0](LICENSE). Derivatives stay free and
open source on the same terms.
