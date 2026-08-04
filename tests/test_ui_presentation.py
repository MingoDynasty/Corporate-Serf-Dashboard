"""Field labels share one font, one weight rule, and the page's left edge.

Presentation invariants that only show themselves in a browser, so nothing
else in the suite notices when one is lost. Each pins a paper cut that
shipped once already.
"""

import re
from pathlib import Path

import dash
import dash_mantine_components as dmc

dash.Dash(__name__, use_pages=True, pages_folder="")
# The Journey layout builds a placeholder figure, which resolves the
# light/dark templates the app registers at import time; a page-only test
# has to register them itself.
dmc.add_figure_templates()

from source.pages import aim_training_journey as journey  # noqa: E402
from source.pages import home  # noqa: E402

STYLESHEET = Path(__file__).resolve().parents[1] / "assets" / "stylesheet.css"

# Anything that would push a control right of its row's left edge.
LEFT_OFFSET_PROPS = ("m", "mx", "ms", "ml")

# A per-component label class taking a font-weight of its own. The captured
# group is the component name, so a failure names whoever crept back in.
LABEL_WEIGHT_RULE = re.compile(r"\.mantine-([A-Za-z]+)-label\s*\{[^}]*font-weight")

CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _walk_components(component):
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk_components(child)
        return
    yield from _walk_components(children)


def _component_by_id(page, component_id):
    return next(
        (
            component
            for component in _walk_components(page)
            if getattr(component, "id", None) == component_id
        ),
        None,
    )


def _help_icon_labels(page):
    """Every label built by the help-icon helper — a Group, not a string."""
    for component in _walk_components(page):
        label = getattr(component, "label", None)
        if isinstance(label, dmc.Group):
            yield component, label


def test_help_icon_labels_inherit_the_input_label_font():
    """dmc.Text applies its own font-size and weight over the enclosing
    <label>, so a label built as a component renders 16px/400 beside the
    14px/700 of every label passed as a plain string. ``inherit`` is what
    makes the two indistinguishable."""
    labels = list(_help_icon_labels(home.layout()))

    assert labels, "Home should still build labels with the help-icon helper"
    for owner, label in labels:
        text = label.children[0]
        assert isinstance(text, dmc.Text)
        assert text.inherit is True, (
            f"{getattr(owner, 'id', owner)}'s label would render in dmc.Text's "
            "own font rather than the input label's"
        )


def test_playlist_filters_start_at_the_pages_left_edge():
    """The filter is the first control in its row, so an indent on it puts
    the row outside the left rail the graph and everything below share."""
    for page, component_id in (
        (home.layout(), "playlist-dropdown-selection"),
        (journey.layout(), "playlists-multi-select"),
    ):
        selector = _component_by_id(page, component_id)
        assert selector is not None, f"{component_id} is missing from its page"

        offsets = {
            prop: getattr(selector, prop, None)
            for prop in LEFT_OFFSET_PROPS
            if getattr(selector, prop, None) is not None
        }
        assert not offsets, f"{component_id} carries a left offset: {offsets}"


def test_field_labels_are_bolded_by_the_class_they_all_share():
    """One rule on ``InputWrapper``, never a list of per-component classes:
    enumerating them silently drops whichever component is added next, which
    is how the stats-directory field lost its bold on becoming an
    Autocomplete. Switch and Radio captions are control text rather than
    field labels and set no weight of their own."""
    css = CSS_COMMENT.sub("", STYLESHEET.read_text(encoding="utf-8"))

    assert set(LABEL_WEIGHT_RULE.findall(css)) == {"InputWrapper"}
