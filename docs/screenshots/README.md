# README screenshots

The three PNGs in this folder show the real app with synthetic runs, notes and
leaderboard values. They contain no player history or account details.

## Screenshot stories

The README introduces the app through three questions: am I improving, where
am I weak, and what should I train next? Each image answers one part of that
story. One fictional player's Voltaic Intermediate benchmark connects the
overview, the scenario table and the ww5t history.

| Image | Story | Sample and framing |
| --- | --- | --- |
| `run_history.png` | Usual performance improves despite variation between runs. | ww5t in Score vs Run with All runs. An early lucky PB, a plateau and uneven gains distinguish typical performance from records. Older stretches fade after long breaks; all twenty latest supporting runs are recent. Keep the note and one session expanded. Show PB and score-threshold lines, with rank overlays off so the trend remains prominent. |
| `playlists.png` | Compare coverage and standing to choose a benchmark to work on. | A completed novice benchmark, an active intermediate benchmark, and partially explored advanced and Viscose benchmarks. Vary run counts, activity dates, medians and weakest percentiles. Use a compact viewport with navigation collapsed and every column visible. |
| `playlist_scenarios.png` | Identify weaknesses and achievable next targets. | Show the same Voltaic Intermediate benchmark, including ww5t near Master. Mix ranks and percentiles, with both strengths and weaknesses and several small gaps to the next rank. Include the whole benchmark so every category is visible and no merged group ends at a crop. Collapse navigation and fit every default column. |

The histories and cached leaderboard values share the same scores and
positions across views. These are illustrative examples, not a claim about
how fast a player will improve. The fixture stays synthetic and uses the
app's real parser, components, statistics and controls.

### Review an updated set

- Inspect the images at their displayed README width as well as full size.
  The main trend, comparison or next target should be apparent quickly.
  Full-resolution viewing supplies the dense table detail.
- Keep one main point per image. Use realistic variation and deliberate
  contrasts; avoid identical completion counts, repeated score waves or a
  procession of new PBs that makes the sample look mechanical.
- Preserve continuity: benchmark names, ww5t's PB and standing, and run counts
  agree wherever they recur. Keep both faded and full-strength history, with
  the latest typical-score point at full strength.
- Close menus, dismiss tooltips and move the pointer off content. Keep useful
  headings and complete rows and category groups, with every column in view.
  Use viewport sizing and normal app controls; don't restyle the app or add
  screenshot-only UI.
- Capture at 2× for crisp full-size inspection. Choose the logical viewport
  and crop for readability; a larger pixel count alone doesn't enlarge text
  within the README.

Automation preserves these curated states and checks rendering and column
fit. A person still checks the story and composition when reviewing a refresh.
Update this brief with the fixture when the intended demonstration changes.

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

## Validate capture behavior

The on-demand workflow runs the Chromium regression checks before capturing the
images. To run them locally after installing the screenshot tools and browser:

```powershell
uv run --group screenshots pytest tests/test_capture_screenshots_browser.py
```

They check that errors on the clean reload fail capture without replacing
existing images, while noise on the initial load is ignored. The standard test
suite skips these browser checks when the optional screenshot Python packages
aren't installed. Once the screenshots group is installed, `uv run pytest tests`
also runs these checks and requires Chromium from the installation step above.
`uv run` retains installed optional packages; `uv sync --locked` restores the
default development environment.

## Capture contract

[The capture script](../../scripts/capture_screenshots.py) starts the app from
its own checkout on a free loopback port. It creates a temporary state root
beneath `ignore/screenshots/`, loads sample CSVs through the production parser,
and seeds sample leaderboard caches. Both the server and the browser refuse
outbound HTTP requests. Existing app settings, notes, caches and stats are
never read or changed.

The sample clock is fixed to October 21, 2026, at 18:00 UTC in both Python and
the browser. Chromium uses English, UTC, a light theme and a fresh browser
context. Captures use a 2× device scale. Run History shows VT ww5t Intermediate
S5 at 1920 by 1080 in Score vs Run with All runs selected. Its sample history
includes long breaks, so the Typical score line and bands visibly change
between full-strength and faded support.

For both table screenshots, the capture tool collapses the left navigation and
measures the total width of every displayed column. It expands the viewport to
at least that width plus the page padding, and checks that the table has no
horizontal overflow. This includes new default columns added by later changes.
Table images are cropped to their headings, headers and all sample rows.
The viewport grows vertically to include the selected benchmark whole.

The script ignores the first load's known Dash Pages race, then attaches error
listeners before reloading so failures during the clean reload are captured.
It waits for the chart, note, grid and leaderboard callbacks, then waits for
two matching frames with animations disabled before saving each screenshot.
It fails on subsequent browser exceptions, HTTP errors, or attempted outbound
requests. All three captures must succeed before any
checked-in image is replaced, and the temporary server and state are removed
on success or failure.

These are documentation captures, not pixel-diff test baselines. Fixed data,
time and browser settings reduce incidental changes; font rendering can still
vary across operating systems. Use Windows, as the workflow does, when
refreshing the committed images.

To change the pictured scenario, playlists or sample history, edit the constants
and sample generator in the capture script. App layout and copy come directly
from production components; the capture tool does not replace or restyle them.
