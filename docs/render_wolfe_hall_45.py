"""
Wolfe Hall West Wall — 45° birds-eye isometric render.
Camera above and south-east of the scene, looking north-west at 45°.
Uses a true isometric projection: X→right-down, Y→left-down, Z→up.
"""

from PIL import Image, ImageDraw
import math, random

W, H = 2800, 2000
img = Image.new("RGB", (W, H), (18, 14, 10))
d   = ImageDraw.Draw(img)

# ── Isometric projection ──────────────────────────────────────────────────────
# Camera angle: 45° azimuth (SE→NW), 45° elevation
# Standard isometric: each world unit maps to screen as:
#   screen_x =  (wx - wy) * cos(30°) * scale
#   screen_y = -(wx + wy) * sin(30°) * scale + wz * scale
SCALE = 0.048
OX, OY = W * 0.62, H * 0.72   # origin on screen

def iso(wx, wy, wz=0):
    sx = (wx - wy) * math.cos(math.radians(30)) * SCALE
    sy = -(wx + wy) * math.sin(math.radians(30)) * SCALE + wz * SCALE * 0.85
    return int(OX + sx), int(OY - sy)

def top_face(pts_xy, z, fill):
    poly = [iso(x, y, z) for x, y in pts_xy]
    d.polygon(poly, fill=fill)

def box(cx, cy, cz, hw, hd, hh, top_c, east_c, north_c, outline=(40,28,12)):
    """Isometric box: top, east face (right), north face (left)."""
    # 8 corners
    TBL = (cx-hw, cy-hd, cz+hh*2)  # top back left
    TBR = (cx+hw, cy-hd, cz+hh*2)
    TFL = (cx-hw, cy+hd, cz+hh*2)
    TFR = (cx+hw, cy+hd, cz+hh*2)
    BBL = (cx-hw, cy-hd, cz)
    BBR = (cx+hw, cy-hd, cz)
    BFL = (cx-hw, cy+hd, cz)
    BFR = (cx+hw, cy+hd, cz)

    def face(corners, color):
        poly = [iso(*c) for c in corners]
        d.polygon(poly, fill=color, outline=outline)

    # Draw back faces first (painter's algo within box)
    face([BBL, BBR, TBR, TBL], east_c)   # back face
    face([BBL, BFL, TFL, TBL], north_c)  # left face
    # East face (right side, viewer sees it)
    face([BBR, BFR, TFR, TBR], east_c)
    # North face (left side)
    face([BFL, BFR, TFR, TFL], north_c)
    # Top
    face([TBL, TBR, TFR, TFL], top_c)

def cylinder_iso(cx, cy, cz, r, h, top_c, side_c):
    N = 16
    angles = [i * 2 * math.pi / N for i in range(N)]
    # Side faces (draw back half first, then front half)
    for i in range(N):
        a0, a1 = angles[i], angles[(i+1) % N]
        bx0, by0 = cx + r*math.cos(a0), cy + r*math.sin(a0)
        bx1, by1 = cx + r*math.cos(a1), cy + r*math.sin(a1)
        # shade by angle relative to light (from NW top)
        brightness = 0.5 + 0.5 * math.cos(a0 + math.pi*0.25)
        sc = tuple(int(c * brightness) for c in side_c)
        d.polygon([iso(bx0,by0,cz), iso(bx1,by1,cz),
                   iso(bx1,by1,cz+h), iso(bx0,by0,cz+h)], fill=sc)
    # Top cap
    top_pts = [iso(cx + r*math.cos(a), cy + r*math.sin(a), cz+h) for a in angles]
    d.polygon(top_pts, fill=top_c)

# ── Sky fill (top portion) ────────────────────────────────────────────────────
sky_h = int(H * 0.38)
for y in range(sky_h):
    t = y / sky_h
    r = int(25  + t*(185-25))
    g = int(35  + t*(120-35))
    b = int(100 + t*(55 -100))
    d.line([(0,y),(W,y)], fill=(r,g,b))

# Sun
sx, sy = int(W*0.78), int(sky_h*0.55)
for rad in range(55,0,-1):
    t = rad/55
    d.ellipse([sx-rad,sy-rad,sx+rad,sy+rad],
              fill=(255, int(210+t*30), int(60*t)))

# Atmospheric haze near horizon
for y in range(sky_h-20, sky_h+50):
    alpha = max(0, 1 - abs(y-sky_h)/40)
    haze = (int(220*alpha*0.3), int(160*alpha*0.25), int(80*alpha*0.2))
    d.line([(0,y),(W,y)], fill=haze)

# ── Ground plane ──────────────────────────────────────────────────────────────
ground_corners = [(-20000,-20000),( 20000,-20000),(20000,20000),(-20000,20000)]
d.polygon([iso(x,y,0) for x,y in ground_corners], fill=(85,65,42))

# Slight variation strips (east-west bands of colour)
for i in range(8):
    yw = -18000 + i*5000
    strip = [(-18000,yw),(18000,yw),(18000,yw+4800),(-18000,yw+4800)]
    if i%2==0:
        d.polygon([iso(x,y,-1) for x,y in strip], fill=(80,62,40))

# ── Lake ─────────────────────────────────────────────────────────────────────
lake_corners = [(-10500,-2000),(-5500,-2000),(-5500,2000),(-10500,2000)]
d.polygon([iso(x,y,-50) for x,y in lake_corners], fill=(38,95,160))
# Shimmer
for i in range(7):
    lx = -10200 + i*650
    p1, p2 = iso(lx,-1800,-45), iso(lx,1800,-45)
    d.line([p1,p2], fill=(65,130,190), width=2)
# Dock
box(-5650, 300, -80, 900, 120, 80, (140,100,55),(115,80,42),(125,88,48))
box(-5650,-300, -80, 900, 120, 80, (140,100,55),(115,80,42),(125,88,48))

# ── Lakeside trees ────────────────────────────────────────────────────────────
random.seed(7)
lake_trees = [
    (-6000,3000),(-9000,2500),(-11000,500),(-11000,-1500),
    (-9500,-3000),(-7000,-3200),(-5200,-1800),(-5000,1500),
    (-7500,3500),(-10000,3200),
]
for tx,ty in lake_trees:
    h_t = random.randint(600,1100)
    r_t = random.randint(350,550)
    # Trunk
    box(tx, ty, 0, 55, 55, h_t//2,
        (85,58,30),(65,44,22),(72,50,26), outline=(0,0,0))
    # Canopy
    cylinder_iso(tx, ty, h_t//2, r_t, r_t,
                 (48,115,40),(35,88,28))

# ── Scrubland ────────────────────────────────────────────────────────────────
scrubs = [(-1500,5500),(3000,6200),(7000,5800),(12000,5200),(-3000,7200),(5500,8500)]
for sx2,sy2 in scrubs:
    cylinder_iso(sx2, sy2, 0, 280, 320, (52,88,32),(38,65,22))

# ── Red rock mesas ────────────────────────────────────────────────────────────
random.seed(42)
mesas = [
    (-3000,13000, 800, 600,1800),
    ( 1000,15000,1100, 900,2800),
    ( 5000,14000, 950, 750,2400),
    ( 9000,12500, 750, 600,2000),
    (12000,11000, 900, 650,2100),
    (-6000,12000, 650, 500,1500),
    ( 3000,16000,1300, 950,3200),
]
for cx,cy,hw,hd,hh in mesas:
    jx = random.randint(-80,80)
    jy = random.randint(-80,80)
    base = (125+random.randint(-8,8), 52+random.randint(-4,4), 22)
    mid  = (150+random.randint(-8,8), 65+random.randint(-4,4), 32)
    top_c= (105, 42, 18)
    east = (90, 35, 14)
    north= (100,40,16)
    # Base slab
    box(cx+jx, cy+jy, 0, hw, hd, int(hh*0.5), mid, east, north)
    # Upper narrower slab
    box(cx+jx+random.randint(-60,60), cy+jy, int(hh*0.5),
        int(hw*0.65), int(hd*0.75), int(hh*0.5), top_c, east, north)

# ── Road (dirt, between building rows) ───────────────────────────────────────
road = [(-1500,-1500),(10500,-1500),(10500,1500),(-1500,1500)]
d.polygon([iso(x,y,-5) for x,y in road], fill=(105,80,50))
# Ruts
for rx in [0,2000,4000,6000,8000]:
    d.line([iso(rx,-1400,-4), iso(rx,1400,-4)], fill=(90,68,42), width=2)

# ── Buildings ─────────────────────────────────────────────────────────────────
buildings = [
    # name, cx, cy, hw, hd, hh, top, east, north
    ("Saloon",      0,  1500, 650,380, 900, (200,158,98),(158,122,74),(172,133,82)),
    ("Gen.Store",3500,  1500, 640,370, 800, (192,150,92),(150,116,70),(164,128,78)),
    ("Sheriff",  7000,  1500, 550,340, 760, (195,153,94),(153,118,72),(167,130,80)),
    ("Barn",     1800, -1500, 800,520,1050, (175,130,72),(135,100,55),(148,110,62)),
    ("Boarding", 5000, -1500, 680,400, 920, (185,142,86),(143,110,64),(156,120,71)),
    ("Stables",  8200, -1500, 680,390, 840, (180,138,83),(140,107,62),(153,117,69)),
]
# Painter's sort: draw back (large cy) first
buildings.sort(key=lambda b: -b[2])
for name,cx,cy,hw,hd,hh,top_c,east_c,north_c in buildings:
    box(cx, cy, 0, hw, hd, hh, top_c, east_c, north_c)
    # Roof ridge
    rp1, rp2 = iso(cx-hw+80, cy, hh*2+60), iso(cx+hw-80, cy, hh*2+60)
    d.line([rp1,rp2], fill=(60,40,18), width=3)
    # Door
    door_w, door_h = 120, 200
    p_d = iso(cx, cy + (hd if cy > 0 else -hd), hh)
    d.ellipse([p_d[0]-8, p_d[1]-int(door_h*SCALE*0.7),
               p_d[0]+8, p_d[1]+4], fill=(50,32,15))
    # Label above
    lp = iso(cx, cy, hh*2 + 300)
    d.text(lp, name, fill=(255,235,180), anchor="mm")

# ── Water tower ───────────────────────────────────────────────────────────────
# Legs
for lx,ly in [(-120,-120),(120,-120),(120,120),(-120,120)]:
    p0 = iso(10000+lx, ly, 0)
    p1 = iso(10000+lx*0.5, ly*0.5, 1200)
    d.line([p0,p1], fill=(110,80,42), width=4)
cylinder_iso(10000, 0, 1200, 380, 500, (152,112,62),(118,86,46))
# Spout
d.line([iso(10000,0,1000), iso(10000-300,0,800)], fill=(90,65,35), width=5)

# ── Hitching posts ────────────────────────────────────────────────────────────
for wx in [600,2800,6000]:
    p0 = iso(wx, 1100, 0)
    p1 = iso(wx, 1100, 420)
    d.line([p0,p1], fill=(105,75,40), width=5)
    d.line([iso(wx-180, 1100, 300), iso(wx+180, 1100, 300)],
           fill=(115,85,45), width=3)

# Barrels at saloon
for bx in [-320,320]:
    cylinder_iso(bx, 820, 0, 90, 160, (162,115,58),(125,88,44))

# Crates
for px2,py2 in [(900,1700),(4000,-1800),(7500,-1700),(3200,1600)]:
    box(px2, py2, 0, 80,70,100, (158,118,62),(122,90,46),(135,100,52))

# ── Railroad ─────────────────────────────────────────────────────────────────
track_y = -4500
# Ballast
ballast = [(-2500,track_y-260),(15500,track_y-260),(15500,track_y+260),(-2500,track_y+260)]
d.polygon([iso(x,y,-10) for x,y in ballast], fill=(68,52,36))

# Ties
for i in range(24):
    wx = -1500 + i*720
    p0 = iso(wx, track_y-240, 0)
    p1 = iso(wx, track_y+240, 0)
    d.line([p0,p1], fill=(80,60,38), width=6)

# Rails
for dy in [-210, 210]:
    pts = [iso(wx, track_y+dy, 22) for wx in range(-2000,15500,300)]
    d.line(pts, fill=(145,128,108), width=3)

# Platform
box(2000,-4000, 0, 1500,300,130, (148,112,66),(115,84,48),(128,96,55))
lp = iso(2000, -4000, 280)
d.text(lp, "Station", fill=(230,210,160), anchor="mm")

# ── Title ─────────────────────────────────────────────────────────────────────
d.rectangle([0,0,W,54], fill=(0,0,0))
d.text((W//2, 16), "WOLFE HALL — West Wall", fill=(255,215,80), anchor="mm")
d.text((W//2, 37), "45° birds-eye view  |  SE → NW", fill=(175,150,95), anchor="mm")

out = "/home/user/SimWorld-Studio/docs/wolfe_hall_45.png"
img.save(out, "PNG")
print(f"Saved: {out}")
