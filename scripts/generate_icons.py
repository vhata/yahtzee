#!/usr/bin/env python3
"""Generate PWA icon PNGs for the Yahtzee web app.

Draws the same 5-pip die design used by the inline SVG favicon.
Run once: uv run --with pillow python generate_icons.py
"""
from PIL import Image, ImageDraw


def draw_die_icon(size):
    """Draw a blue rounded-rect die with 5 white pips."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue rounded rectangle background
    radius = size * 15 // 100  # 15% corner radius, matching the SVG's rx=15/100
    draw.rounded_rectangle(
        [0, 0, size - 1, size - 1],
        radius=radius,
        fill=(70, 130, 180),  # #4682b4
    )

    # 5-pip positions (same as SVG: 30%, 50%, 70% of size)
    pip_positions = [
        (0.30, 0.30),  # top-left
        (0.70, 0.30),  # top-right
        (0.50, 0.50),  # center
        (0.30, 0.70),  # bottom-left
        (0.70, 0.70),  # bottom-right
    ]
    pip_radius = size * 8 // 100  # 8% of size, matching SVG's r=8/100

    for px, py in pip_positions:
        cx, cy = size * px, size * py
        draw.ellipse(
            [cx - pip_radius, cy - pip_radius, cx + pip_radius, cy + pip_radius],
            fill="white",
        )

    return img


if __name__ == "__main__":
    for size in (192, 512):
        img = draw_die_icon(size)
        path = f"static/icon-{size}.png"
        img.save(path)
        print(f"Generated {path}")
