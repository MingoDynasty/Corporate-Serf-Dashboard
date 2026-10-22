"""Keep shared text links readable on the page and the two notice tints."""

import re
from pathlib import Path

import dash_mantine_components as dmc
import pytest

from source import app_shell

STYLESHEET = Path(__file__).resolve().parents[1] / "assets" / "stylesheet.css"


def _rgb(hex_color):
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(character * 2 for character in value)
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _luminance(rgb):
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in rgb
    ]
    return sum(
        channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722))
    )


def _anchor_color(scheme):
    css = STYLESHEET.read_text(encoding="utf-8")
    match = re.search(
        rf':root\[data-mantine-color-scheme="{scheme}"\]\s*\{{([^}}]*)\}}', css
    )
    override = re.search(
        r"--mantine-color-anchor:\s*var\(--mantine-color-(\w+)-(\d)\)",
        match[1] if match else "",
    )
    # Mantine's default anchor shades are blue 6 in light and blue 4 in dark.
    color, shade = (
        override.groups() if override else ("blue", 6 if scheme == "light" else 4)
    )
    return _rgb(dmc.DEFAULT_THEME["colors"][color][int(shade)])


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("surface", ["page", "blue", "yellow"])
def test_shared_text_links_clear_normal_text_contrast(scheme, surface):
    theme = dmc.DEFAULT_THEME
    background = _rgb(
        theme["white"] if scheme == "light" else theme["colors"]["dark"][7]
    )
    if surface != "page":
        tint = _rgb(theme["colors"][surface][6])
        opacity = 0.1 if scheme == "light" else 0.15
        background = tuple(
            foreground * opacity + base * (1 - opacity)
            for foreground, base in zip(tint, background)
        )
    luminances = sorted((_luminance(_anchor_color(scheme)), _luminance(background)))
    contrast = (luminances[1] + 0.05) / (luminances[0] + 0.05)
    assert contrast >= 4.5, f"{scheme} {surface}: {contrast:.2f}:1"


def test_text_links_have_a_persistent_visual_cue():
    provider = app_shell.layout()
    assert (
        provider.theme["components"]["Anchor"]["defaultProps"]["underline"] == "always"
    )
