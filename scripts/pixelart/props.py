"""
SpirandeliEmpire OS — furniture, decoration and environment sprites.
All drawn procedurally as original pixel art in 3/4 top-down perspective.
Each prop is returned as a PIL image; outline + floor shadow applied here.
"""
import random
from PIL import Image, ImageDraw
from .common import outline_pass, shade, with_shadow, TILE

R = random.Random(7)


def new(w, h):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def rr(d, box, c):
    d.rectangle(box, fill=(*c[:3], 255) if len(c) == 3 else c)


def box3d(d, x, y, w, top_h, front_h, top, front=None):
    """Top surface + front face, classic 3/4 furniture block."""
    front = front or shade(top, -40)
    rr(d, [x, y, x + w - 1, y + top_h - 1], top)
    rr(d, [x, y, x + w - 1, y], shade(top, 25))                         # back highlight
    rr(d, [x, y + top_h - 1, x + w - 1, y + top_h - 1], shade(top, -15))
    rr(d, [x, y + top_h, x + w - 1, y + top_h + front_h - 1], front)
    rr(d, [x, y + top_h, x + w - 1, y + top_h], shade(front, 20))


def fin(img, shadow=True, ry=3, rx=None, outline=True):
    if outline:
        img = outline_pass(img)
    if shadow:
        img = with_shadow(img, ry=ry, rx=rx)
    return img


WOOD = (186, 122, 72)
WOOD_D = (140, 86, 48)
WHITE_DESK = (232, 230, 224)
METAL = (120, 130, 148)


# ------------------------------------------------------------------ desks
def desk(color=WOOD, w=64, h=44, legs=True):
    img, d = new(w, h + 4)
    top_h, front_h = 24, 14
    if legs:
        rr(d, [3, top_h, 6, h], shade(color, -50)); rr(d, [w - 7, top_h, w - 4, h], shade(color, -50))
    box3d(d, 1, 2, w - 2, top_h, front_h, color)
    # drawer column
    rr(d, [w - 22, top_h + 2, w - 4, top_h + front_h + 6], shade(color, -30))
    rr(d, [w - 15, top_h + 6, w - 11, top_h + 6], shade(color, 40))
    rr(d, [w - 15, top_h + 13, w - 11, top_h + 13], shade(color, 40))
    return fin(img)


def desk_exec():
    img, d = new(96, 56)
    box3d(d, 1, 4, 94, 26, 22, (120, 62, 32), (92, 44, 22))
    rr(d, [6, 33, 30, 49], (104, 52, 26)); rr(d, [66, 33, 90, 49], (104, 52, 26))
    for yy in (38, 44):
        rr(d, [15, yy, 21, yy], (230, 190, 80)); rr(d, [75, yy, 81, yy], (230, 190, 80))
    rr(d, [34, 36, 62, 46], (82, 38, 18))                          # modesty panel inlay
    rr(d, [22, 9, 74, 25], (40, 34, 30)); rr(d, [23, 10, 73, 24], (60, 50, 44))   # leather blotter
    rr(d, [80, 9, 86, 15], (230, 190, 80)); rr(d, [82, 6, 83, 9], (40, 40, 50))   # pen holder
    rr(d, [8, 10, 18, 18], (250, 250, 245)); rr(d, [9, 12, 17, 12], (160, 160, 170)); rr(d, [9, 14, 15, 14], (160, 160, 170))
    return fin(img)


def reception_desk():
    img, d = new(128, 60)
    box3d(d, 1, 4, 126, 18, 30, (238, 236, 230), (60, 150, 140))
    rr(d, [1, 23, 126, 26], (230, 190, 80))
    for x in range(8, 120, 16):
        rr(d, [x, 30, x + 10, 48], (50, 132, 124))
    rr(d, [52, 32, 76, 44], (36, 40, 56)); rr(d, [56, 35, 72, 41], (230, 190, 80))   # logo plate
    rr(d, [60, 36, 68, 40], (36, 40, 56))
    return fin(img)


def conference_table():
    img, d = new(192, 72)
    rr(d, [20, 44, 28, 66], (70, 40, 26)); rr(d, [164, 44, 172, 66], (70, 40, 26))
    box3d(d, 2, 6, 188, 46, 10, (150, 92, 54), (110, 64, 36))
    rr(d, [10, 12, 182, 46], (164, 104, 62))
    rr(d, [70, 24, 122, 32], (40, 44, 60))                         # cable tray
    for x in range(76, 120, 10):
        rr(d, [x, 26, x + 4, 29], (20, 24, 32)); d.point((x + 2, 27), fill=(80, 220, 120, 255))
    # documents & laptops on table
    for (x, y) in ((30, 16), (60, 36), (134, 16), (156, 36)):
        rr(d, [x, y, x + 10, y + 7], (250, 250, 245)); rr(d, [x + 1, y + 2, x + 8, y + 2], (170, 170, 180))
    for (x, y) in ((96, 14), (100, 36)):
        rr(d, [x, y, x + 14, y + 8], (60, 66, 80)); rr(d, [x + 1, y + 1, x + 13, y + 6], (120, 200, 240))
    return fin(img, ry=4)


def coffee_table():
    img, d = new(48, 28)
    rr(d, [5, 14, 7, 25], (60, 50, 50)); rr(d, [40, 14, 42, 25], (60, 50, 50))
    box3d(d, 1, 4, 46, 14, 5, (200, 160, 110))
    rr(d, [8, 7, 13, 11], (240, 240, 240)); rr(d, [9, 8, 12, 9], (110, 60, 30))     # mug
    rr(d, [26, 6, 40, 13], (220, 60, 70)); rr(d, [28, 8, 38, 8], (250, 250, 250))   # magazine
    return fin(img)


def kitchen_counter(w=128):
    img, d = new(w, 56)
    box3d(d, 1, 14, w - 2, 14, 26, (226, 226, 222), (90, 110, 140))
    for x in range(4, w - 20, 24):
        rr(d, [x, 31, x + 20, 52], (100, 122, 152)); rr(d, [x + 16, 38, x + 17, 44], (220, 220, 230))
    # espresso machine
    rr(d, [10, 0, 34, 20], (50, 54, 66)); rr(d, [12, 2, 32, 6], (200, 205, 215)); rr(d, [18, 10, 24, 13], (150, 155, 170))
    d.point((14, 9), fill=(80, 220, 120, 255)); d.point((16, 9), fill=(240, 180, 40, 255))
    rr(d, [19, 15, 23, 19], (250, 250, 250))
    # fruit bowl, kettle, mugs
    rr(d, [48, 10, 64, 18], (240, 240, 240)); d.ellipse([50, 6, 56, 12], fill=(230, 60, 50)); d.ellipse([55, 5, 61, 11], fill=(240, 200, 40))
    rr(d, [78, 6, 88, 18], (200, 70, 60)); rr(d, [88, 9, 90, 13], (200, 70, 60))
    for x in (100, 108):
        rr(d, [x, 12, x + 5, 18], (250, 250, 250))
    # sink
    rr(d, [w - 30, 17, w - 10, 24], (170, 178, 190)); rr(d, [w - 22, 10, w - 20, 17], (190, 196, 206))
    return fin(img)


# ------------------------------------------------------------------ seating
def chair_back(color=(52, 62, 86)):
    """Office chair seen from BEHIND (rendered in front of a seated agent)."""
    img, d = new(28, 26)
    rr(d, [4, 0, 23, 13], color); rr(d, [5, 1, 22, 2], shade(color, 30)); rr(d, [6, 4, 21, 11], shade(color, -15))
    rr(d, [12, 13, 15, 18], (70, 74, 86))
    rr(d, [3, 16, 24, 19], (60, 64, 76))
    rr(d, [2, 19, 4, 22], (40, 40, 50)); rr(d, [23, 19, 25, 22], (40, 40, 50)); rr(d, [12, 20, 15, 23], (40, 40, 50))
    return fin(img, ry=2)


def chair_front(color=(52, 62, 86), w=28):
    """Empty office chair seen from the front."""
    img, d = new(w, 36)
    rr(d, [6, 0, w - 7, 14], color); rr(d, [7, 1, w - 8, 2], shade(color, 30))
    box3d(d, 4, 14, w - 8, 7, 4, shade(color, 10))
    rr(d, [2, 12, 4, 21], (70, 74, 86)); rr(d, [w - 5, 12, w - 3, 21], (70, 74, 86))
    rr(d, [w // 2 - 2, 25, w // 2 + 1, 29], (70, 74, 86))
    rr(d, [4, 29, w - 5, 31], (60, 64, 76))
    return fin(img, ry=2)


def chair_exec():
    img, d = new(36, 44)
    c = (90, 46, 30)
    rr(d, [5, 0, 30, 26], c); rr(d, [6, 1, 29, 3], shade(c, 35))
    for x in (11, 18, 25):
        for y in (8, 15):
            d.point((x, y), fill=(*shade(c, -30), 255))
    rr(d, [2, 18, 7, 30], shade(c, 10)); rr(d, [28, 18, 33, 30], shade(c, 10))
    box3d(d, 6, 26, 24, 6, 4, shade(c, 15))
    rr(d, [16, 36, 19, 40], (60, 60, 70))
    return fin(img, ry=2)


def sofa(color=(70, 120, 150), w=96):
    img, d = new(w, 44)
    rr(d, [6, 2, w - 7, 20], color); rr(d, [7, 3, w - 8, 4], shade(color, 30))
    n = 3 if w >= 90 else 2
    cw = (w - 16) // n
    for i in range(n):
        x = 8 + i * cw
        box3d(d, x, 18, cw - 1, 10, 8, shade(color, 12), shade(color, -30))
    rr(d, [1, 10, 8, 36], shade(color, -10)); rr(d, [w - 9, 10, w - 2, 36], shade(color, -10))
    rr(d, [1, 10, 8, 11], shade(color, 25)); rr(d, [w - 9, 10, w - 2, 11], shade(color, 25))
    rr(d, [12, 8, 22, 18], (240, 190, 60)); rr(d, [w - 23, 8, w - 13, 18], (240, 240, 230))
    rr(d, [6, 37, 8, 40], (50, 40, 40)); rr(d, [w - 9, 37, w - 7, 40], (50, 40, 40))
    return fin(img, ry=3)


def armchair(color=(200, 90, 70)):
    img, d = new(36, 40)
    rr(d, [6, 2, 29, 18], color); rr(d, [7, 3, 28, 4], shade(color, 30))
    box3d(d, 7, 16, 22, 9, 7, shade(color, 12), shade(color, -30))
    rr(d, [1, 10, 7, 32], shade(color, -10)); rr(d, [28, 10, 34, 32], shade(color, -10))
    return fin(img)


def beanbag(color=(240, 170, 40)):
    img, d = new(30, 24)
    d.ellipse([1, 4, 28, 22], fill=(*color, 255)); d.ellipse([5, 2, 22, 14], fill=(*shade(color, 25), 255))
    return fin(img, ry=2)


# ------------------------------------------------------------------ computers
def monitor(kind="code", w=26, h=22):
    img, d = new(w, h)
    rr(d, [w // 2 - 2, h - 7, w // 2 + 1, h - 3], (60, 64, 76)); rr(d, [w // 2 - 6, h - 3, w // 2 + 5, h - 2], (60, 64, 76))
    rr(d, [0, 0, w - 1, h - 7], (30, 32, 42))
    sx0, sy0, sx1, sy1 = 2, 2, w - 3, h - 9
    rr(d, [sx0, sy0, sx1, sy1], (14, 20, 36))
    _screen(d, kind, sx0, sy0, sx1, sy1)
    return fin(img, shadow=False)


def _screen(d, kind, x0, y0, x1, y1):
    cols = [(90, 200, 250), (250, 200, 70), (120, 230, 140), (200, 130, 250), (250, 110, 120)]
    if kind == "code":
        y = y0 + 1
        while y < y1:
            ind = R.choice([0, 2, 4])
            ln = R.randint(3, x1 - x0 - ind - 1)
            rr(d, [x0 + 1 + ind, y, x0 + 1 + ind + ln, y], R.choice(cols)); y += 2
    elif kind == "chart":
        rr(d, [x0, y0, x1, y1], (16, 30, 40))
        pts = [(x, y1 - 1 - R.randint(0, y1 - y0 - 2)) for x in range(x0 + 1, x1, 3)]
        d.line(pts, fill=(80, 230, 140, 255))
        for i, x in enumerate(range(x0 + 2, x1 - 1, 4)):
            rr(d, [x, y1 - 1 - (i * 3 % (y1 - y0 - 1)), x + 1, y1 - 1], (70, 140, 250))
    elif kind == "dash":
        rr(d, [x0, y0, x1, y0 + 2], (40, 70, 160))
        for i in range(3):
            c = [(80, 220, 120), (240, 190, 60), (80, 220, 120)][i]
            rr(d, [x0 + 1 + i * ((x1 - x0) // 3), y0 + 4, x0 + (i + 1) * ((x1 - x0) // 3) - 1, y1 - 1], (24, 34, 54))
            d.point((x0 + 2 + i * ((x1 - x0) // 3), y0 + 5), fill=(*c, 255))
    elif kind == "timeline":
        rr(d, [x0, y0, x1, y0 + (y1 - y0) // 2], (60, 80, 120))
        rr(d, [x0 + 2, y0 + 1, x1 - 2, y0 + (y1 - y0) // 2 - 1], (240, 140, 90))
        for t, c in enumerate([(70, 140, 250), (200, 100, 250), (90, 220, 130)]):
            yy = y0 + (y1 - y0) // 2 + 2 + t * 2
            if yy < y1:
                xs = x0 + 1 + R.randint(0, 4)
                rr(d, [xs, yy, min(x1 - 1, xs + R.randint(6, x1 - x0 - 4)), yy], c)
    elif kind == "wave":
        mid = (y0 + y1) // 2
        for x in range(x0 + 1, x1):
            a = R.randint(0, (y1 - y0) // 2 - 1)
            rr(d, [x, mid - a, x, mid + a], (170, 110, 250))
    elif kind == "design":
        rr(d, [x0, y0, x1, y1], (240, 236, 230))
        d.ellipse([x0 + 2, y0 + 1, x0 + 9, y1 - 1], fill=(240, 90, 150, 255))
        rr(d, [x0 + 10, y0 + 2, x1 - 2, y0 + 4], (60, 120, 240)); rr(d, [x0 + 10, y0 + 6, x1 - 5, y0 + 7], (250, 190, 50))
    elif kind == "news":
        rr(d, [x0, y0, x1, y0 + 2], (200, 40, 50))
        for yy in range(y0 + 4, y1, 2):
            rr(d, [x0 + 1, yy, x1 - R.randint(1, 6), yy], (210, 214, 224))
    elif kind == "subs":
        rr(d, [x0, y0, x1, y1], (30, 30, 40))
        rr(d, [x0 + 3, y1 - 3, x1 - 3, y1 - 2], (250, 250, 250)); rr(d, [x0 + 6, y1 - 5, x1 - 6, y1 - 5], (250, 230, 80))
    elif kind == "test":
        for i, yy in enumerate(range(y0 + 1, y1, 2)):
            c = (90, 220, 120) if i % 4 != 2 else (240, 80, 80)
            d.point((x0 + 1, yy), fill=(*c, 255)); rr(d, [x0 + 3, yy, x0 + 3 + R.randint(4, x1 - x0 - 5), yy], (180, 190, 210))
    elif kind == "script":
        rr(d, [x0, y0, x1, y1], (245, 242, 230))
        for yy in range(y0 + 1, y1, 2):
            rr(d, [x0 + 2, yy, x1 - R.randint(2, 8), yy], (90, 90, 110))


def dual_monitor(k1="code", k2="chart"):
    a = monitor(k1); b = monitor(k2)
    img = Image.new("RGBA", (52, 22), (0, 0, 0, 0))
    img.alpha_composite(a, (0, 0)); img.alpha_composite(b, (26, 0))
    return img


def ultrawide(kind="timeline"):
    return monitor(kind, w=44, h=24)


def monitor_back():
    img, d = new(26, 22)
    rr(d, [1, 0, 24, 14], (44, 46, 58)); rr(d, [3, 2, 22, 12], (54, 58, 72))
    rr(d, [11, 15, 14, 19], (60, 64, 76)); rr(d, [7, 19, 18, 20], (60, 64, 76))
    d.point((12, 7), fill=(200, 200, 220, 255))
    return fin(img, shadow=False)


def laptop(kind="code"):
    img, d = new(22, 16)
    rr(d, [2, 0, 19, 10], (50, 54, 66)); rr(d, [3, 1, 18, 9], (14, 20, 36)); _screen(d, kind, 3, 1, 18, 9)
    rr(d, [0, 11, 21, 14], (170, 176, 190)); rr(d, [3, 12, 18, 12], (120, 126, 140))
    return fin(img, shadow=False)


def keyboard():
    img, d = new(20, 7)
    rr(d, [0, 0, 19, 5], (60, 64, 78))
    for x in range(1, 19, 2):
        d.point((x, 1), fill=(170, 176, 190, 255)); d.point((x, 3), fill=(170, 176, 190, 255))
    return outline_pass(img)


# ------------------------------------------------------------------ storage
def bookshelf(w=48, h=72):
    img, d = new(w, h)
    c = (128, 78, 44)
    box3d(d, 1, 0, w - 2, 6, h - 8, shade(c, 10), c)
    rr(d, [4, 8, w - 5, h - 5], (70, 40, 24))
    shelves = range(8, h - 6, 15)
    bc = [(220, 70, 70), (70, 120, 220), (90, 190, 110), (240, 190, 60), (170, 100, 220), (240, 240, 230), (240, 130, 60)]
    for sy in shelves:
        rr(d, [4, sy + 13, w - 5, sy + 14], shade(c, 20))
        x = 5
        while x < w - 8:
            if R.random() < 0.15:
                x += 4; continue
            bw = R.choice([2, 3, 3, 4]); bh = R.randint(8, 12)
            rr(d, [x, sy + 13 - bh, x + bw - 1, sy + 12], R.choice(bc)); x += bw + 1
    return fin(img)


def filing_cabinet():
    img, d = new(26, 44)
    box3d(d, 1, 0, 24, 6, 34, (150, 160, 176), (120, 130, 148))
    for y in (10, 21, 32):
        rr(d, [4, y, 21, y + 8], (134, 144, 160)); rr(d, [10, y + 3, 15, y + 4], (210, 214, 224))
    rr(d, [6, 1, 12, 4], (250, 250, 245))
    return fin(img)


def server_rack(variant=0):
    img, d = new(36, 76)
    box3d(d, 1, 0, 34, 8, 64, (52, 58, 74), (26, 30, 42))
    for i, y in enumerate(range(12, 68, 7)):
        rr(d, [4, y, 31, y + 5], (40, 46, 62)); rr(d, [4, y, 31, y], (64, 72, 92))
        for j, x in enumerate(range(6, 14, 3)):
            col = [(80, 230, 120), (80, 200, 250), (250, 190, 50)][(i + j + variant) % 3]
            d.point((x, y + 3), fill=(*col, 255))
        for x in range(16, 30, 3):
            rr(d, [x, y + 2, x + 1, y + 4], (22, 26, 36))
    rr(d, [3, 10, 3, 66], (120, 200, 250, 160))
    return fin(img)


def network_cabinet():
    img, d = new(36, 44)
    box3d(d, 1, 0, 34, 7, 32, (70, 78, 96), (44, 50, 66))
    for y in (11, 18, 25):
        rr(d, [4, y, 31, y + 4], (30, 34, 46))
        for x in range(6, 30, 2):
            d.point((x, y + 2), fill=(*([(80, 230, 120), (250, 190, 50)][(x // 2 + y) % 2]), 255))
    # cable bundle
    for i, col in enumerate([(60, 120, 230), (240, 190, 50), (230, 70, 70)]):
        rr(d, [8 + i * 3, 33, 9 + i * 3, 41], col)
    return fin(img)


def ups_unit():
    img, d = new(28, 30)
    box3d(d, 1, 0, 26, 6, 20, (40, 44, 56), (28, 30, 40))
    rr(d, [6, 10, 21, 15], (20, 60, 40)); rr(d, [7, 11, 16, 14], (80, 230, 120))
    return fin(img)


def monitoring_wall():
    """Wall-mounted NOC screens (no shadow)."""
    img, d = new(104, 40)
    kinds = ["chart", "dash", "chart", "dash", "chart", "code"]
    for i in range(3):
        for j in range(2):
            x = i * 35; y = j * 20
            rr(d, [x, y, x + 33, y + 18], (24, 26, 36)); rr(d, [x + 2, y + 2, x + 31, y + 16], (12, 18, 32))
            _screen(d, kinds[i * 2 + j], x + 2, y + 2, x + 31, y + 16)
    return outline_pass(img)


# ------------------------------------------------------------------ boards & wall decor
def whiteboard(w=72, h=44, kanban=True):
    img, d = new(w, h)
    rr(d, [0, 0, w - 1, h - 5], (180, 186, 200)); rr(d, [2, 2, w - 3, h - 7], (248, 248, 250))
    if kanban:
        cols = 3
        cw = (w - 4) // cols
        for i in range(1, cols):
            rr(d, [2 + i * cw, 3, 2 + i * cw, h - 8], (200, 206, 218))
        sticky = [(250, 210, 70), (250, 140, 180), (110, 200, 250), (130, 230, 140)]
        for i in range(cols):
            for k in range(R.randint(2, 4)):
                x = 5 + i * cw + (k % 2) * 10; y = 5 + (k // 2) * 9
                rr(d, [x, y, x + 7, y + 6], R.choice(sticky))
    else:
        d.line([(8, 30), (18, 18), (28, 24), (40, 10), (52, 16)], fill=(60, 120, 230, 255))
        rr(d, [8, 6, 30, 6], (230, 70, 70)); rr(d, [8, 9, 24, 9], (60, 60, 80))
        d.ellipse([46, 24, 62, 34], outline=(50, 170, 90, 255))
    rr(d, [w // 4, h - 5, 3 * w // 4, h - 3], (150, 156, 170))
    rr(d, [w // 4 + 3, h - 6, w // 4 + 7, h - 6], (230, 70, 70)); rr(d, [w // 4 + 9, h - 6, w // 4 + 13, h - 6], (60, 120, 230))
    return outline_pass(img)


def tv_screen(w=96, h=54, kind="dash"):
    img, d = new(w, h)
    rr(d, [0, 0, w - 1, h - 1], (24, 26, 36)); rr(d, [3, 3, w - 4, h - 4], (10, 16, 30))
    if kind == "graph":
        rr(d, [3, 3, w - 4, 10], (40, 60, 150)); rr(d, [6, 5, 10, 8], (240, 190, 60)); rr(d, [14, 6, 50, 6], (230, 230, 240))
        nodes = [(18, 26), (48, 22), (78, 26), (48, 42), (20, 44)]
        for a, b in ((0, 1), (1, 2), (1, 3), (3, 4)):
            d.line([nodes[a], nodes[b]], fill=(110, 120, 250, 255))
        for i, (x, y) in enumerate(nodes):
            c = (240, 190, 60) if i == 1 else (40, 190, 170)
            rr(d, [x - 4, y - 3, x + 4, y + 3], c)
    else:
        _screen(d, kind, 3, 3, w - 4, h - 4)
    return outline_pass(img)


def painting(kind=0, w=40, h=30):
    img, d = new(w, h)
    frame = [(200, 160, 70), (60, 50, 50), (240, 240, 240)][kind % 3]
    rr(d, [0, 0, w - 1, h - 1], frame); rr(d, [3, 3, w - 4, h - 4], (240, 230, 210))
    if kind == 0:  # landscape
        rr(d, [3, 3, w - 4, h // 2], (130, 200, 240)); rr(d, [3, h // 2, w - 4, h - 4], (90, 170, 90))
        d.polygon([(8, h // 2), (18, 8), (28, h // 2)], fill=(120, 130, 150, 255)); d.ellipse([w - 14, 6, w - 8, 12], fill=(250, 220, 90, 255))
    elif kind == 1:  # abstract
        rr(d, [3, 3, w - 4, h - 4], (30, 34, 50))
        d.ellipse([8, 6, 22, 20], fill=(240, 90, 120, 255)); rr(d, [20, 12, w - 6, 16], (250, 200, 60)); rr(d, [12, 18, 16, h - 6], (90, 200, 230))
    else:  # chart poster
        rr(d, [3, 3, w - 4, h - 4], (250, 250, 250))
        for i, x in enumerate(range(8, w - 8, 6)):
            hh = 4 + (i * 5) % (h - 12)
            rr(d, [x, h - 6 - hh, x + 3, h - 6], [(70, 130, 240), (90, 200, 120), (250, 170, 60)][i % 3])
    return outline_pass(img)


def empire_crest():
    img, d = new(48, 40)
    rr(d, [0, 0, 47, 39], (30, 34, 56)); rr(d, [2, 2, 45, 37], (44, 50, 86))
    d.polygon([(12, 16), (16, 7), (20, 13), (24, 5), (28, 13), (32, 7), (36, 16)], fill=(240, 190, 60, 255))
    rr(d, [12, 16, 36, 18], (240, 190, 60))
    rr(d, [18, 21, 30, 33], (110, 110, 240))
    for y in (23, 27, 31):
        rr(d, [20, y, 28, y], (250, 250, 250))
    rr(d, [20, 23, 20, 27], (250, 250, 250)); rr(d, [28, 27, 28, 31], (250, 250, 250))
    return outline_pass(img)


def wall_clock():
    img, d = new(18, 18)
    d.ellipse([0, 0, 17, 17], fill=(250, 250, 250, 255), outline=(40, 40, 50, 255))
    d.line([(9, 9), (9, 4)], fill=(30, 30, 40, 255)); d.line([(9, 9), (13, 10)], fill=(220, 60, 60, 255))
    return outline_pass(img)


def acoustic_panel():
    img, d = new(32, 32)
    for y in range(0, 32, 8):
        for x in range(0, 32, 8):
            c = (60, 50, 90) if ((x + y) // 8) % 2 == 0 else (80, 66, 120)
            rr(d, [x, y, x + 7, y + 7], c); rr(d, [x + 1, y + 1, x + 6, y + 1], shade(c, 25))
    return outline_pass(img)


def neon_sign(text_color=(250, 90, 180)):
    img, d = new(60, 20)
    rr(d, [0, 0, 59, 19], (30, 26, 44))
    # stylised "ON AIR"-like glyph blocks (no real text)
    for i, x in enumerate(range(6, 54, 9)):
        rr(d, [x, 5, x + 5, 14], text_color if i % 2 == 0 else shade(text_color, -40))
        rr(d, [x + 2, 7, x + 3, 12], (30, 26, 44))
    return outline_pass(img)


def window(w=64, h=48, night=False):
    img, d = new(w, h)
    rr(d, [0, 0, w - 1, h - 1], (230, 230, 236))
    sky_top, sky_bot = ((120, 190, 245), (200, 232, 255))
    for y in range(3, h - 6):
        t = (y - 3) / (h - 9)
        c = tuple(int(sky_top[i] + (sky_bot[i] - sky_top[i]) * t) for i in range(3))
        rr(d, [3, y, w - 4, y], c)
    for i, x in enumerate(range(5, w - 8, 9)):
        bh = R.randint(10, h - 14)
        col = [(150, 180, 220), (120, 160, 210), (170, 196, 230)][i % 3]
        rr(d, [x, h - 6 - bh, x + 7, h - 7], col)
        for wy in range(h - 4 - bh, h - 8, 3):
            d.point((x + 2, wy), fill=(250, 250, 255, 255)); d.point((x + 5, wy), fill=(250, 250, 255, 255))
    rr(d, [w // 2 - 1, 3, w // 2, h - 6], (230, 230, 236))
    d.polygon([(8, 3), (16, 3), (4, 22), (3, 22), (3, 12)], fill=(255, 255, 255, 80))
    rr(d, [0, h - 6, w - 1, h - 1], (210, 210, 218)); rr(d, [0, h - 6, w - 1, h - 6], (250, 250, 250))
    return outline_pass(img)


# ------------------------------------------------------------------ plants & misc
def plant(kind="monstera"):
    if kind == "monstera":
        img, d = new(34, 48)
        d.polygon([(10, 34), (24, 34), (22, 46), (12, 46)], fill=(196, 110, 70, 255)); rr(d, [9, 32, 25, 35], (220, 130, 86))
        leaves = [(3, 12, 17, 28), (16, 8, 31, 24), (9, 2, 24, 18), (11, 18, 26, 33), (2, 22, 14, 33)]
        for i, (a, b, c, e) in enumerate(leaves):
            col = [(40, 140, 70), (60, 170, 90), (50, 155, 80)][i % 3]
            d.ellipse([a, b, c, e], fill=(*col, 255))
            d.line([((a + c) // 2, b + 2), ((a + c) // 2, e - 2)], fill=(*shade(col, 40), 255))
        return fin(img, ry=2, rx=11)
    if kind == "snake":
        img, d = new(24, 42)
        rr(d, [6, 30, 17, 40], (240, 240, 236)); rr(d, [5, 28, 18, 31], (250, 250, 250))
        for x, top in ((8, 4), (12, 0), (16, 6), (10, 10), (14, 12)):
            d.polygon([(x - 2, 29), (x, top), (x + 2, 29)], fill=(50, 140, 70, 255))
            d.line([(x, top + 3), (x, 27)], fill=(200, 210, 90, 255))
        return fin(img, ry=2, rx=8)
    if kind == "tree":
        img, d = new(40, 64)
        rr(d, [12, 50, 27, 62], (90, 96, 110)); rr(d, [11, 48, 28, 51], (110, 116, 130))
        rr(d, [18, 26, 21, 49], (110, 70, 40))
        for (x, y, r) in ((20, 14, 12), (10, 22, 9), (30, 22, 9), (20, 28, 10), (14, 8, 7), (27, 9, 7)):
            d.ellipse([x - r, y - r, x + r, y + r], fill=(*R.choice([(40, 140, 70), (60, 170, 90), (34, 120, 60)]), 255))
        for _ in range(12):
            d.point((R.randint(6, 34), R.randint(4, 34)), fill=(120, 210, 120, 255))
        return fin(img, ry=3, rx=13)
    if kind == "small":
        img, d = new(14, 16)
        rr(d, [3, 9, 10, 15], (230, 120, 80)); d.ellipse([1, 1, 12, 11], fill=(70, 170, 90, 255))
        return outline_pass(img)
    if kind == "cactus":
        img, d = new(16, 26)
        rr(d, [3, 18, 12, 25], (200, 110, 70)); rr(d, [6, 4, 9, 18], (70, 160, 90)); rr(d, [2, 8, 4, 13], (70, 160, 90)); rr(d, [11, 6, 13, 12], (70, 160, 90))
        return fin(img, ry=1)


def water_cooler():
    img, d = new(22, 46)
    box3d(d, 2, 16, 18, 5, 23, (236, 238, 242), (212, 216, 224))
    rr(d, [6, 24, 15, 31], (90, 100, 120)); rr(d, [7, 25, 9, 26], (70, 140, 240)); rr(d, [12, 25, 14, 26], (230, 70, 70))
    d.rounded_rectangle([4, 1, 17, 17], radius=3, fill=(120, 200, 250, 230)); rr(d, [7, 3, 8, 14], (220, 240, 255))
    return fin(img, ry=2)


def vending_machine():
    img, d = new(36, 72)
    box3d(d, 1, 0, 34, 7, 62, (200, 50, 60), (170, 36, 46))
    rr(d, [4, 10, 24, 56], (30, 36, 50))
    for y in range(12, 54, 8):
        for x in range(6, 22, 5):
            rr(d, [x, y, x + 3, y + 5], R.choice([(240, 190, 60), (80, 200, 120), (80, 150, 240), (240, 90, 90)]))
    rr(d, [27, 14, 32, 30], (40, 40, 50)); rr(d, [6, 59, 24, 64], (20, 20, 26))
    return fin(img)


def fridge():
    img, d = new(32, 70)
    box3d(d, 1, 0, 30, 6, 62, (236, 238, 242), (214, 218, 226))
    rr(d, [1, 30, 30, 30], (180, 186, 196)); rr(d, [25, 12, 26, 26], (160, 166, 178)); rr(d, [25, 34, 26, 46], (160, 166, 178))
    rr(d, [5, 12, 12, 18], (250, 210, 70)); rr(d, [14, 14, 19, 19], (110, 200, 250))
    return fin(img)


def trash_bin():
    img, d = new(14, 18)
    rr(d, [1, 3, 12, 16], (90, 100, 120)); rr(d, [0, 2, 13, 4], (120, 130, 150)); rr(d, [3, 0, 10, 2], (230, 230, 230))
    return fin(img, ry=1)


def floor_lamp():
    img, d = new(20, 58)
    d.polygon([(3, 12), (17, 12), (14, 0), (6, 0)], fill=(250, 236, 190, 255))
    rr(d, [9, 12, 10, 52], (60, 60, 70)); rr(d, [4, 52, 15, 54], (60, 60, 70))
    return fin(img, ry=2, rx=7)


def desk_lamp():
    img, d = new(12, 14)
    rr(d, [2, 12, 9, 13], (50, 50, 60)); rr(d, [5, 4, 6, 12], (50, 50, 60)); rr(d, [3, 1, 11, 4], (250, 200, 60))
    return outline_pass(img)


def mic_stand():
    img, d = new(18, 50)
    rr(d, [8, 12, 9, 46], (60, 64, 76)); d.line([(8, 46), (2, 49)], fill=(60, 64, 76, 255)); d.line([(9, 46), (15, 49)], fill=(60, 64, 76, 255))
    d.line([(9, 14), (14, 8)], fill=(60, 64, 76, 255))
    d.ellipse([10, 0, 17, 9], fill=(40, 40, 50, 255)); d.ellipse([11, 1, 16, 8], fill=(150, 150, 170, 255))
    rr(d, [9, 1, 9, 9], (220, 60, 160))   # pop filter ring
    return fin(img, ry=1, rx=7)


def desk_mic():
    img, d = new(12, 16)
    rr(d, [3, 13, 8, 15], (40, 40, 50)); rr(d, [5, 6, 6, 13], (40, 40, 50)); d.ellipse([2, 0, 9, 8], fill=(160, 160, 180, 255))
    return outline_pass(img)


def headphones():
    img, d = new(14, 10)
    d.arc([1, 0, 12, 12], 180, 360, fill=(40, 40, 50, 255), width=2); rr(d, [0, 5, 3, 9], (130, 80, 230)); rr(d, [10, 5, 13, 9], (130, 80, 230))
    return outline_pass(img)


def mixer():
    img, d = new(36, 16)
    box3d(d, 1, 0, 34, 10, 4, (50, 54, 66))
    for x in range(4, 32, 4):
        rr(d, [x, 2, x, 8], (30, 30, 40)); rr(d, [x - 1, 2 + (x * 7) % 6, x + 1, 3 + (x * 7) % 6], (230, 230, 240))
    d.point((32, 2), fill=(80, 230, 120, 255)); d.point((32, 4), fill=(250, 190, 50, 255))
    return outline_pass(img)


def drawing_tablet():
    img, d = new(22, 12)
    rr(d, [0, 0, 21, 11], (40, 42, 54)); rr(d, [3, 2, 18, 9], (70, 74, 90)); rr(d, [17, 4, 20, 5], (220, 220, 230))
    return outline_pass(img)


def camera_tripod():
    img, d = new(34, 52)
    d.line([(16, 22), (5, 50)], fill=(60, 64, 76, 255), width=2); d.line([(16, 22), (27, 50)], fill=(60, 64, 76, 255), width=2); d.line([(16, 22), (16, 50)], fill=(50, 54, 66, 255), width=2)
    rr(d, [7, 8, 25, 22], (30, 32, 42)); rr(d, [25, 10, 32, 20], (50, 54, 66)); d.ellipse([28, 11, 33, 19], fill=(110, 190, 250, 255))
    rr(d, [10, 4, 18, 7], (70, 74, 90)); d.point((10, 11), fill=(240, 50, 50, 255))
    return fin(img, ry=2, rx=12)


def softbox():
    img, d = new(32, 56)
    d.line([(16, 24), (5, 54)], fill=(60, 64, 76, 255), width=2); d.line([(16, 24), (27, 54)], fill=(60, 64, 76, 255), width=2)
    rr(d, [1, 2, 30, 24], (30, 32, 42)); rr(d, [4, 5, 27, 21], (255, 250, 226))
    return fin(img, ry=2, rx=12)


def ring_light():
    img, d = new(28, 56)
    d.ellipse([2, 0, 25, 23], outline=(255, 250, 226, 255), width=3)
    rr(d, [13, 23, 14, 52], (60, 64, 76)); d.line([(13, 52), (5, 55)], fill=(60, 64, 76, 255)); d.line([(14, 52), (22, 55)], fill=(60, 64, 76, 255))
    return fin(img, ry=1, rx=9)


def green_screen():
    img, d = new(96, 72)
    rr(d, [2, 0, 3, 70], (60, 64, 76)); rr(d, [92, 0, 93, 70], (60, 64, 76)); rr(d, [0, 0, 95, 3], (60, 64, 76))
    rr(d, [4, 4, 91, 64], (60, 200, 100)); rr(d, [4, 58, 91, 66], (50, 180, 90))
    for x in range(10, 90, 14):
        rr(d, [x, 6, x, 56], (70, 214, 112))
    return fin(img, ry=3)


def arcade():
    img, d = new(32, 66)
    box3d(d, 1, 0, 30, 6, 58, (60, 40, 120), (44, 28, 96))
    rr(d, [5, 10, 26, 28], (20, 20, 30)); rr(d, [7, 12, 24, 26], (40, 200, 230)); rr(d, [10, 15, 13, 18], (250, 200, 60)); rr(d, [17, 20, 21, 22], (240, 80, 120))
    box3d(d, 3, 30, 26, 6, 4, (80, 60, 150)); d.point((9, 32), fill=(240, 60, 60, 255)); d.point((20, 32), fill=(60, 200, 240, 255)); d.point((23, 33), fill=(250, 200, 60, 255))
    rr(d, [4, 2, 27, 5], (250, 90, 180))
    return fin(img)


def foosball():
    img, d = new(80, 46)
    rr(d, [6, 28, 9, 44], (60, 40, 30)); rr(d, [70, 28, 73, 44], (60, 40, 30))
    box3d(d, 2, 4, 76, 26, 8, (60, 160, 80), (110, 70, 40))
    rr(d, [4, 6, 75, 27], (70, 180, 90)); rr(d, [39, 6, 40, 27], (250, 250, 250))
    for i, x in enumerate(range(10, 72, 9)):
        rr(d, [x, 2, x, 32], (200, 200, 210))
        rr(d, [x - 1, 12, x + 1, 15], (230, 60, 60) if i % 2 == 0 else (60, 110, 230))
    return fin(img)


def rug(w=128, h=80, c1=(200, 90, 70), c2=(240, 200, 120), round_=False):
    img, d = new(w, h)
    if round_:
        d.ellipse([0, 0, w - 1, h - 1], fill=(*c1, 255)); d.ellipse([6, 5, w - 7, h - 6], outline=(*c2, 255), width=2)
        d.ellipse([w // 3, h // 3, 2 * w // 3, 2 * h // 3], outline=(*c2, 255), width=2)
    else:
        rr(d, [0, 0, w - 1, h - 1], c1); d.rectangle([5, 5, w - 6, h - 6], outline=(*c2, 255), width=2)
        for x in range(12, w - 12, 12):
            d.point((x, h // 2), fill=(*c2, 255))
        d.rectangle([14, 14, w - 15, h - 15], outline=(*shade(c1, -25), 255))
    return img


def cable_run(w=96):
    img, d = new(w, 8)
    for i, c in enumerate([(60, 120, 230), (240, 190, 50), (230, 70, 70), (80, 200, 120)]):
        d.line([(0, 1 + i * 2), (w - 1, 1 + i * 2)], fill=(*c, 255))
    return img


def coffee_mug():
    img, d = new(8, 8)
    rr(d, [1, 2, 5, 7], (240, 240, 240)); rr(d, [5, 3, 6, 5], (240, 240, 240)); rr(d, [2, 2, 4, 2], (110, 60, 30))
    return outline_pass(img)


def paper_stack():
    img, d = new(14, 10)
    rr(d, [1, 3, 12, 9], (240, 240, 232)); rr(d, [0, 1, 11, 7], (250, 250, 245)); rr(d, [2, 3, 9, 3], (160, 160, 175)); rr(d, [2, 5, 7, 5], (160, 160, 175))
    return outline_pass(img)


def printer():
    img, d = new(34, 30)
    box3d(d, 1, 4, 32, 10, 12, (220, 222, 228), (190, 194, 204))
    rr(d, [6, 0, 27, 5], (250, 250, 245)); rr(d, [8, 18, 25, 21], (60, 64, 76)); d.point((28, 7), fill=(80, 230, 120, 255))
    return fin(img, ry=2)


def projector():
    img, d = new(20, 10)
    rr(d, [0, 2, 19, 9], (220, 222, 228)); d.ellipse([13, 3, 18, 8], fill=(60, 120, 230, 255))
    return outline_pass(img)


def bench_table(w=96):
    img, d = new(w, 40)
    rr(d, [4, 24, 7, 38], (60, 60, 70)); rr(d, [w - 8, 24, w - 5, 38], (60, 60, 70))
    box3d(d, 1, 2, w - 2, 24, 8, WHITE_DESK)
    return fin(img)


def cork_board():
    img, d = new(56, 36)
    rr(d, [0, 0, 55, 35], (150, 100, 60)); rr(d, [2, 2, 53, 33], (200, 150, 100))
    for _ in range(9):
        x, y = R.randint(4, 44), R.randint(4, 24)
        rr(d, [x, y, x + 8, y + 7], R.choice([(250, 250, 245), (250, 220, 90), (130, 210, 250), (250, 150, 180)]))
        d.point((x + 4, y), fill=(220, 50, 50, 255))
    d.line([(10, 10), (30, 20), (44, 8)], fill=(220, 50, 50, 255))
    return outline_pass(img)


def logo_wall():
    """Big reception wall logo (crown + S mark) — no text."""
    img, d = new(80, 40)
    rr(d, [0, 0, 79, 39], (30, 34, 56)); rr(d, [2, 2, 77, 37], (40, 46, 80))
    d.polygon([(10, 26), (14, 12), (21, 20), (28, 8), (35, 20), (42, 12), (46, 26)], fill=(240, 190, 60, 255))
    rr(d, [52, 10, 70, 14], (250, 250, 250)); rr(d, [52, 10, 56, 20], (250, 250, 250)); rr(d, [52, 18, 70, 22], (250, 250, 250))
    rr(d, [66, 18, 70, 30], (250, 250, 250)); rr(d, [52, 26, 70, 30], (250, 250, 250))
    return outline_pass(img)


def door_frame(style="wood"):
    """Open doorway inside a 2-tile wide, 64px tall wall face."""
    img, d = new(64, 64)
    frame = {"wood": (150, 96, 56), "metal": (130, 140, 160), "dark": (60, 56, 80)}[style]
    rr(d, [0, 0, 63, 63], frame)
    rr(d, [5, 6, 58, 63], (0, 0, 0, 0))
    rr(d, [5, 6, 58, 8], shade(frame, -30))
    # open door leaf swung inward (left side)
    rr(d, [5, 8, 12, 63], shade(frame, 25)); rr(d, [10, 34, 11, 37], (240, 200, 80))
    rr(d, [26, 1, 37, 4], (80, 220, 120))   # exit-style green light
    return img


def entrance_doors():
    img, d = new(64, 40)
    rr(d, [0, 0, 63, 39], (150, 160, 176))
    rr(d, [3, 3, 30, 39], (140, 210, 245, 140)); rr(d, [33, 3, 60, 39], (140, 210, 245, 140))
    rr(d, [27, 16, 28, 26], (240, 240, 245)); rr(d, [35, 16, 36, 26], (240, 240, 245))
    d.line([(8, 6), (4, 18)], fill=(255, 255, 255, 160), width=2); d.line([(40, 6), (36, 18)], fill=(255, 255, 255, 160), width=2)
    return outline_pass(img)


def welcome_mat():
    img, d = new(64, 24)
    rr(d, [0, 0, 63, 23], (60, 60, 70)); d.rectangle([3, 3, 60, 20], outline=(240, 190, 60, 255))
    for x in range(8, 58, 6):
        rr(d, [x, 9, x + 2, 14], (240, 190, 60))
    return img


PROPS = {
    # name: (builder, footprint_w_tiles, footprint_h_tiles)   footprint measured from sprite bottom
    "desk_wood": (lambda: desk(WOOD), 2, 1),
    "desk_white": (lambda: desk(WHITE_DESK), 2, 1),
    "desk_dark": (lambda: desk((70, 74, 92)), 2, 1),
    "desk_exec": (desk_exec, 3, 1),
    "reception_desk": (reception_desk, 4, 1),
    "conference_table": (conference_table, 6, 2),
    "coffee_table": (coffee_table, 2, 1),
    "kitchen_counter": (kitchen_counter, 4, 1),
    "bench_table": (bench_table, 3, 1),
    "chair_back": (chair_back, 0, 0),
    "chair_back_red": (lambda: chair_back((150, 50, 60)), 0, 0),
    "chair_front": (chair_front, 1, 1),
    "chair_front_wine": (lambda: chair_front((120, 40, 60)), 1, 1),
    "chair_exec": (chair_exec, 0, 0),
    "sofa_teal": (lambda: sofa((60, 130, 150)), 3, 1),
    "sofa_wine": (lambda: sofa((140, 50, 64)), 3, 1),
    "sofa_orange": (lambda: sofa((220, 120, 60), 64), 2, 1),
    "armchair_red": (armchair, 1, 1),
    "armchair_blue": (lambda: armchair((70, 110, 200)), 1, 1),
    "beanbag_yellow": (beanbag, 1, 1),
    "beanbag_pink": (lambda: beanbag((230, 100, 160)), 1, 1),
    "mon_code": (lambda: monitor("code"), 0, 0),
    "mon_dual_code": (lambda: dual_monitor("code", "code"), 0, 0),
    "mon_dual_chart": (lambda: dual_monitor("code", "chart"), 0, 0),
    "mon_dual_dash": (lambda: dual_monitor("dash", "chart"), 0, 0),
    "mon_dual_test": (lambda: dual_monitor("test", "code"), 0, 0),
    "mon_news": (lambda: dual_monitor("news", "chart"), 0, 0),
    "mon_script": (lambda: dual_monitor("script", "news"), 0, 0),
    "mon_wave": (lambda: ultrawide("wave"), 0, 0),
    "mon_subs": (lambda: dual_monitor("subs", "wave"), 0, 0),
    "mon_timeline": (lambda: ultrawide("timeline"), 0, 0),
    "mon_design": (lambda: ultrawide("design"), 0, 0),
    "mon_back": (monitor_back, 0, 0),
    "laptop": (laptop, 0, 0),
    "keyboard": (keyboard, 0, 0),
    "bookshelf": (bookshelf, 2, 1),
    "bookshelf_tall": (lambda: bookshelf(64, 80), 2, 1),
    "filing_cabinet": (filing_cabinet, 1, 1),
    "server_rack_a": (lambda: server_rack(0), 1, 1),
    "server_rack_b": (lambda: server_rack(1), 1, 1),
    "server_rack_c": (lambda: server_rack(2), 1, 1),
    "network_cabinet": (network_cabinet, 1, 1),
    "ups_unit": (ups_unit, 1, 1),
    "monitoring_wall": (monitoring_wall, 0, 0),
    "whiteboard_kanban": (whiteboard, 0, 0),
    "whiteboard_plan": (lambda: whiteboard(72, 44, False), 0, 0),
    "tv_graph": (lambda: tv_screen(96, 54, "graph"), 0, 0),
    "tv_dash": (lambda: tv_screen(80, 46, "dash"), 0, 0),
    "painting_landscape": (lambda: painting(0), 0, 0),
    "painting_abstract": (lambda: painting(1), 0, 0),
    "painting_chart": (lambda: painting(2), 0, 0),
    "empire_crest": (empire_crest, 0, 0),
    "wall_clock": (wall_clock, 0, 0),
    "acoustic_panel": (acoustic_panel, 0, 0),
    "neon_sign": (neon_sign, 0, 0),
    "cork_board": (cork_board, 0, 0),
    "logo_wall": (logo_wall, 0, 0),
    "window": (window, 0, 0),
    "plant_monstera": (lambda: plant("monstera"), 1, 1),
    "plant_snake": (lambda: plant("snake"), 1, 1),
    "plant_tree": (lambda: plant("tree"), 1, 1),
    "plant_small": (lambda: plant("small"), 0, 0),
    "plant_cactus": (lambda: plant("cactus"), 0, 0),
    "water_cooler": (water_cooler, 1, 1),
    "vending_machine": (vending_machine, 1, 1),
    "fridge": (fridge, 1, 1),
    "trash_bin": (trash_bin, 0, 0),
    "floor_lamp": (floor_lamp, 1, 1),
    "desk_lamp": (desk_lamp, 0, 0),
    "mic_stand": (mic_stand, 1, 1),
    "desk_mic": (desk_mic, 0, 0),
    "headphones": (headphones, 0, 0),
    "mixer": (mixer, 0, 0),
    "drawing_tablet": (drawing_tablet, 0, 0),
    "camera_tripod": (camera_tripod, 1, 1),
    "softbox": (softbox, 1, 1),
    "ring_light": (ring_light, 1, 1),
    "green_screen": (green_screen, 3, 1),
    "arcade": (arcade, 1, 1),
    "foosball": (foosball, 3, 1),
    "rug_red": (lambda: rug(160, 96, (170, 60, 60), (240, 200, 120)), 0, 0),
    "rug_blue_round": (lambda: rug(128, 80, (70, 100, 170), (230, 230, 240), True), 0, 0),
    "rug_green": (lambda: rug(128, 80, (70, 140, 110), (240, 230, 190)), 0, 0),
    "rug_purple": (lambda: rug(192, 96, (90, 60, 130), (240, 190, 90)), 0, 0),
    "rug_beige": (lambda: rug(224, 112, (210, 180, 140), (150, 100, 70)), 0, 0),
    "cable_run": (cable_run, 0, 0),
    "coffee_mug": (coffee_mug, 0, 0),
    "paper_stack": (paper_stack, 0, 0),
    "printer": (printer, 1, 1),
    "projector": (projector, 0, 0),
    "door_wood": (lambda: door_frame("wood"), 0, 0),
    "door_metal": (lambda: door_frame("metal"), 0, 0),
    "door_dark": (lambda: door_frame("dark"), 0, 0),
    "entrance_doors": (entrance_doors, 0, 0),
    "welcome_mat": (welcome_mat, 0, 0),
}

CATEGORY = {
    "desks": ["desk_", "reception", "conference", "coffee_table", "kitchen", "bench"],
    "chairs": ["chair", "sofa", "armchair", "beanbag"],
    "computers": ["mon_", "laptop", "keyboard", "monitoring", "printer", "projector"],
    "shelves": ["bookshelf", "filing"],
    "servers": ["server", "network", "ups", "cable"],
}


def category_of(name):
    for cat, prefixes in CATEGORY.items():
        if any(name.startswith(p) for p in prefixes):
            return ("furniture", cat)
    if name.startswith("plant"):
        return ("environment", "plants")
    if name.startswith(("door", "entrance", "welcome")):
        return ("environment", "doors")
    if name.startswith("window"):
        return ("environment", "windows")
    if name.startswith(("floor_lamp", "desk_lamp", "softbox", "ring_light")):
        return ("environment", "lighting")
    return ("furniture", "decorations")

