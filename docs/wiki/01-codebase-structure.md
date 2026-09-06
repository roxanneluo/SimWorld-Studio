# 01 — Codebase Structure & Style

## 1. Top-level map

```
SimWorld-Studio/
├── AGENTS.md                    ← engineering contract read by every coding agent
├── README.md                    ← user-facing install + usage
├── INTERNAL_SETUP.md            ← internal deployment notes
├── version.json                 ← Studio version + UE binary download manifest
├── .mcp.json                    ← MCP config for agents working *on this repo*
├── .codex/config.toml           ← Codex CLI config
├── .agents/skills/              ← skills for coding agents editing this repo
│     simworld-ui/SKILL.md       ← "editing the frontend" playbook
│     simworld-mcp/SKILL.md      ← "editing the backend/MCP" playbook
├── SimWorld/                    ← git submodule: SimWorld-AI/SimWorld (UE-side Python)
├── docs/
│     product/                   ← architecture, api_contract, ui_modes, status
│     design/                    ← UI reference PNGs
│     wiki/                      ← you are here
├── SimWorld-Studio.{sh,bat,ps1} ← launchers (Linux/mac, Windows cmd, PowerShell)
├── build.sh, package_*.sh       ← packaging
├── packaging/simworld_arena/    ← prebuilt arena bundle (built output, not source)
└── simworld_studio_workspace/   ← ★ everything that actually runs
```

**Rule of thumb:** if it isn't under `simworld_studio_workspace/`, it's launcher,
packaging, docs, or agent configuration.

## 2. The workspace

```
simworld_studio_workspace/
├── web/                    ← the JS stack (interactive Studio)
│   ├── src/                  React SPA
│   ├── server/               Express + MCP + UE bridges
│   └── public/               Pixel Streaming player
├── gym_env/                ← Python episode harness (embodied agent experiments)
├── nav_task/               ← task definitions, rewards, metrics, validators
├── co_evolve/              ← adversarial coding-agent ↔ nav-agent curriculum loop
├── skills/                 ← custom skills (markdown + YAML frontmatter)
├── arena/skills/builtin/   ← built-in skills
├── scripts/                ← dataset generation, visualisation, one-off Python
├── scenes/                 ← saved scene JSON
├── datasets/               ← generated task datasets
├── results/ experiments/   ← run outputs (trajectories, metrics, plots)
├── arena_data/             ← agent + learned-tool JSON persistence
└── .simworld_memory/       ← Chroma vector store for agent memory
```

### 2.1 `web/src/` — frontend

| File | Size | Role |
|---|---|---|
| `App.jsx` | ~454 KB | **The entire application.** Every component is inline. |
| `index.css` | ~37 KB | All styles; CSS custom properties drive dark/light themes |
| `main.jsx` | tiny | React root mount |
| `PixelStreamPlayer.jsx` | small | UE viewport iframe wrapper |
| `dataClient.js` | small | typed fetch helpers for the data hub |

Yes, `App.jsx` is one file. That is intentional and load-bearing for the current
workflow — `AGENTS.md` explicitly forbids a TypeScript migration without instruction,
and the UI skill treats `App.jsx` as the single place components live.

### 2.2 `web/server/` — backend

One Express process owns the UE connection, subprocess management, SSE push, and
every API route.

| Module | Role |
|---|---|
| `index.js` (~115 KB) | Express app, all REST routes, SSE poller, orchestration |
| `mcp-server.js` (~58 KB) | MCP tool server, spawned as a subprocess *by the coding-agent CLI* |
| `unreal-bridge.js` | Singleton UnrealCV TCP broker — FIFO queue, retries, auto-reconnect |
| `agent-controller.js` | `AgentSession` / `AgentController` — the embodied-agent LLM brain |
| `agent-registry.json` | **Data-driven definition of every embodied agent type** |
| `agents.js` | `AgentManager` — arena *contestant* registry (a different "agent") |
| `agent-sandbox.js` | bubblewrap wrapper making the repo read-only to coding agents |
| `codex-runner.js`, `gemini-runner.js`, `opencode-runner.js` | non-Claude coding-agent CLI adapters |
| `coding-agents.json` | Single source of truth for coding-agent backends + models |
| `context-manager.js` | Current scene state (agents, objects, environment, round) |
| `metrics-hub.js` | 5-second time-series sampler across agent sessions |
| `skills.js` / `skill-selector.js` | Skill registry + LLM-driven skill retrieval |
| `learned-tools-store.js` / `learned-tool-runtime.js` | Agent-authored tools |
| `evolution.js` (~72 KB) | Self-evolution artifact tracking |
| `scenes.js`, `tasksets.js`, `task-gen.js`, `training.js`, `coevolve.js` | Pipeline stages |
| `session-manager.js` | Multi-user UE slot pool (TTL + wait queue) |
| `checkpoints.js`, `data-hub.js`, `ue-queue.js`, `logger.js` | Support |

### 2.3 `gym_env/` — Python experiment harness

```
gym_env/
├── simworld_nav_env.py   SimWorldNavEnv — the Gym-style environment
├── runner.py             run_episode() — the LLM ↔ env loop + CLI
├── batch_runner.py       multi-episode / multi-map orchestration
├── epoch_runner.py       epoch-level driver for curriculum runs
├── action_space.py       4 discrete nav actions → UnrealCV vbp commands
├── observation.py        ObservationBuilder — RGB, depth, GPS+compass
├── episode_builder.py    samples PointNav / ObjectNav episodes
├── ucv_client.py         UnrealCV client (PIE-safe)
├── mcp_client.py         MCP client for pre-PIE scene queries
├── ghost.py              ghost-mode helpers (invisible, selectively-colliding agents)
├── llm/                  claude, claude_sdk, openai_compat backends behind LLMClient
├── memory/               null / text / hierarchical / mem0 memory backends
└── configs/, notebooks/, scripts/, utils/
```

`nav_task/` is the sibling package supplying `NavigationEpisode`, `NAVIGATION_ACTIONS`,
reward shaping, success measures, and validators. `gym_env` imports it; the
`gym_env` docstring notes it uses `EuclideanNavigationInterface` because
agent-built scenes have no road graph.

## 3. The runtime stack, end to end

```
Browser (React)
    │  fetch REST  ·  EventSource /api/events (SSE, 3 s)  ·  POST /api/chat (SSE)
    ▼
Express server (web/server/index.js)
    │
    ├─ spawns ─► coding-agent CLI (claude | codex | gemini | opencode)
    │                 │  which itself spawns
    │                 └─► mcp-server.js  ──TCP 55557──► UE MCP plugin
    │
    ├─ spawns ─► per-agent claude subprocess (agent-controller.js)
    │                 └─► same mcp-server.js
    │
    └─ direct ──► UcvBroker (unreal-bridge.js) ──TCP 9000──► UnrealCV plugin

Browser viewport ◄── WebRTC (Cirrus Pixel Streaming) ── UE
```

Two things about this diagram are worth internalising:

1. **The server never lets the browser touch UE.** Everything is
   `/api/*` → server → MCP or UnrealCV. The MCP skill states this as rule #1.
2. **MCP and UnrealCV are used for different things.** MCP is the *authoring*
   channel (spawn a building, run editor Python, take a screenshot). UnrealCV is the
   *runtime* channel and is PIE-safe (query an agent's velocity, fire a Blueprint
   function, drain hit events). `spawn_agent` is the one that straddles: it requires
   PIE, so the MCP handler calls `ensurePIE()` first
   (`web/server/mcp-server.js:408`).

## 4. House style

### 4.1 JavaScript

- **CommonJS** everywhere on the server (`require` / `module.exports`), `"use strict"`
  at the top of each module.
- **No TypeScript.** Plain `.js` / `.jsx`.
- **Comment style: explain *why*, at length.** The best modules in this repo open with
  a block comment that reads like a design note. `agent-sandbox.js:3-19` explains why
  the bubblewrap wrapper exists and what the weaker alternatives were;
  `codex-runner.js:5-28` documents the verified Codex event schema and why the
  system prompt is prepended rather than passed as a flag;
  `agent-controller.js:16-22` explains why the singleton broker replaced per-call
  TCP sockets. **Match this.** A subtle UE/CLI workaround with no explanation will
  be deleted by the next person.
- **Section dividers** as `// ─── Name ─────` box-drawing rules.
- **Structured logging** through `logger.js`: `log.agent('warn', msg, data)`.

### 4.2 React / UI

The rules in `AGENTS.md` and `.agents/skills/simworld-ui/SKILL.md` are enforced:

1. **Use the shared primitives** — `Badge`, `SourceBadge`, `StatusBadge`, `Btn`,
   `ToggleBtn`, `TagChip`, `ModalOverlay`, `PageHeader`, `Eyebrow`, `Field`, `inputSx`.
2. **No hardcoded colors.** Use CSS variables: `var(--ink)`, `var(--blue)`,
   `var(--panel)`. Themes switch via `data-theme` on the root.
3. **No emoji.** Monochrome SVG line icons only, via `ICONS.*`.
4. **One mode = one job.** Scene Generation must not render agent reward charts.
5. **Mock first** — typed fixtures before real backend integration.
6. **Hooks only** for state. No Redux, no Zustand.

### 4.3 Python

- `from __future__ import annotations` at the top of essentially every module.
- Full type hints; `dataclass` for value types (`StepResult`, `DifficultyProposal`).
- **Module docstrings carry the reasoning.** `action_space.py:1-31` is the model: it
  states that `nav_task.task_spec.NAVIGATION_ACTIONS` is the source of truth for the
  action *set*, then explains in two numbered points why the same module's
  `simworld_cmd` templates are deliberately *not* used, citing the verified Blueprint
  signature in `SimWorld/simworld/communicator/unrealcv.py:619-635`.
- Defensive shims are documented where they sit: `gym_env/__init__.py:29-49` explains
  the unrealcv stdout-encoding monkey-patch and the deadlock it prevents.
- `argparse` CLIs, `python -m gym_env.runner` style entry points.

### 4.4 Configuration is data, not code

A recurring pattern worth naming: **behaviour that varies is pushed into JSON, and
code iterates over it.**

- `agent-registry.json` — agent types, blueprints, actions, classification regexes
- `coding-agents.json` — coding-agent backends, binaries, model lists
- `assets_full.json` — the static asset catalog
- `l3_skills.json`, `skills/python_skills.json` — skill payloads
- Skills themselves — markdown files with YAML frontmatter, loaded from directories

Adding a humanoid action or a new model option should be a JSON edit, not a code edit.
When you find yourself about to add an `if (agentType === ...)` branch, check whether
the registry can express it instead.

## 5. Gotchas

**Some checked-in server files are minified.** `agents.js`, `skills.js`, and long
stretches of `index.js` are single-line bundled output — `skills.js` is one 4 KB line
containing an entire `SkillRegistry` class. Others (`agent-controller.js`,
`agent-sandbox.js`, `codex-runner.js`, `learned-tools-store.js`,
`session-manager.js`) are readable source. Before editing, look at the file. To read
a minified one, pipe it through a formatter rather than fighting it:

```bash
npx prettier --parser babel simworld_studio_workspace/web/server/skills.js | less
```

**`index.js.backup` and `simworld_studio (2).html` are stale artifacts.** Not source.

**`packaging/simworld_arena/` is build output**, and contains its own copies of
`server/agents.js`, `index.js`, `arena.js`. Edit the workspace copies.

**`.mcp.json` at the repo root contains a hardcoded Windows path**
(`C:/Users/28262/Desktop/...`) and `web/mcp.json` a hardcoded Linux one
(`/home/koe/...`). These are per-machine and get rewritten by the launchers; don't
assume they're portable.

**UE's command queue is serial.** Never issue other UE tool calls while a
`execute_python_script` job is still running — the tool description says so.

## 6. Required checks before finishing a task

From `AGENTS.md`:

```bash
cd simworld_studio_workspace/web
npx vite build --mode development          # must succeed with no errors

grep -P "[\x{1F300}-\x{1F9FF}]" src/App.jsx && echo "FAIL: emoji found" || echo "OK"

grep -n '"#[0-9a-fA-F]\{6\}"' src/App.jsx \
  | grep -v "TAG_COLORS\|AGENT_COLORS\|CATEGORY_COLORS\|0b1220\|1e293b" | head -20
```

For Python work, `gym_env/smoke_test.py` is the fast sanity check; it needs a live UE.

## 7. Safety rules (non-negotiable)

Never call these UE tools without explicit user approval:

- `execute_python_script` — arbitrary Python in the UE process
- `delete_all_spawned` — clears the scene
- Filesystem writes outside `simworld_studio_workspace/`
- Network calls beyond the configured UE host

Safe by default: `list_assets`, `take_screenshot`, `get_actors_in_level`,
`find_actors_by_name`, `set_actor_transform`, `spawn_actor`,
`spawn_blueprint_actor`, `verify_scene`, `check_collisions`, `check_floating`,
and the `agent_*` / `get_agent_state` family.

Separately, coding agents are launched with broad permissions so they can drive MCP
autonomously — so the repo itself is bind-mounted **read-only** into a bubblewrap
sandbox (`agent-sandbox.js`). Per-CLI tool restrictions are defence in depth; the
kernel mount is the actual guarantee. It degrades to an unwrapped spawn with a
warning if `bwrap` is missing or `AGENT_SANDBOX=0`.
