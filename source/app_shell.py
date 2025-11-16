import logging

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, clientside_callback
from dash_iconify import DashIconify

from utilities.dash_logging import log_handler

logger = logging.getLogger(__name__)

discord_component = dmc.Tooltip(
    dmc.Anchor(
        DashIconify(
            icon="logos:discord-icon",
            width=40,
        ),
        href="https://discordapp.com/users/222910150636339211",
    ),
    label="Contact me via Discord: MingoDynasty",
)

github_component = dmc.Tooltip(
    dmc.Anchor(
        DashIconify(icon="ion:logo-github", width=40),
        href="https://github.com/MingoDynasty/Corporate-Serf-Dashboard",
    ),
    label="View this app on GitHub",
)

theme_switch_component = dmc.Switch(
    offLabel=DashIconify(
        icon="radix-icons:sun",
        width=25,
        color=dmc.DEFAULT_THEME["colors"]["yellow"][8],
    ),
    onLabel=DashIconify(
        icon="radix-icons:moon",
        width=25,
        color=dmc.DEFAULT_THEME["colors"]["yellow"][6],
    ),
    id="color-scheme-switch",
    persistence=True,
    color="gray",
    size="lg",
    mr="xl",
)


def layout(**kwargs):
    return dmc.MantineProvider(
        children=[
            dmc.AppShell(
                children=[
                    dmc.NotificationContainer(id="notification-container"),
                    dmc.AppShellHeader(
                        dmc.Grid(
                            children=[
                                dmc.GridCol(
                                    dmc.Group(
                                        children=[
                                            dmc.Burger(
                                                id="burger",
                                                size="sm",
                                                opened=False,
                                            ),
                                            dmc.Anchor(
                                                children=[
                                                    dmc.Title(
                                                        "Corporate Serf Dashboard"
                                                    )
                                                ],
                                                href="/",
                                                target="_self",
                                                underline="never",
                                                style={
                                                    "color": "var(--mantine-font-family-headings)"
                                                },
                                            ),
                                        ],
                                        h="100%",
                                        px="md",
                                    ),
                                    span=6,
                                ),
                                dmc.GridCol(
                                    dmc.Group(
                                        children=[
                                            discord_component,
                                            github_component,
                                            theme_switch_component,
                                        ],
                                        h="100%",
                                        px="md",
                                        justify="flex-end",
                                    ),
                                    span=6,
                                ),
                            ],
                        ),
                        pt="0.5em",
                    ),
                    dmc.AppShellNavbar(
                        id="navbar",
                        children=[
                            dmc.NavLink(
                                label="Home",
                                href="/",
                                leftSection=DashIconify(
                                    icon="bi:house-door-fill", height=36
                                ),
                            ),
                            dmc.NavLink(
                                label="Aim Training Journey",
                                href="aim-training-journey",
                                leftSection=DashIconify(
                                    icon="game-icons:journey",
                                    height=36,
                                ),
                            ),
                        ],
                        p="md",
                    ),
                    dmc.AppShellMain(dash.page_container),
                ],
                header={"height": "4em"},
                padding="md",
                navbar={
                    "width": 300,
                    "breakpoint": "sm",
                    "collapsed": {
                        "mobile": True,
                        "desktop": True,
                    },
                },
                id="appshell",
            )
        ]
        + log_handler.embed(),
    )


@callback(
    Output("appshell", "navbar"),
    Input("burger", "opened"),
    State("appshell", "navbar"),
)
def toggle_navbar(opened, navbar):
    navbar["collapsed"] = {
        "mobile": not opened,
        "desktop": not opened,
    }
    return navbar


clientside_callback(
    """
    (switchOn) => {
       document.documentElement.setAttribute('data-mantine-color-scheme', switchOn ? 'dark' : 'light');
       return window.dash_clientside.no_update
    }
    """,
    Output("color-scheme-switch", "id"),
    Input("color-scheme-switch", "checked"),
)
