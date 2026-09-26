# User Guide

The [README](../README.md) covers what Corporate Serf Dashboard is and how to install it.
This guide covers everything after that.

## Configuration

Two files sit side by side. `config.toml` holds boot settings and is yours to
edit:

- **Installed:** `%LOCALAPPDATA%\CorporateSerfDashboard\config.toml`, written on
  first install. Updates never touch it.
- **From source:** copy `example.toml` to `config.toml` in your checkout.

`example.toml` documents every setting (an installed copy keeps it at
`%LOCALAPPDATA%\CorporateSerfDashboard\versions\<tag>\example.toml`); three are worth knowing
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
- `open_browser_on_launch` — on by default. Set it to `false` and the desktop
  shortcut stops opening a browser tab every time you start the dashboard,
  which is what you want if you keep its tab somewhere and would rather switch
  to it yourself. The console window still prints the address. This one is
  read by the shortcut, not by the app, so running from a source checkout
  never opens a browser either way. With the setting off, double-clicking the
  shortcut while the dashboard is already running prints the address and closes
  again, so nothing visible happens — switch to the tab you already have.

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
other, turn on the **Show hidden** switch on the Playlists page and click the
playlist's eye icon — no file copying needed.

You can also import any playlist by share code: on the Playlists page, click
**Import** and enter the code, and the app fetches the playlist from the
KovaaK's API and saves it under `data/playlists`. Playlists imported this way
carry no rank data — the benchmark-rank overlays come only from the bundled
library.

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
`"schema_version"` line.** Installs made before `v2026.08.11.5` wrote their durable files without
a format stamp, and newer versions refuse to guess. Nothing was deleted or changed. The release
ships a converter that stamps all of them in one pass, and its order matters: **copy your `data`
folder somewhere safe**, close the dashboard, then run `scripts\stamp_schema_version.py` from the
installed version folder with its own `.venv\Scripts\python.exe` — the script's header carries the
exact command — and launch again. Seeing this message means the update half of that order has
already happened. Running it a second time changes nothing. Adding the `"schema_version": 1` line
by hand is a last resort: it skips the converter's validation and atomic writes, it fixes only
the file you edit, and the files under `data\playlists\` are machine-written rather than a
hand-edit surface.

**The browser did not open, or the console says a post-start step failed.** The dashboard is
running anyway. Open <http://localhost:8050/> yourself — the console's "Dashboard running at"
line names the exact address, including a configured port.

**Notifications sometimes do not appear.** Keep one Scenario Performance tab open at a time.
Extra tabs are crash-safe, but a new run's notification goes to whichever tab asks first.

**Where the logs are.** `%LOCALAPPDATA%\CorporateSerfDashboard\data\logs`. `debug.log` is the
app's own log; `launcher-app-stderr.log` and `launcher-app-stdout.log` are what the launcher
captured when the dashboard would not start. The Settings page shows this folder. Running from
source, it is `data\logs` in your checkout.

## What it talks to

The dashboard does not collect or send usage or crash analytics. Your runs, settings, and
caches stay on your PC unless you share a chart yourself. These are the outside services it
reaches, and what makes it reach them:

| When | What | Service |
|---|---|---|
| You run the [install one-liner](../README.md#install) | Fetches `get.ps1`, asks which release is the latest, then fetches that release's own `install.ps1` | GitHub |
| Every launch from the shortcut, unless the install is pinned | Asks whether a newer release exists | GitHub |
| Installing or updating | Asks which release is the latest, unless the installer was handed a tag; downloads the release zip, and, when they are not already present, uv, a Python build, and the app's packages | GitHub, Astral, PyPI |
| While running, only with a KovaaK's username set | Looks up your leaderboard position, percentile, and the player total; slowly fills the playlist percentile cache in the background (`percentile_warmup_enabled` in `config.toml` turns that off) | KovaaK's |
| You click **Detect my accounts** (Settings) or **Import** (Playlists) | Checks the Steam accounts on this machine against KovaaK's; fetches a playlist by share code, asking Evxl when KovaaK's has no record of it | KovaaK's, Evxl |
| You click **Share chart...** on a chart's toolbar and confirm | Uploads that chart, including the run data drawn in it, to create a sharing link | Plotly |

Services, not a firewall allowlist. A request that starts at a name like `github.com`,
`astral.sh`, or `pypi.org` is handed on to whatever delivery host that service uses, and those
hosts change: a release download redirects to GitHub's asset storage, and package and Python
downloads follow their own infrastructure. Allowing those names alone will not keep installs and
updates working.

With no KovaaK's username set, the running app makes no network requests on its own. Requests to
KovaaK's identify themselves with the app's name, its version, and this repository's address.
The GitHub, Discord, and **Report a bug** links in the app open in your browser; the app itself
does not contact those sites. Sharing a chart is per click and never automatic: the toolbar
button opens a confirmation naming Plotly Cloud, confirming opens Plotly Cloud in a new browser
tab, and the chart is handed over only once you are signed in there. **Download plot as a PNG**
beside it saves to your PC instead. Without a connection, the launcher starts the version you
already have, and a leaderboard position shows its cached value or says the lookup failed.

## Manual install

If you would rather not pipe a script from the internet, install from a release you have
inspected yourself:

1. Download the app zip (`Corporate-Serf-Dashboard-<tag>.zip`) from the
   [Releases page](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/releases/latest).
   Its SHA-256 digest is listed beside it, and `Get-FileHash <file>` in PowerShell prints the
   same digest for your copy. GitHub's own "Source code" downloads carry no digest.
2. Extract it and read `install.ps1` — it is the same installer the [one-liner](../README.md#install) runs.
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
automatic updates, run the [install one-liner](../README.md#install) again.

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
