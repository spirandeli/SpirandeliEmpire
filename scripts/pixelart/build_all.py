#!/usr/bin/env python3
"""
Exports all pixel art spritesheets, props, tilesets, effects, and Tiled JSON map
into frontend/public/sprites/.
"""
import json
import os
from PIL import Image, ImageDraw

from .characters import AGENTS, build_sheet, build_avatar
from .props import PROPS, category_of
from .tiles import build_tileset, WALL_STYLES, wall_face, partition_glass, wall_cap_v, wall_cap_v_end, wall_cap_h
from .map_builder import build_map
from .common import OUTLINE

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PUBLIC_DIR = os.path.join(ROOT_DIR, "frontend", "public", "sprites")


def ensure(p):
    os.makedirs(p, exist_ok=True)


def export_characters():
    for name, data in AGENTS.items():
        d = os.path.join(PUBLIC_DIR, "agents", name)
        ensure(d)
        build_sheet(data).save(os.path.join(d, "spritesheet.png"))
        build_avatar(data).save(os.path.join(d, "avatar.png"))
    print(f"✓ Exported {len(AGENTS)} character spritesheets & avatars.")


def export_props():
    for name, (builder, _, _) in PROPS.items():
        group, cat = category_of(name)
        d = os.path.join(PUBLIC_DIR, group, cat)
        ensure(d)
        builder().save(os.path.join(d, f"{name}.png"))
    print(f"✓ Exported {len(PROPS)} furniture & decor props.")


def export_tiles_and_walls():
    ts_dir = os.path.join(PUBLIC_DIR, "tilesets")
    ensure(ts_dir)
    sheet, _, _ = build_tileset()
    sheet.save(os.path.join(ts_dir, "office_floors.png"))

    w_dir = os.path.join(PUBLIC_DIR, "environment", "walls")
    ensure(w_dir)
    for style in WALL_STYLES:
        wall_face(style).save(os.path.join(w_dir, f"wall_{style}.png"))
    partition_glass().save(os.path.join(w_dir, "partition_glass.png"))
    wall_cap_v().save(os.path.join(w_dir, "wall_cap_v.png"))
    wall_cap_v_end().save(os.path.join(w_dir, "wall_cap_v_end.png"))
    wall_cap_h().save(os.path.join(w_dir, "wall_cap_h.png"))
    print("✓ Exported tileset and walls.")


def export_effects():
    fx_dir = os.path.join(PUBLIC_DIR, "effects")
    ensure(fx_dir)

    # 1. Speech Bubble (32 x 24)
    bubble = Image.new("RGBA", (32, 24), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bubble)
    bd.rounded_rectangle([1, 1, 30, 17], radius=4, fill=(255, 255, 255, 245), outline=OUTLINE)
    bd.polygon([(12, 17), (16, 22), (18, 17)], fill=(255, 255, 255, 245))
    bd.line([(12, 17), (16, 22)], fill=OUTLINE)
    bd.line([(16, 22), (18, 17)], fill=OUTLINE)
    for x in (9, 15, 21):
        bd.rectangle([x, 8, x + 2, 10], fill=(30, 41, 59, 255))
    bubble.save(os.path.join(fx_dir, "speech_bubble.png"))

    # 2. Status Alert (16 x 16)
    alert = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    ad = ImageDraw.Draw(alert)
    ad.ellipse([1, 1, 14, 14], fill=(239, 68, 68, 255), outline=OUTLINE)
    ad.rectangle([7, 4, 8, 9], fill=(255, 255, 255, 255))
    ad.rectangle([7, 11, 8, 12], fill=(255, 255, 255, 255))
    alert.save(os.path.join(fx_dir, "status_alert.png"))

    # 3. Status Sparkle (16 x 16)
    star = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    sd = ImageDraw.Draw(star)
    sd.polygon([(8, 1), (10, 6), (15, 8), (10, 10), (8, 15), (6, 10), (1, 8), (6, 6)], fill=(250, 204, 21, 255), outline=OUTLINE)
    sd.point((8, 8), fill=(255, 255, 255, 255))
    star.save(os.path.join(fx_dir, "status_sparkle.png"))

    # 4. Status Coding (16 x 16)
    code = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    cd = ImageDraw.Draw(code)
    cd.rounded_rectangle([1, 1, 14, 14], radius=3, fill=(13, 148, 136, 255), outline=OUTLINE)
    cd.line([(5, 6), (3, 8), (5, 10)], fill=(255, 255, 255, 255))
    cd.line([(10, 6), (12, 8), (10, 10)], fill=(255, 255, 255, 255))
    cd.line([(9, 5), (6, 11)], fill=(250, 204, 21, 255))
    code.save(os.path.join(fx_dir, "status_coding.png"))

    # 5. Selection Ring (36 x 18)
    ring = Image.new("RGBA", (36, 18), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse([1, 1, 34, 16], outline=(99, 102, 241, 240), width=2)
    rd.ellipse([3, 3, 32, 14], fill=(99, 102, 241, 70))
    ring.save(os.path.join(fx_dir, "selection_ring.png"))

    print("✓ Exported effects.")


def export_map():
    maps_dir = os.path.join(PUBLIC_DIR, "maps")
    ensure(maps_dir)
    m = build_map()
    with open(os.path.join(maps_dir, "office_map.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2)
    print("✓ Exported Tiled JSON map -> office_map.json")


def main():
    export_characters()
    export_props()
    export_tiles_and_walls()
    export_effects()
    export_map()


if __name__ == "__main__":
    main()

