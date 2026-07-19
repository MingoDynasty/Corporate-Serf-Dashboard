"""Build the shared Dash application shell and navigation."""

import logging

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, clientside_callback

from source.components.local_icon import local_icon
from source.utilities.build_info import get_build_info
from source.utilities.dash_logging import NOTIFICATION_CONTAINER_ID

logger = logging.getLogger(__name__)

APP_INDEX_STRING = """<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        <script>
            (() => {
                const colorSchemeKey = "mantine-color-scheme-value";
                const legacySwitchKey =
                    "_dash_persistence.color-scheme-switch.checked.true";
                let colorScheme = "light";

                try {
                    const storedColorScheme =
                        window.localStorage.getItem(colorSchemeKey);

                    if (
                        storedColorScheme === "dark" ||
                        storedColorScheme === "light"
                    ) {
                        colorScheme = storedColorScheme;
                    } else {
                        const persistedSwitch = JSON.parse(
                            window.localStorage.getItem(legacySwitchKey)
                        );
                        colorScheme =
                            Array.isArray(persistedSwitch) &&
                            persistedSwitch[0] === true
                                ? "dark"
                                : "light";
                        window.localStorage.setItem(
                            colorSchemeKey,
                            colorScheme
                        );
                    }
                    window.localStorage.removeItem(legacySwitchKey);
                } catch (_error) {
                    // Local storage can be unavailable; light is the safe default.
                }

                document.documentElement.setAttribute(
                    "data-mantine-color-scheme",
                    colorScheme
                );
            })();
        </script>
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

discord_component = dmc.Tooltip(
    dmc.Anchor(
        local_icon(
            "logos:discord-icon",
            width=40,
        ),
        href="https://discordapp.com/users/222910150636339211",
    ),
    label="Contact me via Discord: MingoDynasty",
)


def github_component() -> dmc.Tooltip:
    """Build the GitHub link, whose tooltip carries the build identity.

    Built on demand rather than at import: resolving the build identity can
    log (an ignored install manifest, say), and this module is imported
    before the app configures its log handlers.
    """
    return dmc.Tooltip(
        dmc.Anchor(
            local_icon("ion:logo-github", width=40),
            href="https://github.com/MingoDynasty/Corporate-Serf-Dashboard",
        ),
        # The build identity rides along on an existing tooltip: it costs no
        # pixels, and a bug report only needs to read it once.
        label=f"View this app on GitHub — build {get_build_info().short_description}",
    )


theme_switch_component = dmc.Tooltip(
    dmc.ColorSchemeToggle(
        lightIcon=local_icon(
            "radix-icons:sun",
            width=25,
            color=dmc.DEFAULT_THEME["colors"]["yellow"][8],
        ),
        darkIcon=local_icon(
            "radix-icons:moon",
            width=25,
            color=dmc.DEFAULT_THEME["colors"]["yellow"][6],
        ),
        id="color-scheme-switch",
        color="gray",
        size="lg",
        mr="xl",
        **{"aria-label": "Toggle color scheme"},
    ),
    label="Toggle light and dark theme",
)


def nav_link(label: str, href: str, icon: str) -> dmc.NavLink:
    """Build a single-anchor Dash-native navbar link."""
    return dmc.NavLink(
        label=label,
        leftSection=dmc.ThemeIcon(
            local_icon(icon, height=36),
            size="lg",
            variant="outline",
        ),
        href=href,
        refresh=False,
    )


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(**kwargs):  # noqa: ARG001
    """Build the shared application shell around the active Dash page."""
    return dmc.MantineProvider(
        id="mantine-provider",
        defaultColorScheme="light",
        children=[
            dmc.AppShell(
                children=[
                    dmc.NotificationContainer(id=NOTIFICATION_CONTAINER_ID),
                    dmc.AppShellHeader(
                        dmc.Grid(
                            children=[
                                dmc.GridCol(
                                    dmc.Group(
                                        children=[
                                            dmc.Burger(
                                                id="burger",
                                                size="sm",
                                                opened=True,
                                                persisted_props=["opened"],
                                                persistence=True,
                                                persistence_type="local",
                                                **{"aria-label": "Toggle navigation"},
                                            ),
                                            dmc.Anchor(
                                                children=[
                                                    dmc.Title(
                                                        "Corporate Serf Dashboard",
                                                        className="app-header-title",
                                                    ),
                                                ],
                                                href="/",
                                                target="_self",
                                                underline="never",
                                                className="app-header-title-anchor",
                                            ),
                                        ],
                                        h="100%",
                                        px="md",
                                        wrap="nowrap",
                                    ),
                                    className="app-header-title-col",
                                    span="auto",
                                ),
                                dmc.GridCol(
                                    dmc.Group(
                                        children=[
                                            discord_component,
                                            github_component(),
                                            theme_switch_component,
                                        ],
                                        h="100%",
                                        px="md",
                                        justify="flex-end",
                                        wrap="nowrap",
                                    ),
                                    span="content",
                                ),
                            ],
                        ),
                        pt="0.5em",
                    ),
                    dmc.AppShellNavbar(
                        id="navbar",
                        children=[
                            nav_link("Home", "/", "bi:house-door-fill"),
                            nav_link(
                                "Playlists",
                                "/playlists",
                                "material-symbols:playlist-play",
                            ),
                        ],
                        p="md",
                    ),
                    dmc.AppShellMain(dash.page_container),
                ],
                header={"height": "4em"},
                padding="md",
                navbar={
                    "width": 250,
                    "breakpoint": "sm",
                    # Mirrors the burger's `opened` default. The clientside
                    # callback below derives this from the burger on every
                    # load, so a mismatch here would paint the navbar
                    # collapsed for a frame before the callback opens it.
                    "collapsed": {
                        "mobile": False,
                        "desktop": False,
                    },
                },
                id="appshell",
            ),
        ],
    )


clientside_callback(
    """
    (opened, navbar) => ({
        ...navbar,
        collapsed: {
            mobile: !opened,
            desktop: !opened,
        },
    })
    """,
    Output("appshell", "navbar"),
    Input("burger", "opened"),
    State("appshell", "navbar"),
)
