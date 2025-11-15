import logging

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback

logger = logging.getLogger(__name__)


def layout(**kwargs):
    return dmc.MantineProvider(
        dmc.AppShell(
            children=[
                dmc.AppShellHeader(
                    dmc.Group(
                        children=[
                            dmc.Burger(
                                id="burger",
                                size="sm",
                                opened=False,
                            ),
                            dmc.Title("Corporate Serf Dashboard"),
                        ],
                        h="100%",
                        px="md",
                    )
                ),
                dmc.AppShellNavbar(
                    id="navbar",
                    children=[
                        "TODO: Navbar",
                        *[
                            dmc.Skeleton(height=28, mt="sm", animate=False)
                            for _ in range(15)
                        ],
                    ],
                    p="md",
                ),
                dmc.AppShellMain(dash.page_container),
            ],
            header={"height": 60},
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
