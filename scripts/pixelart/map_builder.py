"""
Builds the continuous 58x38 Tiled-compatible JSON map for SpirandeliEmpire OS 3.1.
"""
import json
from .tiles import GID
from .props import PROPS

COLS = 58
ROWS = 38
TILE = 32


def build_map():
    floor = [GID["marble_a"]] * (COLS * ROWS)
    collision = [0] * (COLS * ROWS)

    def set_floor(c0, r0, c1, r1, t_a, t_b=None):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if 0 <= r < ROWS and 0 <= c < COLS:
                    key = t_b if (t_b and (c + r) % 2 == 1) else t_a
                    floor[r * COLS + c] = GID[key]

    def block_rect(c0, r0, c1, r1):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if 0 <= r < ROWS and 0 <= c < COLS:
                    collision[r * COLS + c] = 1

    # Perimeter walls blocked
    block_rect(0, 0, COLS - 1, 1)
    block_rect(0, ROWS - 1, COLS - 1, ROWS - 1)
    block_rect(0, 0, 0, ROWS - 1)
    block_rect(COLS - 1, 0, COLS - 1, ROWS - 1)

    # 1. Floor Zones
    # Hallways base (checkerboard marble_a/b)
    set_floor(1, 2, COLS - 2, ROWS - 2, "marble_a", "marble_b")

    # CEO Office (Cols 1-16, Rows 2-13)
    set_floor(1, 2, 16, 13, "herring_a", "herring_b")
    # Dev Wing (Cols 18-38, Rows 2-13)
    set_floor(18, 2, 38, 13, "teal_a", "teal_b")
    # Infra Hub (Cols 40-56, Rows 2-13)
    set_floor(40, 2, 56, 13, "steel_a", "steel_b")
    set_floor(40, 13, 56, 13, "hazard")

    # Content Studio (Cols 1-16, Rows 17-26)
    set_floor(1, 17, 16, 26, "wood_a", "wood_b")
    # Boardroom (Cols 18-38, Rows 17-26)
    set_floor(18, 17, 38, 26, "wine_a", "wine_b")
    # QA Room (Cols 40-56, Rows 17-26)
    set_floor(40, 17, 56, 26, "navy_a", "navy_b")

    # Breakroom / Cafe corner (Cols 1-10, Rows 29-36)
    set_floor(1, 29, 10, 36, "checker")
    # Reception & Lounge (Cols 11-24, Rows 29-36)
    set_floor(11, 29, 24, 36, "sand_a", "sand_b")
    # Audiovisual Studio (Cols 26-56, Rows 29-36)
    set_floor(26, 29, 56, 36, "studio_a", "studio_b")

    # 2. Walls & Partitions
    walls = []
    rugs = []
    props = []

    def add_wall_h(c0, c1, row, style="beige", door_cols=None, window_cols=None):
        door_cols = set(door_cols or [])
        window_cols = set(window_cols or [])
        c = c0
        while c <= c1:
            if c in door_cols:
                door_tex = "door_wood" if style in ("wood", "beige") else "door_metal"
                walls.append({"x": c * TILE + 32, "y": row * TILE + 32, "texture": door_tex, "depth": row * TILE + 32})
                c += 2
                continue
            if c in window_cols:
                walls.append({"x": c * TILE + 32, "y": row * TILE + 32, "texture": f"wall_{style}", "depth": row * TILE + 30})
                walls.append({"x": c * TILE + 64, "y": row * TILE + 32, "texture": f"wall_{style}", "depth": row * TILE + 30})
                props.append({"x": c * TILE + 32, "y": row * TILE + 26, "texture": "window", "depth": row * TILE + 34})
                c += 2
                continue
            tex = "partition_glass" if style == "glass" else f"wall_{style}"
            walls.append({"x": c * TILE + 16, "y": row * TILE + 32, "texture": tex, "depth": row * TILE + 32})
            collision[row * COLS + c] = 1
            c += 1

    def add_wall_v(col, r0, r1, door_rows=None):
        door_rows = set(door_rows or [])
        for r in range(r0, r1 + 1):
            if r in door_rows:
                continue
            tex = "wall_cap_v_end" if r == r1 else "wall_cap_v"
            walls.append({"x": col * TILE + 16, "y": r * TILE + 16, "texture": tex, "depth": r * TILE + 16})
            collision[r * COLS + col] = 1

    # North exterior wall (Row 1) with skyline windows
    add_wall_h(1, 16, 1, style="wood", window_cols=[3, 7, 11])
    add_wall_h(17, 17, 1, style="exterior")
    add_wall_h(18, 38, 1, style="beige", window_cols=[20, 26, 32])
    add_wall_h(39, 39, 1, style="exterior")
    add_wall_h(40, 56, 1, style="gray", window_cols=[42, 52])

    # Vertical dividers Row 1
    add_wall_v(17, 2, 13)
    add_wall_v(39, 2, 13)

    # South walls of Row 1 (Row 14) -> opens to Main Corridor (Row 15-16)
    add_wall_h(1, 16, 14, style="wood", door_cols=[13])
    add_wall_h(18, 38, 14, style="glass", door_cols=[27, 35])
    add_wall_h(40, 56, 14, style="gray", door_cols=[42])

    # North walls of Row 2 (Row 17)
    add_wall_h(1, 16, 17, style="teal", door_cols=[13])
    add_wall_h(18, 38, 17, style="glass", door_cols=[27])
    add_wall_h(40, 56, 17, style="beige", door_cols=[42])

    # Vertical dividers Row 2
    add_wall_v(17, 18, 26, door_rows=[22, 23])
    add_wall_v(39, 18, 26, door_rows=[22, 23])

    # South walls of Row 2 (Row 27) -> opens to Lower Corridor (Row 28)
    add_wall_h(1, 16, 27, style="teal", door_cols=[13])
    add_wall_h(18, 38, 27, style="glass", door_cols=[27])
    add_wall_h(40, 56, 27, style="beige", door_cols=[42])

    # North walls of Row 3 (Row 29)
    add_wall_h(1, 10, 29, style="brick", door_cols=[7])
    add_wall_h(11, 24, 29, style="beige", door_cols=[16])
    add_wall_h(26, 56, 29, style="acoustic", door_cols=[28, 45])

    # Vertical divider Row 3 between Reception & AV Studio
    add_wall_v(25, 29, 36, door_rows=[32, 33])

    # 3. Rugs (floor layer)
    rugs.append({"x": 8 * TILE, "y": 7 * TILE + 16, "texture": "rug_red"})
    rugs.append({"x": 9 * TILE, "y": 22 * TILE, "texture": "rug_green"})
    rugs.append({"x": 28 * TILE, "y": 22 * TILE + 16, "texture": "rug_beige"})
    rugs.append({"x": 18 * TILE, "y": 33 * TILE, "texture": "rug_blue_round"})
    rugs.append({"x": 41 * TILE, "y": 33 * TILE, "texture": "rug_purple"})

    # Helper to place furniture + block collision footprint
    def add_prop(col, row, tex, ox=0, oy=0, block=True, custom_depth=None):
        px = col * TILE + 16 + ox
        py = row * TILE + 16 + oy
        depth = custom_depth if custom_depth is not None else py
        props.append({"x": px, "y": py, "texture": tex, "depth": depth})
        if block and tex in PROPS:
            _, fw, fh = PROPS[tex]
            if fw > 0 and fh > 0:
                c_start = int(col - fw // 2)
                r_start = int(row - fh + 1)
                for rr in range(r_start, int(row) + 1):
                    for cc in range(c_start, c_start + fw):
                        if 1 < rr < ROWS - 1 and 0 < cc < COLS - 1:
                            collision[rr * COLS + cc] = 1

    # -------------------------------------------------------------
    # FURNISH ALL 8 ZONES
    # -------------------------------------------------------------
    # A. CEO Office (Jeffrey)
    add_prop(8, 2, "empire_crest", oy=-4, block=False, custom_depth=2 * TILE + 36)
    add_prop(15, 2, "painting_landscape", oy=-4, block=False, custom_depth=2 * TILE + 36)
    add_prop(3, 4, "bookshelf_tall")
    add_prop(5, 4, "bookshelf")
    add_prop(8, 7, "desk_exec")
    add_prop(8, 7, "mon_dual_dash", oy=-18, block=False, custom_depth=7 * TILE + 24)
    add_prop(7, 7, "laptop", ox=-10, oy=-14, block=False, custom_depth=7 * TILE + 24)
    add_prop(9, 7, "coffee_mug", ox=16, oy=-12, block=False, custom_depth=7 * TILE + 24)
    add_prop(8, 6, "chair_exec", oy=-4, block=False, custom_depth=6 * TILE + 4)
    add_prop(13, 9, "sofa_wine")
    add_prop(13, 11, "coffee_table")
    add_prop(2, 11, "plant_tree")
    add_prop(15, 5, "plant_monstera")
    add_prop(15, 11, "floor_lamp")
    add_prop(6, 7, "trash_bin", ox=-6, oy=10, block=False)

    # B. Development Wing (Fonseca, Balsini, Noe, Ford)
    add_prop(22, 2, "whiteboard_kanban", oy=-2, block=False, custom_depth=2 * TILE + 36)
    add_prop(30, 2, "whiteboard_plan", oy=-2, block=False, custom_depth=2 * TILE + 36)
    add_prop(36, 2, "wall_clock", oy=-6, block=False, custom_depth=2 * TILE + 36)

    dev_stations = [
        (21, 6, "desk_white", "mon_dual_code"),
        (26, 6, "desk_white", "mon_dual_chart"),
        (31, 6, "desk_wood", "mon_dual_code"),
        (36, 6, "desk_white", "mon_dual_dash"),
    ]
    for c, r, dtex, mtex in dev_stations:
        add_prop(c, r, dtex)
        add_prop(c, r, mtex, oy=-16, block=False, custom_depth=r * TILE + 24)
        add_prop(c, r, "keyboard", oy=-6, block=False, custom_depth=r * TILE + 25)
        add_prop(c, r, "coffee_mug", ox=20, oy=-8, block=False, custom_depth=r * TILE + 25)
        add_prop(c, r + 1, "chair_back", oy=-2, block=False, custom_depth=(r + 1) * TILE + 24)

    add_prop(19, 11, "bookshelf")
    add_prop(21, 11, "printer")
    add_prop(37, 11, "water_cooler")
    add_prop(25, 11, "beanbag_yellow")
    add_prop(27, 11, "beanbag_pink")
    add_prop(19, 5, "plant_monstera")
    add_prop(37, 5, "plant_snake")

    # C. Infrastructure Hub (Jarvis)
    add_prop(47, 2, "monitoring_wall", oy=-2, block=False, custom_depth=2 * TILE + 36)
    for rc, rtex in [(42, "server_rack_a"), (44, "server_rack_b"), (46, "server_rack_c"), (50, "server_rack_a"), (52, "server_rack_b")]:
        add_prop(rc, 5, rtex)
    add_prop(54, 5, "network_cabinet")
    add_prop(54, 7, "ups_unit")
    add_prop(47, 6, "cable_run", block=False, custom_depth=6 * TILE)

    add_prop(47, 9, "desk_dark")
    add_prop(47, 9, "mon_dual_dash", oy=-16, block=False, custom_depth=9 * TILE + 24)
    add_prop(47, 9, "keyboard", oy=-6, block=False, custom_depth=9 * TILE + 25)
    add_prop(47, 10, "chair_back", oy=-2, block=False, custom_depth=10 * TILE + 24)
    add_prop(41, 11, "filing_cabinet")

    # D. Content Studio (Script Agent, News Agent)
    add_prop(5, 18, "cork_board", oy=-2, block=False, custom_depth=18 * TILE + 36)
    add_prop(11, 18, "painting_chart", oy=-2, block=False, custom_depth=18 * TILE + 36)

    add_prop(5, 21, "desk_wood")
    add_prop(5, 21, "mon_script", oy=-16, block=False, custom_depth=21 * TILE + 24)
    add_prop(5, 21, "desk_mic", ox=-18, oy=-12, block=False, custom_depth=21 * TILE + 24)
    add_prop(5, 21, "paper_stack", ox=18, oy=-10, block=False, custom_depth=21 * TILE + 24)
    add_prop(5, 22, "chair_back", oy=-2, block=False, custom_depth=22 * TILE + 24)

    add_prop(12, 21, "desk_wood")
    add_prop(12, 21, "mon_news", oy=-16, block=False, custom_depth=21 * TILE + 24)
    add_prop(12, 21, "laptop", ox=16, oy=-10, block=False, custom_depth=21 * TILE + 24)
    add_prop(12, 22, "chair_back", oy=-2, block=False, custom_depth=22 * TILE + 24)

    add_prop(2, 24, "bookshelf")
    add_prop(15, 25, "sofa_orange")
    add_prop(15, 19, "plant_monstera")
    add_prop(2, 19, "floor_lamp")

    # E. Empire Boardroom (Meeting Room)
    add_prop(28, 18, "tv_graph", oy=-2, block=False, custom_depth=18 * TILE + 36)
    add_prop(22, 18, "whiteboard_plan", oy=-2, block=False, custom_depth=18 * TILE + 36)
    add_prop(28, 22, "conference_table")
    add_prop(28, 22, "projector", oy=-4, block=False, custom_depth=22 * TILE + 28)
    for cx in [23, 26, 29, 32]:
        add_prop(cx, 20, "chair_front_wine", oy=4, block=False, custom_depth=20 * TILE + 12)
        add_prop(cx, 24, "chair_back_red", oy=-2, block=False, custom_depth=24 * TILE + 24)
    add_prop(20, 25, "plant_tree")
    add_prop(36, 25, "plant_snake")
    add_prop(36, 19, "water_cooler")

    # F. QA Quality Gate (Murphy)
    add_prop(45, 18, "whiteboard_kanban", oy=-2, block=False, custom_depth=18 * TILE + 36)
    add_prop(52, 18, "cork_board", oy=-2, block=False, custom_depth=18 * TILE + 36)
    add_prop(46, 21, "desk_white")
    add_prop(46, 21, "mon_dual_test", oy=-16, block=False, custom_depth=21 * TILE + 24)
    add_prop(46, 21, "paper_stack", ox=18, oy=-10, block=False, custom_depth=21 * TILE + 24)
    add_prop(46, 22, "chair_back_red", oy=-2, block=False, custom_depth=22 * TILE + 24)
    add_prop(52, 22, "bench_table")
    add_prop(52, 22, "laptop", ox=-14, oy=-12, block=False, custom_depth=22 * TILE + 24)
    add_prop(52, 22, "printer", ox=18, oy=-10, block=False, custom_depth=22 * TILE + 26)
    add_prop(41, 25, "filing_cabinet")
    add_prop(55, 25, "plant_snake")

    # G. Breakroom, Cafe & Reception
    add_prop(4, 31, "kitchen_counter")
    add_prop(8, 31, "fridge")
    add_prop(10, 31, "vending_machine")
    add_prop(2, 31, "water_cooler")
    add_prop(3, 34, "bench_table")
    add_prop(8, 35, "arcade")
    add_prop(5, 35, "foosball")

    add_prop(16, 30, "logo_wall", oy=-2, block=False, custom_depth=30 * TILE + 36)
    add_prop(21, 30, "wall_clock", oy=-6, block=False, custom_depth=30 * TILE + 36)
    add_prop(18, 33, "sofa_teal")
    add_prop(18, 35, "coffee_table")
    add_prop(14, 34, "armchair_red")
    add_prop(22, 34, "armchair_blue")
    add_prop(18, 36, "reception_desk")
    add_prop(18, 36, "mon_back", oy=-14, block=False, custom_depth=36 * TILE + 24)
    add_prop(12, 35, "plant_tree")
    add_prop(23, 31, "plant_monstera")

    # H. Audiovisual Production Studio
    for ac in [28, 32, 36, 40, 44, 48]:
        add_prop(ac, 30, "acoustic_panel", oy=-2, block=False, custom_depth=30 * TILE + 34)
    add_prop(52, 30, "neon_sign", oy=-4, block=False, custom_depth=30 * TILE + 36)

    av_stations = [
        (29, 33, "desk_dark", "mon_wave", "mixer", "mic_stand"),
        (34, 33, "desk_dark", "mon_subs", "headphones", None),
        (39, 33, "desk_dark", "mon_timeline", "keyboard", None),
        (44, 33, "desk_white", "mon_design", "drawing_tablet", "desk_lamp"),
        (49, 33, "desk_dark", "mon_timeline", "laptop", None),
    ]
    for c, r, dtex, mtex, extra1, extra2 in av_stations:
        add_prop(c, r, dtex)
        add_prop(c, r, mtex, oy=-16, block=False, custom_depth=r * TILE + 24)
        if extra1:
            add_prop(c, r, extra1, ox=16, oy=-8, block=False, custom_depth=r * TILE + 25)
        if extra2 and extra2 == "mic_stand":
            add_prop(c - 1, r + 1, extra2, ox=-6)
        elif extra2:
            add_prop(c, r, extra2, ox=-20, oy=-14, block=False, custom_depth=r * TILE + 25)
        add_prop(c, r + 1, "chair_back", oy=-2, block=False, custom_depth=(r + 1) * TILE + 24)

    # Recording / Filming Set on the right of AV Studio
    add_prop(54, 32, "green_screen")
    add_prop(53, 35, "camera_tripod")
    add_prop(51, 34, "softbox")
    add_prop(55, 34, "ring_light")
    add_prop(27, 35, "plant_snake")

    # 4. All 14 Agents Spawn & Target Points
    agents = [
        {"id": "jeffrey", "name": "Jeffrey", "role": "CEO & Principal AI", "dept": "Executive", "x": 8 * TILE + 16, "y": 6 * TILE + 12, "facing": "front", "meetX": 28 * TILE + 16, "meetY": 20 * TILE + 16, "breakX": 5 * TILE, "breakY": 32 * TILE},
        {"id": "fonseca", "name": "Fonseca", "role": "Frontend Engineer", "dept": "Development", "x": 21 * TILE + 16, "y": 7 * TILE + 8, "facing": "back", "meetX": 23 * TILE + 16, "meetY": 20 * TILE + 16, "breakX": 8 * TILE, "breakY": 32 * TILE},
        {"id": "balsini", "name": "Balsini", "role": "Backend Engineer", "dept": "Development", "x": 26 * TILE + 16, "y": 7 * TILE + 8, "facing": "back", "meetX": 26 * TILE + 16, "meetY": 20 * TILE + 16, "breakX": 4 * TILE, "breakY": 33 * TILE},
        {"id": "noe", "name": "Noé", "role": "Software Architect", "dept": "Development", "x": 31 * TILE + 16, "y": 7 * TILE + 8, "facing": "back", "meetX": 29 * TILE + 16, "meetY": 20 * TILE + 16, "breakX": 14 * TILE, "breakY": 32 * TILE},
        {"id": "ford", "name": "Ford", "role": "Data Engineer", "dept": "Development", "x": 36 * TILE + 16, "y": 7 * TILE + 8, "facing": "back", "meetX": 32 * TILE + 16, "meetY": 20 * TILE + 16, "breakX": 6 * TILE, "breakY": 32 * TILE},
        {"id": "jarvis", "name": "Jarvis", "role": "DevOps Engineer", "dept": "Infrastructure", "x": 47 * TILE + 16, "y": 10 * TILE + 8, "facing": "back", "meetX": 23 * TILE + 16, "meetY": 24 * TILE + 12, "breakX": 37 * TILE, "breakY": 12 * TILE},
        {"id": "script_agent", "name": "Script Agent", "role": "Script Specialist", "dept": "Content", "x": 5 * TILE + 16, "y": 22 * TILE + 8, "facing": "back", "meetX": 26 * TILE + 16, "meetY": 24 * TILE + 12, "breakX": 14 * TILE, "breakY": 24 * TILE},
        {"id": "news_agent", "name": "News Agent", "role": "News Researcher", "dept": "Content", "x": 12 * TILE + 16, "y": 22 * TILE + 8, "facing": "back", "meetX": 29 * TILE + 16, "meetY": 24 * TILE + 12, "breakX": 3 * TILE, "breakY": 32 * TILE},
        {"id": "murphy", "name": "Murphy", "role": "QA Engineer", "dept": "QA", "x": 46 * TILE + 16, "y": 22 * TILE + 8, "facing": "back", "meetX": 32 * TILE + 16, "meetY": 24 * TILE + 12, "breakX": 36 * TILE, "breakY": 20 * TILE},
        {"id": "voice_agent", "name": "Voice Agent", "role": "Audio Specialist", "dept": "Audiovisual", "x": 29 * TILE + 16, "y": 34 * TILE + 8, "facing": "back", "meetX": 20 * TILE + 16, "meetY": 22 * TILE + 16, "breakX": 16 * TILE, "breakY": 32 * TILE},
        {"id": "subtitle_agent", "name": "Subtitle Agent", "role": "Subtitles Specialist", "dept": "Audiovisual", "x": 34 * TILE + 16, "y": 34 * TILE + 8, "facing": "back", "meetX": 35 * TILE + 16, "meetY": 22 * TILE + 16, "breakX": 17 * TILE, "breakY": 32 * TILE},
        {"id": "clipador_agent", "name": "Clipador Agent", "role": "Clip Specialist", "dept": "Audiovisual", "x": 39 * TILE + 16, "y": 34 * TILE + 8, "facing": "back", "meetX": 21 * TILE + 16, "meetY": 24 * TILE + 12, "breakX": 8 * TILE, "breakY": 33 * TILE},
        {"id": "designer_agent", "name": "Designer Agent", "role": "Pixel Art Designer", "dept": "Audiovisual", "x": 44 * TILE + 16, "y": 34 * TILE + 8, "facing": "back", "meetX": 35 * TILE + 16, "meetY": 24 * TILE + 12, "breakX": 19 * TILE, "breakY": 32 * TILE},
        {"id": "video_agent", "name": "Video Agent", "role": "Video Director", "dept": "Audiovisual", "x": 49 * TILE + 16, "y": 34 * TILE + 8, "facing": "back", "meetX": 28 * TILE + 16, "meetY": 25 * TILE + 12, "breakX": 52 * TILE, "breakY": 35 * TILE},
    ]

    # Department zones for camera focus & architectural signage
    rooms = [
        {"id": "ceo", "name": "CEO SUITE • JEFFREY", "x": 8 * TILE, "y": 7 * TILE, "labelX": 8 * TILE, "labelY": 2 * TILE - 12, "color": "#f59e0b", "zoom": 1.35},
        {"id": "dev", "name": "DEVELOPMENT WING", "x": 28 * TILE, "y": 7 * TILE, "labelX": 28 * TILE, "labelY": 2 * TILE - 12, "color": "#06b6d4", "zoom": 1.25},
        {"id": "infra", "name": "INFRASTRUCTURE & SERVERS", "x": 48 * TILE, "y": 7 * TILE, "labelX": 48 * TILE, "labelY": 2 * TILE - 12, "color": "#3b82f6", "zoom": 1.3},
        {"id": "content", "name": "CONTENT STUDIO", "x": 8 * TILE, "y": 21 * TILE, "labelX": 8 * TILE, "labelY": 17 * TILE - 12, "color": "#a855f7", "zoom": 1.3},
        {"id": "meeting", "name": "EMPIRE BOARDROOM", "x": 28 * TILE, "y": 22 * TILE, "labelX": 28 * TILE, "labelY": 17 * TILE - 12, "color": "#eab308", "zoom": 1.3},
        {"id": "qa", "name": "QA QUALITY GATE", "x": 48 * TILE, "y": 21 * TILE, "labelX": 48 * TILE, "labelY": 17 * TILE - 12, "color": "#ef4444", "zoom": 1.3},
        {"id": "lounge", "name": "RECEPTION & BREAKROOM", "x": 12 * TILE, "y": 33 * TILE, "labelX": 12 * TILE, "labelY": 29 * TILE - 12, "color": "#10b981", "zoom": 1.25},
        {"id": "audiovisual", "name": "AUDIOVISUAL STUDIO", "x": 41 * TILE, "y": 33 * TILE, "labelX": 41 * TILE, "labelY": 29 * TILE - 12, "color": "#ec4899", "zoom": 1.2},
    ]

    return {
        "compressionlevel": -1,
        "height": ROWS,
        "width": COLS,
        "tileheight": TILE,
        "tilewidth": TILE,
        "infinite": False,
        "orientation": "orthogonal",
        "renderorder": "right-down",
        "type": "map",
        "version": "1.10",
        "layers": [
            {
                "id": 1,
                "name": "floor",
                "type": "tilelayer",
                "width": COLS,
                "height": ROWS,
                "opacity": 1,
                "visible": True,
                "data": floor,
            },
            {
                "id": 2,
                "name": "collision",
                "type": "tilelayer",
                "width": COLS,
                "height": ROWS,
                "opacity": 0,
                "visible": False,
                "data": collision,
            },
        ],
        "tilesets": [
            {
                "firstgid": 1,
                "name": "office_floors",
                "image": "/sprites/tilesets/office_floors.png",
                "tilewidth": TILE,
                "tileheight": TILE,
                "columns": 8,
            }
        ],
        "custom": {
            "rugs": rugs,
            "walls": walls,
            "props": props,
            "agents": agents,
            "rooms": rooms,
        },
    }

