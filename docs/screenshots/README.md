# README screenshots

The three PNGs in this folder show the real app with synthetic runs, notes and
leaderboard values. They contain no player history or account details.

## Refresh locally

From the repository root, install the optional capture tools and their browser
once:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv sync --locked --group screenshots
uv run --group screenshots playwright install chromium
```

Then regenerate all three images with one command:

```powershell
uv run --group screenshots python -m scripts.capture_screenshots
```

Review the images and commit them with the UI change that made them stale.
To inspect a capture without replacing the checked-in images:

```powershell
uv run --group screenshots python -m scripts.capture_screenshots --output ignore/screenshots/preview
```

## Refresh in GitHub Actions

Run **README screenshots** from the repository's Actions tab and select the
branch to capture. Download the `readme-screenshots-<commit>` artifact, inspect
the images, then replace these PNGs in a normal pull request. The workflow has
read-only repository permissions and does not commit or push images.

## Capture contract

[The capture script](../../scripts/capture_screenshots.py) starts the app from
its own checkout on a free loopback port. It creates a temporary state root
beneath `ignore/screenshots/`, loads sample CSVs through the production parser,
and seeds sample leaderboard caches. Both the server and the browser refuse
outbound HTTP requests. Existing app settings, notes, caches and stats are
never read or changed.

The sample clock is fixed to October 21, 2026, at 18:00 UTC in both Python and
the browser. Chromium uses English, UTC, a light theme and a fresh browser
context. Run History shows VT ww5t Intermediate S5 at 1920 by 1080 in Score vs
Time with All time selected. Its sample history includes long breaks, so the
Typical score line and bands visibly change between full-strength and faded
support.

For both table screenshots, the capture tool collapses the left navigation and
measures the total width of every displayed column. It expands the viewport to
at least that width plus the page padding, and checks that the table has no
horizontal overflow. This includes new default columns added by later changes.
Table images are cropped to their headers and up to twelve rows.

The script reloads once for the known initial Dash Pages race, waits for the
chart, note, grid and leaderboard callbacks, then waits for two matching frames
with animations disabled before saving each screenshot. It fails on subsequent
browser exceptions, HTTP errors,
or attempted outbound requests. All three captures must succeed before any
checked-in image is replaced, and the temporary server and state are removed
on success or failure.

These are documentation captures, not pixel-diff test baselines. Fixed data,
time and browser settings reduce incidental changes; font rendering can still
vary across operating systems. Use Windows, as the workflow does, when
refreshing the committed images.

To change the pictured scenario, playlists or sample history, edit the constants
and sample generator in the capture script. App layout and copy come directly
from production components; the capture tool does not replace or restyle them.
