# README screenshots

The three PNGs show the real app with curated documentation data. Run History
uses a maintainer-approved, sanitized snapshot of real ww5t history. Other
scenario histories and leaderboard positions and totals are synthetic. The
ww5t percentile is the maintainer-provided 88.79%; other percentiles are synthetic.

## Screenshot stories

The README introduces the app through three questions: am I improving, where
am I weak, and what should I train next? Each image answers one part of that
story. The same Voltaic Intermediate benchmark connects the overview, the
scenario table and the ww5t history.

| Image | Story | Data and framing |
| --- | --- | --- |
| `run_history.png` | Separate usual performance from individual results, across practice and long breaks. | Real ww5t history in Score vs Run with All runs: 169 runs across 24 sessions, from August 2025 to August 2026. Preserve the uneven progress and actual gaps. Typical score support is faded after long breaks, including the latest point. Select Median and best for session summaries. Keep the useful Bardpill technique note. Expand the latest session and the April 12 and April 11 sessions. Show run-level green checks for meeting the threshold and a star for a new PB. Show PB and rank-threshold lines so progress has benchmark context, including the next rank target. Hide the score-threshold line because its label overlaps Diamond; the run-list checks still demonstrate threshold attainment. |
| `playlists.png` | Compare coverage and standing to choose a benchmark to work on. | A completed novice benchmark, an active intermediate benchmark, and partially explored advanced and Viscose benchmarks. Vary run counts, activity dates, medians and weakest percentiles. Keep navigation visible, crop out the app banner and fit every column. |
| `playlist_scenarios.png` | Identify weaknesses and achievable next targets. | Show the same Voltaic Intermediate benchmark, including ww5t's real 1470 PB, twenty points below Jade. Show its 88.79% percentile beside varied illustrative standings. Crop to the complete seven-row Clicking category so the image itself stays short and merged labels remain whole. Include Typical Score, Typical Rank and every other default column. Collapse navigation and crop out the app banner. |

Run History is the only full-width image in the README. The two tables appear
as compact, linked previews side by side; full-resolution viewing supplies
their dense detail without making the front page a wall of screenshots.

The histories and cached leaderboard values share the same PB scores across
views. ww5t uses the maintainer-provided 88.79% percentile; its illustrative
position and player total are chosen to reproduce that displayed value. Other
standings illustrate comparison rather than actual leaderboard positions. The
app supplies the real parser, components, statistics and controls.

### Data provenance

[ww5t_history.json](ww5t_history.json) contains only the selected scenario and
its run end and start times, effective durations, scores, normalized cm/360
sensitivity, shots and hits. The maintainer authorized this public snapshot,
including its real dates and scores. It contains no account names, IDs,
original CSVs, file paths or scenario hashes. Capture and CI read this committed
snapshot; they never read the maintainer's private installation or stats folder.

The snapshot retains all 169 available ww5t runs and their recorded local
wall-clock times. It does not smooth scores, shorten gaps or manufacture
improvement. Synthetic practice on other scenarios stays clear of these
sessions so it cannot bridge their boundaries. The latest run follows a long
break: only one of its twenty Typical score supporting runs is within thirty
days. Its faded presentation is intentional.

The scenario note is the maintainer's shortened version of bardOZ's advice:

```text
Take the Bardpill:
1. Learn technique slowly, then speed up.
2. Flick fast. Micro-correct smoothly.
3. Restart if you miss in the first 10s.
4. Restart on the 4th miss.
```

The note uses the app's normal card. At the selected 1960 by 1080 viewport,
five complete rendered lines fit, including the title; wrapped text consumes
another line. Keep each point short enough to fit on one line. Capture checks
that the entire note fits without scrolling. Do not enlarge or restyle the
card just to expose more text in one image.

### Review an updated set

- Inspect the images at their displayed README width as well as full size.
  The main trend, comparison or next target should be apparent quickly.
- Keep one main point per image. Preserve real variation and gaps; avoid
  fabricating a rapid improvement curve for a recognizable scenario.
- Preserve continuity: benchmark names, ww5t's PB, and run counts agree
  wherever they recur. Keep both faded and full-strength history, with recency
  reflecting the snapshot faithfully rather than forcing the latest point
  to full strength.
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
Any replacement real-data snapshot needs the same explicit public-data scope
and field review; never copy raw personal CSVs into the repository.

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
beneath `ignore/screenshots/`, loads the sanitized and synthetic CSVs through
the production parser, and seeds synthetic leaderboard caches. Both the server
and the browser refuse outbound HTTP requests. Existing app settings, notes,
caches and stats are never read or changed.

The sample clock is fixed to August 7, 2026, at 01:02:02, two hours after the
last snapshot run. Python uses these recorded wall-clock values; the browser
uses UTC for repeatability. Chromium uses English, a light theme and a fresh
browser context at 100% zoom. Captures use a 2× device scale for sharper pixels;
this does not enlarge the app's CSS text or controls. Run History shows VT ww5t
Intermediate S5 at 1960 by 1080 in Score vs Run with All runs selected and
Median and best session summaries. The slightly wider frame gives the playlist
field enough room for its full selected name at normal font size. The latest
session and the April 12 and April 11 sessions are expanded, with actual green
checks and a new-PB star in view. Its history includes long breaks, so the
Typical score line and bands visibly change between full-strength and faded
support.

For table screenshots, the capture tool leaves navigation open on Playlists
and collapses it on the scenario table. It waits for every cached row and the
fonts, then auto-sizes columns through the normal header controls. It measures
the width of every displayed column and any visible navigation, expands the
viewport to include them plus page padding, and checks that the table has no
horizontal overflow. This includes new default columns added by later changes.
Both table crops start below the app banner. Playlists includes all four
profiles and the visible navigation. The scenario table ends exactly after
the seventh row, at the complete Clicking category boundary, with no sliver
of the next category. All 21 scenarios remain in the sample dataset; the PNG
is a compact excerpt rather than the entire benchmark.

The script ignores the first load's known Dash Pages race, then attaches error
listeners before reloading so failures during the clean reload are captured.
After closing Chart options, it waits for the control to report closed and for
Plotly's canvas to fill its container. It waits for the chart, note, grid and
leaderboard callbacks, then waits for two matching frames with animations disabled before
saving each screenshot. It fails on subsequent browser exceptions, HTTP
errors, or attempted outbound requests. All three captures must succeed before
any checked-in image is replaced, and the temporary server and state are
removed on success or failure.

These are documentation captures, not pixel-diff test baselines. Fixed data,
time and browser settings reduce incidental changes; font rendering can still
vary across operating systems. Use Windows, as the workflow does, when
refreshing the committed images.

To change the pictured scenario, playlists or synthetic practice, edit the
constants and sample generator in the capture script. To refresh the real
history, update the sanitized JSON snapshot and its capture clock. App layout
and copy come directly from production components; the capture tool does not
replace or restyle them.
