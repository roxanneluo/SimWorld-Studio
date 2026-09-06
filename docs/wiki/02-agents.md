# 02 — Agents: The Concept Map

> **The single most important fact about this codebase:** the word *agent* means
> four unrelated things, and they appear side by side in the same directory.
> `web/server/agents.js` and `web/server/agent-controller.js` are about
> **completely different** kinds of agent. Get this straight first and the rest
> of the code stops being confusing.

## 0. Disambiguation

| # | Kind | Lives in | Defined by | Is it an LLM? | Is it in the 3D world? |
|---|---|---|---|---|---|
| 1 | **Embodied actor** | Unreal Engine | `agent-registry.json` | No — a Blueprint | Yes |
| 2 | **Panel agent** (`AgentSession`) | Node server | `agent-controller.js` | Yes — a Claude subprocess | Drives a #1 |
| 3 | **Gym agent** | Python | `gym_env/` + `llm/` | Yes — any `LLMClient` | Drives a #1 |
| 4 | **Coding agent** | Node server | `coding-agents.json` + runners | Yes — a CLI subprocess | No — it *builds* the world |

Two more are compositions of the above:

| # | Kind | Lives in | What it is |
|---|---|---|---|
| 5 | **Arena contestant** | `agents.js` | A named (backend, model) pair entered into a head-to-head scene-building battle |
| 6 | **Co-evolution pair** | `co_evolve/` | A #4 designing scenes adversarially against a #3 navigating them, refereed by a difficulty teacher |

A useful mental model:

```
        #4 coding agent  ─── builds ───►  the scene
                                            │
                                            │ contains
                                            ▼
                                     #1 embodied actor
                                            ▲
                                            │ controls
                            ┌───────────────┴───────────────┐
                    #2 panel agent                    #3 gym agent
                (interactive, in the UI)        (batch, reproducible, scored)
```

---

## 1. Kind #1 — The embodied actor

**What it is:** a spawned Unreal Engine Blueprint that can be moved and queried.
It has no intelligence of its own. It exposes Blueprint functions; something else
decides when to call them.

### Definition — `web/server/agent-registry.json`

This one JSON file is the source of truth for every agent type in the system. Both
the MCP tool server and the agent controller read it at startup:

```js
// web/server/agent-controller.js:12
const REGISTRY = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'agent-registry.json'), 'utf-8'));
```

An agent type has this shape:

```jsonc
"humanoid": {
  "blueprintPath": "/Game/TrafficSystem/Pedestrian/Base_User_Agent.Base_User_Agent_C",
  "description":   "Robot/humanoid agent with full animation and interaction set",
  "spawnZ":        110,              // ground-level spawn height, cm
  "stopCmd":       "StopAgent",      // BP function that halts it
  "rotateCmd":     "TurnAround",     // BP function that rotates it
  "namePatterns":  ["humanoid", "user_agent", "robot"],   // class-name → type inference
  "actions": {
    "move_forward": { "cmd": "MoveForward", "description": "Start walking forward" },
    "step_forward": { "cmd": "StepForward", "params": ["duration", "direction"],
                      "defaults": [2, 0],
                      "description": "Walk forward for N seconds (direction: 0=fwd, 1=back)" },
    "set_speed":    { "cmd": "SetMaxSpeed", "params": ["speed"],
                      "description": "Set movement speed (100=slow, 200=normal, 400=run)" },
    "pick_up":      { "cmd": "PickUp", "params": ["target"], "description": "Pick up an object by name" }
    // … 18 actions total for humanoid
  }
}
```

### The four shipped types

| Type | Blueprint | spawnZ | Actions | Notes |
|---|---|---|---|---|
| `humanoid` | `Base_User_Agent` | 110 | 18 | Full set: locomotion, sit/stand, pick up/drop, enter/exit vehicle, scooter, gestures, social animations |
| `pedestrian` | `Base_Pedestrian` | 110 | 3 | Crowd NPC — move, stop, set speed |
| `dog` | `/Game/Robot/Dog` | 50 | 3 | Quadruped; `Move_Speed(speed, duration, direction)`, look up/down |
| `scooter` | `BP_Scooter_Pawn` | 0 | 1 | Vehicle; `SetState(throttle, brake, steering)` |

### How an action becomes a UE command

`agent_action` is generic. It looks the action up in the registry, positionally fills
parameters from `params` (falling back to `defaults`), and emits a UnrealCV Blueprint
call (`web/server/mcp-server.js:451`):

```js
let cmdStr = `vbp ${agent_name} ${actionDef.cmd}`;
if (actionDef.params) {
  for (let i = 0; i < actionDef.params.length; i++) {
    const val = params[actionDef.params[i]] ?? defaults[i] ?? "";
    cmdStr += ` ${val}`;
  }
}
```

So `agent_action(agent_name="Robot_1", action="set_speed", params:{speed:400})`
becomes the wire command `vbp Robot_1 SetMaxSpeed 400`.

An unknown action is not a hard failure — the handler returns the list of valid ones,
which is why the MCP tool description tells the model *"call with an invalid action to
see available ones."* That's a deliberate self-describing-API trick.

`agent_rotate` is special-cased because the Blueprint's signature is unusual: the
direction is encoded **twice**, in the sign of the angle and in a trailing ±1:

```js
const dir = direction === "right" ? 1 : -1;
const a   = direction === "right" ? angle : -angle;
await ucvCommandRetry(`vbp ${agent_name} ${rotCmd} 1 ${a} ${dir}`);
```

`gym_env/action_space.py:11-18` documents the same quirk from the Python side, and
notes that `nav_task`'s own command template gets it wrong.

### Spawning

`spawn_agent` (`mcp-server.js:408`) requires PIE (Play-In-Editor) and is defensive
about a known UE behaviour — spawning can reset the UnrealCV socket:

```js
await ensurePIE();
try { await ucvCommand(`vset /objects/spawn_bp_asset ${bp} ${agent_name}`, 15000); }
catch (e) { /* spawn often resets connection, that's OK */ }
await new Promise(r => setTimeout(r, 3000));      // let UE finish loading the character
await ucvCommandRetry(`vset /object/${agent_name}/location ${x} ${y} ${z}`);
await ucvCommandRetry(`vset /object/${agent_name}/rotation ${p} ${y} ${r}`);
await ucvCommandRetry(`vset /object/${agent_name}/collision true`);
await ucvCommandRetry(`vset /object/${agent_name}/object_mobility true`);
```

It returns `available_actions` so the caller immediately knows what the thing can do.

### Discovery and classification

Agents don't have to be spawned by you. The server polls `vget /objects` every 5 s in
PIE and auto-registers pawn-like actors. `classifyPatterns` in the registry decides
what an unknown actor is, by regex on its name:

```jsonc
{ "regex": "^BP_Scooter_",  "type": "scooter",    "isAgent": true },
{ "regex": "^BP_Character_","type": "humanoid",   "isAgent": true },
{ "regex": "^BP_Pedestrian_","type": "pedestrian","isAgent": true },
{ "regex": "Dog",           "type": "dog",        "isAgent": true }
```

At the session level the same job is done by substring match on the actor's class
(`agent-controller.js:129`), defaulting to `pedestrian`:

```js
_resolveType() {
  const cls = (this.agentClass || '').toLowerCase();
  for (const [typeName, def] of Object.entries(REGISTRY.agentTypes)) {
    if (def.namePatterns.some(p => cls.includes(p))) return typeName;
  }
  return 'pedestrian';
}
```

### Ghost mode

`gym_env/ghost.py` defines a variant used heavily in batch experiments: an agent that
is **hidden from all cameras and ignores other agents, but still collides with the
world**. It moves to collision channel 8 (`ECC_GameTraceChannel1`), ignores channel 8
and channel 2 (Pawns), and keeps blocking WorldStatic. This is what lets many episodes
run in parallel in one map without the agents seeing or bumping each other — hence the
`GhostAgent_0`, `GhostAgent_1` … names all over `results/`.

Teleporting a ghost drops collision first to avoid depenetration pushback:

```python
ucv.send(f"vset /object/{actor}/collision false")
ucv.send(f"vset /object/{actor}/location {x} {y} {z}")
ucv.send(f"vset /object/{actor}/collision true")
```

---

## 2. Kind #2 — The panel agent (`AgentSession`)

**What it is:** the LLM brain for one embodied actor, in the interactive Studio. One
`AgentSession` per actor, living for the lifetime of the server process. This is what
the Agent Monitor panel shows.

Defined in `web/server/agent-controller.js`, in two classes:

- `AgentSession` (`:95`) — one agent: its state, memory, and turn loop
- `AgentController` (`:528`) — the registry of sessions, the background poller, and
  inter-agent messaging

### State

```js
AgentSession {
  agentName, agentClass
  location, rotation, velocity, speed   // refreshed by the background poller
  status: 'idle' | 'running'
  currentAction, proc                    // the live Claude subprocess

  history[]          // conversation turns
  inbox[]            // messages from other agents
  activity[]         // last 20 ReAct logs: {thought, actions[], response, cost}
  memory[]           // summarised entries from past turns

  trajectory[]       // last 200 {loc, rot, ts, action}
  collisionCount, recentCollisions[]   // from OnActorHit
  envFeedback[]      // nearby actors within 300 cm
  totalTurns, totalCostUsd, createdAt
}
```

### The turn loop (`run()`, `:207`)

This is the ReAct cycle. It is worth reading in full; the shape is:

```
 0. safety valve      — if status is already 'running', SIGTERM the stuck process
 1. mark running, push the user message onto history
 2. OBSERVE
      getObservation()  → location, rotation, velocity, speed   (3 parallel vget)
      append a trajectory point
      getHitEvents()    → drain queued OnActorHit physics collisions
      getEnvironmentFeedback(300) → nearby actors within 3 m
 3. BUILD PROMPT       — _systemPrompt(), see below
 4. ACT                — _spawnClaude(): Claude Code subprocess with MCP tools
 5. FINALLY            — always reset status to 'idle', always archive the activity log
```

Step 5 is not incidental. The comment above `run()` says *"ALWAYS resets status to
'idle', even on error"* — a stuck `running` flag would wedge the agent permanently, so
the reset lives in a `finally` block and there is a force-kill at the top as a second
line of defence.

### How the system prompt is built (`_systemPrompt()`, `:137`)

**The agent's capabilities are generated from the registry, not hardcoded.** This is
the heart of the design:

```js
const type    = this._resolveType();
const typeDef = REGISTRY.agentTypes[type];

for (const [name, def] of Object.entries(typeDef.actions)) {
  const paramStr = def.params ? `, params: {${def.params.join(', ')}}` : '';
  lines.push(`- agent_action(agent_name="${this.agentName}", action="${name}", agent_type="${type}"${paramStr}) — ${def.description}`);
}
```

A `dog` gets a prompt listing three actions; a `humanoid` gets eighteen. Add an entry
to `agent-registry.json` and the prompt grows by itself.

The assembled prompt has these sections:

```
You control agent "Robot_1" (humanoid) at (500, 0, 110).

## Actions (use agent_action tool)      ← generated from the registry
## Other Tools                          ← agent_stop, agent_rotate, get_agent_state,
                                           get_actors_in_level, take_screenshot
## Communication                        ← "To message another agent, include @AgentName"
## Rules                                ← always use your own name; only control YOUR
                                           agent; observe → think → act → verify; be concise
## SKILLS (reference documentation)     ← auto-retrieved, see §5
## Recent History                       ← last 6 turns, truncated to 300 chars each
## Incoming Messages                    ← inbox, then **cleared**
```

Note the inbox is drained as a side effect of rendering the prompt (`this.inbox = []`)
— messages are delivered exactly once.

### Execution (`_spawnClaude()`, `:289`)

```js
const args = [
  '-p', message,
  '--output-format', 'stream-json',
  '--include-partial-messages',
  '--verbose',
  '--dangerously-skip-permissions',
  '--mcp-config', MCP_CONFIG,
  '--append-system-prompt', systemPrompt,
];
const env = { ...process.env };
for (const key of Object.keys(env)) if (key.startsWith('CLAUDE')) delete env[key];
```

Every `CLAUDE*` environment variable is stripped — otherwise the child CLI detects it
is running inside another Claude session and switches to SDK/extension mode.

The stream-JSON output is parsed line by line into UI events:
`system` → `text` → `thinking` → `tool_start` → `tool_details` → `tool_result` →
`done`. Those same event names are what `codex-runner.js`, `gemini-runner.js`, and
`opencode-runner.js` translate their own vocabularies into, so the React side is
backend-agnostic.

A watchdog kills the subprocess after **3 minutes with no output and no tool running**
(`IDLE_LIMIT = 180000`, `:420`). Alongside it sits a substantial observability block
(`:315-330`) tracking spawn time, init time, first-stream time, and a 4 KB stderr ring
buffer — added after a silent 3.5-minute hang proved impossible to diagnose. On an
idle timeout it dumps elapsed times, the init→first-output gap, the unparsed stdout
tail, and recent stderr. Keep all of it.

### Background poller (`AgentController._startPositionPoller`, `:542`)

Every 3 s, for every **idle** session (running ones get fresh observations at turn
start anyway): refresh position/rotation/velocity, append a trajectory point, drain
hit events, and notify `MetricsHub` immediately on a hit so charts update in real time
rather than at the next 5 s sample.

Hit tracking is armed once, at registration (`getOrCreate`, `:594`), via
`vset /object/{name}/track_hits`, which binds `OnActorHit` in the UE plugin.

### Multi-agent communication

Agents talk to each other by writing `@AgentName` in their response. After a turn
completes, `/api/agent-chat` scans the output and forwards
(`agent-controller.js:652`, wired at `index.js:454`):

```js
const mentioned = agentCtrl.parseAndForwardMentions(agentName, data.text);
for (const targetName of mentioned) {
  const target = agentCtrl.get(targetName);
  if (target && target.status !== "running") {
    setTimeout(() => _triggerAgent(target, `Message from @${agentName}: ...`), 1000);
  }
}
```

The mentioned agent is **auto-triggered** — it takes its own turn a second later. That
is the whole multi-agent conversation mechanism: mentions plus a 1-second debounce,
skipping any agent already mid-turn.

`sendMessage(from, to, text)` with `to = 'all'` (or null) broadcasts to every other
session's inbox and appends to a 200-entry public chat log.

### API surface

| Endpoint | Purpose |
|---|---|
| `GET  /api/agent-sessions` | All sessions, `toJSON()`-shaped (syncs with scene context first) |
| `POST /api/agent-chat` | **Run a turn.** Body `{agentName, message, sessionId}`; responds as an SSE stream |
| `POST /api/agent-stop` / `/api/agent-stop-all` | SIGTERM the subprocess *and* send the type's stop command to UE |
| `GET  /api/agent-state/:name` | Live position + rotation |
| `GET  /api/agent-trajectory/:name` | Full trajectory (the SSE payload only carries the last 10 points) |
| `GET  /api/agent-camera/:name` | First-person render from the actor's camera |
| `GET  /api/agent-history/:name`, `/api/agent-activity/:name` | Conversation and ReAct logs |
| `POST /api/agent-message`, `/api/agent-broadcast` | Inject a message into one or all inboxes |
| `POST /api/agent-discover`, `/api/agent-track` | Manual re-scan of UE for pawn-like actors |

Sessions are also pushed continuously over `GET /api/events` (SSE, 3 s, hash-diffed,
9 s keepalive).

---

## 3. Kind #3 — The gym agent

**What it is:** the same idea as #2, rebuilt for reproducible science. No Claude CLI
dependency, no JS server, any LLM behind one interface, and every step logged.

`gym_env/__init__.py` states the goals plainly: bypass the JS server and agent panel
entirely; support any LLM via a unified `LLMClient`; plug into `nav_task` for rewards
and metrics; talk to UE over UnrealCV (PIE-safe) and only touch MCP for pre-PIE scene
queries.

### Composition

A gym agent is not a class. It is a **composition of four pieces** assembled by
`run_episode()`:

```python
ucv     = UCVClient(); ucv.connect()
episode = sample_pointnav_episode(ucv, seed=42)   # a NavigationEpisode from nav_task
env     = SimWorldNavEnv(ucv_client=ucv)          # the world
llm     = make_llm("claude")                      # the policy
logger  = EpisodeLogger(run_name="my_run")        # the record
run_episode(env, llm, episode, logger)            # the loop
```

| Piece | File | Responsibility |
|---|---|---|
| Environment | `simworld_nav_env.py` — `SimWorldNavEnv` | `reset()` / `step()`; spawns the agent, ensures PIE, resolves the camera, recovers a missing actor, computes final metrics |
| Policy | `llm/` — `LLMClient`, `make_llm()` | `claude` (Anthropic SDK), `claude-sdk` (Claude Code CLI), `gpt`, `gemini`, `qwen` (any OpenAI-compatible endpoint) |
| Action space | `action_space.py` | 4 discrete actions → tool schemas → `vbp` commands |
| Observation | `observation.py` — `ObservationBuilder` | RGB, optional depth, GPS + compass |
| Memory | `memory/` | `null` / `text` / `hierarchical` / `mem0` backends |

### The action space

Exactly four actions, for Habitat parity, with names and descriptions taken from
`nav_task.task_spec.NAVIGATION_ACTIONS`:

| Action | Effect |
|---|---|
| `MOVE_FORWARD` | ~2 s of walking, roughly 200–400 cm |
| `TURN_LEFT` | rotate 30° left |
| `TURN_RIGHT` | rotate 30° right |
| `STOP` | declare arrival |

All four are **parameter-free at the LLM level**. Step duration and turn angle are env
config (`DEFAULT_FORWARD_DURATION_S = 2.0`, `DEFAULT_TURN_ANGLE_DEG = 30.0`), not model
choices — a deliberate decision to keep the action space discrete and comparable
across models.

### Tasks

| Task | Agent sees | Goal |
|---|---|---|
| **PointNav** | GPS + compass + (distance, bearing) to goal, RGB optional | Reach an (x, y) coordinate |
| **ObjectNav** | GPS + compass + category, **RGB required** | Find and reach a named object |

### The system prompt (`runner.py:37`)

Short, and interesting for what it *refuses* to specify:

> Each step you receive the bearing to the goal (in degrees) and the distance. **The
> sign convention of bearing is NOT stated — discover it** by observing how your TURN
> actions change it, then remember which sign means "goal to my right" and which means
> "left". If you notice a flip-flop pattern […] commit to one turn direction for
> several consecutive steps until |bearing| clearly decreases toward 0.

The agent has to *learn the coordinate convention from interaction*. That is the point
of the benchmark.

### The episode loop (`run_episode()`, `runner.py:160`)

```
reset → for t in 1..max_steps:
    build user text  (task, distance+bearing, position+yaw, step number)
    memory.check_rethink()   → prepend a warning if oscillating / stuck / backtracking
    memory.query(k=5)        → prepend recalled past experience
    oscillation heuristic    → soft hint only, NEVER overrides the model's action
    attach RGB if the LLM consumes images (claude-sdk is text-only)
    _strip_images(keep_last_k)  +  _truncate_history(l1_keep, l2_keep)
    llm.chat(history, nav_tool_schemas())
    no tool call → RuntimeError (the model failed to act)
    translate_action() → vbp command → env.step()
    done / truncated → break
```

Two design rules are stated in the code and matter:

- **`_strip_images` / vision-history truncation.** Per-step RGB "blows up token budgets
  fast", so only the last K images survive in history; older turns keep their text.
- **Soft hints only.** The oscillation detector says *"Do NOT override the model action
  in code."* The harness observes and reports; the policy decides. Anything else would
  contaminate the measurement.

### Running one

```bash
cd simworld_studio_workspace
python -m gym_env.runner \
    --model qwen --model-id "Qwen/Qwen3-VL-30B-A3B-Instruct" \
    --base-url "http://gpu-host:8000/v1" --api-key EMPTY \
    --ucv-port 9001 --task pointnav --max-steps 20 --seed 42 \
    --record-trajectory
```

`--memory none|text|hierarchical` selects the memory backend — the no-memory vs
with-memory comparison is the canonical experiment in `gym_env/README.md`.

---

## 4. Kind #4 — The coding agent

**What it is:** the CLI that builds the world. This is what you are talking to in the
Studio chat panel. It never enters the scene; it authors it.

### Definition — `web/server/coding-agents.json`

Its own comment calls it *"single source of truth for the coding-agent backends behind
`/api/chat`."* The server exposes it at `GET /api/coding-agents` and the UI populates
the top-left Agent + Model dropdowns from it.

```jsonc
{
  "default": "claude",
  "agents": {
    "claude":   { "label": "Claude Code",  "runner": "claude",   "binEnv": "CLAUDE_BIN",
                  "defaultModel": "", "models": ["claude-opus-4-8", "claude-sonnet-4-6", ...] },
    "codex":    { "label": "Codex",        "runner": "codex",    "binEnv": "CODEX_BIN",   ... },
    "opencode": { "label": "OpenCode",     "runner": "opencode", "binEnv": "OPENCODE_BIN",... },
    "gemini":   { "label": "Gemini CLI",   "runner": "gemini",   "binEnv": "GEMINI_BIN",  ... }
  }
}
```

`defaultModel: ""` means "let the CLI or its env decide" — preserving each CLI's own
behaviour. `binEnv` names the environment variable that overrides the binary path.

### Runners

Each non-Claude backend gets an adapter whose entire job is **vocabulary translation**
into the Claude-shaped SSE event stream the React app already understands. From
`codex-runner.js:5-10`:

> The frontend talks SSE to `/api/chat` and expects Claude-shaped events
> (`system`/`text`/`tool_start`/`tool_details`/`tool_result`/`screenshot`/`verifier_*`/`done`).
> This module spawns `codex exec --json …` and translates Codex's thread-event
> vocabulary into that shape so nothing on the React side changes.

Each runner also has to solve MCP wiring differently. Codex has no
`--append-system-prompt`, so the prompt is prepended to the user message; and rather
than overriding `CODEX_HOME` (which would lose the user's `codex login`), the runner
injects the simworld MCP server via repeatable `-c mcp_servers.…` TOML overrides,
rewriting `UNREAL_PORT` to the live engine port.

### Tools

The coding agent's capability set is the MCP tool list in `mcp-server.js:643`:

**Scene authoring** — `spawn_blueprint_actor`, `spawn_actor`, `delete_actor`,
`delete_all_spawned`, `set_actor_transform`, `setup_environment`, `list_assets`,
`get_actors_in_level`, `find_actors_by_name`

**Verification** — `take_screenshot`, `verify_scene` (a second Claude scores the
screenshot, returning PASS / NEEDS_IMPROVEMENT / FAIL with issues and suggestions),
`check_floating` (bounding-box column search for actors hovering above ground),
`check_collisions` (AABB intersection, ≤5 cm contacts ignored as normal touching)

**Escape hatch** — `execute_python_script` / `get_python_result`. Restricted. Returns
the full result inline if it finishes within ~50 s (and all errors fail fast, so
tracebacks are always inline); longer builds return a `job_id` to poll.

**Agent control** — `spawn_agent`, `agent_action`, `agent_rotate`, `agent_stop`,
`get_agent_state`. This is the bridge: the coding agent can populate the scene it
just built with kind-#1 actors.

The tool *descriptions* are unusually long and carry real domain knowledge — valid
building ID ranges, the 200 m × 200 m ground extent, "use varied IDs across the full
range for visual diversity rather than spamming the first few", "just call
`setup_environment`, you don't need to check the scene first". Prompt engineering
lives in the schema here. Follow that when adding tools.

**Name collision prevention:** every spawned actor name gets a `_SID` suffix (4-char
session hex) so cross-map restarts never crash on duplicate names.

### Sandbox

Coding agents run with `--dangerously-skip-permissions` so they can drive MCP without
stopping to ask. The compensating control is OS-level (`agent-sandbox.js`): the repo
is bind-mounted **read-only** inside bubblewrap, so a write to source fails at the
kernel regardless of which CLI is running.

```js
const bw = [
  "--dev-bind", "/", "/",             // share the host read-write (incl. /dev, network)
  "--ro-bind", REPO_ROOT, REPO_ROOT,  // …except the repo: read-only
  "--die-with-parent",
  ...(cwd ? ["--chdir", cwd] : []),
  "--", bin, ...args,
];
```

Reads are still allowed (the MCP server and its configs live in the repo); the comment
explains that blocking reads too would be more fragile, and that *"cannot modify"* is
the firm requirement. Falls back to an unwrapped spawn with a warning if `bwrap` is
unavailable or `AGENT_SANDBOX=0`.

Layered on top, at the CLI level (`index.js:644`): file and shell tools stay **enabled**
so the agent can read and write the UE project directory (including `Saved/` logs),
which is whitelisted via `--add-dir $UE_PROJECT_PATH`; and four tools are switched off
outright:

```js
_.push("--disallowedTools", "Task", "TodoWrite", "WebFetch", "WebSearch");
```

The inline comment notes `--disallowedTools` is variadic, so it must come last on the
argv. The repo source stays read-only regardless — that's the sandbox's job, not this
flag's.

---

## 5. Skills — how agents acquire knowledge

A **skill** is a markdown file with YAML frontmatter: reusable procedural knowledge
injected into an agent's prompt.

```markdown
---
id: agent_control
name: Agent Control
version: 1.0.0
author: simworld
tags: [agent, movement, navigation, control, pedestrian, humanoid]
dependencies: []
description: Control humanoid and pedestrian agents in SimWorld — movement, rotation, path following, and actions.
---

## Agent Control Skill
… body: worked tool-call examples the model can pattern-match …
```

`SkillRegistry` (`web/server/skills.js`) loads two directories:

| Source | Directory | Meaning |
|---|---|---|
| `builtin` | `arena/skills/builtin/` | Shipped: `city_layout`, `building_placement`, `water_generation`, `add_fog_atmosphere`, `weather_mood`, `screenshot_tour`, `coastal_island_scene`, … |
| `custom` | `simworld_studio_workspace/skills/` | User- or agent-authored: `agent_control`, `map_asset_discovery`, `street_furniture_obstacles`, `sidewalk_neighborhood`, `weather_mood` |

The API is small: `search(query, tags)` scores by name (+3), description (+2), tag
(+1), plus +2 per matching tag filter; `compose(ids)` concatenates bodies after a
recursive `_resolveDeps()` topological walk; `validate(path)` checks required fields,
minimum body length, and that every declared dependency resolves.

**Panel agents auto-inject skills.** `_systemPrompt()` does not take a skill list —
it searches for them (`agent-controller.js:177`):

```js
const agentSkills = skillRegistry.search('agent', ['agent', 'movement', 'navigation']);
if (agentSkills.length > 0) {
  const composed = skillRegistry.compose(agentSkills.map(s => s.id));
  if (composed) lines.push('', '## SKILLS (reference documentation)', composed);
}
```

Which is exactly why `agent_control_skill.md` is tagged
`[agent, movement, navigation, control, pedestrian, humanoid]` — the tags *are* the
retrieval mechanism. Tag a new skill with those words and every panel agent picks it
up automatically.

`skill-selector.js` is the heavier alternative: it spawns an LLM to choose which
skills are relevant to a given request and returns a validated ID list.

**Learned tools** (`learned-tools-store.js`, `learned-tool-runtime.js`) are the next
rung up: tools an agent authored itself, persisted to `arena_data/learned_tools.json`,
shape-validated and dry-run expanded before being offered as real callable tools.

Gym agents have their own version — the hierarchical memory backend contributes an
"L3 skills" section to the system prompt (`runner.py:195`), seeded from
`l3_skills.json`.

---

## 6. Kind #5 — Arena contestants

`web/server/agents.js` defines `AgentManager`, which is unrelated to
`agent-controller.js`. Here an "agent" is a **contestant**: an id, a label, a type
(`claude-code` | `codex`), a model, an enabled flag.

```js
const DEFAULT_AGENTS = [
  { id: "claude-code",      name: "Claude Code",        type: "claude-code",
    model: "claude-sonnet-4-20250514", enabled: true,  description: "Anthropic Claude Code CLI with MCP tools" },
  { id: "claude-code-opus", name: "Claude Code (Opus)", type: "claude-code",
    model: "claude-opus-4-20250514",   enabled: false, description: "Claude Opus for higher quality (slower, more expensive)" },
  { id: "codex",            name: "OpenAI Codex",       type: "codex",
    model: "o3",                       enabled: false, description: "OpenAI Codex / o3 agent (requires OPENAI_API_KEY)" },
];
```

`pickBattlePair()` shuffles the enabled set and takes two (falling back to the same
agent twice if fewer than two are enabled — a self-play battle). `runBattle()` runs
both on the same prompt, collects screenshots written in the last 120 s, and returns
`{side_a, side_b}` for blind judging. Persisted to `arena_data/agents.json`; managed
through `GET/POST /api/agents` and `PATCH /api/agents/:id`.

---

## 7. Kind #6 — The co-evolution pair

`co_evolve/` closes the loop: **a coding agent designs scenes adversarially against a
navigation agent, refereed by a difficulty teacher.** Both sides carry independent
hierarchical memory.

| Role | File | What it does |
|---|---|---|
| Coding agent | `coding_agent.py` | LLM-driven scene builder + task designer. Adversarial reward: `coding_reward = 1 − nav_sr` |
| Embodied agent | `sim_env.py` + `gym_env` | Runs episodes in the designed scene, produces success rate |
| Teacher | `teacher.py` | Proposes a target difficulty and an acceptance band each epoch |
| Loop | `loop.py`, `__main__.py` | Epoch driver, checkpointing, resume |

The teacher is pluggable: `FixedTeacher` (no-op baseline), `EpsilonGreedyTeacher`
(discrete-bin bandit over a Gaussian reward centred on `target_sr`), and
`ALPGMMTeacher` (continuous, driven by Absolute Learning Progress — resamples past
difficulties weighted by local |ΔSR|, in the spirit of Portelas et al. 2020, with no
external dependency). All persist via `state_dict` / `load_state_dict` so curricula
survive `--resume`.

The coding agent's prompt is a nice specimen of *advisory* control:

> Reward = Gaussian(agent_SR; peak=0.60, sigma=0.20) × (1 + 0.25·progress_bonus).
> The teacher's suggested difficulty band is a HINT for where learning progress is
> currently highest. Try to land near it, but **use your own judgement** based on the
> ROLLING SR + failure patterns below if you have a better idea.
>
> Treat the difficulty band as a soft target. Off-band designs are accepted but logged.

Target success rate is 0.60 — the "learning zone". Too easy and the nav agent learns
nothing; too hard and it gets no signal. And `coding_agent.py` opens with **"NO
FALLBACK"**: on a JSON parse failure it retries the LLM, and if that still fails it
reuses the *last successful design* — never a hardcoded default, because a silent
default would poison the experiment.

```bash
python -m co_evolve --mode live --generations 30
python -m co_evolve --resume runs/co_evolve/coevolve_XXXXXXXX
```

---

## 8. Quick reference: which agent am I looking at?

| If you see… | It's a… |
|---|---|
| `agent-registry.json`, `blueprintPath`, `spawnZ`, `vbp` | #1 embodied actor |
| `AgentSession`, `_systemPrompt()`, `trajectory`, `/api/agent-chat` | #2 panel agent |
| `SimWorldNavEnv`, `run_episode`, `LLMClient`, `NavigationEpisode` | #3 gym agent |
| `coding-agents.json`, `*-runner.js`, `/api/chat`, `sandboxedSpawn` | #4 coding agent |
| `AgentManager`, `pickBattlePair`, `runBattle`, `arena_data/` | #5 arena contestant |
| `teacher.py`, `DifficultyProposal`, `coding_reward` | #6 co-evolution pair |
| `GhostAgent_N` in a results path | a #1 in ghost mode, driven by a #3 |
| `.agents/skills/*/SKILL.md` | none of the above — a playbook for an agent editing *this repo* |
