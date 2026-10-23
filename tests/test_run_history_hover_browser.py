"""Exercise linked hover against the real graph and virtualized run list.

Install the screenshots dependency group to run these browser regressions.
"""

import json
import os
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
SCENARIO = "Hover sample"
GRID = "#run-history-list-grid"


@pytest.fixture(scope="module")
def hover_server(tmp_path_factory):
    state = tmp_path_factory.mktemp("hover-app")
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
    for day in range(34):
        for minute, scenario, bonus in (
            (0, SCENARIO, 0),
            (2, "Other hover sample", 3),
            (4, SCENARIO, 10),
            (6, SCENARIO, 5),
        ):
            ended = noon - timedelta(days=34 - day) + timedelta(minutes=minute)
            name = f"{scenario} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv"
            (stats / name).write_text(
                f"Score:,{100 + day * 2 + bonus}\nScenario:,{scenario}\n"
                "Sens Scale:,cm/360\nHoriz Sens:,40.8\n"
                "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,"
                "Vert Sens,FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,"
                "ADS Sens,ADS Zoom Scale\nRifle,100,70,0,0\n",
                encoding="utf-8",
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
                pytest.fail("The isolated hover app did not start.")
            yield origin
        finally:
            process.terminate()
            process.wait(timeout=15)


@pytest.fixture(scope="module")
def hover_browser():
    with playwright.sync_playwright() as runtime:
        channel = os.environ.get("CSD_HOVER_BROWSER")
        browser = (
            runtime.firefox.launch()
            if channel == "firefox"
            else runtime.chromium.launch(channel=channel)
        )
        yield browser
        browser.close()


@pytest.fixture
def hover_page(hover_browser, hover_server):
    context = hover_browser.new_context(viewport={"width": 1960, "height": 1080})
    context.route(
        "**/*",
        lambda route: (
            route.continue_()
            if route.request.url.startswith(hover_server + "/")
            else route.abort()
        ),
    )
    page = context.new_page()
    page.on("pageerror", lambda error: print("BROWSER ERROR:", error))
    page.goto(hover_server + "/run-history?scenario=Hover%20sample")
    # The known first-load Dash pages race heals on reload.
    page.reload()
    wait_for_history(page)
    yield page
    context.close()


def wait_for_history(page):
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_function("""() => {
        const graph = document.querySelector('#run-history-graph .js-plotly-plot');
        const api = window.runHistoryList?.api;
        return graph?.data?.[0]?.ids?.length && api && !api.isDestroyed()
            && api.getDisplayedRowCount() > 0
            && document.querySelector('#run-history-graph .points .point')
            && Math.abs(graph._fullLayout.width - graph.getBoundingClientRect().width) < 2;
    }""")

    wait_for_chart_quiet(page)


def wait_for_chart_quiet(page):
    # Settling redraws clear hover by contract, so the first markers are not
    # enough to start a pointer assertion. Restart the quiet interval on each draw.
    page.evaluate("""() => {
        const graph = document.querySelector('#run-history-graph .js-plotly-plot');
        if (!graph.__hoverTestQuietListener) {
            graph.__hoverTestQuietListener = true;
            graph.on('plotly_afterplot', () => {
                graph.__hoverTestLastPlot = performance.now();
            });
        }
        graph.__hoverTestLastPlot = performance.now();
    }""")
    page.wait_for_function("""() => {
        const graph = document.querySelector('#run-history-graph .js-plotly-plot');
        return graph && performance.now() - graph.__hoverTestLastPlot >= 500;
    }""")


def run_rows(page):
    return page.evaluate("""() => {
        const rows = [];
        window.runHistoryList.api.forEachNode(node => {
            if (node.data.kind === 'run') rows.push({
                ...node.data, displayed: node.displayed
            });
        });
        return rows;
    }""")


def linked_rows(page):
    return page.evaluate("""() => [...new Set([...document.querySelectorAll(
        '#run-history-list-grid .run-list-row-linked'
    )].map(row => row.closest('.ag-row').getAttribute('row-id')))]""")


def hover_point(page, row, *, star=False):
    position = page.evaluate(
        """({id, star}) => {
        const graph = document.querySelector('#run-history-graph .js-plotly-plot');
        for (const group of graph.querySelectorAll('.trace.scatter')) {
            const trace = group.__data__?.[0]?.trace;
            if (trace?.name !== (star ? 'New PB' : 'Run data point')) continue;
            const point = [...group.querySelectorAll('.points .point')]
                .find(point => point.__data__.id === id);
            if (point) {
                const box = point.getBoundingClientRect();
                return {x: box.x + box.width / 2, y: box.y + box.height / 2};
            }
        }
        return null;
    }""",
        {"id": row["id"][2:], "star": star},
    )
    assert position is not None, f"Missing chart marker for {row['id']}"
    page.mouse.move(position["x"], position["y"])


def list_snapshot(page):
    return page.evaluate("""() => ({
        open: [...window.runHistoryList.views[window.runHistoryList.view].open].sort(),
        scroll: document.querySelector(
            '#run-history-list-grid .ag-body-viewport').scrollTop,
        limit: window.runHistoryList.sessionLimit,
        view: window.runHistoryList.view,
        focus: document.activeElement?.closest('.ag-row')?.getAttribute('row-id'),
        x: document.querySelector('#run-history-graph .js-plotly-plot')._fullLayout.xaxis.range,
        y: document.querySelector('#run-history-graph .js-plotly-plot')._fullLayout.yaxis.range,
    })""")


@pytest.mark.parametrize(
    "mode", ["Score vs Run", "Score vs Time", "Score vs Sensitivity"]
)
def test_chart_hover_links_the_exact_visible_run_without_requests_or_movement(
    hover_page,
    mode,
):
    page = hover_page
    page.get_by_text(mode, exact=True).click()
    title = {
        "Score vs Run": "Run",
        "Score vs Time": "Date",
        "Score vs Sensitivity": "Sensitivity",
    }[mode]
    page.wait_for_function(
        "title => document.querySelector('#run-history-graph .js-plotly-plot')._fullLayout.xaxis.title.text === title",
        arg=title,
    )
    wait_for_chart_quiet(page)
    row = next(row for row in run_rows(page) if row["displayed"])
    before = list_snapshot(page)
    requests = []
    page.on(
        "request",
        lambda request: (
            requests.append(request.post_data_json)
            if "_dash-update-component" in request.url
            else None
        ),
    )
    hover_point(page, row)
    playwright.expect(page.locator(".ag-row.run-list-row-linked")).to_have_count(1)
    assert linked_rows(page) == [row["id"]]
    assert list_snapshot(page) == before
    page.mouse.move(0, 0)
    playwright.expect(page.locator(".run-list-row-linked")).to_have_count(0)
    # Periodic polling may run during a hover; it is independent of the pointer.
    assert all(
        all(prop.endswith(".n_intervals") for prop in request.get("changedPropIds", []))
        for request in requests
    )


def test_collapsed_run_highlights_its_pinned_session_without_opening_it(hover_page):
    page = hover_page
    row = next(row for row in run_rows(page) if row["displayed"])
    toggle = page.locator(f'{GRID} .ag-floating-top button[data-part="toggle"]')
    toggle.click()
    playwright.expect(toggle).to_have_attribute("aria-expanded", "false")
    page.wait_for_function(
        "id => !window.runHistoryList.api.getRowNode(id).displayed", arg=row["id"]
    )
    before = list_snapshot(page)
    hover_point(page, row)
    playwright.expect(
        page.locator(".run-list-session.run-list-row-linked")
    ).to_have_count(1)
    assert linked_rows(page) == [row["sid"]]
    assert list_snapshot(page) == before
    page.mouse.move(0, 0)
    playwright.expect(page.locator(".run-list-row-linked")).to_have_count(0)


@pytest.mark.parametrize(
    ("scheme", "outline"),
    [("light", "rgb(134, 46, 156)"), ("dark", "rgb(229, 153, 247)")],
)
def test_list_hover_emphasizes_its_marker_and_clears_when_leaving(
    hover_page, scheme, outline
):
    page = hover_page
    if page.locator("html").get_attribute("data-mantine-color-scheme") != scheme:
        page.get_by_label("Switch between light and dark mode", exact=True).click()
    playwright.expect(page.locator("html")).to_have_attribute(
        "data-mantine-color-scheme", scheme
    )
    wait_for_history(page)
    row = next(row for row in run_rows(page) if row["displayed"])
    before = list_snapshot(page)
    page.locator(
        f'{GRID} .ag-row[row-id="{row["id"]}"] .ag-cell[col-id="score"]'
    ).hover()
    playwright.expect(page.locator(".run-history-point-linked")).not_to_have_count(0)
    ids = page.locator(".run-history-point-linked").evaluate_all(
        "points => [...new Set(points.map(point => point.__data__.id))]"
    )
    assert ids == [row["id"][2:]]
    playwright.expect(page.locator(".run-history-point-linked").first).to_have_css(
        "stroke", outline
    )
    assert list_snapshot(page) == before
    page.mouse.move(0, 0)
    playwright.expect(page.locator(".run-history-point-linked")).to_have_count(0)


def test_star_hover_still_links_when_ordinary_dots_are_hidden(hover_page):
    page = hover_page
    row = next(row for row in run_rows(page) if row["displayed"] and row["new_pb"])
    page.evaluate("""() => {
        const gd = document.querySelector('#run-history-graph .js-plotly-plot');
        return Plotly.restyle(gd, {visible: 'legendonly'}, [0]);
    }""")
    wait_for_chart_quiet(page)
    hover_point(page, row, star=True)
    playwright.expect(page.locator(".ag-row.run-list-row-linked")).to_have_count(1)
    assert linked_rows(page) == [row["id"]]
    playwright.expect(page.locator(".hoverlayer")).to_contain_text(row["score"])


def test_chart_hover_does_not_load_sessions_or_scroll_to_an_offscreen_match(hover_page):
    page = hover_page
    rows = run_rows(page)
    old = rows[-1]
    page.get_by_role("button", name="Expand all", exact=True).click()
    playwright.expect(
        page.get_by_role("button", name="Collapse all", exact=True)
    ).to_be_visible()
    before = list_snapshot(page)
    hover_point(page, old)
    assert list_snapshot(page) == before
    # Runs older than the first 30 sessions remain plotted but absent from the grid.
    missing = page.evaluate("""() => {
        const gd = document.querySelector('#run-history-graph .js-plotly-plot');
        return gd.data[0].ids.find(id => !window.runHistoryList.api.getRowNode('r:' + id));
    }""")
    assert missing is not None
    hover_point(page, {"id": "r:" + missing})
    assert linked_rows(page) == []
    assert list_snapshot(page) == before


def test_all_scenarios_collapsed_visit_falls_back_to_session(hover_page):
    page = hover_page
    page.get_by_text("All scenarios", exact=True).click()
    page.wait_for_function("window.runHistoryList.view === 'all'")
    row = next(row for row in run_rows(page) if row.get("sel") and row["displayed"])
    toggle = page.locator(
        f'{GRID} .ag-row[row-id="{row["vid"]}"] button[data-part="toggle"]'
    )
    toggle.click()
    playwright.expect(toggle).to_have_attribute("aria-expanded", "false")
    page.wait_for_function(
        "id => !window.runHistoryList.api.getRowNode(id).displayed", arg=row["id"]
    )
    before = list_snapshot(page)
    hover_point(page, row)
    playwright.expect(
        page.locator(".run-list-session.run-list-row-linked")
    ).to_have_count(1)
    assert linked_rows(page) == [row["sid"]]
    assert list_snapshot(page) == before


def test_plot_redraw_and_page_remount_clear_old_highlights(hover_page, hover_server):
    page = hover_page
    row = next(row for row in run_rows(page) if row["displayed"])
    hover_point(page, row)
    playwright.expect(page.locator(".run-list-row-linked")).to_have_count(1)
    page.evaluate("""() => Plotly.restyle(document.querySelector(
        '#run-history-graph .js-plotly-plot'), {'marker.size': 10}, [0])""")
    wait_for_chart_quiet(page)
    playwright.expect(page.locator(".run-list-row-linked")).to_have_count(0)
    page.mouse.move(0, 0)
    page.goto(hover_server + "/")
    page.goto(hover_server + "/run-history?scenario=Hover%20sample")
    wait_for_history(page)
    row = next(row for row in run_rows(page) if row["displayed"])
    hover_point(page, row)
    playwright.expect(page.locator(".ag-row.run-list-row-linked")).to_have_count(1)
    assert linked_rows(page) == [row["id"]]


def test_hover_preserves_the_focused_run_cell(hover_page):
    page = hover_page
    rows = [row for row in run_rows(page) if row["displayed"]]
    cell = page.locator(
        f'{GRID} .ag-row[row-id="{rows[0]["id"]}"] .ag-cell[col-id="score"]'
    )
    # The grid can deliver the click's mouse-over/out after the chart hover.
    # Those older events must neither replace nor clear the new linked run.
    cell.click()
    before = list_snapshot(page)
    hover_point(page, rows[1])
    playwright.expect(page.locator(".ag-row.run-list-row-linked")).to_have_count(1)
    assert list_snapshot(page) == before
    assert linked_rows(page) == [rows[1]["id"]]
    page.mouse.move(0, 0)
    playwright.expect(page.locator(".run-history-point-linked")).to_have_count(0)


def test_summary_hover_clears_a_previously_linked_run(hover_page):
    page = hover_page
    row = next(row for row in run_rows(page) if row["displayed"])
    hover_point(page, row)
    playwright.expect(page.locator(".run-list-row-linked")).to_have_count(1)
    page.evaluate("""() => {
        const graph = document.querySelector('#run-history-graph .js-plotly-plot');
        const summary = graph.data.find(trace => trace.name === 'Typical score');
        graph.emit('plotly_hover', {points: [{data: summary, pointNumber: 0}]});
    }""")
    playwright.expect(page.locator(".run-list-row-linked")).to_have_count(0)
    playwright.expect(page.locator(".run-history-point-linked")).to_have_count(0)
