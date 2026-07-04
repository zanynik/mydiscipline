"""Generate a 1024x1024 AppIcon.png for MyDiscipline.

Pure-Pillow, no external fonts required. Draws a rounded "shield" on a deep
slate background to match the app's focus theme. Run after checking out the
repo (or it's fine to skip — Xcode will warn about a missing icon but still
build).

    python scripts/make_appicon.py
"""

from PIL import Image, ImageDraw

SIZE = 1024


def _rounded_gradient_background(draw: ImageDraw.ImageDraw, img: Image.Image) -> None:
    # Vertical slate gradient.
    top = (30, 40, 60)
    bot = (15, 20, 30)
    for y in range(SIZE):
        t = y / SIZE
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        draw.line([(0, y), (SIZE, y)], fill=(r, g, b))


def _shield_path(size: int):
    # A symmetric shield polygon centered in the canvas.
    cx = size / 2
    top = size * 0.20
    bottom = size * 0.78
    half = size * 0.27
    notch = size * 0.16
    return [
        (cx, top),
        (cx + half, top + size * 0.05),
        (cx + half, top + size * 0.30),
        (cx + half * 0.75, bottom - notch),
        (cx, bottom),
        (cx - half * 0.75, bottom - notch),
        (cx - half, top + size * 0.30),
        (cx - half, top + size * 0.05),
    ]


def main() -> None:
    img = Image.new("RGB", (SIZE, SIZE), (15, 20, 30))
    draw = ImageDraw.Draw(img)

    _rounded_gradient_background(draw, img)

    # Outer shield (green, the "release" color), then an inner red shield to
    # echo the green/red toggle at the heart of the app.
    shield = _shield_path(SIZE)
    draw.polygon(shield, outline=(0, 200, 120), width=int(SIZE * 0.03))

    # Inner checkmark-ish accent: a bold downward chevron in red.
    cx = SIZE / 2
    cy = SIZE * 0.50
    w = SIZE * 0.18
    h = SIZE * 0.22
    chevron = [
        (cx - w, cy - h / 2),
        (cx, cy + h / 2),
        (cx + w, cy - h / 2),
        (cx + w * 0.55, cy - h / 2),
        (cx, cy + h * 0.15),
        (cx - w * 0.55, cy - h / 2),
    ]
    draw.polygon(chevron, fill=(235, 70, 70))

    out = "MyDiscipline/Assets.xcassets/AppIcon.appiconset/AppIcon.png"
    img.save(out, "PNG")
    print(f"Wrote {out} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    main()
