import logging

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback
from dash_iconify import DashIconify

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
                                    icon="bi:house-door-fill", height=32
                                ),
                            ),
                            dmc.NavLink(
                                label="Aim Training Journey",
                                href="aim-training-journey",
                                leftSection=DashIconify(
                                    icon="game-icons:journey",
                                    height=32,
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
        ],
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
