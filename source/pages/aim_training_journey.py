import logging

import dash
import dash_mantine_components as dmc

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/aim-training-journey",
    title="Aim Training Journey",
)


def layout(**kwargs):
    return dmc.MantineProvider(
        [
            dmc.Text("TODO", size="xl"),
        ]
    )
