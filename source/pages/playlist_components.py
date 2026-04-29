"""Shared UI helpers for playlist pages."""

import dash_mantine_components as dmc

from source.kovaaks.data_service import get_playlist_selector_options


def playlist_selector(component_id: str, value: str | None = None) -> dmc.Select:
    """Build the transitional M1 playlist selector."""
    return dmc.Select(
        allowDeselect=False,
        checkIconPosition="right",
        clearable=False,
        data=get_playlist_selector_options(),
        id=component_id,
        label="Playlist",
        maxDropdownHeight="75vh",
        miw=400,
        placeholder="Select a playlist...",
        searchable=True,
        value=value,
    )
