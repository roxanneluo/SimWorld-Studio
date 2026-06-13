# Wolfe Hall — West Wall World: Design Document

## Vision

Wolfe Hall is a Wild West frontier world set in the American Southwest. The world features red rock mesa formations rising behind a small working town, a lake fed by a canyon river, and railroad tracks cutting through the landscape. The aesthetic is warm, dusty, and sun-drenched — the kind of world where a lone cowboy rides past a saloon at dusk and a steam locomotive rolls toward the horizon.

This document describes how to build Wolfe Hall inside **SimWorld Studio** using its AI-native scene generation pipeline.

---

## World Layout

```
                    [Red Rock Mesa Ridge]
                   /                     \
     [Canyon/River]                   [Rock Formations]
           |                                  |
      [Lake Shore]   ← → ← → ← → ← → [Frontier Town]
           |          (main dusty road)       |
      [Dock/Pier]                      [Saloon / General Store]
                                       [Sheriff / Barn]
                                       [Water Tower]
                                              |
                        [Railroad Tracks → → → → → → ]
                                       [Small Train Station]
```

The world is organized in three zones:

| Zone | Contents | Atmosphere |
|---|---|---|
| **Wilderness** | Red rock buttes, sparse cacti, dry scrubland | Harsh, vast, windswept |
| **Lakeside** | Calm water, willow-like trees, sandy shore | Serene contrast |
| **Town** | Saloon, general store, sheriff office, barn, water tower, train station | Lived-in, dusty, frontier |

---

## Map Template

**Best fit:** `Village (Slavic, Day)` — `/Game/Village/Maps/Village`

The Slavic Village day map provides:
- A modular small-town layout with low-rise buildings on a dirt road
- Rolling landscape that can serve as a base for rock formations (via spawned meshes)
- Warm daytime lighting that maps well to a desert sun

**Alternative:** `MiddleEast` — `/Game/MiddleEast/Maps/MiddleEast`
- Desert/arid terrain out of the box
- Sandy palette, narrow village streets, open sky
- Requires more actor replacement but less terrain work

**Recommended approach:** Load `MiddleEast` as the base (gives the desert ground and sky for free), then overlay SimWorld's building blueprints and spawned static meshes to reshape the town into a Western frontier aesthetic.

---

## Scene Composition

### 1. Ground & Sky Environment

Call `setup_environment()` first for sun/sky/fog, then:

- **Sun angle:** Low azimuth (15–25°) for golden-hour warmth
- **Sky color:** Deep blue with orange-tinted horizon
- **Fog:** Light atmospheric haze — adds depth to mesa distance
- **Ground:** Desert sand / red earth material (from MiddleEast pack)

### 2. Red Rock Formations

Spawn large rock static meshes from the MiddleEast or ModularSciFi packs placed in the background at high elevation. Arrange them in a semicircle behind the town as a dramatic backdrop.

- Use `execute_python_script` to batch-spawn rock meshes at Z offsets to simulate height
- Scale up 3–5× for mesa-sized formations
- Apply reddish-orange color tint if material overrides are available

### 3. Frontier Town Buildings

Use SimWorld's `BP_Building_` catalog. Best building IDs for Western feel:

| Role | Blueprint IDs (candidates) | Notes |
|---|---|---|
| Saloon / Main building | BP_Building_01–05 | Small, wide, flat-front facade |
| General store | BP_Building_06–10 | Boxy, one-story |
| Sheriff's office | BP_Building_11–15 | Compact, corner placement |
| Barn | BP_Building_20–25 | Larger footprint |
| Boarding house | BP_Building_30–35 | Two-story if available |

Buildings should line a single main street (the "dusty road") with ~200 cm gaps between them and facing inward toward the road.

### 4. Town Props (Street Furniture)

From the existing `street_furniture` catalog:
- **Barrels / wooden crates** — `BP_Box` variants in front of stores
- **Road blockers** as hitching posts
- **Benches** outside the saloon
- **Trash / cans** for alley scatter

Additional UE Python spawns from MiddleEast/Village packs:
- Hay bales (static meshes from Village pack)
- Water trough (manually placed primitive or Village asset)
- Lanterns / torches

### 5. Water Tower

Use `spawn_actor` with a cylinder static mesh (tall, narrow) + a box on top, grouped manually. Alternatively, if BP_Building contains a tower variant, use that. Place at the town's edge near the railroad.

### 6. Railroad

Use `TrainStation` pack assets (Victorian industrial, licensed allow-AI):
- `/Game/TrainStation/` — track segments, platform planks, station building
- Lay track segments in a straight line at the town's southern edge
- Place a small platform / shelter as the "Wolfe Hall Station"
- Optional: spawn a static locomotive mesh at the platform

### 7. Lake

Place a large `Plane` static mesh scaled to lake dimensions, with a water material applied via Python (`set_material`). Position it west of town, with trees (BP_Tree1–6) clustered around the shore.

- Lake dimensions: ~5000 × 4000 cm
- Add 8–12 trees around the perimeter
- One or two wooden dock planks extending into the water (box meshes)

### 8. Vegetation

- **Sparse scrub / cacti** — use MiddleEast or ModularSciFi pack vegetation assets scattered across the wilderness zone
- **Lakeside trees** — BP_Tree1 through BP_Tree6 clustered at the water edge
- **No dense forest** — keep it open and arid in the wilderness zone

---

## Lighting & Atmosphere

| Setting | Value | Rationale |
|---|---|---|
| Time of day | Late afternoon / golden hour | Warm, dramatic shadows |
| Sun elevation | ~20° above horizon | Long shadows, cinematic |
| Sky saturation | High | Deep blue contrast vs warm rocks |
| Fog density | Low-medium | Haze in distance for depth |
| Ambient light | Warm orange tint | Southwest desert warmth |

Use the `weather_mood_skill.md` as a base — it sets sunset lighting and atmosphere, which is close to the target feel.

---

## Agent Scenarios

Wolfe Hall is built as a testbed world. Suggested agent scenarios:

| Scenario | Agents | Goal |
|---|---|---|
| **Town patrol** | 1–2 pedestrian agents | Navigate main street end-to-end without collision |
| **Saloon to station** | 1 agent | PointNav from saloon to train platform |
| **Lake trail** | 1 agent | Follow lakeside path, avoid water |
| **Crowd scene** | 4–6 agents | Multi-agent coexistence on main street |

---

## Asset Checklist

- [ ] Map base: MiddleEast or Village (day)
- [ ] Rock formations: MiddleEast static meshes or ModularSciFi rocks
- [ ] Town buildings: BP_Building_01–35 (subset)
- [ ] Street props: BP_Box, BP_Bench, road blockers, cans
- [ ] Railroad: TrainStation pack (track segments + platform)
- [ ] Trees: BP_Tree1–6
- [ ] Water plane: Static plane + water material
- [ ] Lighting: sunset atmosphere (weather_mood_skill)
- [ ] Agents: Pedestrian_1 (or Humanoid) × 2–4

---

## Constraints & Notes

- The SimWorld city building catalog (`BP_Building_*`) uses a modern/urban aesthetic — buildings will need to be selected and arranged to approximate frontier architecture (low, boxy, flat-front). There are no dedicated Western-themed building blueprints in the current catalog.
- Red rock terrain requires either the MiddleEast pack's landscape geometry or manual placement of large rock static meshes. No dedicated Southwest landscape pack is in the current allow-AI catalog.
- A steam locomotive static mesh is not confirmed in the asset catalog; a static placeholder (large box + cylinder) can substitute until the TrainStation pack's props are verified.
- All spawned actor names should be unique per session (the server auto-appends `_SID`).
