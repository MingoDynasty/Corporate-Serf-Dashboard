"""Render local SVG icons without runtime Iconify API requests."""

from dataclasses import dataclass
from typing import Any

from dash import html
from dash.development.base_component import Component

ICON_ASSET_ROOT = "/assets/icons"


@dataclass(frozen=True)
class IconAsset:
    """Metadata for one vendored SVG icon."""

    file_name: str
    width: int
    height: int
    preserves_color: bool = False


ICONS: dict[str, IconAsset] = {
    "bi:house-door-fill": IconAsset("bi-house-door-fill.svg", 16, 16),
    "clarity:date-line": IconAsset("clarity-date-line.svg", 36, 36),
    "clarity:settings-line": IconAsset("clarity-settings-line.svg", 36, 36),
    "fontisto:line-chart": IconAsset("fontisto-line-chart.svg", 32, 24),
    "ion:logo-github": IconAsset("ion-logo-github.svg", 512, 512),
    "logos:discord-icon": IconAsset(
        "logos-discord-icon.svg",
        256,
        199,
        preserves_color=True,
    ),
    "material-symbols:check": IconAsset("material-symbols-check.svg", 24, 24),
    "material-symbols:playlist-play": IconAsset(
        "material-symbols-playlist-play.svg",
        24,
        24,
    ),
    "material-symbols:refresh-rounded": IconAsset(
        "material-symbols-refresh-rounded.svg",
        24,
        24,
    ),
    "material-symbols:upload": IconAsset("material-symbols-upload.svg", 24, 24),
    "material-symbols:warning-outline": IconAsset(
        "material-symbols-warning-outline.svg",
        24,
        24,
    ),
    "radix-icons:moon": IconAsset("radix-icons-moon.svg", 15, 15),
    "radix-icons:sun": IconAsset("radix-icons-sun.svg", 15, 15),
}

CssSize = int | float | str


def _scale_size(value: CssSize, factor: float) -> CssSize:
    if not isinstance(value, (int, float)):
        return value

    scaled = value * factor
    if float(scaled).is_integer():
        return int(scaled)
    return round(scaled, 3)


def _default_width(asset: IconAsset) -> str:
    aspect_ratio = asset.width / asset.height
    if aspect_ratio == 1:
        return "1em"
    return f"{aspect_ratio:.3g}em"


def _resolve_size(
    asset: IconAsset,
    width: CssSize | None,
    height: CssSize | None,
) -> tuple[CssSize, CssSize]:
    if width is None and height is None:
        return _default_width(asset), "1em"
    if width is None:
        assert height is not None
        return _scale_size(height, asset.width / asset.height), height
    if height is None:
        return width, _scale_size(width, asset.height / asset.width)
    return width, height


def local_icon(  # noqa: PLR0913
    name: str,
    *,
    width: CssSize | None = None,
    height: CssSize | None = None,
    color: str | None = None,
    className: str | None = None,  # noqa: N803 - matches Dash prop naming.
    style: dict[str, Any] | None = None,
) -> Component:
    """Build a local icon component for a vendored Iconify icon name."""
    asset = ICONS[name]
    icon_width, icon_height = _resolve_size(asset, width, height)
    asset_url = f"{ICON_ASSET_ROOT}/{asset.file_name}"

    base_style: dict[str, Any] = {
        "display": "inline-block",
        "width": icon_width,
        "height": icon_height,
        "verticalAlign": "-0.125em",
        "flex": "0 0 auto",
    }
    if style:
        base_style.update(style)

    if asset.preserves_color:
        return html.Img(
            src=asset_url,
            alt="",
            className=className,
            style=base_style,
            **{"aria-hidden": "true"},
        )

    mask = f"url({asset_url}) no-repeat center / contain"
    return html.Span(
        className=className,
        style={
            **base_style,
            "backgroundColor": color or "currentColor",
            "mask": mask,
            "WebkitMask": mask,
        },
        **{"aria-hidden": "true"},
    )
