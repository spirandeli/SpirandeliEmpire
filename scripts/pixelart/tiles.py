"""Floor tileset + wall textures."""
import random
from PIL import Image, ImageDraw
from .common import shade, TILE

R = random.Random(11)

FLOOR_TILES = [
    "wood_a", "wood_b", "teal_a", "teal_b", "navy_a", "navy_b", "wine_a", "wine_b",
    "steel_a", "steel_b", "marble_a", "marble_b", "checker", "studio_a", "studio_b", "concrete_a",
    "concrete_b", "hazard", "sand_a", "sand_b", "herring_a", "herring_b", "blocked", "rugstripe",
]
GID = {name: i + 1 for i, name in enumerate(FLOOR_TILES)}


def _noise(d, base, n, amt, size=1):
    for _ in range(n):
        x, y = R.randint(0, 31), R.randint(0, 31)
        c = shade(base, R.choice([-amt, amt]))
        d.rectangle([x, y, x + size - 1, y + size - 1], fill=(*c, 255))


def _tile(name):
    img = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    if name.startswith("wood"):
        base = (196, 140, 92) if name == "wood_a" else (188, 132, 86)
        d.rectangle([0, 0, 31, 31], fill=(*base, 255))
        off = 0 if name == "wood_a" else 16
        for i, y in enumerate(range(0, 32, 8)):
            c = shade(base, [0, -10, 6, -4][i])
            d.rectangle([0, y, 31, y + 7], fill=(*c, 255))
            d.line([(0, y + 7), (31, y + 7)], fill=(*shade(base, -45), 255))
            sx = (off + i * 11) % 32
            d.line([(sx, y), (sx, y + 6)], fill=(*shade(base, -45), 255))
            for _ in range(2):
                gx = R.randint(0, 26); d.line([(gx, y + 3), (gx + 4, y + 3)], fill=(*shade(c, -16), 255))
    elif name.startswith(("teal", "navy", "wine", "studio")):
        base = {"teal": (48, 112, 118), "navy": (54, 70, 120), "wine": (128, 48, 64), "studio": (52, 48, 64)}[name.split("_")[0]]
        if name.endswith("b"):
            base = shade(base, -5)
        d.rectangle([0, 0, 31, 31], fill=(*base, 255))
        _noise(d, base, 90, 10)
        if name.startswith("navy"):
            for x in range(0, 32, 8):
                for y in range(0, 32, 8):
                    d.point((x + 4, y + 4), fill=(*shade(base, 22), 255))
        if name.startswith("wine"):
            d.point((8, 8), fill=(*shade(base, 30), 255)); d.point((24, 24), fill=(*shade(base, 30), 255))
    elif name.startswith("steel"):
        base = (88, 96, 112)
        d.rectangle([0, 0, 31, 31], fill=(*base, 255))
        d.rectangle([0, 0, 31, 31], outline=(*shade(base, -30), 255))
        d.line([(1, 1), (30, 1)], fill=(*shade(base, 25), 255)); d.line([(1, 1), (1, 30)], fill=(*shade(base, 25), 255))
        for bx, by in ((4, 4), (27, 4), (4, 27), (27, 27)):
            d.point((bx, by), fill=(*shade(base, 40), 255)); d.point((bx + 1, by + 1), fill=(*shade(base, -40), 255))
        if name == "steel_b":
            for y in range(9, 24, 3):
                d.line([(9, y), (22, y)], fill=(*shade(base, -35), 255))
    elif name.startswith("marble"):
        base = (226, 224, 218) if name == "marble_a" else (214, 212, 206)
        d.rectangle([0, 0, 31, 31], fill=(*base, 255))
        d.line([(0, 31), (31, 31)], fill=(*shade(base, -30), 255)); d.line([(31, 0), (31, 31)], fill=(*shade(base, -30), 255))
        d.line([(0, 0), (30, 0)], fill=(*shade(base, 14), 255))
        x, y = R.randint(0, 10), R.randint(0, 31)
        for _ in range(6):
            nx, ny = x + R.randint(3, 6), y + R.randint(-4, 4)
            d.line([(x, y), (nx, ny)], fill=(*shade(base, -22), 255)); x, y = nx, ny
    elif name == "checker":
        for y in range(0, 32, 16):
            for x in range(0, 32, 16):
                c = (236, 234, 228) if (x + y) // 16 % 2 == 0 else (60, 64, 76)
                d.rectangle([x, y, x + 15, y + 15], fill=(*c, 255))
    elif name.startswith("concrete"):
        base = (150, 142, 136) if name == "concrete_a" else (144, 136, 130)
        d.rectangle([0, 0, 31, 31], fill=(*base, 255)); _noise(d, base, 60, 12)
        d.line([(0, 31), (31, 31)], fill=(*shade(base, -20), 255))
    elif name == "hazard":
        d.rectangle([0, 0, 31, 31], fill=(240, 190, 50, 255))
        for i in range(-32, 64, 12):
            d.polygon([(i, 0), (i + 6, 0), (i + 38, 32), (i + 32, 32)], fill=(40, 40, 46, 255))
    elif name.startswith("sand"):
        base = (222, 196, 156) if name == "sand_a" else (214, 188, 148)
        d.rectangle([0, 0, 31, 31], fill=(*base, 255))
        for k in (15, 31):
            d.line([(0, k), (31, k)], fill=(*shade(base, -28), 255)); d.line([(k, 0), (k, 31)], fill=(*shade(base, -28), 255))
        _noise(d, base, 20, 8)
    elif name.startswith("herring"):
        base = (176, 112, 70)
        d.rectangle([0, 0, 31, 31], fill=(*base, 255))
        flip = name.endswith("b")
        for i in range(0, 32, 8):
            for j in range(0, 32, 16):
                c = shade(base, R.randint(-14, 10))
                if ((i // 8) + (j // 16) + flip) % 2 == 0:
                    d.rectangle([i, j, i + 7, j + 15], fill=(*c, 255), outline=(*shade(base, -40), 255))
                else:
                    d.rectangle([i, j, i + 7, j + 15], fill=(*shade(c, 8), 255), outline=(*shade(base, -40), 255))
    elif name == "blocked":
        d.rectangle([0, 0, 31, 31], fill=(255, 0, 0, 90))
    elif name == "rugstripe":
        d.rectangle([0, 0, 31, 31], fill=(200, 80, 70, 255)); d.line([(0, 4), (31, 4)], fill=(240, 200, 120, 255))
    return img


def build_tileset():
    cols = 8
    rows = (len(FLOOR_TILES) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * TILE, rows * TILE), (0, 0, 0, 0))
    for i, n in enumerate(FLOOR_TILES):
        sheet.paste(_tile(n), ((i % cols) * TILE, (i // cols) * TILE))
    return sheet, cols, rows


# ---------------------------------------------------------------- walls
CAP = (70, 62, 78)
CAP_HI = (110, 100, 120)

WALL_STYLES = {
    "exterior": dict(face=(206, 210, 222), trim=(170, 176, 192), base=(90, 96, 116)),
    "beige":    dict(face=(232, 214, 184), trim=(206, 186, 154), base=(130, 96, 70)),
    "wood":     dict(face=(150, 92, 56),   trim=(120, 70, 40),   base=(80, 46, 28), panel=True),
    "acoustic": dict(face=(70, 58, 98),    trim=(56, 46, 80),    base=(36, 30, 50), foam=True),
    "teal":     dict(face=(70, 150, 146),  trim=(54, 126, 122),  base=(36, 70, 72)),
    "brick":    dict(face=(178, 92, 70),   trim=(150, 74, 56),   base=(80, 50, 46), brick=True),
    "gray":     dict(face=(170, 176, 190), trim=(146, 152, 168), base=(70, 76, 92)),
}


def wall_face(style):
    s = WALL_STYLES[style]
    img = Image.new("RGBA", (TILE, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 31, 7], fill=(*CAP, 255)); d.line([(0, 0), (31, 0)], fill=(*CAP_HI, 255))
    d.rectangle([0, 8, 31, 55], fill=(*s["face"], 255))
    d.line([(0, 8), (31, 8)], fill=(*shade(s["face"], -40), 255))
    d.line([(0, 9), (31, 9)], fill=(*shade(s["face"], -20), 255))
    if s.get("panel"):
        d.rectangle([3, 14, 28, 50], outline=(*s["trim"], 255)); d.line([(4, 15), (27, 15)], fill=(*shade(s["face"], 20), 255))
    elif s.get("foam"):
        for y in range(12, 54, 6):
            for x in range(0, 32, 6):
                d.rectangle([x + 1, y, x + 4, y + 3], fill=(*shade(s["face"], 14 if (x + y) % 12 == 0 else -6), 255))
    elif s.get("brick"):
        for i, y in enumerate(range(10, 54, 6)):
            d.line([(0, y), (31, y)], fill=(*shade(s["face"], -30), 255))
            for x in range((i % 2) * 8, 32, 16):
                d.line([(x, y), (x, y + 5)], fill=(*shade(s["face"], -30), 255))
    else:
        d.line([(0, 34), (31, 34)], fill=(*s["trim"], 255))   # chair rail
        d.rectangle([0, 35, 31, 55], fill=(*shade(s["face"], -10), 255))
    d.rectangle([0, 56, 31, 63], fill=(*s["base"], 255)); d.line([(0, 56), (31, 56)], fill=(*shade(s["base"], 30), 255))
    return img


def partition_glass():
    img = Image.new("RGBA", (TILE, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 31, 5], fill=(*CAP, 255)); d.line([(0, 0), (31, 0)], fill=(*CAP_HI, 255))
    d.rectangle([0, 6, 31, 31], fill=(170, 220, 240, 70))
    d.line([(0, 6), (31, 6)], fill=(200, 230, 245, 200))
    d.line([(4, 8), (12, 8)], fill=(255, 255, 255, 120)); d.line([(3, 10), (8, 26)], fill=(255, 255, 255, 60))
    d.line([(0, 6), (0, 31)], fill=(140, 150, 170, 255))
    d.rectangle([0, 32, 31, 39], fill=(100, 108, 126, 255)); d.line([(0, 32), (31, 32)], fill=(150, 160, 180, 255))
    return img


def wall_cap_v():
    img = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([8, 0, 23, 31], fill=(*CAP, 255)); d.line([(8, 0), (8, 31)], fill=(*CAP_HI, 255))
    d.line([(23, 0), (23, 31)], fill=(*shade(CAP, -25), 255))
    return img


def wall_cap_v_end():
    """Bottom end of a vertical wall: cap + small face."""
    img = Image.new("RGBA", (TILE, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([8, 0, 23, 15], fill=(*CAP, 255)); d.line([(8, 0), (8, 15)], fill=(*CAP_HI, 255))
    d.rectangle([8, 16, 23, 39], fill=(170, 176, 190, 255)); d.line([(8, 16), (23, 16)], fill=(120, 126, 140, 255))
    d.rectangle([8, 34, 23, 39], fill=(80, 86, 104, 255))
    return img


def wall_cap_h():
    img = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 6, 31, 21], fill=(*CAP, 255)); d.line([(0, 6), (31, 6)], fill=(*CAP_HI, 255))
    d.line([(0, 21), (31, 21)], fill=(*shade(CAP, -25), 255))
    return img

