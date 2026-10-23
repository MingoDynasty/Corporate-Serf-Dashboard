"""Refresh README images from an isolated app with synthetic sample data.

Run with ``uv run --group screenshots python -m scripts.capture_screenshots``.
"""

import argparse
import json
import math
import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 21, 18)
SCENARIO = "VT ww5t Intermediate S5"
RUN_HISTORY_PLAYLIST_CODE = "KovaaKsCarryingNarrowCt"
TABLE_PLAYLIST_CODE = RUN_HISTORY_PLAYLIST_CODE
# An early lucky PB, a plateau, and uneven gains keep the typical-score
# story distinct from the personal-best story. Long breaks expose fading.
HISTORY_SESSIONS = (
    (140, (1230, 1118, 1147, 1158, 1095, 1136, 1162, 1129, 1171, 1144, 1107, 1151)),
    (137, (1164, 1198, 1140, 1212, 1177, 1159, 1185, 1205, 1168, 1224, 1191, 1174)),
    (134, (1189, 1165, 1208, 1179, 1151, 1217, 1182, 1197, 1162, 1201, 1174, 1192)),
    (80, (1340, 1234, 1272, 1256, 1328, 1291, 1260, 1308, 1280, 1317, 1275, 1299)),
    (77, (1290, 1321, 1277, 1340, 1302, 1285, 1335, 1312, 1297, 1353, 1324, 1307)),
    (6, (1463, 1372, 1401, 1425, 1388, 1448, 1414, 1395, 1451, 1422, 1406, 1438)),
    (2, (1498, 1482, 1431, 1489, 1468, 1447, 1489, 1473, 1429, 1512, 1461, 1494)),
    (0, (1478, 1450, 1505, 1486, 1442, 1538, 1470, 1518, 1492, 1459, 1526, 1503)),
)
NOTE_TEXT = (
    "Keep the click rhythm steady. Reset the aim between targets and avoid "
    "rushing the final shots."
)
USERNAME = "Sample player"
PLAYLIST_SAMPLES = (
    {
        "name": "Voltaic Novice Benchmarks S5.5",
        "played": 21,
        "age": 45,
        "percentiles": (84, 97),
    },
    {
        "name": "Voltaic Intermediate Benchmarks S5.5",
        "played": 21,
        "age": 3,
        "percentiles": (43, 89),
    },
    {
        "name": "Voltaic Advanced Benchmarks S5.5",
        "played": 6,
        "age": 8,
        "percentiles": (18, 51),
    },
    {
        "name": "Viscose Benchmark S2 - Medium",
        "played": 15,
        "age": 4,
        "percentiles": (39, 78),
    },
)
INTERMEDIATE_PERCENTILES = (
    83,
    76,
    68,
    71,
    61,
    54,
    89,
    84,
    80,
    78,
    74,
    87,
    66,
    72,
    70,
    48,
    65,
    43,
    82,
    77,
    69,
)
IMAGE_NAMES = ("run_history.png", "playlists.png", "playlist_scenarios.png")
WEAPON_HEADER = (
    "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,"
    "Vert Sens,FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,"
    "ADS Sens,ADS Zoom Scale"
)


def write_sample_state(state: Path, port: int) -> list[dict]:
    """Write synthetic runs and settings only beneath the supplied scratch root."""
    stats = state / "stats"
    data = state / "data"
    stats.mkdir(parents=True)
    data.mkdir()
    (state / "config.toml").write_text(
        f'port = {port}\nhost = "127.0.0.1"\ndebug = false\n'
        "percentile_warmup_enabled = false\n",
        encoding="utf-8",
    )
    (data / "settings.json").write_text(
        json.dumps(
            {"schema_version": 1, "stats_dir": str(stats), "kovaaks_username": USERNAME}
        ),
        encoding="utf-8",
    )
    playlists = [
        json.loads(
            (ROOT / "resources" / "benchmarks" / f"{profile['name']}.json").read_text(
                encoding="utf-8"
            )
        )
        for profile in PLAYLIST_SAMPLES
    ]
    (data / "playlist_visibility.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "shown_playlists": [item["code"] for item in playlists],
            }
        ),
        encoding="utf-8",
    )
    rng = random.Random(410)
    samples = []
    practice_slots = {}
    for profile, playlist in zip(PLAYLIST_SAMPLES, playlists, strict=True):
        for index, scenario in enumerate(playlist["scenarios"][: profile["played"]]):
            name = scenario["name"]
            percentile = (
                INTERMEDIATE_PERCENTILES[index]
                if playlist["code"] == TABLE_PLAYLIST_CODE
                else rng.uniform(*profile["percentiles"])
            )
            ranks = scenario["ranks"]
            rank_index = max(0, min(len(ranks) - 1, int((percentile - 35) / 15)))
            threshold = ranks[rank_index]["threshold"]
            next_threshold = (
                ranks[rank_index + 1]["threshold"]
                if rank_index + 1 < len(ranks)
                else threshold * 1.12
            )
            target = (
                threshold + (next_threshold - threshold) * (0.35, 0.9, 0.6)[index % 3]
            )
            if name == SCENARIO:
                sessions = HISTORY_SESSIONS
            else:
                per_session = 6 + 3 * (index % 5)
                sessions = tuple(
                    (
                        profile["age"] + index % 9 + (3 if session == 0 else 0),
                        tuple(
                            round(target * rng.uniform(0.84, 0.99), 2)
                            for _ in range(per_session)
                        ),
                    )
                    for session in range(2)
                )
                # Give the rank and next-rank columns deliberate targets,
                # independent of how many illustrative runs happen to be drawn.
                sessions = (
                    sessions[0],
                    (sessions[1][0], (*sessions[1][1][:-1], round(target, 2))),
                )
            best = 0.0
            for age, scores in sessions:
                for in_session, score in enumerate(scores):
                    if name == SCENARIO:
                        ended = NOW - timedelta(
                            days=age,
                            hours=2,
                            minutes=(len(scores) - 1 - in_session) * 2 + index % 15,
                        )
                    else:
                        # Shared daily slots keep this fictional player's
                        # practice from overlapping across different scenarios.
                        slot = practice_slots.get(age, 0)
                        ended = (
                            NOW.replace(hour=4)
                            - timedelta(days=age)
                            + timedelta(minutes=slot * 2)
                        )
                        practice_slots[age] = slot + 1
                    best = max(best, score)
                    start = ended - timedelta(seconds=60)
                    accuracy = (
                        rng.uniform(0.87, 0.96)
                        if name == SCENARIO
                        else rng.uniform(0.535, 0.625)
                    )
                    shots = round(score / 10 / accuracy) if name == SCENARIO else 6000
                    content = (
                        f"Score:,{score}\nSens Scale:,cm/360\nHoriz Sens:,{40 + index % 3 * 5}\n"
                        f"Scenario:,{name}\nChallenge Start:,{start:%H:%M:%S}.000\n"
                        "Pause Duration:,0\nReloads:,0\nFOV:,103\nFOVScale:,Overwatch\n"
                        f"Avg FPS:,240\n{WEAPON_HEADER}\n"
                        f"Rifle,{shots},{round(shots * accuracy)},0,0\n"
                    )
                    (
                        stats
                        / f"{name} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv"
                    ).write_text(content, encoding="utf-8")
            total = 18000 + index * 1379
            samples.append(
                {
                    "name": name,
                    "leaderboard_id": scenario["leaderboard_id"],
                    "score": best,
                    "rank": round(total * (1 - percentile / 100) + 0.5),
                    "total": total,
                }
            )
    return samples


def serve_sample(state: Path, port: int) -> None:
    """Run the real app with a fixed clock, sample caches and blocked HTTP egress."""
    # Set this before importing app modules: they bind state paths at import.
    os.environ["CSD_STATE_DIR"] = str(state)
    samples = write_sample_state(state, port)
    from freezegun import freeze_time

    from source.app import main
    from source.kovaaks import api_service, scenario_notes_service
    from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus

    def refuse_request(*_args, **_kwargs):
        (state / "network-attempt").touch()
        raise RuntimeError("Screenshot app attempted an outbound HTTP request.")

    with (
        freeze_time(NOW, ignore=["waitress", "watchdog", "threading"]),
        patch("requests.sessions.Session.request", side_effect=refuse_request),
    ):
        api_service.make_cache()
        for sample in samples:
            leaderboard_id = sample["leaderboard_id"]
            api_service.save_scenario_rank(
                leaderboard_id,
                USERNAME,
                ScenarioRankInfo(
                    status=ScenarioRankStatus.RANKED,
                    leaderboard_id=leaderboard_id,
                    scenario_name=sample["name"],
                    rank=sample["rank"],
                    score=sample["score"],
                    fetched_at=NOW.replace(tzinfo=UTC),
                ),
            )
            api_service.save_leaderboard_total(leaderboard_id, sample["total"])
        scenario_notes_service.save_scenario_note(
            SCENARIO,
            NOTE_TEXT,
        )
        main()


def wait_for_server(process: subprocess.Popen, origin: str) -> None:
    """Wait for startup without relying on a fixed sleep or a busy network port."""
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Screenshot app exited before startup completed.")
        try:
            with urlopen(f"{origin}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except URLError, TimeoutError:
            pass
        time.sleep(0.1)
    raise TimeoutError("Screenshot app did not become healthy within 90 seconds.")


def save_stable_screenshot(page, destination: Path, **options) -> None:
    """Wait for two matching frames so late callback paints cannot enter a PNG."""
    deadline = time.monotonic() + 10
    previous = None
    while time.monotonic() < deadline:
        current = page.screenshot(animations="disabled", **options)
        if current == previous:
            destination.write_bytes(current)
            return
        previous = current
        page.wait_for_timeout(200)
    raise TimeoutError("The screenshot did not settle within 10 seconds.")


def fit_table_columns(page, grid: str) -> int:
    """Fit every displayed column with navigation collapsed, without horizontal scrolling."""
    # Cached cells can arrive after the first rows. Use normal header
    # auto-sizing once they're ready so startup widths don't widen the image.
    page.evaluate("document.fonts.ready")
    page.wait_for_function(
        """async grid => {
        const api = await window.dash_ag_grid.getApiAsync(grid);
        const rows = [];
        api.forEachNode(node => rows.push(node.data));
        return rows.length && rows.every(row => grid === 'playlists-overview-grid'
            ? row.percentile_aggregates_resolved
            : !row.position_pending && !row.total_pending && !row.percentile_pending);
    }""",
        arg=grid,
    )
    for handle in page.locator(f"#{grid} .ag-header-cell-resize").all():
        if handle.is_visible():
            handle.dblclick()
    column_width = page.evaluate(
        """async grid => {
        const api = await window.dash_ag_grid.getApiAsync(grid);
        return api.getAllDisplayedColumns().reduce(
            (width, column) => width + column.getActualWidth(), 0);
    }""",
        grid,
    )
    # Measure the actual shown columns so later additions get space
    # without squeezing their labels or cropping the last column.
    width = math.ceil(column_width + 48)
    page.set_viewport_size({"width": width, "height": 1080})
    page.wait_for_function(
        """grid => {
        const viewport = document.querySelector(
            `#${grid} .ag-body-horizontal-scroll-viewport`);
        return viewport && viewport.scrollWidth <= viewport.clientWidth + 1;
    }""",
        arg=grid,
    )
    print(f"{grid}: all displayed columns fit at {width}px with navigation collapsed")
    return width


def capture(origin: str, destination: Path) -> None:
    """Capture the three rendered pages after their actual content is ready."""
    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
            locale="en-US",
            timezone_id="UTC",
            color_scheme="light",
            reduced_motion="reduce",
            service_workers="block",
        )
        external_requests = []

        def local_only(route):
            if urlsplit(route.request.url).netloc == urlsplit(origin).netloc:
                route.continue_()
            else:
                external_requests.append(route.request.url)
                route.abort()

        context.route("**/*", local_only)
        context.add_init_script(
            'localStorage.setItem("mantine-color-scheme-value", "light");'
        )
        page = context.new_page()
        page.clock.set_fixed_time(NOW.replace(tzinfo=UTC))
        page.set_default_timeout(30000)
        # Dash's first-load Pages race clears on reload (AGENTS.md).
        page.goto(
            origin
            + "/run-history?"
            + urlencode(
                {"scenario": SCENARIO, "playlist_code": RUN_HISTORY_PLAYLIST_CODE}
            )
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        responses = []
        page.on(
            "response",
            lambda response: (
                responses.append(response.status) if response.status >= 400 else None
            ),
        )
        page.reload()
        expect(page.locator("#run-history-scenario")).to_have_value(SCENARIO)
        page.wait_for_function("""() => {
            const graph = document.querySelector('#run-history-graph .js-plotly-plot');
            return graph && graph.data && graph.data.some(trace => trace.x?.length > 20)
                && graph.data.some(trace => trace.name === 'Latest run' && trace.visible !== false);
        }""")
        expect(
            page.locator("#run-history-list-grid .run-list-row-latest").first
        ).to_be_visible()
        expect(page.get_by_text(NOTE_TEXT, exact=True)).to_be_visible()
        page.get_by_text("Score vs Run", exact=True).click()
        page.locator("#run-history-run-range").click()
        page.get_by_role("option", name="All runs", exact=True).click()
        expect(page.locator("#run-history-run-range")).to_have_value("All runs")
        page.get_by_role("button", name="Chart options", exact=True).click()
        page.locator("#run-history-rank-overlay-switch").uncheck()
        page.get_by_role("button", name="Chart options", exact=True).click()
        # Plotly can retain the inspector's narrower canvas after it closes.
        # A normal viewport resize retriggers its responsive layout.
        for width in (1919, 1920):
            page.set_viewport_size({"width": width, "height": 1080})
            page.wait_for_function("""() => {
                const graph = document.querySelector('#run-history-graph .js-plotly-plot');
                return Math.abs(graph._fullLayout.width - graph.getBoundingClientRect().width) < 2;
            }""")
        page.wait_for_function("""() => {
            const graph = document.querySelector('#run-history-graph .js-plotly-plot');
            const typical = graph?.data?.filter(trace => trace.name === 'Typical score') || [];
            return graph?._fullLayout?.xaxis.type === 'linear'
                && graph.data[0].x.length === 96
                && typical.some(trace => trace.opacity === 0.35)
                && typical.some(trace => trace.opacity === 1 && trace.x.includes(96))
                && graph.data.find(trace => trace.name === 'New PB')?.x.length <= 10
                && graph.layout.shapes.length === 2;
        }""")
        page.locator("#run-history-graph").click(position={"x": 5, "y": 5})
        page.mouse.move(0, 0)
        page.evaluate("document.fonts.ready")
        save_stable_screenshot(page, destination / IMAGE_NAMES[0])
        page.get_by_role("button", name="Show or hide navigation").click()
        page.wait_for_function("""() =>
            document.getElementById('navbar')?.getBoundingClientRect().right <= 1
        """)
        for path, grid, filename in (
            ("/playlists", "playlists-overview-grid", IMAGE_NAMES[1]),
            (
                f"/playlists/{TABLE_PLAYLIST_CODE}",
                "playlist-scenarios-grid",
                IMAGE_NAMES[2],
            ),
        ):
            page.set_viewport_size(
                {
                    "width": 1440 if grid == "playlists-overview-grid" else 1920,
                    "height": 1080,
                }
            )
            page.goto(origin + path)
            page.wait_for_function("""() =>
                document.getElementById('navbar')?.getBoundingClientRect().right <= 1
            """)
            expect(page.locator(f"#{grid} .ag-row").first).to_be_visible()
            # Cached leaderboard values arrive in a second callback. Wait for
            # the percentile cells as well as the first paint of local stats.
            page.wait_for_function(
                """grid => [...document.querySelectorAll(
                `#${grid} .ag-cell`)].some(cell => /\\d+\\.\\d+%/.test(cell.textContent))
            """,
                arg=grid,
            )
            if grid == "playlist-scenarios-grid":
                expect(page.locator("#playlist-scenarios-status")).to_have_text("")
            fit_table_columns(page, grid)
            page.mouse.move(0, 0)
            page.evaluate("document.fonts.ready")
            rows = page.locator(f"#{grid} .ag-center-cols-container .ag-row")
            # Keep the selected benchmark whole so no merged category label
            # ends at an arbitrary row cutoff. Let normal viewport sizing
            # reveal its rows, without changing the production grid layout.
            last_row = rows.last.bounding_box()
            assert last_row
            viewport = page.viewport_size
            assert viewport
            page.set_viewport_size(
                {
                    "width": viewport["width"],
                    "height": max(
                        1080, math.ceil(last_row["y"] + last_row["height"] + 32)
                    ),
                }
            )
            expect(rows.last).to_be_in_viewport(ratio=1)
            if grid == "playlist-scenarios-grid":
                expect(
                    page.get_by_role("link", name=SCENARIO, exact=True)
                ).to_be_visible()
            main_box = page.locator("main").bounding_box()
            last_row = rows.last.bounding_box()
            assert main_box and last_row
            save_stable_screenshot(
                page,
                destination / filename,
                clip={
                    **main_box,
                    "height": last_row["y"] + last_row["height"] - main_box["y"] + 16,
                },
            )
        browser.close()
        if errors or responses or external_requests:
            raise RuntimeError(
                f"Capture failed: page errors={errors}, HTTP errors={responses}, "
                f"external requests={external_requests}"
            )


def main() -> None:
    """Start a disposable server and publish images only after capture succeeds."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "screenshots")
    parser.add_argument("--serve", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve_sample(args.serve, args.port)
        return
    scratch = ROOT / "ignore" / "screenshots"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch, prefix="capture-") as temporary:
        state = Path(temporary)
        images = state / "images"
        images.mkdir()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        with (state / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "scripts.capture_screenshots",
                    "--serve",
                    str(state),
                    "--port",
                    str(port),
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            try:
                wait_for_server(process, origin)
                capture(origin, images)
                if (state / "network-attempt").exists():
                    raise RuntimeError("Screenshot app attempted an outbound request.")
            except Exception:
                print(
                    (state / "server.log").read_text(encoding="utf-8")[-6000:],
                    file=sys.stderr,
                )
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        args.output.mkdir(parents=True, exist_ok=True)
        for filename in IMAGE_NAMES:
            shutil.copyfile(images / filename, args.output / filename)
            print(args.output / filename)


if __name__ == "__main__":
    main()
