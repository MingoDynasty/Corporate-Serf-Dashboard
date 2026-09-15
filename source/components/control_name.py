"""Render a control named in running text as a bold span."""

from dash import html


def control_name(name: str) -> html.B:
    """Mark a control named in prose, in the casing the control shows.

    Bold is the app's one marker for "this is a control", so every component
    sentence that names one builds it here. A plain ``<b>`` rather than a bold
    ``dmc.Text``: an unsized ``dmc.Text`` renders at Mantine's md font size,
    which would set the name larger than the tooltip, description, or toast it
    sits in. A chart annotation cannot hold a component and writes
    ``<b>name</b>`` into its string instead.
    """
    return html.B(name)
