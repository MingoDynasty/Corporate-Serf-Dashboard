# Dependency Refresh

Dependency and toolchain updates are made by hand, from this playbook, about
once a month. Nothing opens update PRs on its own. A refresh is one or two
ordinary PRs, and merging one that changes what an installed copy runs cuts a
release.

## When to run

Run a refresh about monthly, at a point when little other work is open. There
is no reminder and no bot, because a refresh always finds something: a timer
would say nothing the calendar does not. The reasons are in the
[2026-10-04 decision](decision_log/2026/2026-10-04-dependency-updates-stay-manual-run-from-a-playbook.md).

List the open work first:

```powershell
gh pr list --state open
git worktree list
```

A refresh has two passes, kept apart because they disturb open branches
differently:

- The **package pass** leaves open branches alone. A branch keeps its own
  `uv.lock` until it merges `main`, and conflicts only if it changed
  dependencies too.
- The **toolchain pass** does not. The uv pin is exact, so the machine's uv
  moves with `main`, and every branch still on the old pin refuses `uv run`
  until it merges `main`. Save this pass for a quiet point. Until a branch
  catches up, `uvx uv@<old version> run ...` runs it under its own pin without
  changing the machine.

## What a refresh covers

| Pin | Where it lives | How to see what is new |
| --- | --- | --- |
| Locked packages | `uv.lock` | `uv lock --upgrade --dry-run` |
| Dependency floors | `dependencies` and the `dev` and `screenshots` groups in `pyproject.toml` | `uv tree --all-groups --depth 1` prints the locked version of each |
| `pandas-stubs` | the `dev` group, as a `~=` pin | follows pandas' major.minor line |
| pre-commit ruff | `rev` in `.pre-commit-config.yaml` | must equal the locked ruff |
| uv | `required-version` and the `uv_build` range in `pyproject.toml` | the latest release; see [uv](#uv) |
| GitHub Actions | each `uses:` line in `.github/workflows/*.yml` | `gh api repos/<owner>/<action>/releases/latest --jq .tag_name`, per action; report only, see [GitHub Actions](#github-actions) |
| Vendored browser libraries | `assets/vendor/` | the upstream project; steps in [assets/vendor/README.md](../assets/vendor/README.md) |

The Python version is not part of a refresh. Moving it is its own change, with
its own steps, in [Moving Python](#moving-python).

## Package pass

1. See what would move. An upgrade takes the newest version of every package,
   however recently it was published
   ([2026-10-05 decision](decision_log/2026/2026-10-05-a-refresh-takes-the-newest-version-of-everything.md)).
   Read the release notes of anything crossing a major version, and of every
   package that ships browser code (named under
   [Verify by what moved](#verify-by-what-moved)). For plotly, read the
   plotly.js notes too, for every version between the two it bundles: plotly's
   own notes list only the notable changes.

   ```powershell
   uv lock --upgrade --dry-run
   ```

2. Upgrade the lock and the environment, and commit `uv.lock` alone as
   `chore(deps): upgrade locked dependencies`. The lock diff runs to hundreds
   of lines, so it stays apart from the hand edits that follow it.

   ```powershell
   uv sync --upgrade
   ```

3. If ruff moved, set `rev` in `.pre-commit-config.yaml` to the locked ruff
   version. Left behind, the hook formats and lints with a different ruff than
   CI does. Commit as `chore: sync pre-commit ruff rev with the locked ruff`.

4. Raise each floor in `pyproject.toml` to the version now locked. The floors
   record what is tested, and a stale one lets a resolver hand back a version
   nobody ran. `pandas-stubs` keeps its `~=` pin, which moves only when pandas
   changes its minor version. Then re-lock:

   ```powershell
   uv tree --depth 1
   uv lock
   ```

   `git diff uv.lock` must show no line starting `version = `, because no
   package moves in this step. The `specifier` lines change, and uv may reorder
   the `resolution-markers` list. Commit as
   `chore(deps): refresh dependency floors to the locked, tested versions`.

5. Check the vendored browser libraries, which no uv command sees. Compare
   each row of [assets/vendor/README.md](../assets/vendor/README.md) with its
   upstream project's latest release. To update one, follow that README's
   steps, as its own commit.

6. Verify by what moved, then open the PR.

## Toolchain pass

### uv

1. Find the latest release, and confirm that the installer for it is being
   served. An installed copy downloads exactly the pinned version from that
   address and runs it, so a version it does not serve breaks installs
   ([Release and install](specs/release_and_install.md)).

   ```powershell
   gh api repos/astral-sh/uv/releases --jq '.[] | "\(.tag_name) \(.published_at)"'
   (Invoke-WebRequest -Method Head -UseBasicParsing -Uri https://astral.sh/uv/<version>/install.ps1).StatusCode
   ```

2. Update uv on the development machine first. The pin and the installed uv
   move together, or every `uv` command in the repository refuses to run.

   ```powershell
   uv self update <version>
   ```

3. In `pyproject.toml`, set `required-version` to `==<version>`. Keep it an
   exact `==` pin: the release job reads it into `release.json` and refuses
   anything else. Set the `uv_build` range to the one `uv init` generates for
   that version, which is a floor at the version and a ceiling at the next 0.x
   minor.

4. Check that the lock still holds without a re-lock, and commit as
   `chore: bump required uv to <version>`.

   ```powershell
   uv lock --check
   ```

CI needs no edit, because `setup-uv` reads the pin from `pyproject.toml`.

### GitHub Actions

A refresh reports these pins and does not move them. They move through the
[cross-repo tooling spec](decision_log/2026/2026-10-05-adopt-the-cross-repo-python-v3-tooling-spec.md),
which the maintainer keeps outside this repository. The workflow's top-level
settings and its `test` job are this repository's copy of the spec's workflow.
The spec carries these exact SHAs, so moving them here alone makes this copy
drift from the spec. A pin bump is a new version of the spec, which each
repository then adopts.

1. For each action in `.github/workflows/*.yml`, find the latest release:

   ```powershell
   gh api repos/<owner>/<action>/releases/latest --jq .tag_name
   ```

2. Name any pin that is behind in the PR body, as material for the next
   version of the spec.

When this repository adopts a spec version that moves a pin, read the release
notes for each major version crossed, and check the new SHA against its tag:

```powershell
gh api repos/<owner>/<action>/commits/<tag> --jq .sha
```

Replace the SHA and the version comment on every `uses:` line for that action,
the release jobs' lines included, and commit as `ci: bump pinned actions`.

The PR's CI runs a bumped action only in the `test` job. The first run on
`main` after the merge adds `release-gate`. The `release` job is skipped for a
workflow-only change, so its first run with the new pins is the next merge
that cuts a release: watch that one. A failed release job can be rerun: it
reuses its tag and resumes its draft.

## Verify by what moved

Run the gates in [AGENTS.md](../AGENTS.md#commands) on every refresh. A version
bump can change things they do not cover, so add the check for whatever moved.

### Packages that ship browser code

plotly, dash, dash-ag-grid, dash-mantine-components, and dash-extensions ship
the JavaScript the browser runs. Dash serves plotly.js from inside the plotly
package, so a plotly bump changes the charting library and not only the Python
API. The standard CI gates never open a browser, so they see none of it. The
[on-demand screenshot workflow](screenshots/README.md#refresh-in-github-actions)
captures three pages for documentation; it does not replace these checks.

When one of them moves, run the app (`uv run python source/app.py`) and look at
every page: the chart toolbars, the grids, the menus, and the browser console
after one reload. [AGENTS.md](../AGENTS.md#workflow) names the console messages
that are upstream noise. To see whether the charting library itself changed,
print its version before and after the upgrade:

```powershell
uv run python -c "from plotly.offline import get_plotlyjs_version; print(get_plotlyjs_version())"
```

Looking at a chart does not show a changed default. plotly.js 4.1.0 raised the
double-click delay from 300 ms to 500 ms, and both toolbars stayed the same.
To catch one, print each chart's settings before and after the upgrade and
compare the two. Run this in the browser console on a page with a chart drawn:

```js
JSON.stringify(document.querySelector(".js-plotly-plot")._context)
```

A plotly bump also needs one look that no test can take. On Score vs Time,
hover a New PB star that shares its point with a later run that tied it the
same day. The hover must give the time of the run that set the PB, the earlier
of the two. The app only places that run last in the trace. That plotly.js
answers a shared point with its last point is observed, on 4.0.0 and 4.1.1,
and not documented
([2026-10-05 entry](decision_log/2026/2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star.md)).
If the later run's time shows, stop and ask the maintainer.

A dash-ag-grid bump needs two looks at a benchmark's scenario table, such as
Viscose Benchmark S2 - Medium. Print the AG Grid version the package bundles
first:

```powershell
uv run python -c "import json, pathlib, dash_ag_grid; print(json.loads((pathlib.Path(dash_ag_grid.__file__).parent / 'package-info.json').read_text())['dependencies']['ag-grid-community'])"
```

- **The merged-cell repair.** The table works around a defect in AG Grid
  35.3.1, which AG Grid 36.1.0 fixed
  ([2026-10-06 entry](decision_log/2026/2026-10-06-benchmark-scenario-tables-group-scenarios-by-category-and-subcategory.md)).
  On 36.1.0 or later, remove the repair as its
  [tech-debt entry](tech_debt.md#remove-the-merged-cell-repair-when-dash-ag-grid-bundles-ag-grid-3610)
  says. Either way, click the Scenario header three times, then the Runs
  header three times. Every row must still have its Category and Subcategory
  cell, and each group must be one merged cell again.
- **The following label.** On Hewchy's Smoothness - VAI Complete, scroll
  through the table. Both group names must stay in view from the first row
  to the last. AG Grid 36 lays its rows out in one scrolling container, with
  no separate pinned section, and the label follows the scroll because of
  how the pinned section is built in 35. If the names scroll away, stop and
  ask the maintainer.

A dash-mantine-components bump needs two looks at the playlist filter on
Run History, which no test can take. The filter lists a hidden
playlist while it holds one, and that rests on how the Select treats a value
against its options: it names a value its options have, and drops a value its
new options lack. Both were read in 2.8.0's bundle and seen in a browser, and
neither is documented
([2026-10-12 entry](decision_log/2026/2026-10-12-the-playlist-filter-lists-the-hidden-playlist-it-holds.md)).

- **A held hidden playlist is named.** On Playlists, turn on Show hidden,
  open a hidden playlist's table, and click a scenario. The playlist filter
  must show that playlist's name, and still show it after a reload and after
  leaving the page and coming back.
- **A playlist that is gone is dropped.** Give the filter a code no playlist
  has: run the line below in the browser console on Run History,
  then reload. The filter must come back empty, with no clear button.

  ```js
  localStorage.setItem("_dash_persistence.run-history-playlist-filter.value.true", '["KovaaKsNoSuchCode",null]')
  ```

If either look fails, stop and ask the maintainer.

A refresh changes versions, not behavior. If an upgrade adds or removes
something a user can press, changes what a control does, or adds a new way for
the app to reach an outside service, stop and ask the maintainer before
shipping it or hiding it. A difference in appearance alone is named in the PR
body. plotly 7 added a control and an outside service at once: it put a Share
chart button on the charts by default
([2026-09-12 entry](decision_log/2026/2026-09-12-charts-keep-plotlyjs-4s-share-chart-button.md)).
What the maintainer accepts goes into
[What it talks to](user_guide.md#what-it-talks-to) and the capability spec in
the same PR.

### Vendored browser libraries

When a file under `assets/vendor/` moves, run the app and look at what that
library draws. [assets/vendor/README.md](../assets/vendor/README.md) says what
each one is for. The stop-and-ask rule for packages that ship browser code
applies here too.

### ruff

`uv run ruff check` and `uv run ruff format --check .` must pass with the same
rules enabled as before. A ruff release can widen its default rule set, or
promote a rule into a group this project selects; ruff 0.16 did both. Hold the
difference in `[tool.ruff]` in `pyproject.toml`, with a comment saying what is
held and why, as the entries already there do. Adopting a new rule is a
separate change, never part of a refresh.

### mypy and stubs

A new mypy or stubs release can report findings in code that did not change.
Fix a real finding in its own commit. If the finding is the tool's mistake,
hold that package back.

### Holding a package back

When a new version breaks something a refresh should not fix, cap that package
in `pyproject.toml` with a comment naming what breaks, re-lock, and say so in
the PR body. Lift the cap in a later refresh, once the breakage is gone.

## The PR

- Title it `chore(deps): ...`, with one commit per step.
- In the body, list what moved (the dry-run output), what was held back and
  why, which toolchain pins moved, and what the live check covered.
- Say whether merging cuts a release. A change to `uv.lock`, `pyproject.toml`,
  or anything under `assets/` does. A change to `.github/` or
  `.pre-commit-config.yaml` alone does not.
- If a step here turned out wrong or missing, fix this file in the same PR.

## A security alert between refreshes

GitHub's Dependabot alerts watch `uv.lock` and raise an alert when a locked
package has a known vulnerability. Its automatic fix PRs are off, because they
cannot run against this repository's exact uv pin
([2026-10-04 decision](decision_log/2026/2026-10-04-dependency-updates-stay-manual-run-from-a-playbook.md)).
So the fix is made by hand, as its own PR:

```powershell
uv lock --upgrade-package <name>
uv sync
```

Verify the fix by what moved, the same as a refresh.

## Moving Python

A move to a new Python minor version is its own PR, apart from a refresh. It
changes the interpreter every installed copy runs, and the release it cuts is
the first time the installer and the launcher meet that interpreter. A patch
release needs no change to the repository, because `.python-version` names the
minor version only.

A move waits for three things: the final release of the new version, a uv
release that lists it, and a wheel for every package that ships to users.

1. Pin a uv that lists the new version. uv downloads only the interpreters its
   own release knows, and an installed copy gets its Python from the pinned uv
   ([Release and install](specs/release_and_install.md)). So the
   [toolchain pass](#toolchain-pass) comes first, as its own PR, and the
   Python PR is stacked on it or follows it. With the new uv on the machine:

   ```powershell
   uv python list 3.15
   ```

   The output must name the final release, such as `cpython-3.15.0`. A uv that
   is too old names a release candidate, such as `cpython-3.15.0rc3`, or
   prints nothing.

2. Move the four places that name the version: `.python-version`,
   `requires-python` and ruff's `target-version` in `pyproject.toml`, and the
   opening paragraph of [AGENTS.md](../AGENTS.md). Then re-lock and sync:

   ```powershell
   uv lock
   uv sync
   ```

   The re-lock drops the wheels built for the old version. If
   `git diff uv.lock` shows a line starting `version = `, a package resolved
   differently for the new interpreter: find out why before going on. Besides
   the project itself, the first `uv sync` after the re-lock prints a
   `Building` line for each package that has no wheel for the new version
   yet, and compiles it from its source distribution. For a dev-only package
   that is acceptable when the sync completes: name the package in the PR
   body. pyyaml was one on the move to 3.15. Step 5 checks the packages that
   ship to users.

3. Read what the new version changes. Its What's New page lists the changed
   defaults, the removals, and the porting notes: check each one against
   `source/` and `scripts/`. The gates do not see a changed default. Python
   3.15 made UTF-8 the default text encoding. Every file this app opens names
   its encoding, so no file changed, but the text the app writes to a
   redirected console did change encoding, and the launcher reads that text
   back when a start fails. To measure a default, start Python the way the
   launcher starts the app, and compare the bytes. A variable in the measuring
   shell, such as `PYTHONIOENCODING`, overrides the default and hides the
   change. The stop-and-ask rule under
   [Packages that ship browser code](#packages-that-ship-browser-code) holds
   here too.

4. Run the gates in [AGENTS.md](../AGENTS.md#commands) on the new interpreter.
   A new `target-version` can change what ruff reports and how it formats. Fix
   what it finds in its own commit.

5. Build the environment an install builds, and start it. The gates run the
   development environment. An install has no dev packages, and it has a
   Python folder and a package cache of its own, both empty at first. From
   the committed head:

   ```powershell
   $root = Join-Path (Get-Location) "ignore\python-move"
   New-Item -ItemType Directory -Force -Path $root | Out-Null
   git archive --format=zip --prefix=app/ -o "$root\app.zip" HEAD
   Expand-Archive -LiteralPath "$root\app.zip" -DestinationPath $root
   $env:UV_PYTHON_INSTALL_DIR = "$root\python"
   $env:UV_CACHE_DIR = "$root\uv-cache"
   uv sync --directory "$root\app" --locked --no-dev --managed-python
   ```

   The last line is the installer's own command. uv must download the new
   CPython into the empty folder, and the only `Building` line must be the
   project itself. A second one names a package that ships to users and has no
   wheel, which every install would then have to compile: stop, and wait for
   the wheel. Then start the app, on a port nothing else holds:

   ```powershell
   Set-Content -Path "$root\config.toml" -Value "port = 8059"
   $env:CSD_STATE_DIR = $root
   Push-Location "$root\app"
   .\.venv\Scripts\python.exe source/app.py
   ```

   Open `http://127.0.0.1:8059/health`. Its `sha` must be the head's
   (`git rev-parse HEAD`) and its `source` must be `archive`. Then look at
   every page and the browser console, as
   [Packages that ship browser code](#packages-that-ship-browser-code)
   describes. A new state root detects the stats folder, so the pages have
   real runs, and it has no KovaaK's username, so position lookups stay off.
   Stop the app with Ctrl+C, then clean up:

   ```powershell
   Pop-Location
   Remove-Item Env:UV_PYTHON_INSTALL_DIR, Env:UV_CACHE_DIR, Env:CSD_STATE_DIR
   Remove-Item -Recurse -Force $root
   ```

   The three variables must go before another uv command runs in that shell,
   or it uses the scratch Python folder and cache.

6. Know what none of this ran. `install.ps1` and `launcher.ps1` did not run,
   and the `release-gate` and `release` jobs are skipped on a pull request, so
   the release the merge cuts is their first run on the new version. Watch the
   release job. Then launch an installed copy once: it must print
   `Updated to <tag>.` A release that fails to start leaves the copy on its
   previous version ([Updating](specs/release_and_install.md#updating)).

Title the PR `chore: move Python to <version>`. In the body, say which
packages build from source, what the new version changes for this app and
what was done about each change, what step 5 showed, and that merging cuts a
release. An installed copy that updates downloads the new interpreter and
keeps the old one beside it.
