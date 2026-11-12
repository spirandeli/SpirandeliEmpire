"""
SpirandeliEmpire OS — Character sprite generator (original pixel art).

Each agent gets ONE spritesheet: 4 columns x 13 rows, 32x48 frames.
Feet always touch y=45 so the sprite origin is (0.5, ~0.94).

Rows:
 0 idle_down   1 idle_up    2 idle_left   3 idle_right
 4 walk_down   5 walk_up    6 walk_left   7 walk_right
 8 sit_back (seated at desk, seen from behind, typing)
 9 sit_front (seated behind desk, facing viewer, typing)
10 talk        11 celebrate 12 read
"""
from PIL import Image, ImageOps
from .common import outline_pass, shade, W_CHAR, H_CHAR

ROWS = ["idle_down", "idle_up", "idle_left", "idle_right",
        "walk_down", "walk_up", "walk_left", "walk_right",
        "sit_back", "sit_front", "talk", "celebrate", "read"]

SKIN = {
    "fair":   (255, 224, 196), "warm": (238, 192, 150), "olive": (214, 170, 128),
    "tan":    (190, 138, 98),  "dark": (130, 86, 60),
}
EYE = (34, 26, 38)
SHOE = (44, 38, 46)

# ---------------------------------------------------------------- agents
AGENTS = {
    "jeffrey":        dict(skin="warm",  hair=(58, 42, 34),   style="slick",     top=(34, 52, 120),  pants=(30, 34, 52),  extra=["tie", "suit"], tie=(200, 40, 48)),
    "fonseca":        dict(skin="olive", hair=(36, 30, 28),   style="curly",     top=(20, 150, 140), pants=(48, 58, 84),  extra=["glasses", "hoodie"]),
    "balsini":        dict(skin="fair",  hair=(96, 62, 40),   style="short",     top=(48, 50, 58),   pants=(70, 86, 110), extra=["beard"]),
    "jarvis":         dict(skin="tan",   hair=(28, 30, 38),   style="buzz",      top=(62, 78, 96),   pants=(40, 46, 60),  extra=["headset", "vest"]),
    "noe":            dict(skin="fair",  hair=(150, 146, 140), style="side",     top=(80, 64, 190),  pants=(150, 110, 60), extra=["glasses"]),
    "ford":           dict(skin="fair",  hair=(190, 92, 30),  style="messy",     top=(190, 40, 44),  pants=(40, 64, 130), extra=["flannel", "neckphones"]),
    "murphy":         dict(skin="warm",  hair=(52, 32, 26),   style="bob",       top=(170, 28, 70),  pants=(32, 30, 38),  extra=["glasses"]),
    "script-agent":   dict(skin="fair",  hair=(110, 62, 36),  style="ponytail",  top=(214, 160, 40), pants=(60, 72, 96),  extra=["scarf"]),
    "news-agent":     dict(skin="olive", hair=(40, 34, 30),   style="swept",     top=(20, 150, 186), pants=(40, 46, 64),  extra=["badge"]),
    "voice-agent":    dict(skin="dark",  hair=(40, 28, 24),   style="afro",      top=(150, 60, 220), pants=(34, 32, 40),  extra=["bigphones"]),
    "subtitle-agent": dict(skin="tan",   hair=(30, 26, 24),   style="long",      top=(46, 104, 230), pants=(80, 92, 110), extra=["glasses"]),
    "clipador-agent": dict(skin="warm",  hair=(48, 36, 30),   style="cap",       top=(236, 100, 30), pants=(30, 34, 46),  extra=[], cap=(40, 44, 56)),
    "designer-agent": dict(skin="fair",  hair=(200, 80, 140), style="beret",     top=(226, 70, 140), pants=(60, 70, 90),  extra=[], beret=(60, 40, 90)),
    "video-agent":    dict(skin="olive", hair=(50, 40, 34),   style="bun",       top=(110, 50, 200), pants=(30, 30, 38),  extra=["neckphones"]),
}


class Canvas:
    def __init__(self):
        self.img = Image.new("RGBA", (W_CHAR, H_CHAR), (0, 0, 0, 0))
        self.px = self.img.load()

    def p(self, x, y, c):
        if 0 <= x < W_CHAR and 0 <= y < H_CHAR:
            self.px[x, y] = c if len(c) == 4 else (*c, 255)

    def r(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.p(x, y, c)


# ---------------------------------------------------------------- parts
def head_front(cv, a, hy, blink=False, mouth=0, look_down=False):
    s = SKIN[a["skin"]]
    sd = shade(s, -28)
    # head 14x14 (x 9..22), rounded corners
    cv.r(9, hy + 1, 22, hy + 12, s)
    cv.r(10, hy, 21, hy + 13, s)
    cv.r(21, hy + 2, 22, hy + 12, sd)   # right shade
    cv.r(10, hy + 13, 21, hy + 13, sd)
    # ears
    cv.r(8, hy + 6, 8, hy + 8, sd)
    cv.r(23, hy + 6, 23, hy + 8, sd)
    ey = hy + 7 + (1 if look_down else 0)
    if blink:
        cv.r(12, ey + 1, 13, ey + 1, EYE)
        cv.r(18, ey + 1, 19, ey + 1, EYE)
    else:
        cv.r(12, ey, 12, ey + 1, EYE); cv.p(13, ey + 1, EYE)
        cv.r(19, ey, 19, ey + 1, EYE); cv.p(18, ey + 1, EYE)
        cv.p(12, ey, (255, 255, 255))
        cv.p(19, ey, (255, 255, 255))
    # cheeks
    cv.p(11, hy + 10, shade(s, -12) if a["skin"] in ("dark", "tan") else (246, 170, 160))
    cv.p(20, hy + 10, shade(s, -12) if a["skin"] in ("dark", "tan") else (246, 170, 160))
    # mouth
    mc = (150, 60, 60)
    if mouth == 0:
        cv.r(15, hy + 11, 16, hy + 11, mc)
    else:
        cv.r(15, hy + 11, 16, hy + 12, (110, 30, 40))
    if "glasses" in a["extra"]:
        g = (30, 30, 40)
        cv.r(11, hy + 6, 14, hy + 6, g); cv.r(17, hy + 6, 20, hy + 6, g)
        cv.p(11, hy + 7, g); cv.p(14, hy + 7, g); cv.p(17, hy + 7, g); cv.p(20, hy + 7, g)
        cv.r(11, hy + 9, 14, hy + 9, g); cv.r(17, hy + 9, 20, hy + 9, g)
        cv.r(15, hy + 7, 16, hy + 7, g)
    if "beard" in a["extra"]:
        h = a["hair"]
        cv.r(10, hy + 10, 21, hy + 13, h)
        cv.r(9, hy + 8, 10, hy + 11, h); cv.r(21, hy + 8, 22, hy + 11, h)
        cv.r(14, hy + 11, 17, hy + 11, (150, 70, 60))
        cv.r(11, hy + 13, 20, hy + 14, shade(h, -15))


def hair_front(cv, a, hy):
    h = a["hair"]; hl = shade(h, 30); hd = shade(h, -30)
    st = a["style"]
    if st in ("slick", "short", "side", "swept"):
        cv.r(9, hy - 1, 22, hy + 3, h); cv.r(10, hy - 2, 21, hy - 1, h)
        cv.r(8, hy + 1, 9, hy + 6, h); cv.r(22, hy + 1, 23, hy + 6, h)
        if st == "slick":
            cv.r(11, hy - 1, 18, hy - 1, hl); cv.r(17, hy + 3, 21, hy + 4, h)
        elif st == "side":
            cv.r(9, hy + 3, 14, hy + 4, h); cv.r(10, hy - 1, 15, hy - 1, hl)
            cv.r(8, hy + 4, 9, hy + 8, shade(h, 25))
        elif st == "swept":
            cv.r(9, hy + 3, 17, hy + 5, h); cv.r(12, hy - 1, 19, hy - 1, hl)
        else:
            cv.r(12, hy - 1, 19, hy - 1, hl)
    elif st == "buzz":
        cv.r(9, hy, 22, hy + 2, h); cv.r(10, hy - 1, 21, hy - 1, h)
        cv.r(8, hy + 2, 9, hy + 5, h); cv.r(22, hy + 2, 23, hy + 5, h)
    elif st == "curly":
        cv.r(8, hy - 3, 23, hy + 3, h)
        for x in range(8, 24, 2):
            cv.p(x, hy - 4, h); cv.p(x + 1, hy - 2, hl)
        cv.r(8, hy + 3, 9, hy + 6, hd); cv.r(22, hy + 3, 23, hy + 6, hd)
    elif st == "messy":
        cv.r(8, hy - 2, 23, hy + 3, h)
        for x in (9, 12, 15, 18, 21):
            cv.p(x, hy - 3, h); cv.p(x + 1, hy - 4, h)
        cv.r(10, hy + 3, 12, hy + 4, h); cv.r(16, hy + 3, 18, hy + 4, h)
        cv.r(11, hy - 2, 16, hy - 2, hl)
    elif st == "bob":
        cv.r(8, hy - 2, 23, hy + 3, h); cv.r(7, hy + 1, 9, hy + 13, h); cv.r(22, hy + 1, 24, hy + 13, h)
        cv.r(10, hy - 2, 17, hy - 2, hl); cv.r(7, hy + 11, 9, hy + 13, hd); cv.r(22, hy + 11, 24, hy + 13, hd)
    elif st == "ponytail":
        cv.r(9, hy - 2, 22, hy + 3, h); cv.r(8, hy + 1, 9, hy + 9, h); cv.r(22, hy + 1, 23, hy + 9, h)
        cv.r(11, hy - 2, 16, hy - 2, hl)
    elif st == "long":
        cv.r(8, hy - 2, 23, hy + 3, h); cv.r(7, hy + 1, 9, hy + 18, h); cv.r(22, hy + 1, 24, hy + 18, h)
        cv.r(10, hy - 2, 18, hy - 2, hl)
    elif st == "afro":
        cv.r(6, hy - 5, 25, hy + 4, h); cv.r(7, hy - 6, 24, hy - 5, h); cv.r(6, hy + 4, 8, hy + 9, h); cv.r(23, hy + 4, 25, hy + 9, h)
        for x in range(8, 24, 3):
            cv.p(x, hy - 4, hl)
    elif st == "bun":
        cv.r(9, hy - 2, 22, hy + 3, h); cv.r(8, hy + 1, 9, hy + 7, h); cv.r(22, hy + 1, 23, hy + 7, h)
        cv.r(13, hy - 6, 18, hy - 2, h); cv.r(14, hy - 6, 16, hy - 5, hl)
    elif st == "cap":
        c = a["cap"]
        cv.r(8, hy - 2, 23, hy + 3, c); cv.r(10, hy - 3, 21, hy - 2, c)
        cv.r(7, hy + 3, 24, hy + 4, shade(c, -20))      # brim facing viewer
        cv.r(13, hy - 1, 18, hy + 1, (236, 100, 30))    # logo patch
        cv.r(8, hy + 4, 9, hy + 7, h); cv.r(22, hy + 4, 23, hy + 7, h)
    elif st == "beret":
        b = a["beret"]
        cv.r(8, hy + 1, 9, hy + 10, h); cv.r(22, hy + 1, 23, hy + 10, h); cv.r(9, hy + 1, 22, hy + 3, h)
        cv.r(7, hy - 3, 22, hy + 1, b); cv.r(9, hy - 4, 20, hy - 3, b); cv.p(14, hy - 5, b)
        cv.r(9, hy - 3, 14, hy - 3, shade(b, 30))


def head_back(cv, a, hy):
    s = SKIN[a["skin"]]; h = a["hair"]; hl = shade(h, 25)
    cv.r(10, hy, 21, hy + 13, s); cv.r(9, hy + 1, 22, hy + 12, s)
    cv.r(8, hy + 6, 8, hy + 8, shade(s, -25)); cv.r(23, hy + 6, 23, hy + 8, shade(s, -25))
    st = a["style"]
    bottom = {"buzz": hy + 8, "bob": hy + 13, "long": hy + 19, "afro": hy + 11, "ponytail": hy + 10}.get(st, hy + 10)
    top = hy - {"curly": 3, "messy": 3, "afro": 6, "bun": 2}.get(st, 2)
    x0, x1 = (6, 25) if st == "afro" else ((7, 24) if st in ("bob", "long") else (9, 22))
    cv.r(x0, top, x1, bottom, h)
    cv.r(x0 + 1, top - 1 if st != "buzz" else top, x1 - 1, top, h)
    cv.r(x0 + 2, top, x0 + 6, top, hl)
    if st == "ponytail":
        cv.r(14, hy + 9, 17, hy + 19, h); cv.r(15, hy + 10, 15, hy + 18, hl)
    if st == "bun":
        cv.r(13, hy - 6, 18, hy - 2, h)
    if st == "cap":
        c = a["cap"]; cv.r(8, hy - 2, 23, hy + 4, c); cv.r(10, hy - 3, 21, hy - 2, c)
    if st == "beret":
        b = a["beret"]; cv.r(7, hy - 3, 22, hy + 1, b); cv.r(9, hy - 4, 20, hy - 3, b)
    _head_accessory(cv, a, hy, back=True)


def head_side(cv, a, hy, blink=False):
    """Facing LEFT."""
    s = SKIN[a["skin"]]; h = a["hair"]; hl = shade(h, 25)
    cv.r(10, hy, 21, hy + 13, s); cv.r(9, hy + 2, 21, hy + 12, s)
    cv.p(8, hy + 8, s)  # nose
    cv.r(10, hy + 13, 20, hy + 13, shade(s, -25))
    ey = hy + 7
    if blink:
        cv.r(11, ey + 1, 12, ey + 1, EYE)
    else:
        cv.r(11, ey, 11, ey + 1, EYE); cv.p(12, ey + 1, EYE)
    cv.r(11, hy + 11, 12, hy + 11, (150, 60, 60))
    st = a["style"]
    top = hy - {"curly": 3, "messy": 3, "afro": 5}.get(st, 2)
    back_bottom = {"buzz": hy + 7, "bob": hy + 13, "long": hy + 18, "afro": hy + 10}.get(st, hy + 10)
    cv.r(10, top, 22, hy + 3, h)
    cv.r(15, hy + 3, 22, back_bottom, h)
    cv.r(17, hy + 6, 18, hy + 8, shade(s, -25))  # ear
    cv.r(11, top, 16, top, hl)
    if st == "afro":
        cv.r(8, top, 24, hy + 4, h)
    if st == "ponytail":
        cv.r(21, hy + 4, 24, hy + 14, h)
    if st == "bun":
        cv.r(16, hy - 6, 21, hy - 2, h)
    if st == "cap":
        c = a["cap"]; cv.r(10, hy - 2, 22, hy + 3, c); cv.r(20, hy + 2, 25, hy + 3, shade(c, -20))
    if st == "beret":
        b = a["beret"]; cv.r(9, hy - 3, 23, hy + 1, b)
    if "glasses" in a["extra"]:
        cv.r(9, hy + 6, 13, hy + 6, (30, 30, 40)); cv.r(13, hy + 6, 17, hy + 6, (30, 30, 40))
    if "beard" in a["extra"]:
        cv.r(9, hy + 10, 17, hy + 13, h)
    _head_accessory(cv, a, hy, side=True)


def _head_accessory(cv, a, hy, back=False, side=False):
    ex = a["extra"]
    if "bigphones" in ex:
        band = (40, 40, 52); cup = (130, 80, 230)
        if side:
            cv.r(12, hy - 3, 20, hy - 2, band); cv.r(15, hy + 4, 19, hy + 10, cup)
        else:
            cv.r(9, hy - 4, 22, hy - 3, band); cv.r(7, hy + 4, 9, hy + 10, cup); cv.r(22, hy + 4, 24, hy + 10, cup)
    if "headset" in ex and not side:
        cv.r(22, hy + 5, 24, hy + 9, (40, 40, 52))
        if not back:
            cv.r(18, hy + 10, 21, hy + 10, (40, 40, 52)); cv.p(17, hy + 10, (230, 60, 60))


def torso(cv, a, ty, view="down", arms="side", swing=0, frame=0):
    top = a["top"]; tl = shade(top, 28); td = shade(top, -32)
    s = SKIN[a["skin"]]
    ex = a["extra"]
    if view in ("down", "up"):
        cv.r(14, ty - 1, 17, ty, shade(s, -25))         # neck
        cv.r(10, ty, 21, ty + 11, top)
        cv.r(9, ty + 1, 22, ty + 3, top)                 # shoulders
        cv.r(10, ty + 1, 11, ty + 10, tl)
        cv.r(20, ty + 1, 21, ty + 11, td)
        cv.r(10, ty + 11, 21, ty + 11, td)
        if view == "down":
            if "suit" in ex:
                cv.r(14, ty, 17, ty + 5, (236, 236, 240))
                cv.r(15, ty + 1, 16, ty + 7, a["tie"]); cv.p(15, ty + 1, shade(a["tie"], 30))
                cv.r(12, ty + 1, 13, ty + 6, td); cv.r(18, ty + 1, 19, ty + 6, td)
                cv.p(19, ty + 3, (240, 200, 60))
            if "hoodie" in ex:
                cv.r(12, ty, 19, ty + 1, td); cv.p(14, ty + 2, (240, 240, 240)); cv.p(17, ty + 2, (240, 240, 240))
                cv.p(14, ty + 3, (240, 240, 240)); cv.p(17, ty + 3, (240, 240, 240))
                cv.r(12, ty + 7, 19, ty + 9, td)
            if "vest" in ex:
                cv.r(11, ty + 4, 13, ty + 6, td); cv.r(18, ty + 4, 20, ty + 6, td); cv.r(15, ty, 16, ty + 11, td)
            if "flannel" in ex:
                for yy in range(ty + 1, ty + 11, 3):
                    cv.r(10, yy, 21, yy, shade(top, -45))
                for xx in range(11, 21, 3):
                    cv.r(xx, ty + 1, xx, ty + 10, shade(top, -45))
            if "scarf" in ex:
                cv.r(11, ty, 20, ty + 2, (240, 236, 220)); cv.r(17, ty + 2, 19, ty + 7, (240, 236, 220))
            if "badge" in ex:
                cv.r(18, ty + 3, 20, ty + 5, (250, 250, 250)); cv.p(19, ty + 4, (220, 40, 40))
            if "neckphones" in ex:
                cv.r(11, ty, 20, ty, (30, 30, 40)); cv.r(10, ty, 11, ty + 2, (60, 60, 75)); cv.r(20, ty, 21, ty + 2, (60, 60, 75))
        else:
            cv.r(14, ty + 1, 17, ty + 10, shade(top, -12))  # back seam shading
            if "hoodie" in ex:
                cv.r(11, ty, 20, ty + 3, td)
        # arms
        if arms == "side":
            ly = ty + 1 + swing; ry = ty + 1 - swing
            cv.r(7, ly, 9, ly + 8, top); cv.r(7, ly, 7, ly + 8, tl); cv.r(7, ly + 9, 9, ly + 10, s)
            cv.r(22, ry, 24, ry + 8, top); cv.r(24, ry, 24, ry + 8, td); cv.r(22, ry + 9, 24, ry + 10, s)
        elif arms == "up":
            cv.r(6, ty - 8, 8, ty + 2, top); cv.r(6, ty - 10, 8, ty - 8, s)
            cv.r(23, ty - 8, 25, ty + 2, top); cv.r(23, ty - 10, 25, ty - 8, s)
        elif arms == "gesture":
            cv.r(7, ty + 1, 9, ty + 9, top); cv.r(7, ty + 9, 9, ty + 10, s)
            gy = ty + 2 - (frame % 2)
            cv.r(22, gy, 25, gy + 3, top); cv.r(25, gy - 3, 27, gy + 1, top); cv.r(25, gy - 5, 27, gy - 3, s)
        elif arms == "hold":
            cv.r(8, ty + 1, 10, ty + 6, top); cv.r(21, ty + 1, 23, ty + 6, top)
            cv.r(10, ty + 5, 21, ty + 6, top)
            # document / tablet
            paper = (248, 248, 240) if frame % 2 == 0 else (236, 240, 250)
            cv.r(11, ty + 2, 20, ty + 9, paper); cv.r(12, ty + 4, 18, ty + 4, (150, 160, 180)); cv.r(12, ty + 6, 17, ty + 6, (150, 160, 180))
            cv.r(9, ty + 6, 11, ty + 7, s); cv.r(20, ty + 6, 22, ty + 7, s)
        elif arms == "type_front":
            cv.r(7, ty + 1, 9, ty + 7, top); cv.r(22, ty + 1, 24, ty + 7, top)
            o = frame % 2
            cv.r(9, ty + 7, 13, ty + 9, top); cv.r(18, ty + 7, 22, ty + 9, top)
            cv.r(12, ty + 9 + o, 14, ty + 10 + o, s); cv.r(17, ty + 10 - o, 19, ty + 11 - o, s)
        elif arms == "type_back":
            o = frame % 2
            cv.r(7, ty + 1 + o, 9, ty + 7 + o, top); cv.r(7, ty + 1 + o, 7, ty + 6 + o, tl)
            cv.r(22, ty + 2 - o, 24, ty + 8 - o, top); cv.r(24, ty + 2 - o, 24, ty + 7 - o, td)
    else:  # side view facing left
        cv.r(14, ty - 1, 16, ty, shade(s, -25))
        cv.r(11, ty, 20, ty + 11, top); cv.r(11, ty, 12, ty + 11, tl); cv.r(19, ty, 20, ty + 11, td)
        if "suit" in ex:
            cv.r(11, ty, 12, ty + 4, (236, 236, 240)); cv.r(11, ty + 1, 11, ty + 6, a["tie"])
        ax = 14 - swing
        cv.r(ax, ty + 1, ax + 3, ty + 8, td); cv.r(ax, ty + 9, ax + 3, ty + 10, s)


def legs(cv, a, ly, view="down", step=0):
    p = a["pants"]; pl = shade(p, 22); pd = shade(p, -25)
    if view in ("down", "up"):
        lo = -1 if step == 1 else 0
        ro = -1 if step == 2 else 0
        cv.r(11, ly, 20, ly + 2, p)
        cv.r(11, ly, 14, ly + 10 + lo, p); cv.r(11, ly, 11, ly + 9 + lo, pl)
        cv.r(17, ly, 20, ly + 10 + ro, p); cv.r(20, ly, 20, ly + 9 + ro, pd)
        cv.r(10, ly + 10 + lo, 14, ly + 11 + lo, SHOE)
        cv.r(17, ly + 10 + ro, 21, ly + 11 + ro, SHOE)
    else:  # side, facing left
        if step == 0:
            cv.r(13, ly, 18, ly + 10, p); cv.r(13, ly, 13, ly + 10, pl)
            cv.r(11, ly + 10, 17, ly + 11, SHOE)
        else:
            f = 1 if step == 1 else -1
            cv.r(13 - 2 * f, ly, 16 - 2 * f, ly + 10, pd); cv.r(11 - 2 * f, ly + 10, 16 - 2 * f, ly + 11, shade(SHOE, -10))
            cv.r(15 + 2 * f, ly, 18 + 2 * f, ly + 10, p); cv.r(13 + 2 * f, ly + 10, 18 + 2 * f, ly + 11, SHOE)


# ---------------------------------------------------------------- frames
BASE_HY = 5   # head top for standing pose -> torso 20..31, legs 32..43, shoes 42..43(+2 offset below)


def frame(a, row, f):
    cv = Canvas()
    walk_step = [0, 1, 0, 2][f]
    bob = 1 if (row.startswith("walk") and f in (1, 3)) else 0
    breathe = 1 if (row.startswith("idle") and f == 2) else 0
    hy = BASE_HY + 2 - bob + breathe
    ty = hy + 15
    ly = 34

    if row in ("idle_down", "walk_down", "talk", "celebrate", "read"):
        swing = 0
        if row == "walk_down":
            swing = [0, 1, 0, -1][f]
        jump = 0
        if row == "celebrate":
            jump = [0, 2, 3, 1][f]
        legs(cv, a, ly - jump, "down", walk_step if row == "walk_down" else 0)
        arms = {"talk": "gesture", "celebrate": "up", "read": "hold"}.get(row, "side")
        torso(cv, a, ty - jump, "down", arms, swing, f)
        blink = (row == "idle_down" and f == 3)
        mouth = 1 if (row == "talk" and f in (0, 2)) or (row == "celebrate") else 0
        head_front(cv, a, hy - jump, blink=blink, mouth=mouth, look_down=(row == "read"))
        hair_front(cv, a, hy - jump)
        _head_accessory(cv, a, hy - jump)
    elif row in ("idle_up", "walk_up"):
        swing = [0, 1, 0, -1][f] if row == "walk_up" else 0
        legs(cv, a, ly, "up", walk_step if row == "walk_up" else 0)
        torso(cv, a, ty, "up", "side", swing, f)
        head_back(cv, a, hy)
    elif row in ("idle_left", "idle_right", "walk_left", "walk_right"):
        walking = row.startswith("walk")
        legs(cv, a, ly, "side", walk_step if walking else 0)
        torso(cv, a, ty, "side", "side", ([0, 2, 0, -2][f] if walking else 0), f)
        head_side(cv, a, hy, blink=(not walking and f == 3))
        if row.endswith("right"):
            cv.img = ImageOps.mirror(cv.img); cv.px = cv.img.load()
    elif row == "sit_back":
        # seated, lower body hidden by chair/desk; body sits lower
        shy = BASE_HY + 6 + (1 if f == 2 else 0)
        sty = shy + 15
        cv.r(10, sty + 11, 21, sty + 15, a["pants"])
        torso(cv, a, sty, "up", "type_back", 0, f)
        head_back(cv, a, shy)
    elif row == "sit_front":
        shy = BASE_HY + 6 + (1 if f == 2 else 0)
        sty = shy + 15
        cv.r(10, sty + 11, 21, sty + 15, a["pants"])
        torso(cv, a, sty, "down", "type_front", 0, f)
        head_front(cv, a, shy, blink=(f == 3), look_down=True)
        hair_front(cv, a, shy)
        _head_accessory(cv, a, shy)

    img = outline_pass(cv.img)
    return img


def build_sheet(a):
    sheet = Image.new("RGBA", (W_CHAR * 4, H_CHAR * len(ROWS)), (0, 0, 0, 0))
    for ri, row in enumerate(ROWS):
        for f in range(4):
            sheet.paste(frame(a, row, f), (f * W_CHAR, ri * H_CHAR))
    return sheet


def build_avatar(a):
    """64x64 portrait: bust upscaled 2x with nearest neighbour."""
    fr = frame(a, "idle_down", 0)
    bust = fr.crop((0, 0, 32, 32)).resize((64, 64), Image.NEAREST)
    bg = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    return Image.alpha_composite(bg, bust)

