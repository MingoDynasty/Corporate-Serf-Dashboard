import logging

import dash
import dash_mantine_components as dmc

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/aim-training-journey",
    title="Aim Training Journey",
)


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(**kwargs):  # noqa: ARG001
    return dmc.MantineProvider(
        [
            dmc.Text("TODO", size="xl"),
        ],
    )
