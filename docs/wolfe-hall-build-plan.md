# Wolfe Hall Build Plan

Step-by-step plan to set up the codebase and build the Wolfe Hall West Wall world in SimWorld Studio.

---

## Phase 0: Environment Setup

These steps get SimWorld Studio running and Claude connected to Unreal Engine.

### 0.1 Prerequisites

```
- Linux machine with GPU (8 GB+ VRAM recommended)
- Unreal Engine 5.3 installed (or SimWorld binary downloaded)
- Node.js 18+
- ANTHROPIC_API_KEY set
```

### 0.2 Download / Verify SimWorld Binary

```bash
# If using binary release:
wget <SimWorld-Studio-Minimal.tar.gz URL from HuggingFace>
tar xzf SimWorld-Studio-Minimal.tar.gz

# If from source (this repo):
cd simworld_studio_workspace/web
npm install
```

### 0.3 Set Asset Catalog to Full

The full asset catalog (including allow-AI map templates) is in `assets_full.json`.
Enable it before starting:

```bash
export SIMWORLD_ASSETS_FILE=assets_full.json
```

Or add this to your shell profile / `.env`.

### 0.4 Start SimWorld Studio

```bash
# One-command launch (binary):
simworld-studio start

# From source:
cd simworld_studio_workspace/web
node server/index.js
# In another terminal: open UE 5.3 project and enable PIE
```

Verify:
- Web UI accessible at `http://localhost:3002`
- UE viewport streaming in browser
- MCP server connected (check server logs for `MCP listening on :55557`)

---

## Phase 1: Load Base Map

**Goal:** Get the MiddleEast desert map loaded as the Wolfe Hall base.

### 1.1 In the SimWorld Chat UI

Prompt Claude:

```
Load the MiddleEast map as our base for Wolfe Hall. Use:
execute_python_script to run:
  unreal.EditorLoadingAndSavingUtils.load_map("/Game/MiddleEast/Maps/MiddleEast")
Then take a screenshot so we can see what we're starting with.
```

### 1.2 Save a Derivative Map

```
Save the loaded map as our working copy:
  unreal.EditorLoadingAndSavingUtils.save_map(
    unreal.EditorLevelLibrary.get_editor_world(),
    "/Game/_Runs/WolfeHall_v1"
  )
```

### 1.3 Verify Base State

- Take screenshot, confirm desert ground and sky are visible
- Note the world origin (0,0,0) and usable XY extent

---

## Phase 2: Atmosphere & Lighting

**Goal:** Set up the golden-hour West Wall lighting.

### 2.1 Apply Sunset Atmosphere

In chat:
```
Apply the weather_mood_skill to set a late-afternoon golden hour:
- Sun elevation ~20° (low, warm shadows)
- Atmospheric haze / light fog
- Warm orange ambient light
Take a screenshot after.
```

Reference: `skills/weather_mood_skill.md`

---

## Phase 3: Town Layout — Buildings

**Goal:** Place frontier town buildings along a main street.

### 3.1 Delete Existing Props (if any)

```
delete_all_spawned() to clear any auto-spawned actors from the base map load.
```

### 3.2 Spawn Town Buildings

Prompt Claude to spawn buildings in a line along the X axis (main street). Suggested layout:

```
Street runs along X axis, buildings face inward (Y direction)

North side (Y = +1500):
  Saloon:        BP_Building_03  at (0, 1500, 0)       yaw=180
  General Store: BP_Building_08  at (3000, 1500, 0)    yaw=180
  Sheriff:       BP_Building_12  at (6000, 1500, 0)    yaw=180

South side (Y = -1500):
  Barn:          BP_Building_22  at (1500, -1500, 0)   yaw=0
  Boarding House:BP_Building_31  at (4500, -1500, 0)   yaw=0
  Stables:       BP_Building_18  at (7500, -1500, 0)   yaw=0

Town end (water tower placeholder):
  WaterTower:    static Cylinder at (9000, 0, 0)       scale=(1,1,4)
```

Prompt:
```
Spawn the Wolfe Hall frontier town. Use spawn_blueprint_actor for each building.
Place them along a main street (X axis) with buildings facing each other across
a 3000cm wide road. Use BP_Building_03 for saloon, BP_Building_08 for general
store, BP_Building_12 for sheriff, BP_Building_22 for barn, BP_Building_31 for
boarding house. After spawning take a screenshot.
```

### 3.3 Adjust & Verify

- Take top-down screenshot (set camera to look straight down)
- Check buildings face the road, not each other's backs
- Adjust yaw if needed with `set_actor_transform`

---

## Phase 4: Street Furniture & Props

**Goal:** Dress the town with frontier props.

### 4.1 Saloon Area

```
In front of the Saloon (near 0, 800, 0):
  spawn_blueprint_actor("Barrel_1", "BP_Box", (−200, 800, 0))
  spawn_blueprint_actor("Barrel_2", "BP_Box", (200, 800, 0))
  spawn_blueprint_actor("Bench_Saloon", "BP_Bench", (0, 700, 0))
```

### 4.2 Road Hitching Posts

Use road blockers as hitching post stand-ins:
```
spawn_blueprint_actor("HitchPost_1", "BP_RoadBlocker", (500, 1200, 0), scale=(0.2, 0.2, 1.5))
spawn_blueprint_actor("HitchPost_2", "BP_RoadBlocker", (2500, 1200, 0), scale=(0.2, 0.2, 1.5))
```

### 4.3 Scatter Props

Crates, cans, trash near buildings' sides:
```
spawn_blueprint_actor("Crate_1", "BP_Box", (800, 1600, 0))
spawn_blueprint_actor("Can_1", "BP_Can", (4000, −1600, 0))
```

---

## Phase 5: Railroad

**Goal:** Lay railroad tracks at the town's south end with a small platform.

### 5.1 Discover TrainStation Assets

```
list_assets("/Game/TrainStation/")
```

Identify track segment and platform mesh paths.

### 5.2 Lay Track Segments

Spawn track segments end-to-end running east-west (Y axis) at south of town:

```python
# In execute_python_script:
track_mesh = "/Game/TrainStation/Meshes/SM_Track_01.SM_Track_01"
segment_length = 1000  # cm, adjust to actual mesh length
for i in range(20):
    unreal.EditorLevelLibrary.spawn_actor_from_object(
        unreal.load_asset(track_mesh),
        unreal.Vector(i * segment_length - 5000, -4000, 0),
        unreal.Rotator(0, 0, 0)
    )
```

### 5.3 Station Platform

```
Spawn platform planks or the station building asset from TrainStation pack
at (-2000, -4000, 0) facing the tracks.
```

---

## Phase 6: Lake

**Goal:** Create a lake west of town.

### 6.1 Water Plane

```python
# execute_python_script:
plane = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.StaticMeshActor, unreal.Vector(-8000, 0, -50)
)
plane.static_mesh_component.set_static_mesh(
    unreal.load_asset("/Engine/BasicShapes/Plane.Plane")
)
plane.set_actor_scale3d(unreal.Vector(50, 40, 1))  # 5000x4000 cm
# Apply water material if available
```

### 6.2 Lakeside Trees

Spawn 10–12 trees in a loose cluster around the lake perimeter:
```
BP_Tree3 and BP_Tree5 (denser canopy) at varying positions around (-8000, 0):
  circle of radius 3000–4500, scattered randomly
```

Prompt Claude:
```
Spawn 12 trees around the lake centered at (-8000, 0, 0). Use BP_Tree3 and
BP_Tree5 alternating, placed in a rough circle with radius 3000-4500, with
natural spacing variation. Avoid placing trees in the water center.
```

### 6.3 Wooden Dock

Two plank-shaped box meshes extending into the lake:
```
spawn_actor("Dock_1", "/Engine/BasicShapes/Cube", (-6200, 200, -30), scale=(5,1,0.1))
spawn_actor("Dock_2", "/Engine/BasicShapes/Cube", (-6200, -200, -30), scale=(5,1,0.1))
```

---

## Phase 7: Red Rock Formations

**Goal:** Place dramatic mesa / butte formations in the background.

### 7.1 Discover Rock Meshes

```
list_assets("/Game/MiddleEast/")
list_assets("/Game/ModularSciFi/")
```

Look for rock, cliff, or boulder static mesh assets.

### 7.2 Place Background Rocks

Spawn large rock meshes in a semicircle behind (north of) the town, at elevated Z:

```python
import math
rocks = [
    # (x, y, z, scale, yaw)
    (-3000, 12000, 2000, 8, 0),
    (0,     14000, 3000, 12, 30),
    (4000,  13000, 2500, 10, -20),
    (8000,  12000, 1800, 7, 45),
    (11000, 10000, 2000, 9, 15),
]
for i, (x, y, z, s, yaw) in enumerate(rocks):
    # spawn rock mesh actor at position
    pass
```

Prompt Claude:
```
Spawn 5 large rock formation static meshes from the MiddleEast pack in a
background arc behind the town (Y > 10000). Scale them 7–12× to create
mesa-sized formations. Stagger their Z height (2000–4000) to simulate
cliff elevation. Use any SM_Rock or SM_Cliff mesh found in /Game/MiddleEast/.
```

---

## Phase 8: Verification & Refinement

### 8.1 Full Scene Screenshot

```
Take a screenshot from a cinematic angle: camera positioned at (5000, -8000, 3000)
looking toward the town with the red rocks visible in background.
```

### 8.2 Collision Check

```
check_collisions()
```

Fix any overlapping actors with `set_actor_transform`.

### 8.3 Scene Save

```
Save scene to SimWorld scenes catalog via the UI "Save Scene" button,
or via the API: POST /api/scenes with the current actor list.
```

---

## Phase 9: Agent Scenarios (Optional)

Once the world is built and verified:

### 9.1 Spawn Agents

```
spawn_agent("Cowboy_1", "Humanoid", (0, 0, 0))
spawn_agent("Cowboy_2", "Pedestrian", (3000, 0, 0))
```

### 9.2 Town Patrol Task

```
agent_action("Cowboy_1", "MOVE_FORWARD") -- walk the main street
```

### 9.3 Navigation Episode

Use nav_task module to generate a PointNav episode from saloon to train station:
```bash
python -m nav_task --scene wolfe_hall --start saloon --goal train_station
```

---

## Prompt Sequence (Quick Reference)

Copy these prompts into the SimWorld chat in order:

1. `"Load the MiddleEast map: execute_python_script to call load_map('/Game/MiddleEast/Maps/MiddleEast'), then save as /Game/_Runs/WolfeHall_v1"`
2. `"Set up sunset atmosphere: low sun (20°), warm orange ambient, light haze. Use weather_mood_skill."`
3. `"Spawn the Wolfe Hall frontier town: 6 buildings along a main street (X axis), 3000cm road width, buildings facing inward. Use BP_Building_03, 08, 12, 22, 31, 18. Take a screenshot after."`
4. `"Dress the saloon area with 2 barrels (BP_Box), 1 bench (BP_Bench), and 2 hitching posts (scaled BP_RoadBlocker). Add scattered crates and cans near other buildings."`
5. `"List assets in /Game/TrainStation/ then lay 20 railroad track segments east-west at Y=-4000 and spawn a station platform."`
6. `"Create a lake west of town: large plane mesh at (-8000, 0, -50) scaled 50×40, water material if available. Surround with 12 trees (BP_Tree3, BP_Tree5) in a loose circle."`
7. `"Find rock/cliff meshes in /Game/MiddleEast/ or /Game/ModularSciFi/ and spawn 5 large formations (scale 7-12×) in an arc north of town at elevated Z to create mesa backdrop."`
8. `"Take a cinematic screenshot: camera at (5000, -8000, 3000) looking at the town with rocks in background. Then run check_collisions() and fix any overlaps."`

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Map not found | Verify MiddleEast pack is installed at `/Game/MiddleEast/` |
| Buildings clip through ground | Set Z=0 and check if map has elevated terrain; adjust Z per building |
| Water plane looks black | Try applying `/Game/Water/M_Water_Ocean` or find material in MiddleEast pack |
| Rocks not visible | Increase scale; check if Z offset is needed to bring them above terrain |
| TrainStation assets not found | Verify pack installed; check actual mesh path with `list_assets` |
| Claude can't connect to UE | Confirm MCP server on :55557 and UE is in PIE mode |
