"""Refresh README images from an isolated app with synthetic sample data.

Run with ``uv run --group screenshots python -m scripts.capture_screenshots``.
"""

import argparse
import json
import math
import os
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
SCENARIO = "VT Controlsphere Viscose"
PLAYLIST_CODE = "KovaaKsPeakingNarrowImpact"
USERNAME = "Sample player"
PLAYLIST_NAMES = (
    "Voltaic Novice Benchmarks S5.5",
    "Voltaic Intermediate Benchmarks S5.5",
    "Viscose Benchmark S2 - Easier",
    "Viscose Benchmark S2 - Medium",
    "Viscose Benchmark S2 - Hard",
    "Viscose Benchmark S2 - Expert",
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
            (ROOT / "resources" / "benchmarks" / f"{name}.json").read_text(
                encoding="utf-8"
            )
        )
        for name in PLAYLIST_NAMES
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
    scenarios = {
        item["name"]: item for playlist in playlists for item in playlist["scenarios"]
    }
    samples = []
    for index, (name, scenario) in enumerate(sorted(scenarios.items())):
        ranks = scenario["ranks"]
        rank_index = (
            min(4, len(ranks) - 1)
            if name == SCENARIO
            else 1 + index % min(6, len(ranks) - 1)
        )
        target = ranks[rank_index]["threshold"] * 1.04
        count = 96 if name == SCENARIO else 24
        best = 0.0
        for run in range(count):
            session, in_session = divmod(run, 12)
            ended = NOW - timedelta(
                days=(count // 12 - session - 1) * 3
                if name == SCENARIO
                else 1 + (index // 3) * 2 + (1 - session),
                hours=2 if name == SCENARIO else 4 + index % 3 * 3,
                minutes=(11 - in_session) * 2 + index % 15,
            )
            progress = run / (count - 1)
            score = round(
                target * (0.66 + 0.28 * progress + 0.055 * math.sin(run * 1.7 + index)),
                2,
            )
            best = max(best, score)
            start = ended - timedelta(seconds=60)
            content = (
                f"Score:,{score}\nSens Scale:,cm/360\nHoriz Sens:,{40 + run % 3 * 5}\n"
                f"Scenario:,{name}\nChallenge Start:,{start:%H:%M:%S}.000\n"
                "Pause Duration:,0\nReloads:,0\nFOV:,103\nFOVScale:,Overwatch\n"
                f"Avg FPS:,240\n{WEAPON_HEADER}\n"
                f"Rifle,6000,{round(6000 * (0.48 + 0.12 * progress))},0,0\n"
            )
            (
                stats / f"{name} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv"
            ).write_text(content, encoding="utf-8")
        samples.append(
            {
                "name": name,
                "leaderboard_id": scenario["leaderboard_id"],
                "score": best,
                "rank": 1200 + index * 137,
                "total": 18000 + index * 311,
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
            "Keep the movement smooth. Relax the grip and follow the target "
            "through direction changes.",
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


def capture(origin: str, destination: Path) -> None:
    """Capture the three rendered pages after their actual content is ready."""
    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
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
            + urlencode({"scenario": SCENARIO, "playlist_code": PLAYLIST_CODE})
        )
        page.reload()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        responses = []
        page.on(
            "response",
            lambda response: (
                responses.append(response.status) if response.status >= 400 else None
            ),
        )
        expect(page.locator("#run-history-scenario")).to_have_value(SCENARIO)
        page.wait_for_function("""() => {
            const graph = document.querySelector('#run-history-graph .js-plotly-plot');
            return graph && graph.data && graph.data.some(trace => trace.x?.length > 20)
                && graph.data.some(trace => trace.name === 'Latest run' && trace.visible !== false);
        }""")
        expect(
            page.locator("#run-history-list-grid .run-list-row-latest").first
        ).to_be_visible()
        expect(
            page.get_by_text("Keep the movement smooth.", exact=False)
        ).to_be_visible()
        page.mouse.move(0, 0)
        page.evaluate("document.fonts.ready")
        save_stable_screenshot(page, destination / IMAGE_NAMES[0])
        for path, grid, filename in (
            ("/playlists", "playlists-overview-grid", IMAGE_NAMES[1]),
            (f"/playlists/{PLAYLIST_CODE}", "playlist-scenarios-grid", IMAGE_NAMES[2]),
        ):
            page.set_viewport_size(
                {
                    "width": 2400 if grid == "playlist-scenarios-grid" else 1920,
                    "height": 1080,
                }
            )
            page.goto(origin + path)
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
            page.mouse.move(0, 0)
            page.evaluate("document.fonts.ready")
            main_box = page.locator("main").bounding_box()
            rows = page.locator(f"#{grid} .ag-center-cols-container .ag-row")
            last_row = rows.nth(min(11, rows.count() - 1)).bounding_box()
            assert main_box and last_row
            # Keep the table headers and representative rows, without the
            # empty grid viewport below a short playlist overview.
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
