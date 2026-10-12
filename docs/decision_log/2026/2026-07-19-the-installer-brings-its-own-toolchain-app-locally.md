# 2026-07-19: The Installer Brings Its Own Toolchain, App-Locally

Status: Accepted

Installing the dashboard is one PowerShell command, and it brings everything it
needs with it: its own Python, its own package manager, the app, and a
first-run configuration file. Nothing outside the install folder is used or
disturbed, so uninstalling is deleting that folder and the desktop shortcut.
Installs ask no questions — as of the 2026-08-02 addendum below, the generated
configuration carries only the port the dashboard serves on, and where the
KovaaK's stats live is the app's own business.

Decision: installation is a PowerShell one-liner that fetches `get.ps1` from
`main`. That shim is deliberately trivial and permanently backward compatible —
resolve the latest release, fetch *that release's* `install.ps1`, run it,
nothing else — so the installer is always exactly the same age as the payload it
installs. Without the split, any installer change that merged ahead of its
release would run against a payload whose layout it no longer matched, and would
stay broken indefinitely if a release job failed.

The installer puts the **entire toolchain** under the install root
(`%LOCALAPPDATA%\CorporateSerfDashboard` by default): `UV_UNMANAGED_INSTALL`
places uv in the tree and it is invoked by absolute path,
`UV_PYTHON_INSTALL_DIR` plus `--managed-python` keep a managed CPython there
instead of silently selecting whatever Python the machine has, and
`UV_CACHE_DIR` keeps the cache inside too. No Python, uv, or registry state
outside the root is used or disturbed, so uninstall is deleting the folder and
the shortcut. Two files are written outside it by design: the desktop shortcut
itself, and `get.ps1`'s copy of the installer at
`%TEMP%\csd-install-<tag>.ps1`, which is inert once the install finishes and is
deliberately not cleaned up (the shim stays trivial); the README documents
deleting it.

The uv version is **per release, not per install**: installer and launcher read
the target release's `release.json` and provision that exact uv before syncing.
An install-time-frozen uv would brick the first update that bumps the pin — the
old binary rejects the new project, and `UV_UNMANAGED_INSTALL` disables uv
self-update — so the toolchain upgrade must ride the same transaction as the
code.

First run does not merely copy `example.toml`, whose `stats_dir = "Change me!"`
placeholder would crash the first launch. The installer locates the KovaaK's
stats directory itself (Steam's registry `InstallPath` plus
`libraryfolders.vdf`), confirms it with the user, validates that it exists, and
writes it into `config.toml`. It then **round-trips the generated config through
the installed app's own `load_config()`** and aborts loudly on failure, before
writing the manifest or creating the shortcut. Validating with `tomllib` alone
would only prove the file is syntactically TOML; the app's loader also proves
the schema is one the app accepts. A config the app cannot load must fail the
install loudly rather than surface later as a permanently broken first launch —
permanent because existing `config.toml` and `data/` are never touched again.

Why: the user's machine needs exactly one bootstrapped tool, acquired the way
rustup and uv themselves are distributed. Python and git are never
prerequisites. PyInstaller was rejected: unsigned executables trip SmartScreen
and AV heuristics (fatal for a gaming audience's trust), signing is a recurring
cost, every release would become a large re-download, and bundling
dash/plotly/dash-ag-grid assets under PyInstaller is a known hook-debugging time
sink. Revisit only if "run one command" ever becomes too much to ask.

Addendum (2026-07-20): the first-run `config.toml` now writes only the two
required fields, `stats_dir` and `port`. `polling_interval` (1000) and
`sens_round_decimal_places` (1) gained code defaults on `ConfigData`, so they
are no longer required fields and no longer seeded into the generated file —
`example.toml` still documents them for anyone who wants to tune them. The
round-trip through the installed app's `load_config()` still runs and must pass
with the two-field file.

Addendum (2026-08-02): the stats-directory detection, the `[Y/n]` confirm, the
manual-entry retry loop, and the stats-directory `Stop-Fatal` are all deleted,
so **installs are fully non-interactive** and the generated `config.toml` is
`port` only. `stats_dir` now lives in the app-owned `data/settings.json`, which
the installer never touches — one home, one writer — so its detection had
nowhere legitimate left to write: a `stats_dir` line in `config.toml` would only
be warn-logged and ignored. The app absorbs the consequences instead of the
installer: it starts and serves without a usable stats directory (initial scan
and file watchdog skipped, one log line naming what was configured, a hint on
Home — plain text until the settings page shipped, a link to it since), and an
app-side startup bootstrap that re-detects the directory
follows in the same proposal. Between the two, a fresh install runs empty until
the directory is set by hand. That bootstrap has since shipped — see the
2026-08-02 pinning-and-bootstrap entry, which supersedes this addendum on
stats-directory detection. The `load_config()` round-trip through the
installed app is unchanged and still gates the install, now against the
one-field file.
