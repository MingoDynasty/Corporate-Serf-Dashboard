"""Open and close runs in the run viewer on the real Run History page.

Install the screenshots dependency group to run these browser regressions.
They take the browser channel the linked-hover regressions take, from
``CSD_HOVER_BROWSER``.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

playwright = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[1]
SCENARIO = "Viewer sample"
OTHER = "Other viewer sample"
LANDING = "Landing sample"
BOTS = "Bots sample"
GRID = "#run-history-list-grid"
COLUMN = "#run-history-chart-column"
GRAPH = "#run-history-graph .js-plotly-plot"
BY_BOT = ".run-viewer-by-bot .run-viewer-bot-grid"

# (seconds from the start, bot, shots, hits). Each bot is one kill, played out
# of name order.
TWO_BOTS = ((20, "Bot B", 50, 30), (40, "Bot A", 50, 25))
ONE_BOT = ((20, "Bot A", 50, 30), (40, "Bot A", 50, 25))
# Many kills: every Bots sample run before the newest takes a second a kill,
# and never kills Fly Bot 2. The newest run takes 1.00 s a kill on Fly Bot,
# 2.00 on Fly Bot 10 and 3.00 on Fly Bot 2.
FLY_TYPICAL = (
    (1, "Fly Bot 10", 10, 4),
    (2, "Fly Bot", 10, 8),
    (3, "Fly Bot 10", 10, 4),
    (4, "Fly Bot", 10, 8),
)
FLY_NEWEST = (
    (2, "Fly Bot 10", 10, 5),
    (3, "Fly Bot", 10, 8),
    (6, "Fly Bot 2", 10, 6),
    (8, "Fly Bot 10", 10, 5),
    (9, "Fly Bot", 10, 9),
)


def _stats_text(
    scenario: str, ended: datetime, score: int, kills: tuple = TWO_BOTS
) -> str:
    start = ended - timedelta(seconds=60)
    return "\n".join(
        [
            "Kill #,Timestamp,Bot,Weapon,TTK,Shots,Hits,Accuracy,Damage Done,"
            "Damage Possible,Efficiency,Cheated,OverShots",
            *(
                f"{number},{start + timedelta(seconds=second):%H:%M:%S}.000,{bot},"
                f"Rifle,0.5s,{shots},{hits},{hits / shots},{hits},{shots},"
                f"{hits / shots},0,0"
                for number, (second, bot, shots, hits) in enumerate(kills, start=1)
            ),
            "",
            "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,"
            "Vert Sens,FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,"
            "ADS Sens,ADS Zoom Scale",
            "Rifle,100,55,55,100,",
            "",
            "Kills:,2",
            "Deaths:,0",
            "Midairs:,0",
            "Reloads:,0",
            f"Score:,{score}.0",
            f"Scenario:,{scenario}",
            "Hash:,0123456789abcdef0123456789abcdef",
            f"Challenge Start:,{start:%H:%M:%S}.000",
            "Pause Count:,0",
            "Pause Duration:,0",
            "",
            "Input Lag:,0",
            "Max FPS (config):,999.0",
            "Sens Scale:,cm/360",
            "Sens Increment:,0.181429",
            "Horiz Sens:,45.0",
            "Vert Sens:,45.0",
            "DPI:,1600",
            "FOV:,103.0",
            "FOVScale:,Overwatch",
            "Hide Gun:,false",
            "Crosshair:,dot.png",
            "Crosshair Scale:,1.0",
            "Resolution:,2560x1440",
            "Resolution Scale:,100.0",
            "",
        ]
    )


def _write(
    stats: Path, scenario: str, ended: datetime, score: int, kills: tuple = TWO_BOTS
) -> str:
    name = f"{scenario} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv"
    (stats / name).write_text(
        _stats_text(scenario, ended, score, kills), encoding="utf-8"
    )
    return name


@pytest.fixture(scope="module")
def viewer_server(tmp_path_factory):
    state = tmp_path_factory.mktemp("viewer-app")
    stats = state / "stats"
    stats.mkdir()
    (state / "data").mkdir()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (state / "config.toml").write_text(
        f'host = "127.0.0.1"\nport = {port}\ndebug = false\n'
        "percentile_warmup_enabled = false\n",
        encoding="utf-8",
    )
    (state / "data" / "settings.json").write_text(
        json.dumps({"schema_version": 1, "stats_dir": str(stats)}),
        encoding="utf-8",
    )
    noon = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    for day in range(20):
        session = noon - timedelta(days=20 - day)
        for minute, scenario, bonus, kills in (
            (0, SCENARIO, 0, TWO_BOTS),
            # The middle run names one bot, so it has no By Bot table.
            (2, SCENARIO, 10, ONE_BOT),
            (4, SCENARIO, 5, TWO_BOTS),
            (6, OTHER, 3, TWO_BOTS),
            (8, LANDING, 0, TWO_BOTS),
        ):
            _write(
                stats,
                scenario,
                session + timedelta(minutes=minute),
                100 + day + bonus,
                kills,
            )
        # A morning session of its own, so the newest session stays the one
        # the tests above open.
        _write(
            stats,
            BOTS,
            session - timedelta(hours=4),
            100 + day,
            FLY_NEWEST if day == 19 else FLY_TYPICAL,
        )
    origin = f"http://127.0.0.1:{port}"
    with (state / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "source/app.py"],
            cwd=ROOT,
            env={**os.environ, "CSD_STATE_DIR": str(state)},
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail((state / "server.log").read_text(encoding="utf-8"))
                try:
                    with urlopen(origin + "/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except URLError, TimeoutError:
                    time.sleep(0.1)
            else:
                pytest.fail("The isolated viewer app did not start.")
            yield origin, stats
        finally:
            process.terminate()
            process.wait(timeout=15)


@pytest.fixture(scope="module")
def viewer_browser():
    with playwright.sync_playwright() as runtime:
        channel = os.environ.get("CSD_HOVER_BROWSER")
        browser = (
            runtime.firefox.launch()
            if channel == "firefox"
            else runtime.chromium.launch(channel=channel)
        )
        yield browser
        browser.close()


def _open_page(browser, origin, scenario=SCENARIO):
    context = browser.new_context(viewport={"width": 1960, "height": 1080})
    context.route(
        "**/*",
        lambda route: (
            route.continue_()
            if route.request.url.startswith(origin + "/")
            else route.abort()
        ),
    )
    page = context.new_page()
    page.on("pageerror", lambda error: print("BROWSER ERROR:", error))
    page.goto(f"{origin}/run-history?scenario={scenario.replace(' ', '%20')}")
    # The reload dates from Dash's first-request pages race, fixed in dash
    # 4.5.0 (decision log, 2026-10-29).
    page.reload()
    wait_for_history(page)
    return context, page


@pytest.fixture
def viewer_page(viewer_browser, viewer_server):
    context, page = _open_page(viewer_browser, viewer_server[0])
    yield page
    context.close()


@pytest.fixture
def bots_page(viewer_browser, viewer_server):
    """Run History on the many-kills scenario, its newest run open."""
    context, page = _open_page(viewer_browser, viewer_server[0], BOTS)
    # Its sessions aren't the newest, so the list starts with them closed.
    page.get_by_role("button", name="Expand all", exact=True).click()
    page.wait_for_function(
        """() => {
        let shown = false;
        window.runHistoryList.api.forEachNodeAfterFilterAndSort(node => {
            shown ||= node.data.kind === 'run' && node.displayed;
        });
        return shown;
    }"""
    )
    row = run_rows(page)[0]
    row_cell(page, row["id"]).click()
    wait_open(page, f"Run {row['n']} ")
    page.wait_for_selector(f"{BY_BOT} .ag-row")
    yield page
    context.close()


def wait_for_history(page):
    page.evaluate("document.fonts.ready")
    page.wait_for_function(f"""() => {{
        const graph = document.querySelector('{GRAPH}');
        const api = window.runHistoryList?.api;
        return graph?.data?.[0]?.ids?.length && api && !api.isDestroyed()
            && api.getDisplayedRowCount() > 0
            && document.querySelector('#run-history-graph .points .point')
            && Math.abs(graph._fullLayout.width - graph.getBoundingClientRect().width) < 2;
    }}""")
    wait_for_chart_quiet(page)


def wait_for_chart_quiet(page):
    page.evaluate(f"""() => {{
        const graph = document.querySelector('{GRAPH}');
        if (!graph.__viewerTestQuietListener) {{
            graph.__viewerTestQuietListener = true;
            graph.on('plotly_afterplot', () => {{
                graph.__viewerTestLastPlot = performance.now();
            }});
        }}
        graph.__viewerTestLastPlot = performance.now();
    }}""")
    page.wait_for_function(f"""() => {{
        const graph = document.querySelector('{GRAPH}');
        return graph && performance.now() - graph.__viewerTestLastPlot >= 500;
    }}""")


def is_open(page) -> bool:
    return page.evaluate(
        f"() => document.querySelector('{COLUMN}').classList.contains('run-viewer-open')"
    )


def wait_open(page, title_part=None):
    page.wait_for_function(
        """([column, part]) => {
            const open = document.querySelector(column).classList.contains(
                'run-viewer-open');
            const title = document.querySelector('.run-viewer-title');
            return open && title && (!part || title.textContent.includes(part));
        }""",
        arg=[COLUMN, title_part],
    )


def wait_closed(page):
    page.wait_for_function(
        f"""() => !document.querySelector('{COLUMN}').classList.contains(
            'run-viewer-open')"""
    )


def focused(page) -> dict:
    return page.evaluate("""() => {
        const active = document.activeElement;
        return {
            close: Boolean(active?.closest('.run-viewer-close')),
            row: active?.closest('.ag-row')?.getAttribute('row-id') ?? null,
            mode: Boolean(active?.closest('#run-history-chart-mode')),
            tag: active?.tagName ?? null,
        };
    }""")


def wait_focus(page, check):
    page.wait_for_function(
        """(check) => {
            const active = document.activeElement;
            if (check.close) return Boolean(active?.closest('.run-viewer-close'));
            if (check.row) return active?.closest('.ag-row')?.getAttribute('row-id')
                === check.row;
            if (check.mode) return Boolean(active?.closest('#run-history-chart-mode'));
            return false;
        }""",
        arg=check,
    )


def run_rows(page, displayed=True) -> list[dict]:
    rows = page.evaluate("""() => {
        const rows = [];
        window.runHistoryList.api.forEachNodeAfterFilterAndSort(node => {
            if (node.data.kind === 'run') rows.push({
                ...node.data, displayed: node.displayed,
            });
        });
        return rows;
    }""")
    return [row for row in rows if row["displayed"] or not displayed]


def row_cell(page, row_id):
    return page.locator(f'{GRID} .ag-row[row-id="{row_id}"] .ag-cell').first


def open_rows(page) -> list[str]:
    """The rows drawn with the open run's mark."""
    return page.evaluate(f"""() => [...new Set([...document.querySelectorAll(
        '{GRID} .ag-row.run-list-row-open'
    )].map(row => row.getAttribute('row-id')))]""")


def marked_rows(page) -> list[str]:
    """The rows whose data carries the mark, drawn or not."""
    return page.evaluate("""() => {
        const ids = [];
        window.runHistoryList.api.forEachNode(node => {
            if (node.data.open === true) ids.push(node.id);
        });
        return ids;
    }""")


def show_all_runs(page):
    """Under All scenarios, open every visit of the newest session."""
    page.get_by_text("All scenarios", exact=True).click()
    page.wait_for_function("() => window.runHistoryList.view === 'all'")
    page.get_by_role("button", name="Show all runs", exact=True).first.click()


def graph_state(page) -> dict:
    return page.evaluate(f"""() => {{
        const graph = document.querySelector('{GRAPH}');
        return {{
            visible: graph.getClientRects().length > 0,
            range: graph._fullLayout.xaxis.range.slice(),
            yrange: graph._fullLayout.yaxis.range.slice(),
            width: graph._fullLayout.width,
            box: graph.getBoundingClientRect().width,
            mode: document.querySelector('#run-history-chart-mode input:checked')?.value,
        }};
    }}""")


def point_position(page, run_id):
    position = page.evaluate(
        """({graph, id}) => {
        const plot = document.querySelector(graph);
        for (const group of plot.querySelectorAll('.trace.scatter')) {
            const trace = group.__data__?.[0]?.trace;
            if (trace?.name !== 'Run data point') continue;
            const point = [...group.querySelectorAll('.points .point')]
                .find(point => point.__data__.id === id);
            if (point) {
                const box = point.getBoundingClientRect();
                return {x: box.x + box.width / 2, y: box.y + box.height / 2};
            }
        }
        return null;
    }""",
        {"graph": GRAPH, "id": run_id},
    )
    assert position is not None, f"Missing chart marker for {run_id}"
    return position


def click_point(page, run_id):
    position = point_position(page, run_id)
    page.mouse.move(position["x"], position["y"])
    page.wait_for_function(
        "() => document.querySelector('#run-history-graph .run-history-graph-pointer')"
    )
    page.mouse.click(position["x"], position["y"])


def has_by_bot(page) -> bool:
    return page.evaluate(f"() => document.querySelector('{BY_BOT}') !== null")


def by_bot_rows(page) -> list[str]:
    """The bots in By Bot's rows, top to bottom."""
    return page.evaluate(f"""() => [...document.querySelectorAll(
        '{BY_BOT} .ag-center-cols-container .ag-row'
    )].sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)
        .map(row => row.querySelector('[col-id="bot"]').textContent)""")


def wait_by_bot_rows(page, bots):
    page.wait_for_function(
        f"""(bots) => JSON.stringify([...document.querySelectorAll(
            '{BY_BOT} .ag-center-cols-container .ag-row'
        )].sort((a, b) => a.getBoundingClientRect().top
            - b.getBoundingClientRect().top)
            .map(row => row.querySelector('[col-id="bot"]').textContent))
            === JSON.stringify(bots)""",
        arg=bots,
    )


def wait_by_bot_sorts(page, sorts: dict[str, str]):
    """Wait until the By Bot headers whose ``aria-sort`` names a direction are these."""
    page.wait_for_function(
        f"""(sorts) => JSON.stringify(Object.fromEntries([...document.querySelectorAll(
            '{BY_BOT} .ag-header-cell[aria-sort]'
        )].map(header => [header.getAttribute('col-id'),
            header.getAttribute('aria-sort')])
            .filter(([, sort]) => sort !== 'none'))) === JSON.stringify(sorts)""",
        arg=sorts,
    )


def by_bot_header(page, column):
    return page.locator(
        f'{BY_BOT} .ag-header-cell[col-id="{column}"] .ag-header-cell-label'
    )


def by_bot_cell(page, row_index, column):
    return page.locator(
        f'{BY_BOT} .ag-row[row-index="{row_index}"] .ag-cell[col-id="{column}"]'
    )


def chart_requests(page) -> list[str]:
    """Record every request that writes the chart, from now on."""
    seen: list[str] = []
    page.on(
        "request",
        lambda request: (
            seen.append(request.url)
            if "run-history-cached-plot" in (request.post_data or "")
            else None
        ),
    )
    return seen


def test_a_row_click_opens_its_run_and_close_brings_the_chart_back_as_left(
    viewer_page,
):
    page = viewer_page
    page.evaluate(f"""() => {{
        const graph = document.querySelector('{GRAPH}');
        const [start, end] = graph._fullLayout.xaxis.range;
        return window.Plotly.relayout(graph, {{
            'xaxis.range': [start + (end - start) / 4, end - (end - start) / 4],
        }});
    }}""")
    wait_for_chart_quiet(page)
    before = graph_state(page)
    writes = chart_requests(page)
    row = run_rows(page)[1]

    row_cell(page, row["id"]).click()

    wait_open(page)
    wait_focus(page, {"close": True})
    assert not graph_state(page)["visible"]
    assert open_rows(page) == [row["id"]]
    assert (
        page.locator(".run-viewer-title")
        .text_content()
        .startswith(f"Run {row['n']} · ")
    )
    assert (
        page.locator(".run-viewer-kicker")
        .text_content()
        .startswith(f"{SCENARIO} · ended ")
    )

    page.get_by_role("button", name="Close", exact=True).click()

    wait_closed(page)
    wait_focus(page, {"row": row["id"]})
    wait_for_chart_quiet(page)
    after = graph_state(page)
    assert after["visible"]
    assert after["range"] == before["range"]
    assert after["yrange"] == before["yrange"]
    assert abs(after["width"] - before["width"]) < 2
    assert open_rows(page) == []
    assert writes == []


def test_the_chart_takes_a_new_width_set_while_it_was_hidden(viewer_page):
    page = viewer_page
    before = graph_state(page)
    row_cell(page, run_rows(page)[0]["id"]).click()
    wait_open(page)

    page.set_viewport_size({"width": 1500, "height": 1000})
    page.keyboard.press("Escape")

    wait_closed(page)
    page.wait_for_function(f"""() => {{
        const graph = document.querySelector('{GRAPH}');
        return Math.abs(graph._fullLayout.width - graph.getBoundingClientRect().width) < 2;
    }}""")
    after = graph_state(page)
    assert after["width"] < before["width"] - 300
    assert abs(after["width"] - after["box"]) < 2


@pytest.mark.parametrize("key", ["Enter", " "])
def test_enter_or_space_on_a_run_row_opens_it_and_esc_returns_to_the_row(
    viewer_page, key
):
    page = viewer_page
    row = run_rows(page)[0]
    page.evaluate(
        """(id) => {
        const api = window.runHistoryList.api;
        api.setFocusedCell(api.getRowNode(id).rowIndex, api.getAllDisplayedColumns()[0]);
    }""",
        row["id"],
    )
    wait_focus(page, {"row": row["id"]})

    page.keyboard.press(key)

    wait_open(page)
    wait_focus(page, {"close": True})

    page.keyboard.press("Escape")

    wait_closed(page)
    wait_focus(page, {"row": row["id"]})


def test_another_row_switches_the_run_and_keeps_focus_on_that_row(viewer_page):
    page = viewer_page
    first, second = run_rows(page)[:2]
    row_cell(page, first["id"]).click()
    wait_open(page, f"Run {first['n']} ")
    wait_focus(page, {"close": True})

    row_cell(page, second["id"]).click()

    wait_open(page, f"Run {second['n']} ")
    assert focused(page)["row"] == second["id"]
    assert open_rows(page) == [second["id"]]
    # The mark follows the run into the other view, and is drawn once its
    # visit is open.
    show_all_runs(page)
    assert marked_rows(page) == [second["id"]]
    playwright.expect(
        page.locator(f'{GRID} .ag-row[row-id="{second["id"]}"]')
    ).to_have_class(re.compile(r"\brun-list-row-open\b"))
    assert is_open(page)


def test_everything_recorded_stays_open_through_a_switch_and_starts_closed(
    viewer_page,
):
    page = viewer_page
    first, second, third = run_rows(page)[:3]
    recorded = "() => document.querySelector('.run-viewer-recorded').open"
    row_cell(page, first["id"]).click()
    wait_open(page, f"Run {first['n']} ")
    assert has_by_bot(page)
    page.locator(".run-viewer-summary").click()

    # The middle run names one bot, so it has no By Bot table.
    row_cell(page, second["id"]).click()

    wait_open(page, f"Run {second['n']} ")
    assert not has_by_bot(page)
    assert page.evaluate(recorded)

    row_cell(page, third["id"]).click()

    wait_open(page, f"Run {third['n']} ")
    assert has_by_bot(page)
    assert page.evaluate(recorded)

    page.keyboard.press("Escape")
    wait_closed(page)
    row_cell(page, first["id"]).click()

    wait_open(page, f"Run {first['n']} ")
    assert not page.evaluate(recorded)


def test_a_point_click_opens_its_run_and_close_returns_to_the_chart_mode(
    viewer_page,
):
    page = viewer_page
    row = run_rows(page)[2]
    run_id = row["id"][2:]

    click_point(page, run_id)

    wait_open(page, f"Run {row['n']} ")
    wait_focus(page, {"close": True})
    page.keyboard.press("Escape")
    wait_closed(page)
    wait_focus(page, {"mode": True})
    wait_for_chart_quiet(page)

    # The same point again: Dash would drop a repeated identical clickData.
    click_point(page, run_id)

    wait_open(page, f"Run {row['n']} ")


def test_esc_leaves_the_run_open_in_a_text_field_and_under_a_menu(viewer_page):
    page = viewer_page
    row = run_rows(page)[0]
    row_cell(page, row["id"]).click()
    wait_open(page)
    wait_focus(page, {"close": True})

    field = page.get_by_role("textbox", name="Selected scenario")
    field.click()
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    assert is_open(page)

    page.get_by_role("button", name="Columns", exact=True).click()
    # Mantine's popover closes on Escape only from inside its dropdown, and
    # the button reads expanded before the focus trap has moved focus there.
    page.wait_for_function(
        "() => document.activeElement?.closest('.mantine-Popover-dropdown')"
    )
    page.keyboard.press("Escape")
    page.wait_for_function(
        "() => !document.querySelector('[aria-haspopup][aria-expanded=\"true\"]')"
    )
    page.wait_for_timeout(300)
    assert is_open(page)

    # With nothing open and no text field focused, Esc closes the run.
    page.keyboard.press("Escape")
    wait_closed(page)
    wait_focus(page, {"row": row["id"]})


def test_esc_leaves_the_run_open_under_the_note_dialog(viewer_page):
    page = viewer_page
    row_cell(page, run_rows(page)[0]["id"]).click()
    wait_open(page)
    page.get_by_text("Add a scenario note", exact=True).click()
    editor = page.get_by_role("textbox", name="Scenario note")
    editor.fill("Aim lower")
    page.get_by_role("link", name="Home", exact=True).click()
    dialog = page.get_by_role("dialog")
    playwright.expect(dialog).to_be_visible()

    page.keyboard.press("Escape")

    playwright.expect(dialog).to_be_hidden()
    page.wait_for_timeout(300)
    assert is_open(page)


def test_a_change_of_scenario_closes_the_run(viewer_page):
    page = viewer_page
    show_all_runs(page)
    row = next(row for row in run_rows(page) if row["sel"])
    row_cell(page, row["id"]).click()
    wait_open(page)

    page.get_by_role("button", name=f"Show {OTHER}", exact=True).first.click()

    wait_closed(page)
    page.wait_for_function(
        """(other) => document.querySelector('#run-history-scenario').value === other""",
        arg=OTHER,
    )
    assert focused(page)["tag"] == "BUTTON"
    assert open_rows(page) == []


def test_a_run_of_another_scenario_opens_without_changing_the_selection(
    viewer_page,
):
    page = viewer_page
    show_all_runs(page)
    other = next(row for row in run_rows(page) if not row["sel"])

    row_cell(page, other["id"]).click()

    wait_open(page)
    kicker = page.locator(".run-viewer-kicker").text_content()
    assert kicker.split(" · ended ")[0] in {OTHER, LANDING}
    assert page.locator("#run-history-scenario").input_value() == SCENARIO

    page.keyboard.press("Escape")

    wait_closed(page)
    wait_for_chart_quiet(page)
    assert (
        page.evaluate(f"() => document.querySelector('{GRAPH}')._fullLayout.title.text")
        == SCENARIO
    )


# --- By Bot --------------------------------------------------------------------

NAME_ORDER = ["Fly Bot", "Fly Bot 2", "Fly Bot 10"]


@pytest.mark.parametrize(
    ("column", "ascending", "descending"),
    [
        ("bot", NAME_ORDER, NAME_ORDER[::-1]),
        (
            "time_per_kill",
            ["Fly Bot", "Fly Bot 10", "Fly Bot 2"],
            ["Fly Bot 2", "Fly Bot 10", "Fly Bot"],
        ),
        # No typical run names Fly Bot 2: its empty cell goes last both ways.
        (
            "time_per_kill_difference",
            ["Fly Bot", "Fly Bot 10", "Fly Bot 2"],
            ["Fly Bot 10", "Fly Bot", "Fly Bot 2"],
        ),
    ],
)
def test_a_by_bot_header_click_sorts_up_then_down_then_back(
    bots_page, column, ascending, descending
):
    page = bots_page
    # Many kills a bot start in name order, numbers read as numbers.
    assert by_bot_rows(page) == NAME_ORDER
    wait_by_bot_sorts(page, {})
    header = by_bot_header(page, column)

    header.click()
    wait_by_bot_rows(page, ascending)
    wait_by_bot_sorts(page, {column: "ascending"})

    header.click()
    wait_by_bot_rows(page, descending)
    wait_by_bot_sorts(page, {column: "descending"})

    header.click()
    wait_by_bot_rows(page, NAME_ORDER)
    wait_by_bot_sorts(page, {})


def test_enter_on_a_focused_by_bot_header_sorts_up_then_down_then_back(bots_page):
    page = bots_page
    page.evaluate(
        """(selector) => {
        const grid = document.querySelector(selector);
        window.dash_ag_grid.getApi(grid.id).setFocusedHeader('time_per_kill');
    }""",
        BY_BOT,
    )
    page.wait_for_function(
        "() => document.activeElement?.closest('.ag-header-cell')"
        "?.getAttribute('col-id') === 'time_per_kill'"
    )

    page.keyboard.press("Enter")
    wait_by_bot_rows(page, ["Fly Bot", "Fly Bot 10", "Fly Bot 2"])
    wait_by_bot_sorts(page, {"time_per_kill": "ascending"})

    page.keyboard.press("Enter")
    wait_by_bot_rows(page, ["Fly Bot 2", "Fly Bot 10", "Fly Bot"])
    wait_by_bot_sorts(page, {"time_per_kill": "descending"})

    page.keyboard.press("Enter")
    wait_by_bot_rows(page, NAME_ORDER)
    wait_by_bot_sorts(page, {})
    assert is_open(page)


def test_by_bot_marks_the_hovered_row_and_colors_each_difference(bots_page):
    page = bots_page
    # Rows are indexed in their default order: Fly Bot, Fly Bot 2, Fly Bot 10.
    by_bot_cell(page, 2, "bot").hover()

    playwright.expect(
        page.locator(f'{BY_BOT} .ag-row[row-index="2"]').first
    ).to_have_class(re.compile(r"\bag-row-hover\b"))
    slower = by_bot_cell(page, 2, "time_per_kill_difference")
    playwright.expect(slower).to_have_text("+1.00 s")
    playwright.expect(slower).to_have_class(re.compile(r"\brun-viewer-worse\b"))
    even = by_bot_cell(page, 0, "time_per_kill_difference")
    playwright.expect(even).to_have_text("0.00 s")
    playwright.expect(even).to_have_class(re.compile(r"\brun-viewer-even\b"))
    playwright.expect(by_bot_cell(page, 1, "time_per_kill_difference")).to_have_text("")
    # The typical's hover is the browser's own title.
    title = by_bot_cell(page, 0, "time_per_kill_typical").evaluate(
        "cell => cell.closest('[title]')?.title"
        " ?? cell.querySelector('[title]')?.title ?? null"
    )
    assert title == "Median of your 19 typical runs"


def test_one_kill_each_starts_in_play_order_and_a_switch_starts_over(viewer_page):
    page = viewer_page
    first, _second, third = run_rows(page)[:3]
    row_cell(page, first["id"]).click()
    wait_open(page, f"Run {first['n']} ")
    page.wait_for_selector(f"{BY_BOT} .ag-row")
    # Bot B is killed first.
    assert by_bot_rows(page) == ["Bot B", "Bot A"]
    header = by_bot_header(page, "bot")
    header.click()
    wait_by_bot_rows(page, ["Bot A", "Bot B"])
    header.click()
    header.click()
    wait_by_bot_rows(page, ["Bot B", "Bot A"])
    wait_by_bot_sorts(page, {})
    header.click()
    wait_by_bot_rows(page, ["Bot A", "Bot B"])

    row_cell(page, third["id"]).click()

    # Each run's table starts in its own default order.
    wait_open(page, f"Run {third['n']} ")
    wait_by_bot_rows(page, ["Bot B", "Bot A"])
    wait_by_bot_sorts(page, {})


def test_a_run_that_lands_while_one_is_open_joins_the_list_and_the_run_stays(
    viewer_browser, viewer_server
):
    # Last in the module: the run it lands starts a newer session, which the
    # tests above don't expect.
    origin, stats = viewer_server
    context, page = _open_page(viewer_browser, origin, LANDING)
    try:
        row = run_rows(page)[0]
        row_cell(page, row["id"]).click()
        wait_open(page, f"Run {row['n']} ")
        title = page.locator(".run-viewer-title").text_content()
        newest = page.evaluate("() => window.runHistoryList.newestRun")

        landed = _write(stats, LANDING, datetime.now().replace(microsecond=0), 500)

        page.wait_for_function(
            "(newest) => window.runHistoryList.newestRun !== newest",
            arg=newest,
            timeout=30_000,
        )
        assert page.evaluate(
            "(id) => Boolean(window.runHistoryList.api.getRowNode('r:' + id))", landed
        )
        assert is_open(page)
        assert page.locator(".run-viewer-title").text_content() == title
        assert open_rows(page) == [row["id"]]

        page.keyboard.press("Escape")

        wait_closed(page)
        # Redrawn while hidden, the chart comes back with the run and at its
        # own width.
        page.wait_for_function(
            "([graph, id]) => document.querySelector(graph).data[0].ids.includes(id)",
            arg=[GRAPH, landed],
        )
        page.wait_for_function(f"""() => {{
            const graph = document.querySelector('{GRAPH}');
            return Math.abs(graph._fullLayout.width
                - graph.getBoundingClientRect().width) < 2;
        }}""")
    finally:
        context.close()
