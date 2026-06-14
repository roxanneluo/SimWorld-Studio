"""
Wolfe Hall — Round 2 reproduction with corrected proportions.
Measured from reference screenshot:
  - Buildings: hw=420, hd=260, hh=920  packed 900cm apart (nearly touching)
  - Trees:     canopy_r=900, h=1500    (taller & wider than buildings)
  - Mesas:     hh=8000-12000           (8-10x building height)
  - Road:      half-width=380cm        (narrow frontier street)
  - Train:     loco hw=1400, hd=340    (≈3 building widths long)
  - Mining:    hh=350-600              (shorter, industrial)
"""

from PIL import Image, ImageDraw, ImageFilter
import math, random

random.seed(42)

W, H = 3400, 1350
img = Image.new("RGB", (W, H), (18,14,10))
d   = ImageDraw.Draw(img)

# ── Projection: 45° azimuth, ~38° elevation, looking NW ──────────────────────
SCALE = 0.050
AZ    = math.radians(42)   # azimuth — how far rotated from E-W axis
EL    = 0.44               # elevation compression
OX    = W * 0.56
OY    = H * 0.64

def iso(wx, wy, wz=0):
    rx =  wx * math.cos(AZ) - wy * math.sin(AZ)
    ry = (wx * math.sin(AZ) + wy * math.cos(AZ)) * EL
    return int(OX + rx*SCALE), int(OY - ry*SCALE - wz*SCALE*0.72)

def face(pts, fill, outline=None):
    d.polygon(pts, fill=fill, outline=outline)

def box(cx,cy,cz, hw,hd,hh, top,east,north, ol=(25,16,6)):
    c = [(sx,sy,sz) for sx in [-hw,hw] for sy in [-hd,hd] for sz in [0,hh*2]]
    def v(sx,sy,sz): return iso(cx+sx, cy+sy, cz+sz)
    # back
    face([v(-hw,-hd,0),v(hw,-hd,0),v(hw,-hd,hh*2),v(-hw,-hd,hh*2)], east, ol)
    face([v(-hw,-hd,0),v(-hw,hd,0),v(-hw,hd,hh*2),v(-hw,-hd,hh*2)], north, ol)
    # front
    face([v(hw,-hd,0),v(hw,hd,0),v(hw,hd,hh*2),v(hw,-hd,hh*2)], east, ol)
    face([v(-hw,hd,0),v(hw,hd,0),v(hw,hd,hh*2),v(-hw,hd,hh*2)], north, ol)
    # top
    face([v(-hw,-hd,hh*2),v(hw,-hd,hh*2),v(hw,hd,hh*2),v(-hw,hd,hh*2)], top, ol)

def shadow(cx,cy, hw,hd, opacity=60):
    """Soft ground shadow ellipse."""
    sx,sy = iso(cx,cy,0)
    rw = int((hw+hd)*SCALE*0.9)
    rh = int((hw+hd)*SCALE*0.38)
    for i in range(8,0,-1):
        a = int(opacity * i/8)
        shade = (0,0,0) if False else tuple(max(0,c-a//2) for c in (185,158,108))
        d.ellipse([sx-rw-i,sy-rh-i//2,sx+rw+i,sy+rh+i//2], fill=shade)

def peaked_roof(cx,cy,cz, hw,hd,ph, slope,end, ol=(20,12,4)):
    """Gable roof: two slopes + two gable ends."""
    def v(sx,sy,sz): return iso(cx+sx,cy+sy,cz+sz)
    ridge_front = v(0, hd, ph)
    ridge_back  = v(0,-hd, ph)
    # south slope (viewer-facing)
    face([v(-hw,hd,0),v(hw,hd,0),ridge_front], slope, ol)
    # north slope
    dark_slope = tuple(max(0,c-35) for c in slope)
    face([v(-hw,-hd,0),v(hw,-hd,0),ridge_back], dark_slope, ol)
    # west gable
    face([v(-hw,-hd,0),v(-hw,hd,0),ridge_front,ridge_back], end, ol)
    # east gable
    face([v(hw,-hd,0),v(hw,hd,0),ridge_front,ridge_back], end, ol)
    # ridge cap
    d.line([ridge_front, ridge_back], fill=ol, width=2)

def canopy_tree(cx,cy,tr_h,cn_r,cn_h, base_green, ol=(0,0,0)):
    """Layered tree: trunk + 3 canopy tiers."""
    # Shadow first
    sx,sy = iso(cx,cy,0)
    d.ellipse([sx-int(cn_r*SCALE*1.1), sy-int(cn_r*SCALE*0.45),
               sx+int(cn_r*SCALE*1.1), sy+int(cn_r*SCALE*0.45)],
              fill=(65,52,32))
    # Trunk
    box(cx,cy,0, 55,55,tr_h, (82,55,28),(62,40,18),(72,48,22), ol=(0,0,0))
    # 3 canopy tiers (each slightly narrower/higher)
    for i,frac in enumerate([1.0, 0.78, 0.55]):
        z = tr_h + i * int(cn_h*0.28)
        r = int(cn_r*frac)
        N = 20
        pts = [iso(cx+int(r*math.cos(k*2*math.pi/N)),
                   cy+int(r*math.sin(k*2*math.pi/N)), z) for k in range(N)]
        g = min(255, base_green + i*18)
        face(pts, (22+i*4, g, 18+i*3))
    # Top bright spot
    tip = [iso(cx+int(cn_r*0.32*math.cos(k*2*math.pi/10)),
               cy+int(cn_r*0.32*math.sin(k*2*math.pi/10)),
               tr_h+int(cn_h*0.82)) for k in range(10)]
    face(tip, (38, min(255,base_green+45), 28))

# ══════════════════════════════════════════════════════════════════════════════
# SKY
# ══════════════════════════════════════════════════════════════════════════════
sky_h = int(H*0.29)
for y in range(sky_h):
    t = y/sky_h
    d.line([(0,y),(W,y)], fill=(
        int(145+t*62), int(172+t*38), int(205+t*18)))
# Horizon haze
for y in range(sky_h-15, sky_h+55):
    t = max(0, 1-abs(y-sky_h)/45)
    d.line([(0,y),(W,y)], fill=(
        int(205+50*t), int(182+30*t), int(148+20*t)))

# ══════════════════════════════════════════════════════════════════════════════
# GROUND
# ══════════════════════════════════════════════════════════════════════════════
gpts = [iso(-24000,-24000),iso(24000,-24000),iso(24000,24000),iso(-24000,24000)]
face(gpts, (190,162,108))
# Subtle terrain variation
for i in range(14):
    yw = -22000+i*3500
    c = (183,156,104) if i%2==0 else (196,168,114)
    s = [iso(-22000,yw),iso(22000,yw),iso(22000,yw+3400),iso(-22000,yw+3400)]
    face(s, c)

# ══════════════════════════════════════════════════════════════════════════════
# RED ROCK MESAS  (8-10× building height)
# Building hh ≈ 920 → mesas hh = 8000-12000
# ══════════════════════════════════════════════════════════════════════════════
mesas = [
    # cx,     cy,     hw,   hd,   hh
    (-20000, 10000, 4500, 2800, 8500),
    (-13000, 12500, 5500, 3200,11000),
    ( -5000, 14000, 6000, 3500,12000),
    (  3500, 15500, 6500, 3800,13000),
    ( 11000, 14000, 5800, 3400,11500),
    ( 18000, 12000, 4800, 2900, 9000),
    ( 24000,  9000, 3800, 2400, 7500),
    ( -9000, 11500, 4000, 2500, 8000),
    (  7000, 13500, 4500, 2700, 9500),
]
for cx,cy,hw,hd,hh in mesas:
    j = random.randint(-150,150)
    # Layer 1: broad base
    c1 = (112+random.randint(-6,6), 46+random.randint(-4,4), 16)
    c1e = (tuple(max(0,v-28) for v in c1))
    c1n = (tuple(max(0,v-18) for v in c1))
    box(cx+j,cy,0, hw,hd,int(hh*0.4), c1,c1e,c1n, ol=(15,8,2))
    # Layer 2: narrower mid
    c2 = (145+random.randint(-6,6), 62+random.randint(-4,4), 26)
    c2e = tuple(max(0,v-28) for v in c2)
    c2n = tuple(max(0,v-18) for v in c2)
    box(cx+j,cy,int(hh*0.4), int(hw*0.75),int(hd*0.78),int(hh*0.35),
        c2,c2e,c2n, ol=(15,8,2))
    # Layer 3: narrow top cap
    c3 = (168+random.randint(-5,5), 80+random.randint(-3,3), 36)
    c3e = tuple(max(0,v-25) for v in c3)
    c3n = tuple(max(0,v-15) for v in c3)
    box(cx+j,cy,int(hh*0.75), int(hw*0.48),int(hd*0.52),int(hh*0.25),
        c3,c3e,c3n, ol=(15,8,2))
    # Talus scree at base
    scree = [iso(cx+j-hw,cy-hd,0), iso(cx+j+hw,cy-hd,0),
             iso(cx+j+int(hw*0.88),cy-hd,int(hh*0.12)),
             iso(cx+j-int(hw*0.88),cy-hd,int(hh*0.12))]
    face(scree, (148,108,68))
    # Cliff face cracks (horizontal ledge lines)
    for frac in [0.38, 0.62, 0.80]:
        lz = int(hh*frac)
        p1 = iso(cx+j-int(hw*(1-frac*0.5)), cy-hd, lz)
        p2 = iso(cx+j+int(hw*(1-frac*0.5)), cy-hd, lz)
        d.line([p1,p2], fill=tuple(max(0,v-40) for v in c2), width=2)

# ══════════════════════════════════════════════════════════════════════════════
# LAKE  (left side)
# ══════════════════════════════════════════════════════════════════════════════
lake_pts = [iso(-15000,-2500),iso(-6500,-2500),iso(-6500,3000),iso(-15000,3000)]
face(lake_pts, (42,98,168))
lake_deep = [iso(-14000,-1800),iso(-8000,-1800),iso(-8000,2000),iso(-14000,2000)]
face(lake_deep, (30,78,148))
# Shimmer
for i in range(12):
    wy = -2200+i*380
    p1,p2 = iso(-14500,wy,4), iso(-7000,wy,4)
    d.line([p1,p2], fill=(68,138,205), width=2)
# Shore gradient
shore_pts = [iso(-15200,-2700),iso(-6300,-2700),iso(-6300,-2200),iso(-15200,-2200)]
face(shore_pts, (155,132,88))

# ══════════════════════════════════════════════════════════════════════════════
# DENSE VEGETATION around lake  (trees TALLER & WIDER than buildings)
# Building hh=920 → tree cn_h=1500, cn_r=900
# ══════════════════════════════════════════════════════════════════════════════
lake_trees = [
    # cx,      cy,    tr_h, cn_r, cn_h, base_green
    (-15200,   800,   420, 920, 1450, 98),
    (-15000, -1400,   400, 880, 1380, 88),
    (-14200,  2100,   450, 960, 1500, 105),
    (-13500, -2200,   380, 840, 1320, 92),
    (-12800,  2800,   470, 1000,1550, 112),
    (-12000, -2600,   360, 820, 1280, 85),
    (-11200,  3100,   490, 980, 1520, 108),
    (-10500, -2800,   400, 880, 1380, 95),
    ( -9800,  3300,   460, 950, 1480, 102),
    ( -9200, -2900,   420, 900, 1420, 90),
    ( -8500,  2900,   440, 920, 1450, 98),
    ( -7800, -2600,   400, 860, 1360, 88),
    ( -7200,  2400,   420, 900, 1400, 95),
    ( -6800, -2000,   380, 820, 1280, 85),
    ( -6200,  1600,   400, 860, 1350, 92),
    (-13000,  1000,   460, 940, 1470, 100),
    (-11000, -1000,   440, 910, 1430, 96),
    ( -9800,  1200,   470, 960, 1500, 108),
    (-15500,  -200,   410, 870, 1360, 90),
    (-14800,  1800,   430, 900, 1410, 95),
    (-10200,   200,   450, 930, 1460, 100),
    (-12500, -3000,   370, 800, 1260, 82),
    ( -8000,  3200,   440, 920, 1450, 98),
]
# Sort back to front (higher cy = further back = draw first)
lake_trees.sort(key=lambda t: -t[1])
for tx,ty,trh,cnr,cnh,bg in lake_trees:
    canopy_tree(tx,ty,trh,cnr,cnh,bg)

# Sparse scrub transitioning east toward town
for tx,ty in [(-5500,1800),(-5000,-900),(-4500,2400),(-5800,-1600),(-4000,1000)]:
    canopy_tree(tx,ty,280,480,760,78)

# ══════════════════════════════════════════════════════════════════════════════
# DIRT ROAD  (narrow — half-width=380cm)
# ══════════════════════════════════════════════════════════════════════════════
road_pts = [iso(-15000,-380),iso(22000,-380),iso(22000,380),iso(-15000,380)]
face(road_pts, (168,142,92))
for rx in range(-14000,21000,900):
    d.line([iso(rx,-320,2),iso(rx,320,2)], fill=(155,130,82), width=2)
# Wheel ruts
for ry in [-220, 220]:
    rut_pts = [iso(wx,ry,3) for wx in range(-14000,21000,180)]
    d.line(rut_pts, fill=(148,122,76), width=3)

# ══════════════════════════════════════════════════════════════════════════════
# FRONTIER BUILDINGS  (hw=420, hd=260, hh=920 — nearly touching, 80cm gaps)
# Centers: 900cm apart (gap = 900 - 420 - 420 = 60cm each side)
# Buildings face SOUTH (toward road), so cy = road_edge + hd = 380+260 = 640
# ══════════════════════════════════════════════════════════════════════════════
BY = 640   # building center Y (south face flush with road north edge)
BH = 920   # wall height
BHW = 420  # half-width
BHD = 260  # half-depth

buildings = [
    # name,    cx,    cy,  hw,  hd,   hh,  wall_top,         wall_e,          wall_n,        roof_slope,      roof_end,     roof_ph
    ("Saloon",  -1800, BY, BHW, BHD,  BH,  (188,142, 88),(148,108,64),(165,122,74),(125, 68,32),(100,52,24),  440),
    ("GS 002",  - 900, BY, BHW, BHD,  880, (148, 72, 65),(112, 54,48),(130, 62,56),( 95, 42,28),( 75,32,22),  420),
    ("GS 003",      0, BY, BHW, BHD,  900, ( 88,128, 78),( 65, 98,58),( 75,112,66),( 58, 88,42),( 45,68,32),  430),
    ("Bldg004",   900, BY, BHW, BHD,  870, (148,132, 88),(115,100,66),(130,115,76),(100, 88,52),( 80,68,40),  410),
    ("Saloon B", 1800, BY, BHW, BHD,  930, (178,148, 98),(138,112,72),(155,128,83),(118, 95,55),( 95,75,42),  445),
    ("GS Stone", 2700, BY, BHW, BHD,  880, (168,118, 72),(130, 90,54),(148,102,62),(110, 72,38),( 88,56,28),  420),
    ("Boarding", 3600, BY, BHW, BHD,  910, (188,152, 98),(145,116,74),(165,132,83),(125, 98,56),(100,78,44),  440),
    ("Sheriff",  4500, BY, BHW, BHD,  860, (168,132, 85),(130,100,62),(148,115,72),(110, 85,46),( 88,68,36),  410),
    ("Bandstand",5400, BY, BHW, BHD,  870, (158,128, 80),(122, 98,60),(138,112,68),(105, 82,44),( 85,65,34),  415),
]
# Sort: further back (higher cy) first — all same cy so sort by cx far east first
# Actually since they're the same cy we just draw them and handle occlusion via cx
# For this camera angle, higher cx = further away, so draw high cx first
buildings_sorted = sorted(buildings, key=lambda b: -b[1])

for name,cx,cy,hw,hd,hh,wt,we,wn,rs,re,rph in buildings_sorted:
    shadow(cx,cy, hw+400,hd+200, 55)
    box(cx,cy,0, hw,hd,hh, wt,we,wn)
    # Facade windows (front face = south, cy+hd)
    for woff in [-1,1]:
        wp = iso(cx+woff*int(hw*0.44), cy+hd, int(hh*0.55))
        d.rectangle([wp[0]-5,wp[1]-9,wp[0]+5,wp[1]+3], fill=(55,38,18))
    # Door center front
    dp = iso(cx, cy+hd, int(hh*0.2))
    d.rectangle([dp[0]-7,dp[1]-18,dp[0]+7,dp[1]+4], fill=(42,28,12))
    # Roof
    peaked_roof(cx,cy,hh, hw,hd,rph, rs,re)
    # Sign board below roofline
    sp = iso(cx, cy+hd, int(hh*0.88))
    d.rectangle([sp[0]-int(hw*SCALE*0.9),sp[1]-4,sp[0]+int(hw*SCALE*0.9),sp[1]+4],
                fill=tuple(max(0,c-20) for c in wt))

# Hitching posts (north side of road = cy = road edge)
for px in [-1500,-600,300,1200,2100,3000,3900]:
    p0=iso(px,380,0); p1=iso(px,380,360)
    d.line([p0,p1], fill=(108,78,38), width=5)
    d.line([iso(px-180,380,260),iso(px+180,380,260)], fill=(118,86,44), width=3)

# Barrels & crates at saloon
for bx in [-2200,-2050]:
    box(bx,500,0, 75,65,130, (155,110,52),(120,84,40),(136,96,45), ol=(25,16,4))
box(-1900,520,0, 110,90,95, (148,105,48),(112,80,36),(128,90,42), ol=(25,16,4))

# ══════════════════════════════════════════════════════════════════════════════
# WATER TOWER
# ══════════════════════════════════════════════════════════════════════════════
WT = (6500, 1000)
for lx,ly in [(-110,-110),(110,-110),(110,110),(-110,110)]:
    p0=iso(WT[0]+lx,WT[1]+ly,0); p1=iso(WT[0]+lx//2,WT[1]+ly//2,1500)
    d.line([p0,p1], fill=(110,80,40), width=5)
box(WT[0],WT[1],1500, 380,280,580, (148,108,58),(115,82,42),(128,92,48))
peaked_roof(WT[0],WT[1],2080, 380,280,300, (105,65,28),(80,48,20))

# ══════════════════════════════════════════════════════════════════════════════
# RAILROAD  (south of road, at y = -1400)
# ══════════════════════════════════════════════════════════════════════════════
TY = -1400
# Ballast
face([iso(-16000,TY-420),iso(23000,TY-420),iso(23000,TY+420),iso(-16000,TY+420)],
     (78,62,44))
# Ties — every 700cm, thick
for i in range(57):
    wx = -16000+i*680
    d.line([iso(wx,TY-380,5),iso(wx,TY+380,5)], fill=(88,65,38), width=8)
# Rails
for dy in [-265,265]:
    rpts = [iso(wx,TY+dy,28) for wx in range(-16000,23000,220)]
    d.line(rpts, fill=(162,145,118), width=4)

# ── STEAM LOCOMOTIVE (3× building width ≈ 2600cm long) ───────────────────────
LX = 1800  # center X of loco
# Main body
shadow(LX,TY, 1800,380, 70)
box(LX,TY,28, 1400,310,640, (65,82,112),(46,60,88),(55,70,100))
# Boiler top
box(LX-300,TY,668, 350,240,240, (75,92,122),(56,70,98),(65,80,110))
# Smokestack
box(LX-900,TY,640, 130,130,400, (48,48,48),(35,35,35),(42,42,42))
# Smoke puff
for si in range(4):
    sr = 80+si*40; sx,sy = iso(LX-900, TY, 1040+si*120)
    d.ellipse([sx-sr,sy-int(sr*0.45),sx+sr,sy+int(sr*0.45)],
              fill=tuple(int(c*(0.5+si*0.12)) for c in (155,148,140)))
# Cowcatcher
face([iso(LX+1400,TY-310,28),iso(LX+1600,TY-180,28),
      iso(LX+1600,TY+180,28),iso(LX+1400,TY+310,28),
      iso(LX+1400,TY+310,200),iso(LX+1400,TY-310,200)], (58,72,98),(25,28,40))
# Wheels
for wx_off in [-900,-400,100,600,1100]:
    wp = iso(LX+wx_off,TY+310,28)
    d.ellipse([wp[0]-14,wp[1]-7,wp[0]+14,wp[1]+7], fill=(28,28,28))
    wp2 = iso(LX+wx_off,TY-310,28)
    d.ellipse([wp2[0]-14,wp2[1]-7,wp2[0]+14,wp2[1]+7], fill=(28,28,28))

# ── WAGON/CAR behind loco ─────────────────────────────────────────────────────
WGX = LX - 3500
shadow(WGX,TY, 1100,320, 60)
box(WGX,TY,28, 1000,280,480, (92,78,52),(70,58,38),(80,66,44))
box(WGX,TY,508, 1000,280,70, (105,88,58),(80,66,44),(90,75,50))
for wx_off in [-700,-200,300,800]:
    wp = iso(WGX+wx_off,TY+280,28)
    d.ellipse([wp[0]-12,wp[1]-6,wp[0]+12,wp[1]+6], fill=(28,28,28))

# ══════════════════════════════════════════════════════════════════════════════
# MINING COMPLEX  (shorter structures, dark industrial)
# hh = 350-600 (vs building 920)
# ══════════════════════════════════════════════════════════════════════════════
mine = [
    # cx,     cy,   hw, hd,  hh,    top,            east,           north
    (10500, -2200, 380,280, 520, (68,60,54),(50,44,38),(58,50,44)),
    (11800, - 600, 480,340, 720, (75,65,58),(55,48,42),(64,56,48)),
    (13200, -2000, 420,300, 580, (65,58,52),(48,42,36),(56,50,44)),
    (14500, - 800, 460,330, 660, (72,62,56),(53,46,40),(62,53,46)),
    (15800, -1800, 400,290, 540, (62,55,50),(46,40,35),(54,47,42)),
    (17000, - 400, 440,320, 620, (70,60,54),(52,45,39),(60,52,46)),
    (18200, -1500, 380,270, 500, (60,54,48),(44,38,33),(52,46,40)),
    (10000,  1000, 320,240, 420, (58,52,46),(42,37,32),(50,44,38)),
    (12500,  1200, 360,260, 480, (65,57,50),(47,41,35),(55,48,42)),
    (16500,  1000, 340,250, 450, (62,55,49),(46,40,34),(53,46,41)),
]
for cx,cy,hw,hd,hh,tc,ec,nc in mine:
    shadow(cx,cy, hw+150,hd+100, 45)
    box(cx,cy,0, hw,hd,hh, tc,ec,nc, ol=(18,12,6))
    # Horizontal scaffolding bands
    for zh in [200,400]:
        if zh < hh*2:
            d.line([iso(cx-hw,cy-hd,zh),iso(cx+hw,cy-hd,zh)], fill=(32,28,22), width=2)

# Raised platforms connecting mine buildings
box(11200,-1400,0, 1600,450,125, (80,70,58),(62,54,44),(70,62,50))
box(14800,-1200,0, 1400,420,125, (78,68,56),(60,52,42),(68,60,48))
# Ore carts
for ox,oy in [(11000,-800),(12200,-900),(15500,-700)]:
    box(ox,oy,28, 200,150,200, (52,46,40),(38,33,28),(44,38,34))

# ══════════════════════════════════════════════════════════════════════════════
# SCRUBLAND mid-ground
# ══════════════════════════════════════════════════════════════════════════════
scrubs = [
    (-3500,5200,320,640,82),( 800,6000,300,600,78),(4500,5600,310,620,80),
    (8500,5000,290,580,76),(13000,5500,310,620,80),(-2000,7000,330,660,84),
    (3000,7800,300,600,78),(7000,6500,320,640,82),(11000,4800,280,560,74),
]
scrubs.sort(key=lambda s: -s[1])
for sx,sy,r,h,bg in scrubs:
    canopy_tree(sx,sy,280,r,h,bg)

# ══════════════════════════════════════════════════════════════════════════════
# LEGEND (top right matching reference)
# ══════════════════════════════════════════════════════════════════════════════
lx,ly = W-220,32
items = [((40,195,35),"Vegetation"),((175,80,75),"Building Store"),
         ((180,140,88),"Buildings"),((80,72,65),"Rocks"),
         ((65,80,115),"Vehicles"),((175,158,80),"Vehicles"),((140,90,50),"Rocks")]
d.rectangle([lx-8,ly-4,W-4,ly+len(items)*22+8], fill=(8,6,4))
d.rectangle([lx-8,ly-4,W-4,ly+len(items)*22+8], outline=(90,78,60))
for i,(col,name) in enumerate(items):
    y2=ly+4+i*22
    d.rectangle([lx,y2,lx+14,y2+14],fill=col,outline=(180,180,180))
    d.text((lx+20,y2+7),name,fill=(225,218,205),anchor="lm")

# ══════════════════════════════════════════════════════════════════════════════
# TITLE
# ══════════════════════════════════════════════════════════════════════════════
d.rectangle([0,0,W,44],fill=(0,0,0))
d.text((W//2,14),"WOLFE HALL — West Wall",fill=(255,215,75),anchor="mm")
d.text((W//2,30),"Round 2  ·  corrected proportions: buildings shoulder-to-shoulder, trees taller, mesas 10× height, train 3× building width",
       fill=(165,142,85),anchor="mm")

# Light smooth
img = img.filter(ImageFilter.SMOOTH_MORE)

out = "/home/user/SimWorld-Studio/docs/wolfe_hall_r2.png"
img.save(out,"PNG")
print(f"Saved: {out}")
