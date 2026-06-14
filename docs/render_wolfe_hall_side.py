"""
Wolfe Hall West Wall — side-view (south-facing) renderer.
Camera is positioned south of town looking north: railroad in foreground,
main street mid-ground, red rock mesas on the horizon.
Simple painter's-algorithm depth sort + fake perspective projection.
"""

from PIL import Image, ImageDraw
import math, random

W, H = 2400, 1400

# ── Sky gradient ──────────────────────────────────────────────────────────────
img = Image.new("RGB", (W, H), (20, 15, 10))
d   = ImageDraw.Draw(img)

# Sky: deep blue at top → warm amber at horizon
horizon_y = int(H * 0.48)
for y in range(horizon_y):
    t = y / horizon_y
    r = int(18  + t * (210 - 18))
    g = int(25  + t * (130 - 25))
    b = int(80  + t * (60  - 80))
    d.line([(0, y), (W, y)], fill=(r, g, b))

# Sun — low on the horizon, slightly right
sun_x, sun_y = int(W * 0.72), int(horizon_y * 0.78)
for radius in range(60, 0, -1):
    t = radius / 60
    r = int(255)
    g = int(200 + t * 30)
    b = int(50  * t)
    d.ellipse([sun_x-radius, sun_y-radius, sun_x+radius, sun_y+radius],
              fill=(r, g, b))

# Atmospheric haze near horizon
for y in range(horizon_y - 30, horizon_y + 1):
    alpha = 1 - (horizon_y - y) / 30
    haze  = (int(200*alpha), int(150*alpha), int(80*alpha))
    d.line([(0, y), (W, y)], fill=haze)

# ── Ground (desert floor) ────────────────────────────────────────────────────
for y in range(horizon_y, H):
    t = (y - horizon_y) / (H - horizon_y)
    r = int(90  + t * 40)
    g = int(65  + t * 20)
    b = int(38  + t * 10)
    d.line([(0, y), (W, y)], fill=(r, g, b))

# ── Perspective helpers ───────────────────────────────────────────────────────
# Camera: south of scene at y=-8000, looking north (+Y)
# World X maps to screen X, world Y (depth) maps to screen Y via perspective
# World Z (height) maps to screen Y offset

CAM_Y    = -8000     # camera depth (UE Y)
FOV_SCALE = 900      # controls perspective strength
SCREEN_CX = W // 2
GROUND_Y  = horizon_y

def project(world_x, world_y, world_z):
    """Project UE world coords to screen (px, py)."""
    depth = max(world_y - CAM_Y, 100)
    scale = FOV_SCALE / depth
    sx = int(SCREEN_CX + world_x * scale)
    # ground at z=0 → GROUND_Y; higher z → higher on screen (lower py)
    sy = int(GROUND_Y - world_z * scale * 0.6)
    return sx, sy, scale

def ground_y_at(world_y):
    """Screen Y of ground level at given world depth."""
    _, sy, _ = project(0, world_y, 0)
    return sy

def draw_box(cx, cy, cz, hw, hd, hh, fill, top_fill, side_fill, outline=None):
    """Draw a perspective box. cy=depth, cz=height base."""
    # 8 corners: (±hw, cy±hd, cz + 0 or hh*2)
    pts = {}
    for xi, xv in enumerate([-hw, hw]):
        for yi, yv in enumerate([-hd, hd]):
            for zi, zv in enumerate([0, hh*2]):
                pts[(xi,yi,zi)] = project(cx+xv, cy+yv, cz+zv)

    def face(corners, color):
        poly = [(pts[c][0], pts[c][1]) for c in corners]
        d.polygon(poly, fill=color, outline=outline or color)

    # Back face (far)
    face([(0,1,0),(1,1,0),(1,1,1),(0,1,1)], fill)
    # Left face
    face([(0,0,0),(0,1,0),(0,1,1),(0,0,1)], side_fill)
    # Right face
    face([(1,0,0),(1,1,0),(1,1,1),(1,0,1)], side_fill)
    # Front face (near)
    face([(0,0,0),(1,0,0),(1,0,1),(0,0,1)], top_fill)
    # Top face
    face([(0,0,1),(1,0,1),(1,1,1),(0,1,1)], top_fill)

# ── Red rock mesas (far background) ──────────────────────────────────────────
mesas = [
    (-3000,13000,  0, 800, 600,1800),
    ( 1000,15000,  0,1100, 800,2800),
    ( 5000,14000,  0, 900, 700,2400),
    ( 9000,12500,  0, 750, 550,2000),
    (12000,11000,  0, 850, 600,2100),
    (-6000,12000,  0, 650, 500,1500),
    ( 3000,16000,  0,1300, 900,3200),
]
random.seed(42)
for cx,cy,cz,hw,hd,hh in mesas:
    # Jagged mesa top: draw as stacked irregular shapes
    base_col  = (130+random.randint(-10,10), 55+random.randint(-5,5), 25)
    mid_col   = (155+random.randint(-10,10), 70+random.randint(-5,5), 35)
    top_col   = (100, 45, 20)
    side_col  = (90, 38, 15)
    # Base slab
    draw_box(cx, cy, cz, hw, hd, int(hh*0.5), base_col, mid_col, side_col)
    # Upper narrower slab
    draw_box(cx+random.randint(-100,100), cy, int(hh*0.5),
             int(hw*0.7), int(hd*0.8), int(hh*0.5), mid_col, top_col, side_col)

# ── Lake (west, partially visible) ───────────────────────────────────────────
lake_pts = [
    project(-10500,  500, -50),
    project( -5500,  500, -50),
    project( -5500, -500, -50),
    project(-10500, -500, -50),
]
d.polygon([(p[0],p[1]) for p in lake_pts], fill=(35, 90, 150))
# Shimmer lines
for i in range(6):
    wy = -200 + i * 80
    p1 = project(-10000, wy, 0)
    p2 = project( -6000, wy, 0)
    d.line([(p1[0],p1[1]),(p2[0],p2[1])], fill=(60,120,180), width=2)

# Lakeside trees (left side of scene)
lake_trees_side = [
    (-10000,2800),(-9000,2500),(-7000,3000),(-5500,-2500),(-9500,-2800),
]
for tx,ty in lake_trees_side:
    px,py,sc = project(tx, ty, 0)
    tr = max(4, int(22*sc))
    # Trunk
    d.line([(px, py),(px, py-int(tr*1.4))], fill=(80,55,30), width=max(2,int(3*sc)))
    # Canopy
    d.ellipse([px-tr, py-int(tr*2.5), px+tr, py-int(tr*0.2)],
              fill=(45,105,35), outline=(35,80,25))

# ── Scrubland mid-ground ──────────────────────────────────────────────────────
scrubs = [(-1500,5500),(3000,6200),(7000,5800),(12000,5200),(-3000,7000),(5500,8500)]
for sx,sy in scrubs:
    px,py,sc = project(sx, sy, 0)
    r = max(3, int(14*sc))
    d.ellipse([px-r, py-int(r*1.6), px+r, py+int(r*0.3)], fill=(50,80,30))

# ── Town buildings ────────────────────────────────────────────────────────────
# Sort back-to-front so closer buildings occlude far ones
buildings = [
    # name,  cx,    cy,  cz,   hw,  hd,   hh,    facing_color, top, side
    ("Saloon",        0,  1500, 0,  650, 400, 900,
     (175,135,85),(200,160,100),(140,105,65)),
    ("Gen.Store",  3500,  1500, 0,  650, 400, 780,
     (165,130,80),(190,155,95),(130,100,60)),
    ("Sheriff",    7000,  1500, 0,  550, 380, 750,
     (170,132,82),(195,157,97),(135,102,62)),
    ("Barn",       1800, -1500, 0,  800, 550,1050,
     (155,115,65),(178,138,80),(120, 90,50)),
    ("Boarding",   5000, -1500, 0,  700, 430, 900,
     (168,128,78),(192,152,93),(133, 98,58)),
    ("Stables",    8200, -1500, 0,  700, 420, 820,
     (163,124,74),(187,148,89),(128, 95,55)),
]
# Sort by cy (back to front = higher cy first)
buildings.sort(key=lambda b: -b[2])

for name,cx,cy,cz,hw,hd,hh,fc,tc,sc in buildings:
    draw_box(cx,cy,cz,hw,hd,hh,fc,tc,sc, outline=(50,35,15))
    # Flat-front sign / door detail
    px,py,scale = project(cx, cy-hd, hh*0.5)
    label_s = max(8, int(12*scale))
    try:
        d.text((px, py), name, fill=(240,220,170), anchor="mm")
    except:
        pass

# ── Water tower ───────────────────────────────────────────────────────────────
px,py,sc = project(10000, 0, 0)
tw = max(6, int(30*sc))
# Legs
for lx in [-tw, tw]:
    d.line([(px+lx, py),(px+int(lx*0.5), py-int(tw*6))], fill=(100,75,40), width=max(2,int(3*sc)))
# Tank
tank_top = py - int(tw*5)
d.ellipse([px-int(tw*1.8), tank_top-int(tw*1.2),
           px+int(tw*1.8), tank_top+int(tw*1.2)], fill=(145,108,60), outline=(60,40,15))

# ── Railroad (foreground) ─────────────────────────────────────────────────────
track_world_y = -4500

# Ballast / ground under tracks
gp0 = project(-5000, track_world_y-300, -20)
gp1 = project( 15000, track_world_y-300, -20)
gp2 = project( 15000, track_world_y+300, -20)
gp3 = project(-5000, track_world_y+300, -20)
d.polygon([(p[0],p[1]) for p in [gp0,gp1,gp2,gp3]], fill=(70,55,38))

# Ties (sleepers) — perspective spacing
for i in range(22):
    wx = -2000 + i * 750
    p_far  = project(wx, track_world_y+220, 0)
    p_near = project(wx, track_world_y-220, 0)
    w = max(2, int(p_near[2] * 80))
    d.line([(p_far[0],p_far[1]),(p_near[0],p_near[1])],
           fill=(80,60,38), width=w)

# Two rails
for dx in [-250, 250]:
    pts = [project(wx, track_world_y+dx, 20) for wx in range(-2000, 16000, 400)]
    d.line([(p[0],p[1]) for p in pts], fill=(140,125,105), width=3)

# Station platform
draw_box(2000, -4000, 0, 1500, 300, 120,
         (145,110,65),(165,130,80),(115,85,50), outline=(50,35,15))

# ── Hitching posts & props (foreground) ───────────────────────────────────────
for wx in [600, 2800, 6000]:
    px,py,sc = project(wx, 1200, 0)
    ph = int(60*sc)
    pw = max(2, int(5*sc))
    d.line([(px, py),(px, py-ph)], fill=(100,70,35), width=pw)
    d.line([(px-int(pw*3), py-int(ph*0.7)),(px+int(pw*3), py-int(ph*0.7))],
           fill=(110,80,40), width=max(1,pw-1))

# Barrel pair at saloon
for bx in [-300, 300]:
    px,py,sc = project(bx, 800, 0)
    br = max(4, int(12*sc))
    d.ellipse([px-br, py-int(br*1.5), px+br, py+int(br*0.4)],
              fill=(155,110,55), outline=(60,40,20))

# ── Dust haze over ground ─────────────────────────────────────────────────────
# Subtle gradient overlay at horizon to blend sky/ground
for y in range(horizon_y-10, horizon_y+40):
    t = 1 - abs(y - horizon_y) / 40
    overlay = (int(200*t*0.25), int(150*t*0.2), int(80*t*0.15))
    d.line([(0,y),(W,y)], fill=overlay)

# ── Title ─────────────────────────────────────────────────────────────────────
d.rectangle([0,0,W,52], fill=(0,0,0,180))
d.text((W//2, 16), "WOLFE HALL — West Wall", fill=(255,215,90), anchor="mm")
d.text((W//2, 36), "Side view looking north  |  Railroad → Town → Red Rock Mesas", fill=(180,155,100), anchor="mm")

out = "/home/user/SimWorld-Studio/docs/wolfe_hall_sideview.png"
img.save(out, "PNG")
print(f"Saved: {out}")
