from pathlib import Path

from dash import html

from source.components.local_icon import ICONS, local_icon


def test_registered_local_icons_have_committed_assets():
    icon_root = Path(__file__).resolve().parents[1] / "assets" / "icons"

    missing_icons = [
        icon_name
        for icon_name, asset in ICONS.items()
        if not (icon_root / asset.file_name).is_file()
    ]

    assert missing_icons == []


def test_monochrome_local_icon_uses_asset_mask_and_current_color():
    icon = local_icon("material-symbols:refresh-rounded", width=14)

    assert isinstance(icon, html.Span)
    assert icon.style["width"] == 14
    assert icon.style["height"] == 14
    assert icon.style["backgroundColor"] == "currentColor"
    assert icon.style["mask"] == (
        "url(/assets/icons/material-symbols-refresh-rounded.svg) "
        "no-repeat center / contain"
    )


def test_multicolor_local_icon_renders_asset_image():
    icon = local_icon("logos:discord-icon", width=40)

    assert isinstance(icon, html.Img)
    assert icon.src == "/assets/icons/logos-discord-icon.svg"
    assert icon.style["width"] == 40
    assert icon.style["height"] == 31.094
