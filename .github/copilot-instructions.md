# OpenSpace — Cubecloud Fork Guidelines

This is the **Cubecloud fork** (`JZKK720/OpenSpace`) of [`HKUDS/OpenSpace`](https://github.com/HKUDS/OpenSpace) — an AI agent runtime over MCP and direct protocols, extended with the Cubecloud dashboard, i18n, and Windows distribution support.

## Architecture

| Layer | Path | Notes |
|---|---|---|
| Core runtime | `openspace/` | Python ≥ 3.12 |
| Skill system | `openspace/skills/`, `openspace/host_skills/` | YAML-fronted `SKILL.md` per skill |
| Agent config | `openspace/config/external_agents.json` | MCP servers + external agent definitions |
| Dashboard backend | `openspace/dashboard_server.py` | Flask API on `:7788` |
| Dashboard frontend | `frontend/` | React + Vite + Tailwind; Node ≥ 20 |
| Cloud integration | `openspace/cloud/` | Upload/download skills to open-space.cloud |
| Docker stack | `docker-compose.yml` | runtime + dashboard + agents-monitor services |
| Benchmark harness | `gdpval_bench/` | Evaluation tasks for skill quality |

CLI entry points (from `pyproject.toml`):
- `openspace-mcp` — MCP server (primary integration point)
- `openspace-dashboard` — dashboard Flask backend
- `openspace-server` — local server
- `openspace-download-skill` / `openspace-upload-skill` — cloud skill CLI

## Build & Run

**Python install (Windows):**
```powershell
pip install -e ".[windows]"
openspace-mcp --help   # verify
```

**Frontend dev server:**
```powershell
cd frontend
npm install
cp .env.example .env   # first time only; edit VITE_API_PROXY_TARGET if needed
npm run dev
```

**Dashboard backend** (separate terminal):
```powershell
openspace-dashboard --host 127.0.0.1 --port 7788
```

**Full Docker stack:**
```powershell
docker compose up -d --build
```

**Linting / tests** (dev extras: `pip install -e ".[dev]"`):
```powershell
black openspace/        # format
flake8 openspace/       # lint
mypy openspace/         # type-check
pytest                  # tests (requires pytest-asyncio)
```

See [INSTALL_FORK_WINDOWS.md](../INSTALL_FORK_WINDOWS.md) for the full Windows rollout script.

## Fork Conventions

- **Never push to `upstream` (HKUDS/OpenSpace).** All pushes go to `origin` (JZKK720).
- **Sync strategy:** rebase our Cubecloud commits onto `upstream/main`, then force-push to `origin` with `--force-with-lease`. See [FORK_MAIN_PR.md](../FORK_MAIN_PR.md).
- **Cubecloud-specific commits are tagged** (`cubecloud-YYYY.MM.DD`). Preserve these tags when rebasing.
- **Branding is off-limits** unless explicitly requested. Do not modify `BRAND_ASSETS.md`, `TRADEMARKS.md`, Cubecloud logos, or brand-related UI strings without explicit instruction.

## Key Conventions

- **Skill safety**: Skills go through `check_skill_safety` automatically; never bypass it.  
- **litellm version**: Upstream pinned `litellm<1.82.7` (PYSEC-2026-2 supply-chain fix). Keep this pin in sync.
- **Env vars**: `OPENSPACE_MODEL`, `OPENSPACE_LLM_API_KEY`, `OPENSPACE_LLM_API_BASE` control model routing. See `docker-compose.yml` for the full set.
- **Skill dirs priority**: `OPENSPACE_HOST_SKILL_DIRS` > `config_grounding.json` > `openspace/skills/`. See [openspace/skills/README.md](../openspace/skills/README.md).
- **Frontend env**: copy `.env.example` → `.env` in `frontend/` before first run; never commit `.env`.

## Important Docs

- Architecture & contributing: [CONTRIBUTING.md](../CONTRIBUTING.md)
- Windows install: [INSTALL_FORK_WINDOWS.md](../INSTALL_FORK_WINDOWS.md)
- Brand policy: [BRAND_ASSETS.md](../BRAND_ASSETS.md), [TRADEMARKS.md](../TRADEMARKS.md)
- Skill authoring: [openspace/skills/README.md](../openspace/skills/README.md)
- Dashboard frontend: [frontend/README.md](../frontend/README.md)
- Benchmark: [gdpval_bench/README.md](../gdpval_bench/README.md)
