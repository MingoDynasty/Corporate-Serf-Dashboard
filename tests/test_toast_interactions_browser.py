"""Keep Mantine 8's toast interactions on the real app's toast container.

Mantine 9 dismisses a toast on a sideways drag or scroll, and pauses every
toast while any one is hovered. The app turns all three off, and only a browser
can see them. Install the screenshots dependency group to run these; they take
the browser channel the linked-hover regressions take, from
``CSD_HOVER_BROWSER``.
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

playwright = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[1]
CONTAINER_ID = "notification-container"
STAYS = "Stays until closed"
TIMED = "Closes on its own"


@pytest.fixture(scope="module")
def toast_server(tmp_path_factory):
    state = tmp_path_factory.mktemp("toast-app")
    (state / "data").mkdir()
    (state / "stats").mkdir()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (state / "config.toml").write_text(
        f'host = "127.0.0.1"\nport = {port}\ndebug = false\n'
        "percentile_warmup_enabled = false\n",
        encoding="utf-8",
    )
    (state / "data" / "settings.json").write_text(
        json.dumps({"schema_version": 1, "stats_dir": str(state / "stats")}),
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
                pytest.fail("The isolated toast app did not start.")
            yield origin
        finally:
            process.terminate()
            process.wait(timeout=15)


@pytest.fixture(scope="module")
def toast_browser():
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
def page(toast_server, toast_browser):
    context = toast_browser.new_context(viewport={"width": 1600, "height": 900})
    page = context.new_page()
    page.goto(f"{toast_server}/settings")
    page.wait_for_function(
        "() => window.dash_clientside && window.dash_clientside.set_props"
        f" && document.getElementById('{CONTAINER_ID}')"
    )
    yield page
    context.close()


def show(page, toast_id, title, auto_close):
    """Send one toast to the app's container, as a callback's payload would."""
    payload = {
        "action": "show",
        "id": toast_id,
        "title": title,
        "message": "Toast interaction probe.",
        "autoClose": auto_close,
    }
    page.evaluate(
        "([id, payload]) => window.dash_clientside.set_props("
        "id, {sendNotifications: [payload]})",
        [CONTAINER_ID, payload],
    )
    toast = page.locator(".mantine-Notification-root").filter(has_text=title)
    playwright.expect(toast).to_be_visible()
    # Let the entry transition finish, so a gesture lands on a resting toast.
    page.wait_for_timeout(500)
    return toast


def test_a_sideways_drag_leaves_a_toast_on_screen(page):
    toast = show(page, "probe-drag", STAYS, False)
    box = toast.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + box["width"], y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(1000)

    playwright.expect(toast).to_be_visible()


def test_a_sideways_scroll_leaves_a_toast_on_screen(page):
    toast = show(page, "probe-scroll", STAYS, False)
    box = toast.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    for _ in range(4):
        page.mouse.wheel(400, 0)
        page.wait_for_timeout(100)
    page.wait_for_timeout(1000)

    playwright.expect(toast).to_be_visible()


def test_hovering_one_toast_leaves_another_toasts_timer_running(page):
    stays = show(page, "probe-hover-stays", STAYS, False)
    timed = show(page, "probe-hover-timed", TIMED, 1500)
    box = stays.bounding_box()

    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    playwright.expect(timed).to_have_count(0, timeout=6000)
    playwright.expect(stays).to_be_visible()
