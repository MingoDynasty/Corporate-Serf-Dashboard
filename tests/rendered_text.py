"""Flatten rendered copy into the text a reader sees, bold control names marked."""

from dash import html


def rendered_text(children) -> str:
    """Flatten a children value to text, rendering a bold span as ``**name**``.

    ``**name**`` is the Copy block's own marker for a bold control name, so a
    test compares the ratified sentence verbatim, and a name that loses its
    bold fails the comparison instead of passing as the same words. Every other
    component contributes only its children's text.
    """
    if children is None:
        return ""
    if isinstance(children, str):
        return children
    if isinstance(children, (int, float)):
        return str(children)
    if isinstance(children, (list, tuple)):
        return "".join(rendered_text(child) for child in children)
    text = rendered_text(getattr(children, "children", None))
    if isinstance(children, html.B):
        return f"**{text}**"
    return text
