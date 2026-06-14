"""
Wolfe Hall — reproduction of the reference SimWorld Studio screenshot.
Wide 45° isometric view looking NW. Studied from the real UE5 render:
  - Left:   lake (blue) + dense green vegetation canopy
  - Center: dirt road + frontier buildings (saloon, general store, etc.)
  - Center: railroad tracks + steam train + wagon
  - Right:  mining structures (platforms, crushers, industrial)
  - Back:   red sandstone mesa formations across full horizon
  - Ground: sandy tan desert
"""

from PIL import Image, ImageDraw, ImageFilter
import math, random

random.seed(99)

W, H = 3200, 1300
img = Image.new("RGB", (W, H), (200, 175, 130))
d   = ImageDraw.Draw(img)

# ── Isometric projection (matched to reference camera angle) ─────────────────
# Camera: SE of scene, ~45° elevation, looking NW
SCALE  = 0.052
COS_A  = math.cos(math.radians(28))
SIN_A  = math.sin(math.radians(28))
OX, OY = W * 0.52, H * 0.62

def iso(wx, wy, wz=0):
    # Rotate world XY 45° then apply elevation
    rx =  wx * COS_A - wy * SIN_A
    ry = (wx * SIN_A + wy * COS_A) * 0.48
    sx = OX + rx * SCALE
    sy = OY - ry * SCALE - wz * SCALE * 0.72
    return int(sx), int(sy)

def poly(pts, fill, outline=None, width=1):
    d.polygon(pts, fill=fill, outline=outline)

def quad(p1,p2,p3,p4, fill, outline=None):
    poly([p1,p2,p3,p4], fill, outline)

def box(cx,cy,cz, hw,hd,hh, top,east,north, ol=(30,20,8)):
    tbl=iso(cx-hw,cy-hd,cz+hh); tbr=iso(cx+hw,cy-hd,cz+hh)
    tfl=iso(cx-hw,cy+hd,cz+hh); tfr=iso(cx+hw,cy+hd,cz+hh)
    bbl=iso(cx-hw,cy-hd,cz);    bbr=iso(cx+hw,cy-hd,cz)
    bfl=iso(cx-hw,cy+hd,cz);    bfr=iso(cx+hw,cy+hd,cz)
    # back faces
    quad(bbl,bbr,tbr,tbl, east,  ol)
    quad(bbl,bfl,tfl,tbl, north, ol)
    # front faces
    quad(bbr,bfr,tfr,tbr, east,  ol)
    quad(bfl,bfr,tfr,tfl, north, ol)
    # top
    quad(tbl,tbr,tfr,tfl, top,   ol)

def roof_peak(cx,cy,cz, hw,hd,hh,ph, col_slope, col_end, ol=(30,20,8)):
    """Peaked gable roof."""
    bl=iso(cx-hw,cy-hd,cz); br=iso(cx+hw,cy-hd,cz)
    fl=iso(cx-hw,cy+hd,cz); fr=iso(cx+hw,cy+hd,cz)
    pk_l=iso(cx-hw,cy,cz+ph); pk_r=iso(cx+hw,cy,cz+ph)
    # two slope faces
    quad(bl,br,pk_r,pk_l, col_slope, ol)
    quad(fl,fr,pk_r,pk_l, col_slope, ol)
    # gable ends
    poly([bl,fl,pk_l], col_end, ol)
    poly([br,fr,pk_r], col_end, ol)

# ── Sky ───────────────────────────────────────────────────────────────────────
sky_h = int(H*0.30)
for y in range(sky_h):
    t = y/sky_h
    r = int(160+t*60); g = int(185+t*40); b = int(210+t*20)
    d.line([(0,y),(W,y)], fill=(r,g,b))

# Sun haze near top
for y in range(sky_h-30, sky_h+60):
    t = max(0, 1-abs(y-(sky_h+10))/50)
    d.line([(0,y),(W,y)], fill=(int(230*t+160*(1-t)), int(195*t+175*(1-t)), int(140*t+130*(1-t))))

# ── Ground (sandy desert) ─────────────────────────────────────────────────────
gpts = [iso(-22000,-22000), iso(22000,-22000), iso(22000,22000), iso(-22000,22000)]
poly(gpts, (195,168,118))

# Ground texture stripes
for i in range(12):
    yw = -20000 + i*3800
    s = [iso(-20000,yw), iso(20000,yw), iso(20000,yw+3600), iso(-20000,yw+3600)]
    c = (188,162,112) if i%2==0 else (200,172,122)
    poly(s, c)

# ── Road (dirt track through town) ───────────────────────────────────────────
# Road runs W-E, slightly south of center
road_pts = [iso(-14000,-600), iso(20000,-600), iso(20000,600), iso(-14000,600)]
poly(road_pts, (175,148,98))
# Ruts
for rx in range(-13000, 19000, 1200):
    d.line([iso(rx,-400,2), iso(rx,400,2)], fill=(160,135,88), width=2)

# ── RED ROCK MESAS — full horizon arc ────────────────────────────────────────
mesas = [
    # cx,   cy,    hw,  hd,   hh
    (-18000,10000, 3500,2000, 4500),
    (-12000,12000, 4000,2500, 5500),
    ( -5000,14000, 4500,2800, 6500),
    (  3000,15000, 5000,3000, 7500),
    ( 10000,14000, 4200,2600, 6000),
    ( 17000,12000, 3800,2200, 5000),
    ( 22000, 9000, 3000,1800, 4000),
    ( -9000,11000, 3000,1800, 4000),
    (  7000,13000, 2800,1800, 3800),
]
for cx,cy,hw,hd,hh in mesas:
    j = random.randint(-200,200)
    dark  = (115+random.randint(-8,8), 48+random.randint(-5,5), 18)
    mid   = (148+random.randint(-8,8), 65+random.randint(-5,5), 28)
    light = (168+random.randint(-5,5), 82+random.randint(-4,4), 38)
    # Layered slabs for mesa look
    box(cx+j, cy, 0,      hw,     hd,      int(hh*0.45), dark, (80,32,12),  (90,36,14))
    box(cx+j, cy, int(hh*0.45), int(hw*0.78), int(hd*0.82), int(hh*0.35), mid, (100,40,16),(110,44,18))
    box(cx+j, cy, int(hh*0.80), int(hw*0.52), int(hd*0.58), int(hh*0.22), light,(120,50,20),(130,55,22))
    # Talus/scree slope at base
    scree = [iso(cx+j-hw,cy-hd,0), iso(cx+j+hw,cy-hd,0),
             iso(cx+j+int(hw*0.85),cy-hd,int(hh*0.20)),
             iso(cx+j-int(hw*0.85),cy-hd,int(hh*0.20))]
    poly(scree, (140,100,62))

# ── LAKE — left side, with water shimmer ─────────────────────────────────────
lake_pts = [iso(-14000,-2200), iso(-6500,-2200), iso(-6500,2800), iso(-14000,2800)]
poly(lake_pts, (48,105,175))
# Depth variation
lake_deep = [iso(-13000,-1500), iso(-8000,-1500), iso(-8000,1800), iso(-13000,1800)]
poly(lake_deep, (35,88,158))
# Shimmer lines
for i in range(10):
    wy = -1800 + i*380
    p1,p2 = iso(-13500,wy,5), iso(-7000,wy,5)
    d.line([p1,p2], fill=(80,145,210), width=2)
# Shore detail
shore = [iso(-14200,-2400), iso(-6200,-2400), iso(-6200,-1800), iso(-14200,-1800)]
poly(shore, (160,140,90))

# ── DENSE VEGETATION — around lake ───────────────────────────────────────────
def tree_canopy(cx, cy, r, h, variation=0):
    """Dense round tree canopy."""
    # Trunk
    box(cx,cy,0, 60,60,h//2, (82,55,28),(60,40,18),(70,46,22), ol=(0,0,0))
    # Canopy layers - multiple overlapping circles projected
    base_r = r
    for layer in range(3):
        frac = 1 - layer*0.18
        lh = h//2 + layer*(h//5)
        pts = 16
        canopy = [iso(cx + int(base_r*frac*math.cos(i*2*math.pi/pts)),
                      cy + int(base_r*frac*math.sin(i*2*math.pi/pts)), lh)
                  for i in range(pts)]
        g_v = 95 + layer*18 + variation
        poly(canopy, (28, g_v, 22))
    # Top highlight
    top_pts = [iso(cx + int(base_r*0.4*math.cos(i*2*math.pi/8)),
                   cy + int(base_r*0.4*math.sin(i*2*math.pi/8)), h//2+int(h*0.55))
               for i in range(8)]
    poly(top_pts, (45, min(165,110+variation), 35))

# Dense cluster of trees around lake
lake_trees = [
    (-14500, 800, 550,1100,10), (-14200,-1200,480,1000,5), (-13500, 2000,520,1050,8),
    (-12800,-2000,500, 980,12), (-12000, 2500,600,1200,6), (-11500,-2200,470,950,9),
    (-10800, 3000,550,1100,15), (-10200,-2500,510,1020,3), (-9500,  3200,580,1150,7),
    (-8800, -2800,490, 980,11), (-8200,  2800,540,1080,4), (-7500, -2600,460, 940,13),
    (-7000,  2200,520,1050,8), (-6800, -1800,500,1000,6), (-6200,  1500,480, 960,10),
    (-13000, 1000,600,1200,5), (-11000,-1000,530,1060,9), (-9800,  1200,570,1140,7),
    (-15000,-200, 510,1020,12),(-14800, 1800,490, 980,3),
]
# Sort back to front
lake_trees.sort(key=lambda t: t[1])
for tx,ty,r,h,v in lake_trees:
    tree_canopy(tx,ty,r,h,v)

# Extra scrub east of lake
for tx,ty in [(-5500,1500),(-5000,-800),(-4500,2200),(-5800,-1500)]:
    tree_canopy(tx,ty,320,680,8)

# ── FRONTIER BUILDINGS ────────────────────────────────────────────────────────
# Main street: buildings face south (toward road), packed tightly
buildings = [
    # name,  cx,   cy,  hw, hd,  wall_h, roof_h, wall_top, wall_e, wall_n, roof_c
    ("Saloon",       -2000, 2200, 550,320, 920,420, (188,140, 88),(148,108,64),(165,122,74),(120, 65,35)),
    ("Gen Store 1",    400, 2100, 520,300, 850,380, (168,108, 72),(130, 82,54),(148, 95,62),( 90, 50,25)),
    ("Gen Store 2",   1500, 2100, 520,300, 860,380, (108,138, 95),( 82,108,72),( 95,122,82),( 65, 88,50)),
    ("Building 003",  2600, 2000, 500,290, 840,360, (148,128, 88),(115, 98,66),(130,112,76),( 95, 80,45)),
    ("Saloon B",      3700, 2100, 540,310, 900,410, (168,138, 92),(130,105,68),(148,120,78),(110, 85,48)),
    ("Gen Stone",     4800, 2000, 510,295, 820,360, (138,118, 80),(108, 90,60),(122,102,68),( 88, 72,40)),
    ("Boarding",      5900, 2100, 530,305, 880,400, (178,148, 98),(138,114,72),(155,128,83),(115, 90,50)),
    ("Sheriff",       7000, 1950, 490,285, 800,350, (158,128, 85),(122, 98,62),(138,112,72),(100, 78,42)),
]
# Sort back to front
buildings.sort(key=lambda b: b[2])
for name,cx,cy,hw,hd,wh,rh,wt,we,wn,rc in buildings:
    box(cx,cy,0, hw,hd,wh, wt,we,wn)
    # Windows
    for wxi in [-1,1]:
        wp = iso(cx+wxi*int(hw*0.45), cy+hd, int(wh*0.55))
        d.ellipse([wp[0]-6,wp[1]-9,wp[0]+6,wp[1]+3], fill=(80,60,30))
    # Peaked roof
    roof_pts = [iso(cx-hw,cy-hd,wh), iso(cx+hw,cy-hd,wh),
                iso(cx+hw,cy+hd,wh), iso(cx-hw,cy+hd,wh)]
    peak_l = iso(cx, cy-hd, wh+rh)
    peak_r = iso(cx, cy+hd, wh+rh)
    # South slope (visible)
    poly([iso(cx-hw,cy+hd,wh), iso(cx+hw,cy+hd,wh), peak_r, peak_l], rc,  (20,12,4))
    # North slope
    darker_rc = tuple(max(0,c-30) for c in rc)
    poly([iso(cx-hw,cy-hd,wh), iso(cx+hw,cy-hd,wh), peak_r, peak_l], darker_rc, (20,12,4))

# ── WATER TOWER ───────────────────────────────────────────────────────────────
for lx,ly in [(-110,-110),(110,-110),(110,110),(-110,110)]:
    p0=iso(8800+lx, 1200+ly, 0); p1=iso(8800+lx//2, 1200+ly//2, 1400)
    d.line([p0,p1], fill=(105,75,40), width=5)
box(8800,1200,1400, 380,280,580, (148,108,58),(115,82,42),(128,92,48))

# ── RAILROAD ─────────────────────────────────────────────────────────────────
track_y = -1200
# Ballast bed
ballast = [iso(-16000,track_y-380), iso(22000,track_y-380),
           iso(22000,track_y+380),  iso(-16000,track_y+380)]
poly(ballast, (75,60,42))

# Ties
for i in range(42):
    wx = -15000 + i*850
    d.line([iso(wx,track_y-340,5), iso(wx,track_y+340,5)], fill=(88,65,38), width=7)

# Two rails
for dy in [-240,240]:
    rail_pts = [iso(wx, track_y+dy, 25) for wx in range(-15000,22000,250)]
    d.line(rail_pts, fill=(155,138,115), width=4)

# ── STEAM TRAIN ───────────────────────────────────────────────────────────────
tx = 2000
# Locomotive body
box(tx, track_y, 30, 900,260,620, (70,85,110),(50,62,85),(60,72,95))
# Boiler dome
box(tx-200, track_y, 650, 200,200,220, (80,95,120),(60,72,95),(70,82,108))
# Smokestack
box(tx-600, track_y, 620, 120,120,350, (55,55,55),(40,40,40),(48,48,48))
# Cowcatcher
catcher = [iso(tx+900,track_y-260,30), iso(tx+1050,track_y-180,30),
           iso(tx+1050,track_y+180,30), iso(tx+900,track_y+260,30),
           iso(tx+900,track_y+260,200), iso(tx+900,track_y-260,200)]
poly([iso(tx+900,track_y-280,30),iso(tx+1100,track_y-160,30),
      iso(tx+1100,track_y+160,30),iso(tx+900,track_y+280,30),
      iso(tx+900,track_y+280,200),iso(tx+900,track_y-280,200)], (65,75,100), (30,30,40))
# Wheels (dark circles projected)
for wx_off in [-500,-100,300,700]:
    wp = iso(tx+wx_off, track_y+260, 30)
    d.ellipse([wp[0]-12,wp[1]-8,wp[0]+12,wp[1]+8], fill=(35,35,35))

# Wagon/car behind locomotive
box(tx-2200, track_y, 30, 700,250,500, (88,72,48),(65,52,35),(75,60,40))
box(tx-2200, track_y, 530, 700,250,80,  (98,80,52),(72,58,38),(82,66,44))

# ── MINING STRUCTURES (right side) ───────────────────────────────────────────
mine_buildings = [
    # cx,    cy,   hw, hd,  hh,   top,             east,           north
    (12000, -2500, 400,300, 600, (65,58,52),(48,42,38),(55,48,44)),   # Mine Structure
    (13500,  -500, 500,350, 800, (72,62,55),(54,46,40),(62,52,46)),   # Mine Platform
    (15000, -2000, 380,280, 550, (60,55,50),(44,40,36),(52,46,42)),   # Crusher
    (16500,  -800, 420,300, 650, (68,60,54),(50,44,38),(58,50,44)),   # Platform B
    (14200,  1000, 350,260, 480, (58,52,48),(42,38,34),(50,44,40)),   # Mine Structure 2
    (17500, -1500, 440,320, 700, (70,62,56),(52,46,40),(60,52,46)),   # Structure 3
    (11000,   500, 300,220, 420, (55,50,46),(40,36,32),(48,42,38)),   # Small structure
]
for cx,cy,hw,hd,hh,tc,ec,nc in mine_buildings:
    box(cx,cy,0, hw,hd,hh, tc,ec,nc, ol=(20,16,12))
    # Platform/scaffolding lines
    for zh in range(200,hh,200):
        d.line([iso(cx-hw,cy-hd,zh), iso(cx+hw,cy-hd,zh)], fill=(35,30,26), width=2)

# Mine platform raised floors
box(13000,-1800,0, 1200,500,120, (80,70,58),(62,54,44),(70,62,50))
box(16000,-1200,0, 1000,450,120, (78,68,56),(60,52,42),(68,60,48))

# Ore carts on tracks near mine
for ox in [11500, 12500]:
    box(ox, -800, 30, 220,160,200, (55,48,42),(40,35,30),(48,42,36))

# ── SCRUBLAND between town and mesas ─────────────────────────────────────────
scrub_pos = [
    (-3000,5500,280,580),( 1000,6500,300,620),( 5000,5800,260,540),
    (9000, 5200,290,600),(-1000,7200,310,640),(3500, 8000,270,560),
    (7500, 7000,300,620),(11500,6000,250,520),(13500,4500,280,580),
]
for sx,sy,r,h in scrub_pos:
    tree_canopy(sx,sy,r,h,5)

# ── HITCHING POSTS + PROPS ────────────────────────────────────────────────────
for px in [-1200,600,2000,3500]:
    p0=iso(px,1800,0); p1=iso(px,1800,380)
    d.line([p0,p1], fill=(105,75,38), width=5)
    d.line([iso(px-160,1800,280), iso(px+160,1800,280)], fill=(115,82,42), width=3)

# Barrels
for bx,by in [(-2400,1600),(-1600,1600),(200,1500),(5600,1500)]:
    box(bx,by,0, 80,70,140, (158,112,55),(122,85,42),(138,97,48))

# ── DIRT ROAD detail ──────────────────────────────────────────────────────────
# Wagon tracks / wheel ruts along road
for ry in [-350,350]:
    ruts = [iso(wx,ry,2) for wx in range(-13000,10000,200)]
    d.line(ruts, fill=(162,138,90), width=3)

# ── LEGEND (matching reference image) ────────────────────────────────────────
legend_x, legend_y = W-200, 30
legend_items = [
    ((40,200,40),   "Vegetation"),
    ((80,130,80),   "Building Store"),
    ((180,80,80),   "Buildings"),
    ((80,80,80),    "Rocks"),
    ((80,120,180),  "Vehicles"),
    ((180,160,80),  "Vehicles"),
    ((140,90,50),   "Rocks"),
]
d.rectangle([legend_x-10, legend_y-5, W-5, legend_y+len(legend_items)*22+10],
            fill=(0,0,0,180), outline=(80,70,60))
for i,(col,name) in enumerate(legend_items):
    ly2 = legend_y + 5 + i*22
    d.rectangle([legend_x, ly2, legend_x+14, ly2+14], fill=col, outline=(200,200,200))
    d.text((legend_x+20, ly2+7), name, fill=(230,225,215), anchor="lm")

# ── Title ─────────────────────────────────────────────────────────────────────
d.rectangle([0,0,W,42], fill=(0,0,0))
d.text((W//2,14), "WOLFE HALL — West Wall  |  SimWorld Studio scene reproduction", fill=(255,215,80), anchor="mm")
d.text((W//2,30), "45° isometric  ·  lake + frontier town + railroad + mine + red rock mesas", fill=(175,150,90), anchor="mm")

# ── Soften slightly to reduce pixelation ─────────────────────────────────────
img = img.filter(ImageFilter.SMOOTH)
d = ImageDraw.Draw(img)

out = "/home/user/SimWorld-Studio/docs/wolfe_hall_reference_repro.png"
img.save(out, "PNG")
print(f"Saved: {out}")
