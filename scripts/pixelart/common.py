"""Shared helpers for the SpirandeliEmpire pixel-art pipeline."""
from PIL import Image

W_CHAR, H_CHAR = 32, 48
TILE = 32
OUTLINE = (38, 28, 42, 255)


def shade(c, amt):
    return tuple(max(0, min(255, v + amt)) for v in c[:3])


def outline_pass(img, color=OUTLINE):
    """Adds a crisp 1px outline around every opaque region (4-neighbourhood)."""
    w, h = img.size
    src = img.load()
    out = img.copy()
    dst = out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] != 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] > 200:
                    dst[x, y] = color
                    break
    return out


def with_shadow(img, cx=None, rx=None, ry=3, bottom_pad=0, alpha=70):
    """Composites a soft elliptical floor shadow under a prop."""
    from PIL import ImageDraw
    w, h = img.size
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    cx = w // 2 if cx is None else cx
    rx = (w // 2 - 2) if rx is None else rx
    yb = h - 1 - bottom_pad
    d.ellipse([cx - rx, yb - 2 * ry, cx + rx, yb], fill=(20, 10, 30, alpha))
    return Image.alpha_composite(base, img)

