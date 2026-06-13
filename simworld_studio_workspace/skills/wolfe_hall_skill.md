---
id: "wolfe_hall_skill"
name: "Wolfe Hall West Wall"
version: "1.0.0"
author: "custom"
tags: ["custom", "world", "western", "frontier", "desert"]
dependencies: []
description: "Build the Wolfe Hall West Wall world: a Wild West frontier town with red rock mesa backdrop, dusty main street, lake, and railroad."
---

## Wolfe Hall West Wall

### When To Use
Use this skill when the user asks to build "Wolfe Hall", a "West Wall world", a "Western frontier scene", or a "Wild West town with red rocks, lake, and railroad."

### Execution Policy
Follow the phases below in order. Call `take_screenshot()` after each major phase so the user can see progress. Do NOT skip `setup_environment()` — the scene will be black without it.

---

### Phase 0 — Clear & Environment

```
delete_all_spawned()
setup_environment()
```

After setup_environment, execute this Python to set golden-hour lighting:

```python
import unreal

# Set sun angle for late-afternoon warmth
sky_light = unreal.EditorLevelLibrary.get_all_level_actors_of_class(unreal.DirectionalLight)
if sky_light:
    sl = sky_light[0]
    sl.set_actor_rotation(unreal.Rotator(-20, 45, 0), False)

# Set atmospheric fog / exponential height fog for haze
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    if "ExponentialHeightFog" in actor.get_class().get_name():
        fog_comp = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
        if fog_comp:
            fog_comp.set_editor_property("fog_density", 0.03)
            fog_comp.set_editor_property("fog_inscattering_color", unreal.LinearColor(0.9, 0.6, 0.3, 1.0))
```

Take screenshot and show user the base lighting.

---

### Phase 1 — Frontier Town Buildings

Spawn 6 buildings along the X axis forming a main street. Buildings face inward across a 3000 cm wide road (Y = ±1500).

**North side of road (Y = +1500, yaw = 180 so facade faces south toward road):**

```
spawn_blueprint_actor("Saloon",        "BP_Building_03", location=[0,    1500, 0], rotation=[0, 180, 0])
spawn_blueprint_actor("GeneralStore",  "BP_Building_08", location=[3500, 1500, 0], rotation=[0, 180, 0])
spawn_blueprint_actor("SheriffOffice", "BP_Building_12", location=[7000, 1500, 0], rotation=[0, 180, 0])
```

**South side of road (Y = -1500, yaw = 0 so facade faces north toward road):**

```
spawn_blueprint_actor("Barn",          "BP_Building_22", location=[1800, -1500, 0], rotation=[0, 0, 0])
spawn_blueprint_actor("BoardingHouse", "BP_Building_31", location=[5000, -1500, 0], rotation=[0, 0, 0])
spawn_blueprint_actor("Stables",       "BP_Building_18", location=[8200, -1500, 0], rotation=[0, 0, 0])
```

Take screenshot. Verify buildings face the road (not each other's backs). If yaw is wrong, correct with set_actor_transform.

---

### Phase 2 — Street Furniture & Props

Place frontier-style props to dress the town:

**In front of Saloon (around [0, 700, 0]):**
```
spawn_blueprint_actor("Barrel_L",     "BP_Box",         location=[-250,  800, 0])
spawn_blueprint_actor("Barrel_R",     "BP_Box",         location=[ 250,  800, 0])
spawn_blueprint_actor("Bench_Saloon", "BP_Bench",       location=[  0,   700, 0])
```

**Hitching posts (scaled road blockers):**
```
spawn_blueprint_actor("HitchPost_1",  "BP_RoadBlocker", location=[ 600,  1100, 0], scale=[0.15, 0.15, 1.8])
spawn_blueprint_actor("HitchPost_2",  "BP_RoadBlocker", location=[2800,  1100, 0], scale=[0.15, 0.15, 1.8])
spawn_blueprint_actor("HitchPost_3",  "BP_RoadBlocker", location=[6000,  1100, 0], scale=[0.15, 0.15, 1.8])
```

**Scatter crates and cans near other buildings:**
```
spawn_blueprint_actor("Crate_1",    "BP_Box2",    location=[ 900,  1700, 0])
spawn_blueprint_actor("Crate_2",    "BP_Box3",    location=[4000, -1800, 0])
spawn_blueprint_actor("TrashCan_1", "BP_Trash_can", location=[3200,  1600, 0])
spawn_blueprint_actor("Can_1",      "BP_Can",     location=[7500, -1700, 0])
```

**Water tower (north-east edge of town):**
```python
import unreal

# Spawn cylinder as tower shaft
tower_base = unreal.EditorLevelLibrary.spawn_actor_from_object(
    unreal.load_asset("/Engine/BasicShapes/Cylinder.Cylinder"),
    unreal.Vector(10000, 0, 0)
)
tower_base.set_actor_scale3d(unreal.Vector(1.5, 1.5, 6))
tower_base.set_actor_label("WaterTower_Shaft")

# Tank on top
tank = unreal.EditorLevelLibrary.spawn_actor_from_object(
    unreal.load_asset("/Engine/BasicShapes/Cylinder.Cylinder"),
    unreal.Vector(10000, 0, 900)
)
tank.set_actor_scale3d(unreal.Vector(3, 3, 2))
tank.set_actor_label("WaterTower_Tank")
```

Take screenshot.

---

### Phase 3 — Railroad

First discover what track assets are available:
```
list_assets("/Game/TrainStation/")
```

Then lay track segments east-west along Y = -4500 (south of town):

```python
import unreal

# Find a track mesh — try common names
track_candidates = [
    "/Game/TrainStation/Meshes/SM_Track_Straight",
    "/Game/TrainStation/Meshes/SM_Rail",
    "/Game/TrainStation/StaticMeshes/SM_Track",
]
track_asset = None
for path in track_candidates:
    try:
        track_asset = unreal.load_asset(path)
        if track_asset:
            break
    except:
        pass

if track_asset:
    segment_length = 1000  # adjust if needed after first placement
    for i in range(18):
        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(
            track_asset,
            unreal.Vector(-1000 + i * segment_length, -4500, 0)
        )
        if actor:
            actor.set_actor_label(f"Track_{i:02d}")
else:
    # Fallback: simple plank tracks with box meshes
    for i in range(10):
        rail_l = unreal.EditorLevelLibrary.spawn_actor_from_object(
            unreal.load_asset("/Engine/BasicShapes/Cube.Cube"),
            unreal.Vector(-2000 + i * 1000, -4350, 0)
        )
        if rail_l:
            rail_l.set_actor_scale3d(unreal.Vector(10, 0.3, 0.3))
            rail_l.set_actor_label(f"RailLeft_{i}")
        rail_r = unreal.EditorLevelLibrary.spawn_actor_from_object(
            unreal.load_asset("/Engine/BasicShapes/Cube.Cube"),
            unreal.Vector(-2000 + i * 1000, -4650, 0)
        )
        if rail_r:
            rail_r.set_actor_scale3d(unreal.Vector(10, 0.3, 0.3))
            rail_r.set_actor_label(f"RailRight_{i}")
```

**Station platform near town:**
```python
platform = unreal.EditorLevelLibrary.spawn_actor_from_object(
    unreal.load_asset("/Engine/BasicShapes/Cube.Cube"),
    unreal.Vector(2000, -4200, 50)
)
if platform:
    platform.set_actor_scale3d(unreal.Vector(30, 8, 1.5))
    platform.set_actor_label("StationPlatform")
```

Also spawn the TrainStation building if available:
```
list_assets("/Game/TrainStation/Blueprints/")
# If found, spawn_blueprint_actor("TrainStation", "<found_id>", location=[2000, -4800, 0])
```

Take screenshot.

---

### Phase 4 — Lake (West of Town)

```python
import unreal

# Water surface plane
lake = unreal.EditorLevelLibrary.spawn_actor_from_object(
    unreal.load_asset("/Engine/BasicShapes/Plane.Plane"),
    unreal.Vector(-8000, 0, -80)
)
if lake:
    lake.set_actor_scale3d(unreal.Vector(50, 40, 1))
    lake.set_actor_label("Lake_Surface")
    # Try to apply a water material from MiddleEast or engine
    water_mat_paths = [
        "/Game/MiddleEast/Materials/M_Water",
        "/Game/Water/M_LakeWater",
        "/Engine/MapTemplates/Materials/BasicAsset03",
    ]
    for mat_path in water_mat_paths:
        try:
            mat = unreal.load_asset(mat_path)
            if mat:
                lake.static_mesh_component.set_material(0, mat)
                break
        except:
            pass

# Wooden dock planks
dock1 = unreal.EditorLevelLibrary.spawn_actor_from_object(
    unreal.load_asset("/Engine/BasicShapes/Cube.Cube"),
    unreal.Vector(-5500, 300, -60)
)
if dock1:
    dock1.set_actor_scale3d(unreal.Vector(18, 2.5, 0.4))
    dock1.set_actor_label("Dock_1")

dock2 = unreal.EditorLevelLibrary.spawn_actor_from_object(
    unreal.load_asset("/Engine/BasicShapes/Cube.Cube"),
    unreal.Vector(-5500, -300, -60)
)
if dock2:
    dock2.set_actor_scale3d(unreal.Vector(18, 2.5, 0.4))
    dock2.set_actor_label("Dock_2")
```

**Lakeside trees — loose circle around lake perimeter:**
```
spawn_blueprint_actor("LakeTree_1",  "BP_Tree3", location=[-6000,  3000,  0])
spawn_blueprint_actor("LakeTree_2",  "BP_Tree5", location=[-9000,  2500,  0])
spawn_blueprint_actor("LakeTree_3",  "BP_Tree3", location=[-11000,  500,  0])
spawn_blueprint_actor("LakeTree_4",  "BP_Tree5", location=[-11000, -1500, 0])
spawn_blueprint_actor("LakeTree_5",  "BP_Tree3", location=[-9500, -3000,  0])
spawn_blueprint_actor("LakeTree_6",  "BP_Tree5", location=[-7000, -3200,  0])
spawn_blueprint_actor("LakeTree_7",  "BP_Tree1", location=[-5200, -1800,  0])
spawn_blueprint_actor("LakeTree_8",  "BP_Tree2", location=[-5000,  1500,  0])
spawn_blueprint_actor("LakeTree_9",  "BP_Tree4", location=[-7500,  3500,  0])
spawn_blueprint_actor("LakeTree_10", "BP_Tree6", location=[-10000, 3200,  0])
```

Take screenshot.

---

### Phase 5 — Red Rock Mesa Formations (Background)

First discover rock meshes:
```
list_assets("/Game/MiddleEast/")
list_assets("/Game/ModularSciFi/")
```

Then spawn 5–7 large rock formations in a background arc north of the town (Y > 10000), elevated on Z:

```python
import unreal

# Try common rock mesh paths from MiddleEast / ModularSciFi packs
rock_candidates = [
    "/Game/MiddleEast/StaticMeshes/SM_Rock",
    "/Game/MiddleEast/Meshes/SM_Rock_Large",
    "/Game/MiddleEast/Meshes/SM_Cliff",
    "/Game/ModularSciFi/Meshes/SM_Rock",
    "/Game/Cave/StaticMeshes/SM_Rock",
]

rock_asset = None
for path in rock_candidates:
    try:
        a = unreal.load_asset(path)
        if a:
            rock_asset = a
            print(f"Found rock mesh at: {path}")
            break
    except:
        pass

formations = [
    # (x,       y,     z,    sx,  sy, sz,  yaw)
    (-3000,  13000, 1500,  10,  10, 14,   0),
    ( 1000,  15000, 2500,  14,  12, 18,  30),
    ( 5000,  14000, 2000,  12,  10, 16, -20),
    ( 9000,  12500, 1800,   9,   9, 12,  45),
    (12000,  11000, 2200,  11,   8, 15,  15),
    (-6000,  12000, 1200,   8,   8, 10, -30),
    ( 3000,  16000, 3000,  16,  13, 20,  10),
]

for i, (x, y, z, sx, sy, sz, yaw) in enumerate(formations):
    if rock_asset:
        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(
            rock_asset, unreal.Vector(x, y, z)
        )
    else:
        # Fallback: use large box to approximate mesa silhouette
        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(
            unreal.load_asset("/Engine/BasicShapes/Cube.Cube"),
            unreal.Vector(x, y, z)
        )
    if actor:
        actor.set_actor_scale3d(unreal.Vector(sx, sy, sz))
        actor.set_actor_rotation(unreal.Rotator(0, yaw, 0), False)
        actor.set_actor_label(f"Mesa_{i+1}")
        # Try to apply a reddish sandstone material
        red_mat_paths = [
            "/Game/MiddleEast/Materials/M_Sandstone",
            "/Game/MiddleEast/Materials/M_Rock",
            "/Game/Cave/Materials/M_Rock",
        ]
        for mat_path in red_mat_paths:
            try:
                mat = unreal.load_asset(mat_path)
                if mat:
                    for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
                        comp.set_material(0, mat)
                    break
            except:
                pass
```

Take screenshot.

---

### Phase 6 — Scrubland Vegetation (Wilderness Zone)

Scatter sparse trees and low vegetation between town and mesa backdrop:

```
spawn_blueprint_actor("Scrub_1",  "BP_Tree1", location=[-1500,  5000, 0], scale=[0.6, 0.6, 0.6])
spawn_blueprint_actor("Scrub_2",  "BP_Tree2", location=[ 3000,  6000, 0], scale=[0.5, 0.5, 0.5])
spawn_blueprint_actor("Scrub_3",  "BP_Tree4", location=[ 7000,  5500, 0], scale=[0.7, 0.7, 0.7])
spawn_blueprint_actor("Scrub_4",  "BP_Tree1", location=[12000,  5000, 0], scale=[0.5, 0.5, 0.5])
spawn_blueprint_actor("Scrub_5",  "BP_Tree6", location=[-3000,  7500, 0], scale=[0.6, 0.6, 0.6])
spawn_blueprint_actor("Scrub_6",  "BP_Tree2", location=[ 5500,  8000, 0], scale=[0.4, 0.4, 0.4])
```

---

### Phase 7 — Final Screenshot & Save

Take a cinematic screenshot from an angle that shows the whole world:

```python
import unreal
# Position camera: south-east, elevated, looking northwest toward town + mesas
unreal.EditorLevelLibrary.set_level_viewport_camera_info(
    unreal.CameraTransform(
        location=unreal.Vector(15000, -8000, 4000),
        rotation=unreal.Rotator(-15, 140, 0)
    )
)
```

Then:
```
take_screenshot()
check_collisions()
```

Fix any overlapping actors with set_actor_transform, then take a final screenshot.

---

### Spawn Layout Reference

```
                [Mesa_6]  [Mesa_1]  [Mesa_2]  [Mesa_7]  [Mesa_3]  [Mesa_4]  [Mesa_5]
                          ← ← ← ← RED ROCK BACKDROP ← ← ← ←

  [LakeTree_10]                 [Scrub_5]        [Scrub_2]       [Scrub_3]
[LakeTree_9]                               [Scrub_1]    [Scrub_6]     [Scrub_4]
[LakeTree_3]                                                                   [Scrub_7]
[LakeTree_2]   LAKE        Saloon | GeneralStore | SheriffOffice
[LakeTree_1]  [Dock_1]    ══════════ MAIN STREET ══════════════
[LakeTree_8]  [Dock_2]     Barn   | BoardingHouse | Stables   [WaterTower]
[LakeTree_7]
[LakeTree_4]
[LakeTree_5]
[LakeTree_6]
                          ══════════ RAILROAD TRACKS ══════════════
                                   [Station Platform]
```

### Notes
- All units in Unreal centimeters (1 m = 100 cm)
- If a BP_Building_* ID produces an unsuitable result, substitute nearby IDs (±2-3) to find a better fit
- The lake water material depends on pack availability; a blue tinted plane is a functional fallback
- Mesa formations use fallback box meshes if no rock mesh is found — replace with discovered asset paths after running list_assets
