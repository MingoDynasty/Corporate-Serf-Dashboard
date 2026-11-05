"""Build the page drawn for an address that matches no page.

Dash Pages finds this page by its module name, ``not_found_404``, and draws it
for every address no other page claims, under the title registered here. Without
it Dash draws a bare "404 - Page not found" heading under the app's own title,
with no way onward when the navbar is collapsed.
"""

import dash
import dash_mantine_components as dmc

from source.pages.page_title import page_title

NOT_FOUND_TITLE = "Page Not Found"
NOT_FOUND_MESSAGE = "This address doesn't match any page in this app."
GO_HOME_LABEL = "Go to Home"

dash.register_page(
    __name__,
    path="/404",
    title=page_title(NOT_FOUND_TITLE),
)


def layout(**_kwargs):
    """Build the page.

    ``**_kwargs`` takes the query parameters of the address that was not
    found, which Dash passes to whatever page it draws.
    """
    return dmc.Stack(
        children=[
            dmc.Title(NOT_FOUND_TITLE, order=2),
            dmc.Text(NOT_FOUND_MESSAGE),
            dmc.Anchor(GO_HOME_LABEL, href="/", refresh=False),
        ],
        align="flex-start",
        gap="md",
    )
