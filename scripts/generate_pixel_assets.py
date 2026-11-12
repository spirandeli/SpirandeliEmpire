#!/usr/bin/env python3
"""
SpirandeliEmpire OS 3.1 — Pixel Art Asset Generator
Creates high-fidelity pixel art sprites, tilesets, furniture, decorations,
animations, and portraits for the 14 agents and the virtual office.
"""

import os
from PIL import Image, ImageDraw

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLIC_DIR = os.path.join(ROOT_DIR, "frontend", "public", "sprites")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# -------------------------------------------------------------
# Color Palettes & Helpers
# -------------------------------------------------------------
TRANSPARENT = (0, 0, 0, 0)
OUTLINE = (22, 24, 38, 255)       # Crisp dark outline
OUTLINE_SOFT = (35, 40, 58, 255)
SHADOW = (0, 0, 0, 70)

SKIN_TONES = {
    "fair": [(255, 230, 204, 255), (235, 195, 165, 255), (205, 160, 130, 255)],
    "warm": [(240, 200, 160, 255), (215, 165, 125, 255), (180, 130, 95, 255)],
    "olive": [(220, 180, 140, 255), (190, 145, 105, 255), (155, 110, 75, 255)],
    "tanned": [(195, 145, 105, 255), (165, 115, 80, 255), (135, 90, 60, 255)],
    "dark": [(140, 95, 70, 255), (110, 70, 48, 255), (85, 50, 32, 255)]
}

# -------------------------------------------------------------
# Agent Definitions
# -------------------------------------------------------------
AGENTS = {
    "jeffrey": {
        "folder": "jeffrey",
        "name": "Jeffrey",
        "role": "CEO",
        "hair_color": [(50, 40, 35, 255), (35, 28, 25, 255)],
        "hair_style": "executive",
        "skin": "warm",
        "top_color": [(30, 58, 138, 255), (23, 37, 84, 255)],  # Navy CEO suit
        "tie_color": [(220, 38, 38, 255), (153, 27, 27, 255)],   # Red silk tie
        "pants_color": [(15, 23, 42, 255), (2, 6, 23, 255)],
        "accessory": "tie",
        "accent": (234, 179, 8, 255)  # Gold watch
    },
    "fonseca": {
        "folder": "fonseca",
        "name": "Fonseca",
        "role": "Frontend",
        "hair_color": [(40, 35, 30, 255), (25, 20, 18, 255)],
        "hair_style": "curly_fade",
        "skin": "olive",
        "top_color": [(13, 148, 136, 255), (15, 118, 110, 255)], # Teal hoodie
        "tie_color": None,
        "pants_color": [(30, 41, 59, 255), (15, 23, 42, 255)],
        "accessory": "glasses",
        "accent": (20, 184, 166, 255)
    },
    "balsini": {
        "folder": "balsini",
        "name": "Balsini",
        "role": "Backend",
        "hair_color": [(70, 50, 40, 255), (50, 35, 28, 255)],
        "hair_style": "short_part",
        "skin": "fair",
        "top_color": [(39, 39, 42, 255), (24, 24, 27, 255)],   # Dark tech tee
        "tie_color": None,
        "pants_color": [(71, 85, 105, 255), (51, 65, 85, 255)],
        "accessory": "beard",
        "accent": (16, 185, 129, 255)
    },
    "jarvis": {
        "folder": "jarvis",
        "name": "Jarvis",
        "role": "DevOps",
        "hair_color": [(30, 35, 45, 255), (18, 22, 30, 255)],
        "hair_style": "buzz",
        "skin": "warm",
        "top_color": [(51, 65, 85, 255), (30, 41, 59, 255)],   # Tactical utility vest
        "tie_color": None,
        "pants_color": [(30, 41, 59, 255), (15, 23, 42, 255)],
        "accessory": "headset",
        "accent": (59, 130, 246, 255)
    },
    "noe": {
        "folder": "noe",
        "name": "Noé",
        "role": "Architect",
        "hair_color": [(120, 115, 110, 255), (90, 85, 80, 255)], # Salt & pepper
        "hair_style": "mature_side",
        "skin": "fair",
        "top_color": [(67, 56, 202, 255), (49, 46, 129, 255)], # Indigo knit cardigan
        "tie_color": None,
        "pants_color": [(161, 98, 7, 255), (113, 63, 18, 255)], # Khaki
        "accessory": "glasses",
        "accent": (139, 92, 246, 255)
    },
    "ford": {
        "folder": "ford",
        "name": "Ford",
        "role": "Data",
        "hair_color": [(180, 83, 9, 255), (146, 64, 14, 255)], # Redhead / Auburn
        "hair_style": "messy_curly",
        "skin": "fair",
        "top_color": [(185, 28, 28, 255), (127, 29, 29, 255)], # Flannel red
        "tie_color": None,
        "pants_color": [(30, 58, 138, 255), (23, 37, 84, 255)],
        "accessory": "neck_headphones",
        "accent": (245, 158, 11, 255)
    },
    "murphy": {
        "folder": "murphy",
        "name": "Murphy",
        "role": "QA Lead",
        "hair_color": [(45, 30, 25, 255), (30, 20, 18, 255)],
        "hair_style": "neat_bob",
        "skin": "warm",
        "top_color": [(159, 18, 57, 255), (136, 19, 55, 255)], # Crimson blazer
        "tie_color": None,
        "pants_color": [(24, 24, 27, 255), (9, 9, 11, 255)],
        "accessory": "glasses_clipboard",
        "accent": (239, 68, 68, 255)
    },
    "script-agent": {
        "folder": "script-agent",
        "name": "Script Agent",
        "role": "Content",
        "hair_color": [(60, 40, 30, 255), (40, 25, 20, 255)],
        "hair_style": "long_ponytail",
        "skin": "fair",
        "top_color": [(202, 138, 4, 255), (161, 98, 7, 255)],  # Mustard sweater
        "tie_color": None,
        "pants_color": [(51, 65, 85, 255), (30, 41, 59, 255)],
        "accessory": "scarf",
        "accent": (234, 179, 8, 255)
    },
    "news-agent": {
        "folder": "news-agent",
        "name": "News Agent",
        "role": "Researcher",
        "hair_color": [(35, 30, 25, 255), (20, 18, 15, 255)],
        "hair_style": "side_swept",
        "skin": "olive",
        "top_color": [(8, 145, 178, 255), (14, 116, 144, 255)], # Cyan trench/polo
        "tie_color": None,
        "pants_color": [(30, 41, 59, 255), (15, 23, 42, 255)],
        "accessory": "press_badge",
        "accent": (6, 182, 212, 255)
    },
    "voice-agent": {
        "folder": "voice-agent",
        "name": "Voice Agent",
        "role": "Audio",
        "hair_color": [(80, 50, 35, 255), (55, 35, 25, 255)],
        "hair_style": "waves",
        "skin": "dark",
        "top_color": [(147, 51, 234, 255), (126, 34, 206, 255)], # Purple audio hoodie
        "tie_color": None,
        "pants_color": [(24, 24, 27, 255), (9, 9, 11, 255)],
        "accessory": "studio_headphones",
        "accent": (168, 85, 247, 255)
    },
    "subtitle-agent": {
        "folder": "subtitle-agent",
        "name": "Subtitle Agent",
        "role": "Subtitles",
        "hair_color": [(40, 35, 30, 255), (25, 22, 20, 255)],
        "hair_style": "short_neat",
        "skin": "tanned",
        "top_color": [(37, 99, 235, 255), (29, 78, 216, 255)], # Royal blue
        "tie_color": None,
        "pants_color": [(71, 85, 105, 255), (51, 65, 85, 255)],
        "accessory": "glasses",
        "accent": (59, 130, 246, 255)
    },
    "clipador-agent": {
        "folder": "clipador-agent",
        "name": "Clipador Agent",
        "role": "Video Clips",
        "hair_color": [(45, 35, 30, 255), (30, 22, 20, 255)],
        "hair_style": "cap_backward",
        "skin": "warm",
        "top_color": [(234, 88, 12, 255), (194, 65, 12, 255)], # Orange streetwear
        "tie_color": None,
        "pants_color": [(15, 23, 42, 255), (2, 6, 23, 255)],
        "accessory": "cap",
        "accent": (249, 115, 22, 255)
    },
    "designer-agent": {
        "folder": "designer-agent",
        "name": "Designer Agent",
        "role": "Design",
        "hair_color": [(180, 80, 120, 255), (130, 50, 90, 255)], # Magenta-tinted hair
        "hair_style": "beret",
        "skin": "fair",
        "top_color": [(219, 39, 119, 255), (190, 24, 93, 255)], # Pink creative
        "tie_color": None,
        "pants_color": [(51, 65, 85, 255), (30, 41, 59, 255)],
        "accessory": "beret_stylus",
        "accent": (236, 72, 153, 255)
    },
    "video-agent": {
        "folder": "video-agent",
        "name": "Video Agent",
        "role": "Director",
        "hair_color": [(50, 45, 40, 255), (35, 30, 28, 255)],
        "hair_style": "bun",
        "skin": "olive",
        "top_color": [(109, 40, 217, 255), (91, 33, 182, 255)], # Deep violet
        "tie_color": None,
        "pants_color": [(24, 24, 27, 255), (9, 9, 11, 255)],
        "accessory": "director_clapper",
        "accent": (139, 92, 246, 255)
    }
}

# -------------------------------------------------------------
# Drawing Character Sprites (32 x 48)
# -------------------------------------------------------------
def draw_agent_frame(agent, action="idle", frame_idx=0, direction="down"):
    """
    Renders a 32x48 character frame with authentic Habbo-like proportions.
    Head: ~14x14, Torso: ~12x14, Legs: ~8x14.
    """
    img = Image.new("RGBA", (32, 48), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    skin_light, skin_mid, skin_dark = SKIN_TONES[agent["skin"]]
    hair_light, hair_dark = agent["hair_color"]
    top_light, top_dark = agent["top_color"]
    pants_light, pants_dark = agent["pants_color"]

    # Bobbing / breathing offset
    y_off = 0
    if action == "idle":
        y_off = 1 if frame_idx in (1, 2) else 0
    elif action == "work":
        y_off = 1 if (frame_idx % 2 == 1) else 0

    # Leg offsets for walking
    leg_l_off = 0
    leg_r_off = 0
    if action == "walk":
        if frame_idx == 1:
            leg_l_off = -3
            leg_r_off = 2
        elif frame_idx == 3:
            leg_l_off = 2
            leg_r_off = -3

    # 1. Ground Shadow (under feet)
    shadow_w = 20 if action != "sit" else 24
    draw.ellipse([16 - shadow_w//2, 43, 16 + shadow_w//2, 47], fill=(0, 0, 0, 80))

    if action == "sit":
        # Sitting character: lower torso and legs tucked forward
        # Pants / lap
        draw.rectangle([10, 34, 22, 42], fill=pants_dark, outline=OUTLINE)
        draw.rectangle([11, 35, 21, 38], fill=pants_light)
        # Shoes tucked
        draw.rectangle([10, 42, 14, 45], fill=(20, 20, 25, 255))
        draw.rectangle([18, 42, 22, 45], fill=(20, 20, 25, 255))
        # Torso
        t_y = 22 + y_off
        draw.rectangle([9, t_y, 23, t_y + 12], fill=top_dark, outline=OUTLINE)
        draw.rectangle([11, t_y + 1, 21, t_y + 10], fill=top_light)
        # Arms forward (typing)
        draw.rectangle([7, t_y + 4, 10, t_y + 11], fill=top_dark, outline=OUTLINE)
        draw.rectangle([22, t_y + 4, 25, t_y + 11], fill=top_dark, outline=OUTLINE)
        # Hands on desk
        draw.rectangle([7, t_y + 10, 11, t_y + 13], fill=skin_mid)
        draw.rectangle([21, t_y + 10, 25, t_y + 13], fill=skin_mid)
    else:
        # Standing / Walking legs
        # Left Leg
        draw.rectangle([10, 34 + leg_l_off, 14, 44 + leg_l_off], fill=pants_dark, outline=OUTLINE)
        draw.rectangle([11, 34 + leg_l_off, 13, 42 + leg_l_off], fill=pants_light)
        draw.rectangle([9, 43 + leg_l_off, 14, 45 + leg_l_off], fill=(25, 25, 30, 255), outline=OUTLINE) # Shoe

        # Right Leg
        draw.rectangle([17, 34 + leg_r_off, 21, 44 + leg_r_off], fill=pants_dark, outline=OUTLINE)
        draw.rectangle([18, 34 + leg_r_off, 20, 42 + leg_r_off], fill=pants_light)
        draw.rectangle([17, 43 + leg_r_off, 22, 45 + leg_r_off], fill=(25, 25, 30, 255), outline=OUTLINE) # Shoe

        # Torso
        t_y = 20 + y_off
        draw.rectangle([9, t_y, 22, t_y + 14], fill=top_dark, outline=OUTLINE)
        draw.rectangle([11, t_y + 1, 20, t_y + 12], fill=top_light)

        # Arms
        if direction in ("down", "up"):
            arm_l_y = t_y + 2 - (leg_l_off // 2)
            arm_r_y = t_y + 2 - (leg_r_off // 2)
            draw.rectangle([6, arm_l_y, 9, arm_l_y + 10], fill=top_dark, outline=OUTLINE)
            draw.rectangle([7, arm_l_y + 1, 8, arm_l_y + 8], fill=top_light)
            draw.rectangle([6, arm_l_y + 8, 9, arm_l_y + 11], fill=skin_mid) # Hand

            draw.rectangle([22, arm_r_y, 25, arm_r_y + 10], fill=top_dark, outline=OUTLINE)
            draw.rectangle([23, arm_r_y + 1, 24, arm_r_y + 8], fill=top_light)
            draw.rectangle([22, arm_r_y + 8, 25, arm_r_y + 11], fill=skin_mid) # Hand
        elif direction == "left":
            draw.rectangle([10, t_y + 2, 14, t_y + 11], fill=top_dark, outline=OUTLINE)
            draw.rectangle([9, t_y + 8, 12, t_y + 11], fill=skin_mid)
        elif direction == "right":
            draw.rectangle([18, t_y + 2, 22, t_y + 11], fill=top_dark, outline=OUTLINE)
            draw.rectangle([20, t_y + 8, 23, t_y + 11], fill=skin_mid)

    # Torso details (Tie / Collar / Scarf)
    t_y = 20 + y_off if action != "sit" else 22 + y_off
    if direction == "down" or action == "sit":
        if agent["tie_color"]:
            tie_light, tie_dark = agent["tie_color"]
            draw.rectangle([15, t_y + 1, 17, t_y + 9], fill=tie_dark)
            draw.rectangle([15, t_y + 2, 16, t_y + 7], fill=tie_light)
        elif agent["accessory"] == "scarf":
            draw.rectangle([11, t_y, 21, t_y + 4], fill=(245, 158, 11, 255), outline=OUTLINE)
            draw.rectangle([13, t_y + 3, 16, t_y + 8], fill=(217, 119, 6, 255))
        elif agent["name"] == "Fonseca": # Hoodie strings
            draw.rectangle([13, t_y + 2, 14, t_y + 7], fill=(240, 240, 240, 255))
            draw.rectangle([18, t_y + 2, 19, t_y + 7], fill=(240, 240, 240, 255))
        elif agent["name"] == "Jarvis": # Utility pockets
            draw.rectangle([11, t_y + 5, 14, t_y + 8], fill=(30, 41, 59, 255), outline=OUTLINE)
            draw.rectangle([18, t_y + 5, 21, t_y + 8], fill=(30, 41, 59, 255), outline=OUTLINE)

    # Head (14 x 14)
    h_y = 7 + y_off
    if action == "sit":
        h_y = 9 + y_off

    # Neck
    draw.rectangle([14, h_y + 12, 18, h_y + 14], fill=skin_dark)

    # Face base
    draw.rectangle([9, h_y + 2, 22, h_y + 12], fill=skin_mid, outline=OUTLINE)
    draw.rectangle([10, h_y + 3, 21, h_y + 11], fill=skin_light)

    # Ears
    if direction in ("down", "up"):
        draw.rectangle([7, h_y + 5, 9, h_y + 8], fill=skin_mid, outline=OUTLINE)
        draw.rectangle([22, h_y + 5, 24, h_y + 8], fill=skin_mid, outline=OUTLINE)

    # Eyes & Face details
    if direction == "down" or action in ("idle", "work", "sit"):
        # Blinking logic for idle
        is_blinking = (action == "idle" and frame_idx == 2)
        if not is_blinking:
            # Left Eye
            draw.rectangle([11, h_y + 5, 13, h_y + 7], fill=(30, 30, 40, 255))
            draw.point((12, h_y + 5), fill=(255, 255, 255, 255)) # Glimmer
            # Right Eye
            draw.rectangle([18, h_y + 5, 20, h_y + 7], fill=(30, 30, 40, 255))
            draw.point((19, h_y + 5), fill=(255, 255, 255, 255)) # Glimmer
        else:
            # Closed eyes (blink line)
            draw.rectangle([11, h_y + 6, 13, h_y + 6], fill=(50, 40, 35, 255))
            draw.rectangle([18, h_y + 6, 20, h_y + 6], fill=(50, 40, 35, 255))

        # Smile / mouth
        draw.point((15, h_y + 9), fill=(180, 100, 80, 255))
        draw.point((16, h_y + 9), fill=(180, 100, 80, 255))

        # Glasses
        if "glasses" in agent["accessory"]:
            draw.rectangle([10, h_y + 4, 14, h_y + 8], outline=(15, 23, 42, 255))
            draw.rectangle([17, h_y + 4, 21, h_y + 8], outline=(15, 23, 42, 255))
            draw.rectangle([14, h_y + 5, 17, h_y + 5], fill=(15, 23, 42, 255)) # Bridge

        # Beard for Balsini
        if "beard" in agent["accessory"]:
            draw.rectangle([11, h_y + 9, 20, h_y + 12], fill=hair_dark)
            draw.rectangle([12, h_y + 10, 19, h_y + 11], fill=hair_light)

    elif direction == "left":
        draw.rectangle([10, h_y + 5, 12, h_y + 7], fill=(30, 30, 40, 255))
        draw.point((10, h_y + 5), fill=(255, 255, 255, 255))
        draw.point((9, h_y + 8), fill=(210, 140, 110, 255)) # Nose
    elif direction == "right":
        draw.rectangle([19, h_y + 5, 21, h_y + 7], fill=(30, 30, 40, 255))
        draw.point((20, h_y + 5), fill=(255, 255, 255, 255))
        draw.point((22, h_y + 8), fill=(210, 140, 110, 255)) # Nose

    # Hair Styles
    style = agent["hair_style"]
    if style == "executive":
        # Sharp comb over
        draw.rectangle([8, h_y - 1, 23, h_y + 3], fill=hair_dark, outline=OUTLINE)
        draw.rectangle([9, h_y, 22, h_y + 2], fill=hair_light)
        draw.rectangle([8, h_y + 2, 10, h_y + 5], fill=hair_dark)
        draw.rectangle([21, h_y + 2, 23, h_y + 5], fill=hair_dark)
    elif style == "curly_fade":
        # Afro curly top with fade sides
        draw.rectangle([8, h_y - 2, 23, h_y + 2], fill=hair_dark, outline=OUTLINE)
        draw.rectangle([9, h_y - 1, 22, h_y + 1], fill=hair_light)
        draw.point((12, h_y - 3), fill=hair_light)
        draw.point((16, h_y - 3), fill=hair_light)
        draw.point((19, h_y - 3), fill=hair_light)
        draw.rectangle([8, h_y + 3, 10, h_y + 5], fill=hair_dark)
    elif style == "short_part":
        draw.rectangle([8, h_y - 1, 23, h_y + 3], fill=hair_dark, outline=OUTLINE)
        draw.rectangle([11, h_y, 22, h_y + 2], fill=hair_light)
    elif style == "buzz":
        draw.rectangle([9, h_y, 22, h_y + 3], fill=hair_dark, outline=OUTLINE)
    elif style == "mature_side":
        draw.rectangle([8, h_y - 1, 23, h_y + 3], fill=hair_dark, outline=OUTLINE)
        draw.rectangle([9, h_y, 22, h_y + 2], fill=hair_light)
        draw.rectangle([8, h_y + 3, 10, h_y + 6], fill=(160, 160, 160, 255)) # Grey temples
    elif style == "messy_curly":
        draw.rectangle([7, h_y - 2, 24, h_y + 3], fill=hair_dark, outline=OUTLINE)
        draw.rectangle([8, h_y - 1, 23, h_y + 2], fill=hair_light)
        draw.point((11, h_y - 3), fill=hair_light)
        draw.point((15, h_y - 3), fill=hair_light)
        draw.point((20, h_y - 3), fill=hair_light)
    elif style == "neat_bob":
        draw.rectangle([8, h_y - 1, 23, h_y + 7], fill=hair_dark, outline=OUTLINE)
        draw.rectangle([9, h_y, 22, h_y + 2], fill=hair_light)
        draw.rectangle([8, h_y + 3, 10, h_y + 9], fill=hair_light)
        draw.rectangle([21, h_y + 3, 23, h_y + 9], fill=hair_light)
    elif style == "long_ponytail":
        draw.rectangle([8, h_y - 1, 23, h_y + 4], fill=hair_dark, outline=OUTLINE)
        draw.rectangle([9, h_y, 22, h_y + 2], fill=hair_light)
        draw.rectangle([22, h_y + 3, 25, h_y + 11], fill=hair_dark, outline=OUTLINE) # Ponytail
    elif style == "cap_backward":
        draw.rectangle([7, h_y - 1, 24, h_y + 3], fill=(234, 88, 12, 255), outline=OUTLINE)
        draw.rectangle([8, h_y, 23, h_y + 2], fill=(249, 115, 22, 255))
        draw.rectangle([6, h_y + 2, 10, h_y + 4], fill=(194, 65, 12, 255)) # Brim backward
    elif style == "beret":
        draw.rectangle([6, h_y - 3, 25, h_y + 2], fill=(157, 23, 77, 255), outline=OUTLINE)
        draw.rectangle([8, h_y - 2, 23, h_y + 1], fill=(219, 39, 119, 255))
        draw.point((15, h_y - 4), fill=(131, 24, 67, 255)) # Beret tip
    elif style == "bun":
        draw.rectangle([8, h_y - 1, 23, h_y + 4], fill=hair_dark, outline=OUTLINE)
        draw.rectangle([9, h_y, 22, h_y + 2], fill=hair_light)
        draw.rectangle([13, h_y - 4, 18, h_y - 1], fill=hair_dark, outline=OUTLINE) # Top bun

    # Special Head Accessories
    if "studio_headphones" in agent["accessory"]:
        # Big studio headphones over ears
        draw.arc([7, h_y - 2, 24, h_y + 7], 180, 360, fill=(30, 41, 59, 255), width=2)
        draw.rectangle([6, h_y + 4, 9, h_y + 9], fill=(79, 70, 229, 255), outline=OUTLINE)
        draw.rectangle([22, h_y + 4, 25, h_y + 9], fill=(79, 70, 229, 255), outline=OUTLINE)
    elif "headset" in agent["accessory"]:
        draw.rectangle([22, h_y + 5, 25, h_y + 8], fill=(30, 41, 59, 255), outline=OUTLINE)
        draw.line([(22, h_y + 8), (17, h_y + 10)], fill=(15, 23, 42, 255), width=1) # Mic boom
        draw.point((17, h_y + 10), fill=(239, 68, 68, 255))

    return img

def generate_agent_sprites():
    """Generates all animations and portraits for each agent."""
    for key, agent in AGENTS.items():
        agent_dir = os.path.join(PUBLIC_DIR, "agents", agent["folder"])
        ensure_dir(agent_dir)

        # 1. Idle Spritesheet (4 frames: 128 x 48)
        idle_sheet = Image.new("RGBA", (128, 48), TRANSPARENT)
        for i in range(4):
            f = draw_agent_frame(agent, action="idle", frame_idx=i, direction="down")
            idle_sheet.paste(f, (i * 32, 0))
        idle_sheet.save(os.path.join(agent_dir, "idle.png"))

        # 2. Walk Down Spritesheet (4 frames: 128 x 48)
        walk_down = Image.new("RGBA", (128, 48), TRANSPARENT)
        for i in range(4):
            f = draw_agent_frame(agent, action="walk", frame_idx=i, direction="down")
            walk_down.paste(f, (i * 32, 0))
        walk_down.save(os.path.join(agent_dir, "walk_down.png"))

        # 3. Walk Up Spritesheet (4 frames: 128 x 48)
        walk_up = Image.new("RGBA", (128, 48), TRANSPARENT)
        for i in range(4):
            f = draw_agent_frame(agent, action="walk", frame_idx=i, direction="up")
            walk_up.paste(f, (i * 32, 0))
        walk_up.save(os.path.join(agent_dir, "walk_up.png"))

        # 4. Walk Left & Right
        walk_left = Image.new("RGBA", (128, 48), TRANSPARENT)
        walk_right = Image.new("RGBA", (128, 48), TRANSPARENT)
        for i in range(4):
            f_l = draw_agent_frame(agent, action="walk", frame_idx=i, direction="left")
            walk_left.paste(f_l, (i * 32, 0))
            f_r = draw_agent_frame(agent, action="walk", frame_idx=i, direction="right")
            walk_right.paste(f_r, (i * 32, 0))
        walk_left.save(os.path.join(agent_dir, "walk_left.png"))
        walk_right.save(os.path.join(agent_dir, "walk_right.png"))

        # 5. Sit / Work Spritesheet (4 frames: 128 x 48)
        work_sheet = Image.new("RGBA", (128, 48), TRANSPARENT)
        for i in range(4):
            f = draw_agent_frame(agent, action="work" if i % 2 == 1 else "sit", frame_idx=i, direction="down")
            work_sheet.paste(f, (i * 32, 0))
        work_sheet.save(os.path.join(agent_dir, "work.png"))

        # 6. High-Res Pixel Art Portrait / Avatar (64 x 64)
        portrait = Image.new("RGBA", (64, 64), (15, 23, 42, 255))
        p_draw = ImageDraw.Draw(portrait)
        # Background gradient circle
        p_draw.ellipse([4, 4, 60, 60], fill=(30, 41, 59, 255), outline=agent["accent"], width=2)
        # Render agent body cropped & scaled
        char_frame = draw_agent_frame(agent, action="idle", frame_idx=0, direction="down")
        # Upscale 2x with NEAREST to preserve crisp pixel art
        char_2x = char_frame.resize((64, 96), Image.NEAREST)
        portrait.paste(char_2x, (0, -10), char_2x)
        # Border
        p_draw.rounded_rectangle([0, 0, 63, 63], radius=10, outline=OUTLINE, width=1)
        portrait.save(os.path.join(agent_dir, "avatar.png"))

    print(f"✓ Generated spritesheets and portraits for all {len(AGENTS)} agents.")

# -------------------------------------------------------------
# Environment Tiles (32 x 32)
# -------------------------------------------------------------
def generate_floor_tiles():
    floors_dir = os.path.join(PUBLIC_DIR, "environment", "floors")
    ensure_dir(floors_dir)

    # 1. Warm Oak Wood Floor (Planks with grain)
    wood = Image.new("RGBA", (32, 32), (180, 115, 65, 255))
    w_draw = ImageDraw.Draw(wood)
    # Plank borders
    w_draw.line([(0, 15), (31, 15)], fill=(130, 75, 35, 255), width=1)
    w_draw.line([(0, 31), (31, 31)], fill=(110, 60, 25, 255), width=1)
    # Staggered vertical joints
    w_draw.line([(15, 0), (15, 14)], fill=(130, 75, 35, 255), width=1)
    w_draw.line([(7, 16), (7, 30)], fill=(130, 75, 35, 255), width=1)
    w_draw.line([(23, 16), (23, 30)], fill=(130, 75, 35, 255), width=1)
    # Wood grain highlights
    w_draw.line([(2, 3), (12, 3)], fill=(200, 135, 80, 255))
    w_draw.line([(18, 7), (29, 7)], fill=(200, 135, 80, 255))
    w_draw.line([(3, 20), (6, 20)], fill=(200, 135, 80, 255))
    w_draw.line([(10, 25), (20, 25)], fill=(200, 135, 80, 255))
    wood.save(os.path.join(floors_dir, "wood_floor.png"))

    # 2. Executive Navy Blue Carpet
    navy = Image.new("RGBA", (32, 32), (23, 37, 84, 255))
    n_draw = ImageDraw.Draw(navy)
    for x in range(0, 32, 4):
        for y in range(0, 32, 4):
            if (x + y) % 8 == 0:
                n_draw.point((x + 1, y + 1), fill=(30, 58, 138, 255))
                n_draw.point((x + 2, y + 2), fill=(15, 23, 42, 255))
    navy.save(os.path.join(floors_dir, "carpet_navy.png"))

    # 3. Development Teal/Slate Carpet
    teal = Image.new("RGBA", (32, 32), (15, 46, 56, 255))
    t_draw = ImageDraw.Draw(teal)
    for x in range(0, 32, 4):
        for y in range(0, 32, 4):
            if (x + y) % 8 == 0:
                t_draw.point((x + 1, y + 1), fill=(21, 75, 92, 255))
                t_draw.point((x + 2, y + 2), fill=(10, 30, 38, 255))
    teal.save(os.path.join(floors_dir, "carpet_teal.png"))

    # 4. Boardroom / CEO Wine-Red Carpet
    wine = Image.new("RGBA", (32, 32), (76, 20, 35, 255))
    wn_draw = ImageDraw.Draw(wine)
    for x in range(0, 32, 4):
        for y in range(0, 32, 4):
            if (x + y) % 8 == 0:
                wn_draw.point((x + 1, y + 1), fill=(105, 28, 48, 255))
                wn_draw.point((x + 2, y + 2), fill=(50, 12, 22, 255))
    wine.save(os.path.join(floors_dir, "carpet_wine.png"))

    # 5. Server Room Steel Anti-Static Tile with Warning Edges
    steel = Image.new("RGBA", (32, 32), (30, 35, 45, 255))
    s_draw = ImageDraw.Draw(steel)
    s_draw.rectangle([0, 0, 31, 31], outline=(15, 18, 24, 255))
    # Grid bolts
    for bx, by in [(4, 4), (27, 4), (4, 27), (27, 27)]:
        s_draw.rectangle([bx-1, by-1, bx+1, by+1], fill=(71, 85, 105, 255))
        s_draw.point((bx, by), fill=(15, 23, 42, 255))
    # Steel mesh perforations
    for px in range(8, 24, 4):
        for py in range(8, 24, 4):
            s_draw.point((px, py), fill=(15, 18, 24, 255))
    steel.save(os.path.join(floors_dir, "server_steel.png"))

    # 6. Polished Marble / Terrazzo Corridor Tile
    marble = Image.new("RGBA", (32, 32), (226, 232, 240, 255))
    m_draw = ImageDraw.Draw(marble)
    m_draw.rectangle([0, 0, 31, 31], outline=(203, 213, 225, 255))
    # Subtle stone flecks
    m_draw.point((7, 9), fill=(148, 163, 184, 255))
    m_draw.point((8, 10), fill=(148, 163, 184, 255))
    m_draw.point((22, 6), fill=(148, 163, 184, 255))
    m_draw.point((17, 21), fill=(148, 163, 184, 255))
    m_draw.point((26, 24), fill=(148, 163, 184, 255))
    marble.save(os.path.join(floors_dir, "marble_tile.png"))

    # 7. Hazard Warning Stripe Border Tile (32 x 32)
    hazard = Image.new("RGBA", (32, 32), (234, 179, 8, 255)) # Yellow
    h_draw = ImageDraw.Draw(hazard)
    for i in range(-32, 64, 8):
        h_draw.polygon([(i, 0), (i+4, 0), (i+4+32, 32), (i+32, 32)], fill=(24, 24, 27, 255))
    hazard.save(os.path.join(floors_dir, "hazard_stripe.png"))

    print("✓ Generated floor tilesets.")

def generate_wall_tiles():
    walls_dir = os.path.join(PUBLIC_DIR, "environment", "walls")
    ensure_dir(walls_dir)

    # 1. Standard Office Wall (32 x 64: Top trim + Textured Wall Face + Baseboard)
    wall = Image.new("RGBA", (32, 64), TRANSPARENT)
    w_draw = ImageDraw.Draw(wall)
    # Wall top edge (top-down perspective thickness)
    w_draw.rectangle([0, 0, 31, 14], fill=(71, 85, 105, 255), outline=OUTLINE)
    w_draw.rectangle([1, 1, 30, 4], fill=(148, 163, 184, 255)) # Highlight
    # Wall front vertical face
    w_draw.rectangle([0, 15, 31, 56], fill=(51, 65, 85, 255), outline=OUTLINE)
    w_draw.rectangle([1, 15, 30, 20], fill=(71, 85, 105, 255)) # Upper shadow/bevel
    # Baseboard
    w_draw.rectangle([0, 57, 31, 63], fill=(30, 41, 59, 255), outline=OUTLINE)
    w_draw.line([(0, 58), (31, 58)], fill=(100, 116, 139, 255))
    wall.save(os.path.join(walls_dir, "wall_office.png"))

    # 2. Luxury Wood Paneled Wall (CEO / Boardroom)
    wood_wall = Image.new("RGBA", (32, 64), TRANSPARENT)
    ww_draw = ImageDraw.Draw(wood_wall)
    ww_draw.rectangle([0, 0, 31, 14], fill=(110, 60, 25, 255), outline=OUTLINE)
    ww_draw.rectangle([1, 1, 30, 4], fill=(160, 95, 45, 255))
    # Mahogany panels
    ww_draw.rectangle([0, 15, 31, 56], fill=(120, 53, 15, 255), outline=OUTLINE)
    ww_draw.rectangle([4, 19, 27, 52], outline=(69, 26, 3, 255), width=2)
    ww_draw.rectangle([5, 20, 26, 51], fill=(146, 64, 14, 255))
    # Baseboard
    ww_draw.rectangle([0, 57, 31, 63], fill=(69, 26, 3, 255), outline=OUTLINE)
    wood_wall.save(os.path.join(walls_dir, "wall_wood.png"))

    # 3. Glass Partition Wall with Aluminum Frame (32 x 64)
    glass = Image.new("RGBA", (32, 64), TRANSPARENT)
    g_draw = ImageDraw.Draw(glass)
    g_draw.rectangle([0, 0, 31, 14], fill=(100, 116, 139, 255), outline=OUTLINE)
    # Tinted glass pane
    g_draw.rectangle([1, 15, 30, 58], fill=(56, 189, 248, 50), outline=(148, 163, 184, 180))
    # Diagonal reflection shine
    g_draw.polygon([(4, 16), (12, 16), (2, 45), (0, 45)], fill=(255, 255, 255, 70))
    # Base rail
    g_draw.rectangle([0, 59, 31, 63], fill=(71, 85, 105, 255), outline=OUTLINE)
    glass.save(os.path.join(walls_dir, "glass_partition.png"))

    print("✓ Generated wall tilesets.")

def generate_windows_doors():
    env_dir = os.path.join(PUBLIC_DIR, "environment")

    # 1. Panoramic Skyscraper Office Window (64 x 64)
    win_dir = os.path.join(env_dir, "windows")
    ensure_dir(win_dir)
    win = Image.new("RGBA", (64, 64), TRANSPARENT)
    w_draw = ImageDraw.Draw(win)
    # Wall top & frame
    w_draw.rectangle([0, 0, 63, 8], fill=(51, 65, 85, 255), outline=OUTLINE)
    w_draw.rectangle([0, 8, 3, 58], fill=(51, 65, 85, 255), outline=OUTLINE)
    w_draw.rectangle([60, 8, 63, 58], fill=(51, 65, 85, 255), outline=OUTLINE)
    w_draw.rectangle([30, 8, 33, 58], fill=(71, 85, 105, 255), outline=OUTLINE) # Mullion
    # Sky gradient background
    for y in range(9, 58):
        ratio = (y - 9) / 49.0
        r = int(56 + (224 - 56) * ratio)
        g = int(189 + (242 - 189) * ratio)
        b = int(248 + (254 - 248) * ratio)
        w_draw.line([(4, y), (59, y)], fill=(r, g, b, 255))
    # Distant pixel skyscrapers
    w_draw.rectangle([8, 32, 20, 57], fill=(147, 197, 253, 200))
    w_draw.rectangle([22, 24, 30, 57], fill=(96, 165, 250, 200))
    w_draw.rectangle([34, 28, 44, 57], fill=(96, 165, 250, 200))
    w_draw.rectangle([46, 36, 56, 57], fill=(147, 197, 253, 200))
    # Skyscraper windows
    for sy in range(30, 54, 4):
        w_draw.point((25, sy), fill=(255, 255, 255, 220))
        w_draw.point((38, sy), fill=(255, 255, 255, 220))
    # Glass reflection highlights
    w_draw.polygon([(10, 9), (24, 9), (4, 48), (0, 48)], fill=(255, 255, 255, 60))
    # Sill
    w_draw.rectangle([0, 58, 63, 63], fill=(30, 41, 59, 255), outline=OUTLINE)
    win.save(os.path.join(win_dir, "window_skyline.png"))

    # 2. Modern Double Glass Doors (64 x 64)
    door_dir = os.path.join(env_dir, "doors")
    ensure_dir(door_dir)
    door = Image.new("RGBA", (64, 64), TRANSPARENT)
    d_draw = ImageDraw.Draw(door)
    # Door frame
    d_draw.rectangle([0, 0, 63, 63], outline=(71, 85, 105, 255), width=3)
    d_draw.line([(31, 0), (31, 63)], fill=(71, 85, 105, 255), width=2)
    # Left glass door
    d_draw.rectangle([4, 4, 29, 60], fill=(56, 189, 248, 60), outline=OUTLINE)
    d_draw.rectangle([25, 28, 28, 38], fill=(226, 232, 240, 255), outline=OUTLINE) # Steel handle
    # Right glass door
    d_draw.rectangle([34, 4, 59, 60], fill=(56, 189, 248, 60), outline=OUTLINE)
    d_draw.rectangle([35, 28, 38, 38], fill=(226, 232, 240, 255), outline=OUTLINE) # Steel handle
    # Diagonal reflection
    d_draw.line([(10, 8), (4, 24)], fill=(255, 255, 255, 100), width=2)
    d_draw.line([(40, 8), (34, 24)], fill=(255, 255, 255, 100), width=2)
    door.save(os.path.join(door_dir, "doors_glass.png"))

    print("✓ Generated windows and doors.")

# -------------------------------------------------------------
# Furniture & Office Equipment
# -------------------------------------------------------------
def generate_furniture():
    f_dir = os.path.join(PUBLIC_DIR, "furniture")

    # 1. Modern Developer Workstation Desk (64 x 48)
    desks_dir = os.path.join(f_dir, "desks")
    ensure_dir(desks_dir)
    tech_desk = Image.new("RGBA", (64, 48), TRANSPARENT)
    td = ImageDraw.Draw(tech_desk)
    # Desk shadow
    td.ellipse([2, 40, 62, 47], fill=SHADOW)
    # Legs (steel frame)
    td.rectangle([6, 22, 9, 44], fill=(71, 85, 105, 255), outline=OUTLINE)
    td.rectangle([54, 22, 57, 44], fill=(71, 85, 105, 255), outline=OUTLINE)
    # Desk Top (sleek dark grey/white surface)
    td.rectangle([2, 10, 61, 26], fill=(51, 65, 85, 255), outline=OUTLINE)
    td.rectangle([3, 11, 60, 24], fill=(100, 116, 139, 255))
    td.rectangle([4, 12, 59, 14], fill=(148, 163, 184, 255)) # Front bevel highlight
    # Cable grommet
    td.ellipse([50, 13, 54, 17], fill=(30, 41, 59, 255))
    # Desk mousepad
    td.rectangle([14, 16, 44, 24], fill=(15, 23, 42, 255))
    # Keyboard with RGB underglow
    td.rectangle([18, 18, 36, 23], fill=(30, 41, 59, 255))
    td.line([(19, 19), (35, 19)], fill=(99, 102, 241, 255)) # Purple LED
    # Mouse
    td.rectangle([39, 19, 42, 22], fill=(226, 232, 240, 255))
    # Coffee mug with warm coffee
    td.rectangle([8, 14, 12, 19], fill=(239, 68, 68, 255), outline=OUTLINE)
    td.point((10, 15), fill=(120, 53, 15, 255))
    tech_desk.save(os.path.join(desks_dir, "desk_tech.png"))

    # 2. Executive Mahogany Desk (64 x 48)
    exec_desk = Image.new("RGBA", (64, 48), TRANSPARENT)
    ed = ImageDraw.Draw(exec_desk)
    ed.ellipse([2, 40, 62, 47], fill=SHADOW)
    # Wood pedestal base
    ed.rectangle([4, 18, 16, 44], fill=(110, 50, 20, 255), outline=OUTLINE)
    ed.rectangle([47, 18, 59, 44], fill=(110, 50, 20, 255), outline=OUTLINE)
    # Brass drawer handles
    ed.rectangle([8, 26, 12, 28], fill=(234, 179, 8, 255))
    ed.rectangle([8, 34, 12, 36], fill=(234, 179, 8, 255))
    ed.rectangle([51, 26, 55, 28], fill=(234, 179, 8, 255))
    ed.rectangle([51, 34, 55, 36], fill=(234, 179, 8, 255))
    # Top surface
    ed.rectangle([1, 8, 62, 24], fill=(146, 64, 14, 255), outline=OUTLINE)
    ed.rectangle([2, 9, 61, 22], fill=(180, 83, 9, 255))
    # Leather blotter pad
    ed.rectangle([16, 11, 48, 21], fill=(24, 24, 27, 255), outline=(234, 179, 8, 255))
    # Executive pen stand
    ed.rectangle([50, 12, 54, 15], fill=(234, 179, 8, 255))
    exec_desk.save(os.path.join(desks_dir, "desk_executive.png"))

    # 3. Large Conference Table (160 x 64)
    conf_table = Image.new("RGBA", (160, 64), TRANSPARENT)
    cd = ImageDraw.Draw(conf_table)
    cd.ellipse([10, 16, 150, 58], fill=SHADOW)
    # Solid wooden pedestal legs
    cd.rectangle([35, 28, 50, 48], fill=(90, 40, 15, 255), outline=OUTLINE)
    cd.rectangle([110, 28, 125, 48], fill=(90, 40, 15, 255), outline=OUTLINE)
    # Polished oval top
    cd.ellipse([8, 10, 152, 48], fill=(146, 64, 14, 255), outline=OUTLINE)
    cd.ellipse([10, 12, 150, 44], fill=(180, 83, 9, 255))
    # Center connectivity strip & power modules
    cd.rectangle([40, 24, 120, 32], fill=(30, 41, 59, 255), outline=(71, 85, 105, 255))
    for mx in range(48, 116, 16):
        cd.rectangle([mx, 26, mx+8, 30], fill=(15, 23, 42, 255))
        cd.point((mx+4, 28), fill=(34, 197, 94, 255)) # Green power light
    conf_table.save(os.path.join(desks_dir, "conference_table.png"))

    # 4. Ergonomic Swivel Mesh Office Chair (32 x 40)
    chairs_dir = os.path.join(f_dir, "chairs")
    ensure_dir(chairs_dir)
    chair = Image.new("RGBA", (32, 40), TRANSPARENT)
    ch = ImageDraw.Draw(chair)
    # 5-star wheeled base
    ch.ellipse([6, 32, 26, 38], fill=SHADOW)
    ch.line([(16, 26), (8, 34)], fill=(71, 85, 105, 255), width=2)
    ch.line([(16, 26), (24, 34)], fill=(71, 85, 105, 255), width=2)
    ch.line([(16, 26), (16, 35)], fill=(71, 85, 105, 255), width=2)
    # Castor wheels
    ch.point((8, 35), fill=OUTLINE)
    ch.point((24, 35), fill=OUTLINE)
    ch.point((16, 36), fill=OUTLINE)
    # Seat cushion
    ch.rectangle([7, 20, 25, 27], fill=(30, 41, 59, 255), outline=OUTLINE)
    ch.rectangle([8, 21, 24, 25], fill=(51, 65, 85, 255))
    # Armrests
    ch.rectangle([5, 14, 7, 22], fill=(71, 85, 105, 255), outline=OUTLINE)
    ch.rectangle([25, 14, 27, 22], fill=(71, 85, 105, 255), outline=OUTLINE)
    # Mesh backrest with lumbar support
    ch.rectangle([8, 4, 24, 19], fill=(15, 23, 42, 255), outline=OUTLINE)
    ch.rectangle([10, 6, 22, 17], fill=(30, 58, 138, 255))
    ch.line([(9, 14), (23, 14)], fill=(71, 85, 105, 255), width=1) # Lumbar band
    chair.save(os.path.join(chairs_dir, "chair_office.png"))

    # 5. Executive Leather Armchair (32 x 44)
    exec_chair = Image.new("RGBA", (32, 44), TRANSPARENT)
    ech = ImageDraw.Draw(exec_chair)
    ech.ellipse([5, 36, 27, 42], fill=SHADOW)
    ech.rectangle([6, 22, 26, 30], fill=(69, 26, 3, 255), outline=OUTLINE)
    ech.rectangle([7, 23, 25, 28], fill=(120, 53, 15, 255)) # Cognac leather seat
    # High backrest with tufted buttons
    ech.rectangle([6, 4, 26, 21], fill=(69, 26, 3, 255), outline=OUTLINE)
    ech.rectangle([8, 6, 24, 19], fill=(120, 53, 15, 255))
    for bx in (12, 18):
        for by in (9, 14):
            ech.point((bx, by), fill=(45, 15, 5, 255))
    # Padded armrests
    ech.rectangle([4, 15, 7, 25], fill=(120, 53, 15, 255), outline=OUTLINE)
    ech.rectangle([25, 15, 28, 25], fill=(120, 53, 15, 255), outline=OUTLINE)
    exec_chair.save(os.path.join(chairs_dir, "chair_executive.png"))

    # 6. Monitors & Computers
    comp_dir = os.path.join(f_dir, "computers")
    ensure_dir(comp_dir)
    # Dual Monitor setup (48 x 28)
    dual_mon = Image.new("RGBA", (48, 28), TRANSPARENT)
    dm = ImageDraw.Draw(dual_mon)
    # Stands
    dm.rectangle([10, 18, 14, 26], fill=(71, 85, 105, 255), outline=OUTLINE)
    dm.rectangle([34, 18, 38, 26], fill=(71, 85, 105, 255), outline=OUTLINE)
    # Monitor 1 (Left: Code IDE)
    dm.rectangle([1, 2, 23, 18], fill=(15, 23, 42, 255), outline=OUTLINE)
    dm.rectangle([2, 3, 22, 17], fill=(2, 6, 23, 255))
    # Colorful syntax code lines
    dm.line([(4, 5), (12, 5)], fill=(56, 189, 248, 255))  # Cyan keyword
    dm.line([(14, 5), (20, 5)], fill=(234, 179, 8, 255))  # Yellow function
    dm.line([(6, 8), (18, 8)], fill=(74, 222, 128, 255))  # Green string
    dm.line([(6, 11), (15, 11)], fill=(168, 85, 247, 255))# Purple var
    dm.line([(4, 14), (10, 14)], fill=(244, 63, 94, 255)) # Red return
    # Monitor 2 (Right: Graphs/Terminal)
    dm.rectangle([25, 2, 47, 18], fill=(15, 23, 42, 255), outline=OUTLINE)
    dm.rectangle([26, 3, 46, 17], fill=(15, 23, 42, 255))
    # Line chart & metrics
    dm.line([(28, 14), (32, 10), (37, 12), (44, 6)], fill=(34, 197, 94, 255), width=1)
    dm.point((44, 6), fill=(74, 222, 128, 255))
    dual_mon.save(os.path.join(comp_dir, "monitor_dual.png"))

    # Ultrawide Curved Monitor (48 x 26)
    ultra_mon = Image.new("RGBA", (48, 26), TRANSPARENT)
    um = ImageDraw.Draw(ultra_mon)
    um.rectangle([22, 16, 26, 24], fill=(71, 85, 105, 255), outline=OUTLINE)
    um.ellipse([18, 22, 30, 25], fill=(30, 41, 59, 255))
    um.rectangle([2, 2, 46, 16], fill=(15, 23, 42, 255), outline=OUTLINE)
    um.rectangle([3, 3, 45, 15], fill=(9, 9, 11, 255))
    # Timeline video editing tracks
    um.line([(5, 5), (43, 5)], fill=(59, 130, 246, 255))   # Video track 1
    um.line([(5, 8), (30, 8)], fill=(168, 85, 247, 255))  # Video track 2
    um.line([(5, 11), (43, 11)], fill=(34, 197, 94, 255))  # Audio wave
    for ax in range(6, 42, 4):
        um.line([(ax, 10), (ax, 12)], fill=(74, 222, 128, 255))
    ultra_mon.save(os.path.join(comp_dir, "monitor_ultrawide.png"))

    # 7. Enterprise Server Rack (32 x 64)
    srv_dir = os.path.join(f_dir, "servers")
    ensure_dir(srv_dir)
    rack = Image.new("RGBA", (32, 64), TRANSPARENT)
    rd = ImageDraw.Draw(rack)
    rd.ellipse([2, 58, 30, 63], fill=SHADOW)
    # Server chassis
    rd.rectangle([1, 2, 30, 60], fill=(15, 23, 42, 255), outline=OUTLINE)
    rd.rectangle([2, 3, 29, 6], fill=(71, 85, 105, 255)) # Top ventilation fan
    # Server blade units (4U, 2U slots)
    for u, y_pos in enumerate(range(8, 56, 6)):
        rd.rectangle([3, y_pos, 28, y_pos + 4], fill=(30, 41, 59, 255), outline=(15, 23, 42, 255))
        # Status LEDs (cyan, green, amber)
        rd.point((5, y_pos + 2), fill=(34, 197, 94, 255) if u % 3 != 0 else (56, 189, 248, 255))
        rd.point((7, y_pos + 2), fill=(34, 197, 94, 255))
        rd.point((9, y_pos + 2), fill=(234, 179, 8, 255) if u == 4 else (34, 197, 94, 255))
        # Drive bays
        for dx in range(12, 26, 3):
            rd.rectangle([dx, y_pos + 1, dx + 1, y_pos + 3], fill=(15, 23, 42, 255))
    # Glass door tint & reflection
    rd.line([(4, 10), (4, 54)], fill=(56, 189, 248, 120))
    rd.polygon([(6, 12), (14, 12), (4, 40), (4, 30)], fill=(255, 255, 255, 40))
    rack.save(os.path.join(srv_dir, "server_rack.png"))

    # 8. Bookshelves & Storage (48 x 64)
    shelves_dir = os.path.join(f_dir, "shelves")
    ensure_dir(shelves_dir)
    shelf = Image.new("RGBA", (48, 64), TRANSPARENT)
    sh = ImageDraw.Draw(shelf)
    sh.ellipse([2, 58, 46, 63], fill=SHADOW)
    # Wooden frame
    sh.rectangle([1, 2, 46, 60], fill=(120, 53, 15, 255), outline=OUTLINE)
    # Shelves rows
    for sy in (18, 32, 46):
        sh.rectangle([3, sy, 44, sy + 3], fill=(69, 26, 3, 255), outline=OUTLINE)
    # Books and binders on shelves
    book_colors = [
        (239, 68, 68, 255), (59, 130, 246, 255), (34, 197, 94, 255),
        (234, 179, 8, 255), (168, 85, 247, 255), (236, 72, 153, 255)
    ]
    # Row 1 books
    bx = 4
    for i, col in enumerate(book_colors[:5]):
        w = 3 + (i % 2)
        sh.rectangle([bx, 6, bx + w, 17], fill=col, outline=OUTLINE)
        bx += w + 2
    # Row 2 folders & tech manuals
    bx = 6
    for i in range(4):
        sh.rectangle([bx, 21, bx + 5, 31], fill=(226, 232, 240, 255), outline=OUTLINE)
        sh.point((bx + 2, 26), fill=(15, 23, 42, 255))
        bx += 8
    # Row 3 AI trophies & potted mini plant
    sh.rectangle([8, 38, 14, 45], fill=(234, 179, 8, 255), outline=OUTLINE) # Gold trophy
    sh.point((11, 36), fill=(234, 179, 8, 255))
    # Mini plant
    sh.rectangle([28, 41, 34, 45], fill=(180, 83, 9, 255))
    sh.ellipse([27, 36, 35, 41], fill=(34, 197, 94, 255))
    shelf.save(os.path.join(shelves_dir, "bookshelf.png"))

    # 9. Lounge Modular Sofa (80 x 36)
    sofas_dir = os.path.join(f_dir, "sofas")
    ensure_dir(sofas_dir)
    sofa = Image.new("RGBA", (80, 36), TRANSPARENT)
    sf = ImageDraw.Draw(sofa)
    sf.ellipse([4, 28, 76, 35], fill=SHADOW)
    # Base & backrest
    sf.rectangle([2, 6, 77, 22], fill=(24, 24, 27, 255), outline=OUTLINE)
    sf.rectangle([3, 7, 76, 18], fill=(39, 39, 42, 255))
    # Seat cushions (3 sections)
    for i in range(3):
        cx = 6 + i * 23
        sf.rectangle([cx, 16, cx + 21, 28], fill=(63, 63, 70, 255), outline=OUTLINE)
        sf.rectangle([cx + 1, 17, cx + 20, 25], fill=(82, 82, 91, 255))
    # Armrests
    sf.rectangle([1, 10, 6, 28], fill=(39, 39, 42, 255), outline=OUTLINE)
    sf.rectangle([73, 10, 78, 28], fill=(39, 39, 42, 255), outline=OUTLINE)
    # Throw cushions
    sf.rectangle([8, 12, 16, 20], fill=(234, 179, 8, 255), outline=OUTLINE)
    sf.rectangle([63, 12, 71, 20], fill=(13, 148, 136, 255), outline=OUTLINE)
    sofa.save(os.path.join(sofas_dir, "sofa_lounge.png"))

    # 10. Plants (Monstera in Pot: 32 x 44)
    plants_dir = os.path.join(PUBLIC_DIR, "environment", "plants")
    ensure_dir(plants_dir)
    monstera = Image.new("RGBA", (32, 44), TRANSPARENT)
    mp = ImageDraw.Draw(monstera)
    mp.ellipse([4, 38, 28, 43], fill=SHADOW)
    # Pot
    mp.polygon([(8, 28), (24, 28), (21, 41), (11, 41)], fill=(180, 83, 9, 255), outline=OUTLINE)
    mp.rectangle([7, 26, 25, 29], fill=(217, 119, 6, 255), outline=OUTLINE) # Rim
    # Lush foliage (leaves)
    mp.ellipse([3, 10, 16, 24], fill=(22, 101, 52, 255), outline=OUTLINE)
    mp.ellipse([4, 11, 14, 22], fill=(34, 197, 94, 255))
    mp.ellipse([15, 6, 29, 22], fill=(22, 101, 52, 255), outline=OUTLINE)
    mp.ellipse([16, 7, 27, 20], fill=(34, 197, 94, 255))
    mp.ellipse([10, 14, 24, 28], fill=(21, 128, 61, 255), outline=OUTLINE)
    mp.ellipse([11, 15, 23, 26], fill=(74, 222, 128, 255))
    monstera.save(os.path.join(plants_dir, "plant_monstera.png"))

    # Tall Snake Plant (24 x 40)
    snake_plant = Image.new("RGBA", (24, 40), TRANSPARENT)
    sp = ImageDraw.Draw(snake_plant)
    sp.ellipse([3, 34, 21, 39], fill=SHADOW)
    sp.polygon([(6, 26), (18, 26), (16, 38), (8, 38)], fill=(226, 232, 240, 255), outline=OUTLINE)
    # Upright striped leaves
    sp.polygon([(11, 4), (14, 26), (10, 26)], fill=(22, 101, 52, 255), outline=OUTLINE)
    sp.line([(12, 6), (12, 24)], fill=(234, 179, 8, 255)) # Yellow border
    sp.polygon([(6, 10), (10, 26), (7, 26)], fill=(21, 128, 61, 255), outline=OUTLINE)
    sp.polygon([(17, 8), (17, 26), (13, 26)], fill=(22, 101, 52, 255), outline=OUTLINE)
    snake_plant.save(os.path.join(plants_dir, "plant_snake.png"))

    # 11. Office Amenities: Water Cooler & Espresso Coffee Station
    deco_dir = os.path.join(f_dir, "decorations")
    ensure_dir(deco_dir)
    # Water Cooler (24 x 42)
    water_cooler = Image.new("RGBA", (24, 42), TRANSPARENT)
    wc = ImageDraw.Draw(water_cooler)
    wc.ellipse([2, 37, 22, 41], fill=SHADOW)
    # Machine body
    wc.rectangle([4, 16, 20, 39], fill=(241, 245, 249, 255), outline=OUTLINE)
    wc.rectangle([5, 17, 19, 37], fill=(226, 232, 240, 255))
    # Dispenser alcove
    wc.rectangle([7, 24, 17, 32], fill=(71, 85, 105, 255), outline=OUTLINE)
    wc.rectangle([8, 25, 11, 27], fill=(59, 130, 246, 255)) # Cold tap
    wc.rectangle([13, 25, 16, 27], fill=(239, 68, 68, 255)) # Hot tap
    # Translucent Blue Water Jug
    wc.rounded_rectangle([5, 4, 19, 17], radius=3, fill=(56, 189, 248, 200), outline=OUTLINE)
    wc.rounded_rectangle([7, 6, 17, 15], radius=2, fill=(14, 165, 233, 230))
    wc.line([(9, 7), (9, 13)], fill=(255, 255, 255, 180)) # Water reflection
    water_cooler.save(os.path.join(deco_dir, "water_cooler.png"))

    # Espresso Machine (32 x 32)
    coffee_maker = Image.new("RGBA", (32, 32), TRANSPARENT)
    cm = ImageDraw.Draw(coffee_maker)
    cm.ellipse([2, 27, 30, 31], fill=SHADOW)
    cm.rectangle([4, 6, 28, 28], fill=(30, 41, 59, 255), outline=OUTLINE)
    cm.rectangle([6, 8, 26, 12], fill=(226, 232, 240, 255)) # Chrome top cup warmer
    # Pressure gauges & buttons
    cm.point((8, 15), fill=(34, 197, 94, 255))
    cm.point((11, 15), fill=(234, 179, 8, 255))
    cm.ellipse([18, 14, 22, 18], fill=(241, 245, 249, 255), outline=OUTLINE) # Gauge
    # Portafilter grouphead & espresso shot glass
    cm.rectangle([11, 18, 17, 21], fill=(148, 163, 184, 255))
    cm.line([(11, 20), (6, 20)], fill=(15, 23, 42, 255), width=2) # Handle
    cm.rectangle([12, 23, 16, 26], fill=(255, 255, 255, 200), outline=OUTLINE)
    cm.point((14, 25), fill=(120, 53, 15, 255)) # Fresh espresso
    coffee_maker.save(os.path.join(deco_dir, "coffee_machine.png"))

    # 12. Conference Whiteboard with Sprint Tasks (64 x 48)
    whiteboard = Image.new("RGBA", (64, 48), TRANSPARENT)
    wb = ImageDraw.Draw(whiteboard)
    wb.ellipse([4, 43, 60, 47], fill=SHADOW)
    # Metal stand & rolling wheels
    wb.line([(8, 38), (4, 44)], fill=(100, 116, 139, 255), width=2)
    wb.line([(56, 38), (60, 44)], fill=(100, 116, 139, 255), width=2)
    wb.line([(6, 44), (58, 44)], fill=(71, 85, 105, 255), width=1)
    # Board Frame
    wb.rectangle([2, 4, 61, 38], fill=(241, 245, 249, 255), outline=OUTLINE, width=2)
    # Kanban Sprint Columns
    wb.line([(22, 6), (22, 36)], fill=(203, 213, 225, 255), width=1)
    wb.line([(42, 6), (42, 36)], fill=(203, 213, 225, 255), width=1)
    # Colorful sticky notes
    sticky_colors = [
        (250, 204, 21, 255), # Yellow
        (244, 114, 182, 255),# Pink
        (56, 189, 248, 255), # Cyan
        (74, 222, 128, 255)  # Green
    ]
    # Column 1 (To Do)
    wb.rectangle([5, 8, 10, 12], fill=sticky_colors[0])
    wb.rectangle([13, 8, 18, 12], fill=sticky_colors[1])
    wb.rectangle([5, 15, 10, 19], fill=sticky_colors[2])
    # Column 2 (In Progress)
    wb.rectangle([25, 8, 30, 12], fill=sticky_colors[3])
    wb.rectangle([33, 14, 38, 18], fill=sticky_colors[0])
    # Column 3 (Done)
    wb.rectangle([45, 8, 50, 12], fill=sticky_colors[3])
    wb.rectangle([53, 8, 58, 12], fill=sticky_colors[3])
    wb.rectangle([49, 16, 54, 20], fill=sticky_colors[3])
    # Marker tray
    wb.rectangle([18, 37, 46, 39], fill=(148, 163, 184, 255), outline=OUTLINE)
    whiteboard.save(os.path.join(deco_dir, "whiteboard.png"))

    # 13. High-Tech Presentation Projector Display Screen (96 x 56)
    proj = Image.new("RGBA", (96, 56), TRANSPARENT)
    pd = ImageDraw.Draw(proj)
    # Screen bezel
    pd.rectangle([0, 0, 95, 54], fill=(15, 23, 42, 255), outline=OUTLINE, width=2)
    pd.rectangle([2, 2, 93, 52], fill=(2, 6, 23, 255))
    # Empire OS UI Header
    pd.rectangle([3, 3, 92, 10], fill=(30, 58, 138, 255))
    pd.rectangle([6, 5, 8, 7], fill=(234, 179, 8, 255)) # Empire icon
    pd.line([(12, 6), (50, 6)], fill=(255, 255, 255, 255)) # "SPIRANDELIEMPIRE OS"
    # Live LangGraph workflow nodes
    nodes = [(18, 22), (48, 22), (78, 22), (48, 40)]
    for nx, ny in nodes:
        pd.rectangle([nx-4, ny-4, nx+4, ny+4], fill=(13, 148, 136, 255), outline=(45, 212, 191, 255))
    # Edges between nodes
    pd.line([nodes[0], nodes[1]], fill=(99, 102, 241, 255), width=1)
    pd.line([nodes[1], nodes[2]], fill=(99, 102, 241, 255), width=1)
    pd.line([nodes[1], nodes[3]], fill=(234, 179, 8, 255), width=1)
    # Glow effect
    pd.line([(3, 52), (92, 52)], fill=(56, 189, 248, 180))
    proj.save(os.path.join(deco_dir, "projector_screen.png"))

    # 14. Audiovisual Equipment: Tripod Camera & Studio Softbox Light
    cam = Image.new("RGBA", (32, 48), TRANSPARENT)
    cd = ImageDraw.Draw(cam)
    cd.ellipse([4, 42, 28, 47], fill=SHADOW)
    # Tripod legs
    cd.line([(16, 22), (6, 44)], fill=(51, 65, 85, 255), width=2)
    cd.line([(16, 22), (26, 44)], fill=(51, 65, 85, 255), width=2)
    cd.line([(16, 22), (16, 44)], fill=(30, 41, 59, 255), width=2)
    # Camera body
    cd.rectangle([8, 10, 24, 22], fill=(15, 23, 42, 255), outline=OUTLINE)
    cd.rectangle([24, 12, 29, 20], fill=(30, 41, 59, 255), outline=OUTLINE) # Lens
    cd.ellipse([27, 13, 29, 19], fill=(56, 189, 248, 200)) # Glass element
    # Top microphone & Red REC tally light
    cd.rectangle([10, 6, 18, 9], fill=(71, 85, 105, 255))
    cd.point((14, 11), fill=(239, 68, 68, 255)) # Red recording LED
    cam.save(os.path.join(deco_dir, "camera_tripod.png"))

    # Studio Softbox Light (28 x 48)
    softbox = Image.new("RGBA", (28, 48), TRANSPARENT)
    sbd = ImageDraw.Draw(softbox)
    sbd.ellipse([3, 42, 25, 47], fill=SHADOW)
    sbd.line([(14, 20), (6, 44)], fill=(51, 65, 85, 255), width=2)
    sbd.line([(14, 20), (22, 44)], fill=(51, 65, 85, 255), width=2)
    # Rectangular softbox diffuser facing camera
    sbd.rectangle([2, 4, 25, 22], fill=(15, 23, 42, 255), outline=OUTLINE)
    sbd.rectangle([4, 6, 23, 20], fill=(255, 255, 240, 240), outline=(234, 179, 8, 180)) # Warm white glow
    softbox.save(os.path.join(deco_dir, "studio_softbox.png"))

    # Wall Clock (20 x 20)
    clock = Image.new("RGBA", (20, 20), TRANSPARENT)
    ck = ImageDraw.Draw(clock)
    ck.ellipse([1, 1, 18, 18], fill=(241, 245, 249, 255), outline=OUTLINE, width=2)
    ck.point((9, 4), fill=(15, 23, 42, 255))  # 12
    ck.point((15, 9), fill=(15, 23, 42, 255)) # 3
    ck.point((9, 15), fill=(15, 23, 42, 255)) # 6
    ck.point((4, 9), fill=(15, 23, 42, 255))  # 9
    ck.line([(9, 9), (9, 5)], fill=(15, 23, 42, 255), width=1)   # Hour hand
    ck.line([(9, 9), (13, 9)], fill=(239, 68, 68, 255), width=1) # Minute hand
    clock.save(os.path.join(deco_dir, "wall_clock.png"))

    # SpirandeliEmpire Corporate Wall Crest (48 x 32)
    crest = Image.new("RGBA", (48, 32), TRANSPARENT)
    crd = ImageDraw.Draw(crest)
    crd.rectangle([0, 0, 47, 31], fill=(15, 23, 42, 255), outline=(234, 179, 8, 255), width=2)
    crd.rectangle([2, 2, 45, 29], fill=(24, 30, 48, 255))
    # Golden Crown & 'S' Emblem
    crd.polygon([(16, 12), (20, 6), (24, 10), (28, 6), (32, 12), (30, 16), (18, 16)], fill=(234, 179, 8, 255))
    crd.rectangle([20, 18, 28, 26], fill=(99, 102, 241, 255))
    crd.line([(22, 19), (26, 19)], fill=(255, 255, 255, 255))
    crd.line([(22, 22), (26, 22)], fill=(255, 255, 255, 255))
    crd.line([(22, 25), (26, 25)], fill=(255, 255, 255, 255))
    crest.save(os.path.join(deco_dir, "empire_crest.png"))

    print("✓ Generated all office furniture, tech, and decor sprites.")

# -------------------------------------------------------------
# Effects & HUD Indicators
# -------------------------------------------------------------
def generate_effects():
    fx_dir = os.path.join(PUBLIC_DIR, "effects")
    ensure_dir(fx_dir)

    # 1. Animated Speech Bubble (32 x 24)
    bubble = Image.new("RGBA", (32, 24), TRANSPARENT)
    bd = ImageDraw.Draw(bubble)
    bd.rounded_rectangle([1, 1, 30, 17], radius=4, fill=(255, 255, 255, 240), outline=OUTLINE)
    bd.polygon([(12, 17), (16, 22), (18, 17)], fill=(255, 255, 255, 240))
    bd.line([(12, 17), (16, 22)], fill=OUTLINE)
    bd.line([(16, 22), (18, 17)], fill=OUTLINE)
    # Typing dots (...)
    bd.point((8, 9), fill=(15, 23, 42, 255))
    bd.point((15, 9), fill=(15, 23, 42, 255))
    bd.point((22, 9), fill=(15, 23, 42, 255))
    bubble.save(os.path.join(fx_dir, "speech_bubble.png"))

    # 2. Status Alert Icon (Exclamation mark: 16 x 16)
    alert = Image.new("RGBA", (16, 16), TRANSPARENT)
    ad = ImageDraw.Draw(alert)
    ad.ellipse([1, 1, 14, 14], fill=(239, 68, 68, 255), outline=(185, 28, 28, 255))
    ad.line([(8, 4), (8, 9)], fill=(255, 255, 255, 255), width=2)
    ad.point((8, 12), fill=(255, 255, 255, 255))
    alert.save(os.path.join(fx_dir, "status_alert.png"))

    # 3. Status Sparkle / Star Icon (16 x 16)
    star = Image.new("RGBA", (16, 16), TRANSPARENT)
    sd = ImageDraw.Draw(star)
    sd.polygon([(8, 1), (10, 6), (15, 8), (10, 10), (8, 15), (6, 10), (1, 8), (6, 6)], fill=(234, 179, 8, 255), outline=OUTLINE)
    sd.point((8, 8), fill=(255, 255, 255, 255))
    star.save(os.path.join(fx_dir, "status_sparkle.png"))

    # 4. Status Coding Icon (16 x 16)
    code_ico = Image.new("RGBA", (16, 16), TRANSPARENT)
    cid = ImageDraw.Draw(code_ico)
    cid.rounded_rectangle([1, 1, 14, 14], radius=3, fill=(13, 148, 136, 255), outline=OUTLINE)
    cid.line([(4, 6), (2, 8), (4, 10)], fill=(255, 255, 255, 255))
    cid.line([(11, 6), (13, 8), (11, 10)], fill=(255, 255, 255, 255))
    cid.line([(9, 5), (6, 11)], fill=(234, 179, 8, 255))
    code_ico.save(os.path.join(fx_dir, "status_coding.png"))

    # 5. Selection Ring / Halo for active agent (32 x 16)
    ring = Image.new("RGBA", (32, 16), TRANSPARENT)
    rd = ImageDraw.Draw(ring)
    rd.ellipse([2, 2, 29, 13], outline=(99, 102, 241, 230), width=2)
    rd.ellipse([4, 4, 27, 11], fill=(99, 102, 241, 60))
    ring.save(os.path.join(fx_dir, "selection_ring.png"))

    print("✓ Generated visual effects and HUD indicators.")

def main():
    print("=" * 60)
    print("SpirandeliEmpire OS 3.1 — Generating Pixel Art Assets...")
    print(f"Target directory: {PUBLIC_DIR}")
    print("=" * 60)

    generate_agent_sprites()
    generate_floor_tiles()
    generate_wall_tiles()
    generate_windows_doors()
    generate_furniture()
    generate_effects()

    print("=" * 60)
    print("✓ All Pixel Art assets successfully generated!")
    print("=" * 60)

if __name__ == "__main__":
    main()

