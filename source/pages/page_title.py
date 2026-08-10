"""Optionally prefix browser tab titles with the running build's release label.

Operators who run several instances side by side -- a release install, a local
branch, an older release -- otherwise see the same ``Playlists`` in every tab
and have to open Settings to tell them apart. Turning on
``show_version_in_title`` prefixes every page title with
``BuildInfo.release_label``, so each instance labels itself with no
per-instance configuration: ``dev - Playlists`` from a checkout,
``v2026.08.09.9 - Playlists`` from an install.

The flag is read per request, not at ``register_page`` time, because pages
import during ``DashProxy`` construction -- before ``main`` loads the config.
Reading it there would raise on a missing or unparseable ``config.toml`` at
import, bypassing the startup path that turns that into an actionable message.
So every title is registered as a callable, which Dash resolves on both
surfaces that render one: the server's meta tags and the client-side router.
Both pass the route's path variables, so the wrapper forwards them and a
dynamic title keeps working.

``app.title`` is deliberately untouched: it already folds in the release tag,
and Dash Pages overwrites it on every navigation anyway.
"""

from collections.abc import Callable

from source.config.config_service import get_config
from source.utilities.build_info import get_build_info

TITLE_SEPARATOR = " - "


def page_title(title: str | Callable[..., str]) -> Callable[..., str]:
    """Wrap a page title -- string or callable -- for ``register_page``."""

    def resolve(**path_variables: str) -> str:
        """Resolve the title for one request, prefixed when opted in."""
        resolved = title(**path_variables) if callable(title) else title
        if not get_config().show_version_in_title:
            return resolved
        # The label is used verbatim, "unknown" included: only an operator who
        # asked for the marker ever sees it, and it never claims a release
        # identity the build cannot prove.
        return f"{get_build_info().release_label}{TITLE_SEPARATOR}{resolved}"

    return resolve
