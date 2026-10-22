"""Check capture error handling in Chromium when screenshot tools are installed."""

import re
import sys

import pytest

from scripts import capture_screenshots

playwright = pytest.importorskip("playwright.sync_api")
pytest.importorskip("freezegun")


@pytest.mark.parametrize(
    ("failure", "load_number"),
    [("pageerror", 2), ("http503", 2), ("pageerror", 1)],
    ids=["clean-reload-javascript", "clean-reload-http", "ignore-first-load-noise"],
)
def test_capture_observes_clean_reload_errors(
    monkeypatch, tmp_path, failure, load_number
):
    create_context = playwright.Browser.new_context

    def context_with_failure(browser, **options):
        context = create_context(browser, **options)
        if failure == "pageerror":
            context.add_init_script(f"""
                if (location.pathname === '/run-history') {{
                    const count = Number(sessionStorage.getItem('capture-probe-load') || 0) + 1;
                    sessionStorage.setItem('capture-probe-load', String(count));
                    if (count === {load_number}) {{
                        window.addEventListener('load', () => {{
                            throw new Error('capture-reload-probe');
                        }});
                    }}
                }}
            """)
        else:
            visits = 0

            def respond_with_error(route):
                nonlocal visits
                visits += 1
                if visits == load_number:
                    # Preserve the working app document so DOM readiness can
                    # succeed even though the clean load returned HTTP 503.
                    route.fulfill(response=route.fetch(), status=503)
                else:
                    route.continue_()

            context.on(
                "page",
                lambda page: page.route(
                    re.compile(r"/run-history\?"), respond_with_error
                ),
            )
        return context

    monkeypatch.setattr(playwright.Browser, "new_context", context_with_failure)
    output = tmp_path / "images"
    output.mkdir()
    for filename in capture_screenshots.IMAGE_NAMES:
        (output / filename).write_bytes(b"existing image")
    monkeypatch.setattr(sys, "argv", ["capture_screenshots", "--output", str(output)])
    if load_number == 2:
        match = "capture-reload-probe" if failure == "pageerror" else "503"
        with pytest.raises(RuntimeError, match=match):
            capture_screenshots.main()
        assert all(
            (output / filename).read_bytes() == b"existing image"
            for filename in capture_screenshots.IMAGE_NAMES
        )
    else:
        capture_screenshots.main()
        assert all(
            (output / filename).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            for filename in capture_screenshots.IMAGE_NAMES
        )
