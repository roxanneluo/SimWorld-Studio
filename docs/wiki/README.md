# SimWorld Studio — Developer Wiki

An orientation guide to *how this codebase is put together* and *how agents work in it*.

This wiki is descriptive: it documents the code as it exists today, with file and
line references you can jump to. It is not a spec. Where the code and
[`AGENTS.md`](../../AGENTS.md) disagree, the code wins and this wiki says so.

## Pages

| Page | Read it when you want to… |
|---|---|
| [01 — Codebase Structure & Style](01-codebase-structure.md) | Find your way around the repo, understand the two parallel stacks, learn the house conventions before writing code |
| [02 — Agents: The Concept Map](02-agents.md) | Understand what "agent" means here (it means four different things), how each kind is defined, and what each one does |
| [03 — Agent Cookbook](03-agent-cookbook.md) | Copy a worked example: define a new agent type, drive one from the API, trace a turn, run a gym episode, write a skill |

## The 60-second version

SimWorld Studio is an **LLM-driven authoring and evaluation environment for Unreal
Engine 5.3**. A chat agent builds a 3D scene by calling MCP tools; embodied agents
are then spawned into that scene and driven by LLMs; their trajectories are recorded
and scored; and a co-evolution loop feeds those scores back into scene difficulty.

The product is organised as a four-stage pipeline — **Scene → Task → Training →
Co-evolution** — and the UI enforces that separation ("one mode = one job").

Two mostly-independent stacks implement it:

```
┌─ JS / Studio stack ──────────────────┐   ┌─ Python / research stack ────────────┐
│  React SPA  (web/src/App.jsx)        │   │  gym_env/     episode harness        │
│      ↕ REST + SSE                    │   │  nav_task/    tasks, rewards, metrics│
│  Express server (web/server/)        │   │  co_evolve/   adversarial curriculum │
│      ↕ MCP (stdio) + UnrealCV (TCP)  │   │      ↕ UnrealCV (TCP) + MCP          │
└──────────────┬───────────────────────┘   └───────────────┬──────────────────────┘
               └───────────► Unreal Engine 5.3 ◄───────────┘
```

The JS stack is the interactive product. The Python stack is the experiment harness
and **deliberately bypasses the JS server entirely** — `gym_env/README.md` says so in
as many words: *"Do NOT run `SimWorld-Studio.bat` or the JS web server."*

Both stacks eventually speak the same two wire protocols to UE:

- **MCP** (Model Context Protocol) — scene authoring, editor-mode operations
- **UnrealCV** — a plain-text TCP protocol (`vget` / `vset` / `vbp`), used for
  everything runtime: agent state, movement, camera capture, collision events

## Ports

| Port | Who listens | Env var | Purpose |
|---|---|---|---|
| **3002** | Node/Express | `PORT` | Studio HTTP API + SSE |
| 5173 | Vite dev server | — | Frontend dev; proxies `/api` → 3002 |
| **9000** | UnrealCV plugin | `UCV_PORT` | Runtime agent control. `gym_env` recommends **9001** instead, to dodge a VS Code conflict — set it in `unrealcv.ini` *and* pass `--ucv-port` |
| **55559** | UE MCP TCP server | `UNREAL_PORT` | Scene authoring. Falls back to the value in `web/mcp.json`, else `55559`. Older docs and the `gym_env` README say 55557 — check your launcher |
| 8585 / 8586 | Cirrus | `CIRRUS_HTTP_PORT` / `CIRRUS_WS_PORT` | Pixel Streaming HTTP / WebSocket |

> ⚠️ `docs/product/architecture.md` states the server port is 9001. That is stale —
> `web/server/index.js:1` defaults `PORT` to **3002**, and `web/vite.config.js`
> proxies `/api` to `localhost:3002`.

Multi-user deployments allocate a port triple per slot, striding by 2 from
`UE_BASE_MCP_PORT` (55559), `UE_BASE_CIRRUS_HTTP` (8585) and `UE_BASE_CIRRUS_WS`
(8586) — see `web/server/session-manager.js:22`.
