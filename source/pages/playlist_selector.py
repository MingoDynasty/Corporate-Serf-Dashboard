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
    # Target 400px, but narrow before the row wraps. Flex line-breaking uses
    # each item's *hypothetical* main size -- its flex-basis clamped by min/max
    # width -- and flex-shrink only redistributes space inside a line that has
    # already been collected. So a 400px basis, exactly like the 400px
    # ``miw`` floor it replaced, books 400px of the row before anything can
    # give ground, and the control wraps to the next line instead of shrinking.
    # Break at the readable 200px floor instead and grow back toward the 400px
    # target with whatever room the line has left. The ``100%`` clamps keep
    # high page zoom from overflowing a container narrower than either bound.
    "flex": "1 1 200px",
    "maw": "min(400px, 100%)",
    "maxDropdownHeight": "75vh",
    # Explicit rather than the flex-item default of ``auto``: a min-content
    # floor above 200px would quietly raise the wrap threshold again.
    "miw": "min(200px, 100%)",
    "placeholder": "Select a playlist...",
    "scrollAreaProps": {"type": "always"},
    "searchable": True,
}
