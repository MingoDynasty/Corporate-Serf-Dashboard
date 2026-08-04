"""Shared prop preset for the playlist-selector dropdowns.

Home's ``dmc.Select`` filter and the Aim Training Journey ``dmc.MultiSelect``
comparison picker stay distinct components with role-specific behavior
(clearable/persistence/value semantics), but should share the same search,
sizing, and scroll conventions so the two dropdowns look and behave
consistently. This preset holds only the role-agnostic props; each call site
splats it and adds its own role-specific props.
"""

# Splatted into both playlist dropdowns. Only props valid on both
# ``dmc.Select`` and ``dmc.MultiSelect`` belong here; Select-only refinements
# (clearSearchOnFocus, allowDeselect, autoSelectOnBlur) and role-specific props
# (clearable, persistence, value) stay at the call sites.
PLAYLIST_SELECTOR_PRESET = {
    "checkIconPosition": "right",
    # Target 400px but shrink before the row wraps. A bare ``miw`` of 400px
    # floors the control there, so a row that no longer fits wraps to a second
    # line instead of narrowing -- the jarring reflow that opening the navbar
    # used to trigger. flex-basis sets the width to aim for and the floor below
    # keeps the control readable once it starts giving ground.
    "flex": "0 1 400px",
    "maxDropdownHeight": "75vh",
    # Shrink with the container below 200px so narrow windows and high page
    # zoom don't force horizontal overflow.
    "miw": "min(200px, 100%)",
    "placeholder": "Select a playlist...",
    "scrollAreaProps": {"type": "always"},
    "searchable": True,
}
