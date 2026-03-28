# Cubecloud Frontend

A dashboard frontend for Cubecloud, providing skill browsing, lineage visualization, and workflow inspection.

## Prerequisites

- **Node.js ≥ 20**

## First-time Setup

1. **Copy the environment file**

```bash
cd frontend
cp .env.example .env
```

Edit `.env` if your backend runs on a different host/port:

```dotenv
VITE_HOST=127.0.0.1
VITE_PORT=3888
VITE_API_PROXY_TARGET=http://127.0.0.1:7788
VITE_API_BASE_URL=/api/v1
```

2. **Install dependencies**

```bash
npm install
```

3. **Start the backend** (in a separate terminal)

```bash
# option A – CLI entry point
openspace-dashboard --host 127.0.0.1 --port 7788

# option B – from the repo root
python -m openspace.dashboard_server --host 127.0.0.1 --port 7788
```

> Requires Python ≥ 3.12 with `flask` installed.

4. **Start the frontend**

```bash
npm run dev
```

The dev server will be available at `http://127.0.0.1:3888` (or whatever `VITE_PORT` you set).

## Subsequent Starts

Once `.env` is configured and dependencies are installed, you only need:

```bash
# terminal 1 – backend
openspace-dashboard --host 127.0.0.1 --port 7788

# terminal 2 – frontend
cd frontend
npm run dev
```

## Default URLs

| Service             | URL                      |
| ------------------- | ------------------------ |
| Frontend dev server | `http://127.0.0.1:3888`  |
| Dashboard API       | `http://127.0.0.1:7788`  |

## Advanced Configuration

### Bypass the Vite proxy

If you prefer to call the backend directly (e.g. for debugging), you can set `VITE_API_BASE_URL` to the full backend URL:

```bash
VITE_API_BASE_URL=http://127.0.0.1:7788/api/v1 npm run dev
```

## Production Build

```bash
cd frontend
npm run build
```

After building, start the backend and it will serve `frontend/dist` as static files automatically — no need to run the dev server.

## Docker Compose

If you want the packaged local web deployment, run this from the repo root:

```bash
docker compose up --build -d
```

Open these URLs after the services become healthy:
- `http://127.0.0.1:7788` for OpenSpace
- `http://127.0.0.1:5173` for Agents Monitor

What this does:
- Builds the React frontend and copies `frontend/dist` into the image.
- Installs the Python package and starts `openspace.dashboard_server` on `0.0.0.0:7788`.
- Builds `showcase/my-daily-monitor` and starts its Node production server on `0.0.0.0:5173`.
- Connects the dashboard to Agents Monitor with separate internal and public URLs so health checks work inside Docker and browser links still open on the host.
- Persists dashboard state by mounting `./.openspace` and `./logs` into the container.

Useful commands:

```bash
docker compose logs -f
docker compose down
```

To change the exposed local ports:

```bash
CUBECLOUD_PORT=8080 AGENTS_MONITOR_PORT=5174 docker compose up --build -d
```

This Compose stack is for the **web apps**. OpenSpace features that depend on direct host GUI or shell automation should still run on the host machine.

## Main Pages

- **Dashboard** – overall health, pipeline stages, top skills, recent workflows
- **Skills** – searchable skill list and score breakdown
- **Skill Detail** – source preview, lineage graph, scoring metrics, recent analyses
- **Workflows** – recorded workflow sessions from `logs/recordings` and `logs/trajectories`
- **Workflow Detail** – timeline, artifacts, metadata, selected skills, plans, and decisions
