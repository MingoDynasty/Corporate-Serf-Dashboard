"""The page drawn for an address that matches no page."""

import json
from collections import OrderedDict

import dash
import dash_mantine_components as dmc
import pytest
from dash import _callback, _pages, html

APP = dash.Dash(__name__, use_pages=True, pages_folder="")
# The router then calls only the page it draws. Validation would call every
# page in the registry.
APP.config.suppress_callback_exceptions = True

from source.pages import not_found_404  # noqa: E402

APP.layout = html.Div(dash.page_container)


def test_the_page_states_what_happened_and_links_home():
    page = not_found_404.layout(unexpected="query")

    title, message, home_link = page.children
    assert isinstance(title, dmc.Title)
    assert title.children == "Page Not Found"
    assert message.children == "This address doesn't match any page in this app."
    assert isinstance(home_link, dmc.Anchor)
    assert home_link.children == "Go to Home"
    assert home_link.href == "/"
    # Inside the app, as the navbar's links are, so the shell is kept.
    assert home_link.refresh is False


def _route(monkeypatch: pytest.MonkeyPatch, pathname: str) -> tuple[str, str]:
    """Ask Dash's router what it draws for ``pathname``: content and tab title.

    The registry holds this page alone, with its layout: the suite's other
    pages are registered without one, because no pages folder is walked, and
    Dash refuses to route a registry that holds such a page. The first
    request moves every callback the suite has registered from Dash's global
    lists into this app, so they are put back for the tests that read them
    there.
    """
    module = not_found_404.__name__
    page = {**_pages.PAGE_REGISTRY[module], "layout": not_found_404.layout}
    monkeypatch.setattr(_pages, "PAGE_REGISTRY", OrderedDict({module: page}))
    saved_list = list(_callback.GLOBAL_CALLBACK_LIST)
    saved_map = dict(_callback.GLOBAL_CALLBACK_MAP)
    saved_scripts = list(_callback.GLOBAL_INLINE_SCRIPTS)
    try:
        client = APP.server.test_client()
        response = client.post(
            "/_dash-update-component",
            json={
                "output": ".._pages_content.children..._pages_store.data..",
                "outputs": [
                    {"id": "_pages_content", "property": "children"},
                    {"id": "_pages_store", "property": "data"},
                ],
                "inputs": [
                    {
                        "id": "_pages_location",
                        "property": "pathname",
                        "value": pathname,
                    },
                    {"id": "_pages_location", "property": "search", "value": ""},
                ],
                "changedPropIds": ["_pages_location.pathname"],
                "state": [],
            },
        )
    finally:
        _callback.GLOBAL_CALLBACK_LIST[:] = saved_list
        _callback.GLOBAL_CALLBACK_MAP.clear()
        _callback.GLOBAL_CALLBACK_MAP.update(saved_map)
        _callback.GLOBAL_INLINE_SCRIPTS[:] = saved_scripts
    assert response.status_code == 200
    payload = json.loads(response.data)["response"]
    return (
        json.dumps(payload["_pages_content"]["children"]),
        payload["_pages_store"]["data"]["title"],
    )


def test_dash_draws_this_page_and_its_title_for_an_unknown_address(monkeypatch):
    """Dash finds the page by its module name, so a rename would lose it."""
    content, title = _route(monkeypatch, "/no-such-page")

    assert "Page Not Found" in content
    assert "This address doesn't match any page in this app." in content
    assert "404 - Page not found" not in content
    assert title == "Page Not Found"
