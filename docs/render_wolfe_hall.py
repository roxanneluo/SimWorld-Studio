"""
Wolfe Hall West Wall — top-down scene renderer.
Produces a birds-eye view of the full world layout using the exact
spawn coordinates from wolfe_hall_skill.md.
"""

from PIL import Image, ImageDraw, ImageFont
import math, os

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H = 2400, 2000
SCALE = 0.065          # UE cm → pixels
OX, OY = 1050, 1050   # world origin in pixels (0,0 UE → here)

BG       = (34, 28, 20)       # dark earth
GROUND   = (90, 70, 48)       # dusty sand
ROAD_C   = (110, 85, 55)      # packed dirt road
LAKE_C   = (40, 100, 160)     # water
LAKE_SH  = (55, 120, 180)     # lake highlight
MESA_C   = (140, 65, 30)      # red sandstone
MESA_SH  = (170, 80, 40)
TREE_C   = (40, 100, 40)
TREE_SH  = (60, 130, 50)
BLDG_C   = (180, 140, 90)     # frontier building
BLDG_SH  = (210, 165, 110)
BLDG_OUT = (60, 40, 20)
RAIL_C   = (70, 60, 50)       # railroad tie
RAIL_SH  = (120, 110, 90)     # rail steel
PROP_C   = (160, 120, 70)
DOCK_C   = (130, 95, 55)
TOWER_C  = (150, 110, 60)
SCRUB_C  = (55, 85, 35)
LABEL_C  = (255, 240, 200)
TITLE_C  = (255, 220, 100)

img = Image.new("RGB", (W, H), BG)
d   = ImageDraw.Draw(img)

def ue(x, y):
    """Convert UE coords (cm) to image pixels."""
    px = int(OX + x * SCALE)
    py = int(OY - y * SCALE)   # UE Y+ is forward, image Y+ is down
    return px, py

def rect_ue(cx, cy, hw, hh, fill, outline=None, rotation=0):
    """Draw a rotated rectangle centred at UE (cx,cy), half-width hw, half-height hh."""
    corners = [(-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh)]
    if rotation:
        r = math.radians(rotation)
        corners = [(x*math.cos(r)-y*math.sin(r), x*math.sin(r)+y*math.cos(r)) for x,y in corners]
    pts = [ue(cx+dx, cy+dy) for dx,dy in corners]
    d.polygon(pts, fill=fill, outline=outline)

def circle_ue(cx, cy, r, fill, outline=None):
    px, py = ue(cx, cy)
    d.ellipse([px-r, py-r, px+r, py+r], fill=fill, outline=outline)

def label(cx, cy, text, color=LABEL_C, size=11, offset=(0,0)):
    px, py = ue(cx, cy)
    px += offset[0]; py += offset[1]
    d.text((px, py), text, fill=color, anchor="mm")

# ── Ground base ───────────────────────────────────────────────────────────────
# Whole visible play area
d.rectangle([0,0,W,H], fill=BG)
# Desert floor  (cover most of canvas)
x0,y0 = ue(-20000, 20000)
x1,y1 = ue( 20000,-10000)
d.rectangle([min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1)], fill=GROUND)

# ── Lake (west of town) ───────────────────────────────────────────────────────
# Plane at (-8000, 0, -80) scaled 50×40  → 5000×4000 cm
lake_cx, lake_cy = -8000, 0
lake_hw, lake_hh = 2500, 2000
# Subtle gradient: draw two ovals
rect_ue(lake_cx, lake_cy, lake_hw, lake_hh, LAKE_C)
rect_ue(lake_cx-100, lake_cy+200, lake_hw-400, lake_hh-400, LAKE_SH)

# Dock planks
rect_ue(-5650, 300, 900, 125, DOCK_C)
rect_ue(-5650, -300, 900, 125, DOCK_C)

# ── Lakeside trees ────────────────────────────────────────────────────────────
lake_trees = [
    (-6000,3000),(-9000,2500),(-11000,500),(-11000,-1500),
    (-9500,-3000),(-7000,-3200),(-5200,-1800),(-5000,1500),
    (-7500,3500),(-10000,3200),
]
for tx,ty in lake_trees:
    circle_ue(tx, ty, 14, TREE_SH)
    circle_ue(tx-3, ty+3, 11, TREE_C)

# ── Dirt road (main street) ───────────────────────────────────────────────────
road_x0, road_x1 = -1500, 10500
road_hw = 1500   # half-width of road zone
rect_ue((road_x0+road_x1)/2, 0, (road_x1-road_x0)/2, road_hw, ROAD_C)

# ── Town buildings ────────────────────────────────────────────────────────────
buildings = [
    # name,  cx,    cy,   hw,  hh, rotation
    ("Saloon",        0,   1500, 700, 500, 0),
    ("Gen.Store",  3500,   1500, 700, 500, 0),
    ("Sheriff",    7000,   1500, 600, 450, 0),
    ("Barn",       1800,  -1500, 800, 600, 0),
    ("Boarding",   5000,  -1500, 700, 500, 0),
    ("Stables",    8200,  -1500, 700, 500, 0),
]
for name, cx, cy, hw, hh, rot in buildings:
    rect_ue(cx, cy, hw, hh, BLDG_SH, BLDG_OUT, rot)
    rect_ue(cx-30, cy+30, hw-80, hh-80, BLDG_C, None, rot)
    label(cx, cy, name, size=9, offset=(0,0))

# ── Water tower ───────────────────────────────────────────────────────────────
circle_ue(10000, 0, 22, TOWER_C, BLDG_OUT)
circle_ue(10000, 0, 14, BLDG_SH)
label(10000, 0, "Tower", offset=(0, 30))

# ── Street props (saloon area) ────────────────────────────────────────────────
for px,py in [(-250,800),(250,800)]:
    circle_ue(px, py, 8, PROP_C, BLDG_OUT)
rect_ue(0, 700, 120, 40, PROP_C)   # bench

# Hitching posts
for px in [600, 2800, 6000]:
    d.line([ue(px,1050), ue(px,1200)], fill=(80,55,25), width=3)

# Scattered crates
for px,py in [(900,1700),(4000,-1800),(7500,-1700),(3200,1600)]:
    rect_ue(px, py, 70, 60, PROP_C, BLDG_OUT)

# ── Railroad tracks ───────────────────────────────────────────────────────────
track_y = -4500
# Ground under tracks
rect_ue(7000, track_y, 9000, 220, (65, 50, 35))

# Sleepers (ties) — every 600 cm
for i in range(25):
    tx = -2000 + i * 700
    rect_ue(tx, track_y, 220, 180, RAIL_C)

# Two rails
for ry in [-4650, -4350]:
    pts = [ue(-2000, ry), ue(15000, ry)]
    d.line(pts, fill=RAIL_SH, width=4)

# Station platform
rect_ue(2000, -4200, 1500, 400, DOCK_C, BLDG_OUT)
label(2000, -4200, "Station", offset=(0,0))

# ── Red rock mesa formations (background arc, north) ─────────────────────────
mesas = [
    # cx,    cy,   rx,   ry
    (-3000, 13000, 650, 1100),
    ( 1000, 15000, 900, 1500),
    ( 5000, 14000, 750, 1300),
    ( 9000, 12500, 600, 1000),
    (12000, 11000, 700, 1100),
    (-6000, 12000, 550,  900),
    ( 3000, 16000,1000, 1700),
]
for cx, cy, rx, ry in mesas:
    # Draw rough mesa silhouette as a series of ellipses
    px, py = ue(cx, cy)
    rx_px = int(rx * SCALE)
    ry_px = int(ry * SCALE)
    d.ellipse([px-rx_px, py-ry_px, px+rx_px, py+ry_px], fill=MESA_SH)
    d.ellipse([px-rx_px+8, py-ry_px+12, px+rx_px-8, py+ry_px-8], fill=MESA_C)

# Mesa labels
for cx, cy, rx, ry in mesas:
    label(cx, cy, "Mesa", size=8, offset=(0, -int(ry*SCALE)-10))

# ── Scrubland vegetation ──────────────────────────────────────────────────────
scrubs = [
    (-1500,5000),( 3000,6000),( 7000,5500),
    (12000,5000),(-3000,7500),( 5500,8000),
]
for sx, sy in scrubs:
    circle_ue(sx, sy, 9, SCRUB_C)
    circle_ue(sx-2, sy+2, 6, TREE_C)

# ── Compass rose ─────────────────────────────────────────────────────────────
cx, cy = W-80, H-80
d.ellipse([cx-30,cy-30,cx+30,cy+30], fill=(40,35,30), outline=(150,130,100))
d.line([cx, cy-25, cx, cy+25], fill=(200,180,100), width=2)
d.line([cx-25, cy, cx+25, cy], fill=(200,180,100), width=2)
d.text((cx, cy-32), "N", fill=TITLE_C, anchor="mm")

# ── Scale bar ────────────────────────────────────────────────────────────────
sb_x, sb_y = 80, H-60
sb_len = int(5000 * SCALE)   # 5000 cm = 50 m
d.rectangle([sb_x, sb_y, sb_x+sb_len, sb_y+8], fill=(180,160,110))
d.text((sb_x + sb_len//2, sb_y-10), "50 m", fill=LABEL_C, anchor="mm")

# ── Title & legend ────────────────────────────────────────────────────────────
d.text((W//2, 30), "WOLFE HALL — West Wall", fill=TITLE_C, anchor="mm")
d.text((W//2, 55), "Top-down scene layout  (1 px ≈ 15 cm)", fill=(180,160,100), anchor="mm")

legend = [
    (BLDG_C,   "Frontier buildings"),
    (LAKE_C,   "Lake"),
    (TREE_C,   "Trees"),
    (MESA_C,   "Red rock mesas"),
    (RAIL_SH,  "Railroad tracks"),
    (ROAD_C,   "Main street / dirt road"),
    (PROP_C,   "Props & furniture"),
    (DOCK_C,   "Dock / platform"),
]
lx, ly = 20, 90
for color, name in legend:
    d.rectangle([lx, ly, lx+16, ly+16], fill=color, outline=(80,70,60))
    d.text((lx+22, ly+8), name, fill=LABEL_C, anchor="lm")
    ly += 22

# ── Zone labels ───────────────────────────────────────────────────────────────
label(-9000, -5500, "WILDERNESS", color=(120,100,70))
label(-8000,    0,  "LAKE",        color=(100,160,200))
label( 4000,    0,  "MAIN STREET", color=(200,170,110))
label( 7000, -4500, "RAILROAD",    color=(150,130,90))
label( 3000, 14000, "RED ROCK MESA BACKDROP", color=(200,110,60))

out = "/home/user/SimWorld-Studio/docs/wolfe_hall_topdown.png"
img.save(out, "PNG")
print(f"Saved: {out}  ({W}×{H})")
