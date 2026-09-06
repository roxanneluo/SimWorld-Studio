# 03 — Agent Cookbook

Worked examples. Each one is a complete path from "I want X" to "here is the code".
Read [02 — Agents](02-agents.md) first if the word "agent" is still ambiguous.

---

## Example 1 — Add a new action to an existing agent type

**Scenario:** the humanoid Blueprint has a `Crouch` function and you want agents to use it.

This is a **one-line JSON edit**. No JavaScript.

`web/server/agent-registry.json`:

```jsonc
"humanoid": {
  "actions": {
    // …existing actions…
    "crouch": { "cmd": "Crouch", "description": "Crouch down low" }
  }
}
```

What happens automatically:

1. `mcp-server.js` `toolAgentAction` resolves `crouch` → emits `vbp Robot_1 Crouch`.
2. `_systemPrompt()` in `agent-controller.js` iterates the registry, so every humanoid
   panel agent's prompt now lists
   `agent_action(agent_name="Robot_1", action="crouch", agent_type="humanoid") — Crouch down low`.
3. `spawn_agent` returns `crouch` in its `available_actions`.
4. Calling `agent_action` with a bogus action name now includes `crouch` in the
   "Available:" error message.

With parameters, declare them in order and supply defaults:

```jsonc
"crouch": {
  "cmd": "Crouch",
  "params": ["duration", "depth"],
  "defaults": [2, 0.5],
  "description": "Crouch for N seconds at a given depth (0.0–1.0)"
}
```

`agent_action(..., params: {duration: 4})` → `vbp Robot_1 Crouch 4 0.5`
(positional fill; `depth` falls through to its default).

**Verify** on a live UE before committing — a wrong `cmd` name fails silently at the
Blueprint layer:

```bash
curl -s -X POST localhost:3002/api/agent-chat \
  -H 'Content-Type: application/json' \
  -d '{"agentName":"Robot_1","message":"crouch for 3 seconds"}'
```

---

## Example 2 — Define a whole new agent type

**Scenario:** a drone Blueprint at `/Game/Drones/BP_Drone.BP_Drone_C`.

### Step 1 — register the type

`web/server/agent-registry.json`, under `agentTypes`:

```jsonc
"drone": {
  "blueprintPath": "/Game/Drones/BP_Drone.BP_Drone_C",
  "description":   "Quadcopter drone with altitude control",
  "spawnZ":        500,               // spawns airborne, unlike ground agents
  "stopCmd":       "Hover",           // "stop" for a drone means hold position
  "rotateCmd":     "Yaw",
  "namePatterns":  ["drone", "quadcopter", "uav"],
  "actions": {
    "move_forward": { "cmd": "MoveForward", "params": ["duration"], "defaults": [2],
                      "description": "Fly forward for N seconds" },
    "ascend":       { "cmd": "ChangeAltitude", "params": ["delta"], "defaults": [100],
                      "description": "Change altitude by N cm (negative to descend)" },
    "hover":        { "cmd": "Hover", "description": "Hold current position" },
    "set_speed":    { "cmd": "SetMaxSpeed", "params": ["speed"],
                      "description": "Set flight speed (200=slow, 600=fast)" }
  }
}
```

### Step 2 — teach auto-discovery about it

Same file, `classifyPatterns` — so drones already present in a loaded map get picked
up by the 5-second `vget /objects` poll:

```jsonc
{ "regex": "^BP_Drone_", "type": "drone", "isAgent": true }
```

Also make sure at least one `namePatterns` entry is a substring of the UE **class**
name, since `AgentSession._resolveType()` matches on class, not actor name:

```js
// agent-controller.js:129 — substring match, lowercased, first hit wins
if (def.namePatterns.some(p => cls.includes(p))) return typeName;
```

`BP_Drone_C` lowercases to `bp_drone_c`, which contains `drone`. Good.

> ⚠️ **Ordering matters.** `_resolveType()` iterates `Object.entries(REGISTRY.agentTypes)`
> in insertion order and returns the first match, and the fallback is `pedestrian`
> — not an error. A broad pattern placed early will shadow later types. Keep
> patterns specific.

### Step 3 — that's it

`spawn_agent`'s tool description is built from `Object.keys(AGENT_REGISTRY.agentTypes)`
(`mcp-server.js:643`), so the new type is advertised to the model with no further
change:

```
spawn_agent(agent_name="Drone_1", agent_type="drone", location=[0, 0, 500])
```

### Step 4 — optionally, write a skill

If the drone needs procedural guidance (flight patterns, safe altitudes), add
`simworld_studio_workspace/skills/drone_control_skill.md` with the retrieval tags —
see Example 5.

---

## Example 3 — Drive an agent from the API

Everything the UI does is available over HTTP. **Server default port is 3002** (`PORT`) — not 9001, despite what `docs/product/architecture.md` says.

```bash
# 1. What agents does the server know about?
curl -s localhost:3002/api/agent-sessions | jq '.[] | {agentName, agentClass, status, location}'

# 2. Nothing? Force a scan of UE for pawn-like actors.
curl -s -X POST localhost:3002/api/agent-discover

# 3. Give one a task. Responds as an SSE stream — watch the ReAct cycle live.
curl -N -X POST localhost:3002/api/agent-chat \
  -H 'Content-Type: application/json' \
  -d '{"agentName":"Pedestrian_1","message":"Walk to the red building and stop 3 m short of it."}'

# 4. Live state / full trajectory (SSE only carries the last 10 points)
curl -s localhost:3002/api/agent-state/Pedestrian_1
curl -s localhost:3002/api/agent-trajectory/Pedestrian_1 | jq '. | length'

# 5. First-person render
curl -s localhost:3002/api/agent-camera/Pedestrian_1 --output fpv.png

# 6. Stop it (kills the subprocess AND sends the type's stopCmd to UE)
curl -s -X POST localhost:3002/api/agent-stop -H 'Content-Type: application/json' \
  -d '{"agentName":"Pedestrian_1"}'
```

The SSE event stream from step 3:

```
event: system        {"sessionId":"…"}
event: thinking      {"text":"I should first check where I am…"}
event: tool_start    {"tool":"get_agent_state"}
event: tool_result   {"ok":true,"result":"…"}
event: tool_start    {"tool":"agent_action"}
event: tool_details  {"input":{"agent_name":"Pedestrian_1","action":"move_forward"}}
event: tool_result   {"ok":true}
event: text          {"text":"Moving toward the building."}
event: done          {"text":"…","cost":0.0123}
```

### Multi-agent conversation

```bash
# Broadcast to every agent's inbox
curl -s -X POST localhost:3002/api/agent-broadcast \
  -H 'Content-Type: application/json' \
  -d '{"text":"Everyone gather at the fountain."}'
```

Or let agents do it themselves: if `Pedestrian_1`'s response contains
`@Pedestrian_2`, the server forwards the message and auto-triggers `Pedestrian_2` one
second later — provided it isn't already mid-turn (`index.js:454`).

---

## Example 4 — Trace one panel-agent turn through the code

Following `POST /api/agent-chat {agentName:"Robot_1", message:"walk forward 5 m"}`:

| # | Where | What happens |
|---|---|---|
| 1 | `index.js:454` | Route handler; looks up scene context, calls `agentCtrl.syncWithContext(ctx)` |
| 2 | `agent-controller.js:619` | `syncWithContext` — `getOrCreate()` each agent in the scene; drop sessions whose actor is gone *unless* status is `running` |
| 3 | `index.js:465` | `agentCtrl.sendMessage("user", "Robot_1", message)` → lands in the session's `inbox` and the public chat log |
| 4 | `index.js` | SSE headers flushed; `agent.run(message, send)` invoked |
| 5 | `agent-controller.js:209` | **Safety valve** — if already `running`, SIGTERM the stuck process |
| 6 | `:214` | `status = 'running'`; message pushed onto `history` |
| 7 | `:229` | `getObservation()` — three parallel `vget` (location, rotation, velocity) through the broker; speed derived as `‖velocity‖` |
| 8 | `:234` | Trajectory point appended; ring-buffered at 200 |
| 9 | `:243` | `getHitEvents()` drains queued `OnActorHit` events → `collisionCount`, `recentCollisions` (capped at 50) |
| 10 | `:261` | `getEnvironmentFeedback(300)` — actors within 3 m → `envFeedback` (capped at 20) |
| 11 | `:267` | `_systemPrompt()` — registry actions, tools, rules, retrieved skills, last 6 history turns, **inbox (then cleared)** |
| 12 | `:289` | `_spawnClaude()` — `claude -p … --output-format stream-json --mcp-config … --append-system-prompt …`, with every `CLAUDE*` env var stripped |
| 13 | `:341` | stdout parsed line-by-line; each JSON becomes an SSE event and is accumulated into `_currentActivity` |
| 14 | — | Claude calls `agent_action` over MCP → `mcp-server.js:451` → `vbp Robot_1 StepForward 2 0` → UnrealCV → UE |
| 15 | `:427` | Idle-timeout watchdog; on trip, dumps elapsed times, unparsed stdout tail, stderr tail |
| 16 | `:281` | `finally` — `status = 'idle'`, `proc = null`, activity archived (last 20 kept) |
| 17 | `index.js:483` | On `done`: broadcast the response, scan for `@mentions`, auto-trigger those agents after 1 s |

Meanwhile, independently: the 3-second poller (`:542`) keeps refreshing idle agents,
and `MetricsHub` samples every 5 s — plus an immediate `recordAgentHit()` on any
physics collision so the charts don't wait for the next tick.

---

## Example 5 — Write a skill

Create `simworld_studio_workspace/skills/drone_control_skill.md`:

```markdown
---
id: drone_control
name: Drone Control
version: 1.0.0
author: simworld
tags: [agent, movement, navigation, drone, flight]
dependencies: []
description: Control quadcopter drones in SimWorld — altitude, flight patterns, and safe operating envelopes.
---

## Drone Control Skill

### Spawning
    spawn_agent(agent_name="Drone_1", agent_type="drone", location=[0, 0, 500])

Z=500 is a safe starting altitude. Below 200 you risk clipping street furniture.

### Altitude
    agent_action(agent_name="Drone_1", action="ascend", agent_type="drone", params={"delta": 300})
    agent_action(agent_name="Drone_1", action="ascend", agent_type="drone", params={"delta": -150})

### Survey pattern
Ascend to 1500, then alternate `move_forward` (duration 4) with 90° `agent_rotate`
calls to fly a rectangle. Call `take_screenshot` at each corner.

### Rules
- Always `hover` before changing altitude.
- Never descend below 200 in a city scene.
- Buildings reach ~3000 cm; fly above 3500 to cross a block safely.
```

### Why the tags matter

`agent-controller.js:177` retrieves with
`skillRegistry.search('agent', ['agent', 'movement', 'navigation'])`. Scoring is
name +3, description +2, tag-substring +1, and +2 per tag-filter hit. Tagging
`[agent, movement, navigation, …]` guarantees selection; tag it only `[drone]` and no
panel agent will ever see it.

### Validate it

```js
const { SkillRegistry } = require('./simworld_studio_workspace/web/server/skills.js');
const r = new SkillRegistry();
console.log(r.validate('simworld_studio_workspace/skills/drone_control_skill.md'));
// { valid: true, skill: {...} }  — or { valid: false, errors: [...] }
```

Checks: frontmatter present, `id` / `name` / `description` non-empty, body ≥ 20 chars,
every entry in `dependencies` resolvable.

Skills compose. Declaring `dependencies: [agent_control]` makes `compose()` emit
`agent_control`'s body first, resolved recursively with cycle protection
(`_resolveDeps`).

---

## Example 6 — Run a gym episode from Python

### Programmatic

```python
from gym_env import SimWorldNavEnv, make_llm, run_episode, EpisodeLogger
from gym_env.episode_builder import sample_pointnav_episode
from gym_env.ucv_client import UCVClient

ucv = UCVClient(port=9001)
ucv.connect()

episode = sample_pointnav_episode(ucv, seed=42)     # a nav_task.NavigationEpisode
env     = SimWorldNavEnv(ucv_client=ucv)            # auto-starts PIE on first reset()
llm     = make_llm("claude")                        # or "gpt" / "gemini" / "qwen" / "claude-sdk"
logger  = EpisodeLogger(run_name="drone_smoke")

metrics = run_episode(env, llm, episode, logger, max_steps=20)
print(metrics)          # success, SPL, distance_to_goal, steps, …
```

### CLI

```bash
cd simworld_studio_workspace
export PYTHONPATH=/path/to/task_gen

python -m gym_env.runner \
    --model qwen --model-id "Qwen/Qwen3-VL-30B-A3B-Instruct" \
    --base-url "http://gpu-host:8000/v1" --api-key EMPTY \
    --ucv-port 9001 --task pointnav \
    --n-episodes 30 --max-steps 20 --seed 300 \
    --memory text --record-trajectory \
    --run-name qwen_with_memory
```

Prerequisites, from `gym_env/README.md`:

- UE launched with `-MCPPort=55557`, `unrealcv.ini` set to `Port=9001`
- **Do not** run `SimWorld-Studio.bat` or the JS server — the harness talks to UE directly
- `Base_User_Agent` with a working `FusionCamSensor`; `EnableController True` must be
  called after spawn (the env does this)
- PIE auto-starts on first `env.reset()`; pass `--no-start-pie` if it's already running

### Adding a new LLM backend

Implement `LLMClient` in `gym_env/llm/` and register it in `make_llm()`. The contract
is one method:

```python
def chat(self, messages: list[LLMMessage], tools: list[dict], *, max_tokens: int) -> LLMResponse
```

`LLMResponse` carries `.text` and `.tool_calls`. If the endpoint can't do tool calls,
follow the Qwen precedent: fall back to strict if-else text prompting and parse the
action name out of the reply. Note that `claude-sdk` is text-only, and `runner.py:253`
skips image attachment for it by checking `getattr(llm, "name", "")` — set `.name` on
your client accordingly.

---

## Example 7 — Add a new MCP tool

Following the pattern in `.agents/skills/simworld-mcp/SKILL.md`:

1. **Schema** → `TOOL_DEFS` in `mcp-server.js:643`. Write a *long* description: valid
   ranges, units, failure modes, when to call it. The existing descriptions carry real
   domain knowledge ("Ground is 200 m × 200 m centered at origin, so keep X and Y
   between −9500 and 9500") and that is where the prompt engineering lives.
2. **Handler** → an `async function toolYourThing({...})` with input validation, and
   an entry in `TOOL_HANDLERS`.
3. **Return structured JSON** — `{status: "success"|"error", …}`. Never a raw string.
4. **Classify it** — safe, or restricted (requiring explicit approval). Update
   `AGENTS.md`, `docs/product/architecture.md`, and the MCP skill.
5. **Register it** in `.codex/config.toml` under `enabled_tools` / `disabled_tools`.
6. **Emit an audit event** — `mcpLog('info', 'your_thing', {sanitized params})`.

Reach for UnrealCV (`ucvCommandRetry`) for runtime/PIE work and UE Python for
editor-mode work. Remember UE's command queue is serial: never issue another UE tool
call while an `execute_python_script` job is still running.

---

## Example 8 — Switch coding-agent backends

Add a model to an existing backend — `web/server/coding-agents.json`, no code:

```jsonc
"claude": {
  "label": "Claude Code",
  "runner": "claude",
  "binEnv": "CLAUDE_BIN",
  "defaultModel": "",
  "models": ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001", "your-new-model"]
}
```

The UI reads `GET /api/coding-agents` to build the top-left Agent + Model dropdowns,
and also offers a free-text **Custom…** entry. `defaultModel: ""` means "let the CLI
or its env decide".

Point at a specific binary:

```bash
export CLAUDE_BIN=/opt/claude/bin/claude      # the backend's `binEnv`
export CODEX_BIN=/usr/local/bin/codex
```

Adding a whole new CLI backend means writing a runner alongside
`codex-runner.js` / `gemini-runner.js` / `opencode-runner.js`. Its entire job is to
translate that CLI's event vocabulary into the Claude-shaped SSE stream the frontend
expects — `system`, `text`, `thinking`, `tool_start`, `tool_details`, `tool_result`,
`screenshot`, `verifier_*`, `done` — so nothing on the React side changes. Study
`codex-runner.js:5-28` first; it documents the verified event schema and the MCP
injection strategy, and both were hard-won.

---

## Example 9 — Run a co-evolution experiment

```bash
export UE_PROJECT="/path/to/SimWorld.uproject"
export NAV_BASE_URL="http://llm-host:8002/v1"
export CODING_BASE_URL="http://llm-host:8002/v1"
export NAV_MODEL_ID="Qwen3.5-9B"
export CODING_MODEL_ID="Qwen3.5-9B"

# Start UE Editor manually (load the agent_test map), then:
cd simworld_studio_workspace
python -m co_evolve --mode live --generations 30

# Resume an interrupted run
python -m co_evolve --resume runs/co_evolve/coevolve_XXXXXXXX
```

Per generation: the **teacher** proposes a target difficulty and band; the **coding
agent** designs a scene aiming near it (advisory, not enforced — off-band designs are
accepted and logged); the **nav agent** runs episodes; the observed success rate
updates the teacher and feeds the coding agent's adversarial reward
(`coding_reward = 1 − nav_sr`, shaped by a Gaussian peaking at SR = 0.60).

Swap the curriculum controller in `co_evolve/config.py`: `FixedTeacher` (baseline),
`EpsilonGreedyTeacher` (discrete bandit), `ALPGMMTeacher` (continuous, learning-progress
driven). All implement `state_dict` / `load_state_dict`, so `--resume` restores the
curriculum, not just the checkpoint.

---

## Where to look next

| Question | File |
|---|---|
| What does an agent's prompt actually contain? | `web/server/agent-controller.js:137` |
| What can an agent physically do? | `web/server/agent-registry.json` |
| How does an action reach Unreal? | `web/server/mcp-server.js:451` |
| What tools does the scene-building agent have? | `web/server/mcp-server.js:643` |
| How is an episode scored? | `nav_task/measures.py`, `nav_task/reward.py` |
| How does the browser learn about agents? | `web/server/README.md` — SSE payload |
| What are the engineering rules? | `AGENTS.md` |
