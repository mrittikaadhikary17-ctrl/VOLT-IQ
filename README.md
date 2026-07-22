# EV Supply Chain & Asset Intelligence Platform

An AI-assisted operations platform for industrial/commercial EV fleets — built for the "AI for Industrial EV Supply Chain & Asset Intelligence: Accelerating Net Zero" hackathon problem statement.

It combines a multi-agent input/synthesis layer with a live fleet dashboard, so a fleet manager can log real telemetry for a named vehicle and immediately see it reflected — battery health, risk status, and position — across the whole fleet view.

---

## What's in here

| File | Role |
|---|---|
| `Actual_Fleet.html` | Data-entry + agent layer. Enter a vehicle name plus IoT telemetry, environmental/supply conditions, and route/aero conditions. Runs an instant local preview, then POSTs the inputs to the backend for synthesis. Also includes a **Rename Vehicle** tool. |
| `backend.py` | FastAPI backend. Runs the actual agent math (energy demand, degradation risk, SoH estimate, carbon savings vs. diesel baseline), stores the latest synthesized result per vehicle, and serves both HTML pages same-origin. |
| `dashboard.html` | Live fleet dashboard. Polls the backend every few seconds and renders real per-vehicle data (Battery Health, Fleet Readiness map) once at least one vehicle has been submitted — falls back to a demo animation otherwise. |

### How data flows

```
Actual_Fleet.html  --POST /api/vehicles-->  backend.py  --stores in memory-->
                                                  |
dashboard.html  <--GET /api/vehicles (polled)-----+
```

---

## Quickstart

```bash
pip install fastapi uvicorn --break-system-packages
uvicorn backend:app --reload --port 8000
```

Then open in your browser:

- **`http://localhost:8000/actual_fleet.html`** — enter a vehicle and run the agents
- **`http://localhost:8000/`** — the live dashboard

Submit a few differently-named vehicles from Actual_Fleet.html and watch them appear on the dashboard within a few seconds.

---

## Agent logic (current implementation)

All three "agents" currently live as pure functions inside `backend.py::synthesize()` — no LLM calls yet, just deterministic/heuristic math, which keeps the demo fast and reproducible:

- **Fleet Planner Agent** — estimates energy required for the route from distance, payload, speed, and a weather-drag multiplier.
- **Telemetry Agent** — flags degradation risk (`LOW` / `WARNING` / `HIGH` / `CRITICAL`) from temperature, cycle count, and state of charge, and produces a heuristic State-of-Health (SoH) score.
- **Supply/Environmental Agent** — estimates CO₂ avoided vs. a diesel baseline, using local grid carbon intensity (ppm CO2e).

> This heuristic layer is intentionally simple so the pipeline (input → synthesis → storage → live dashboard) works end-to-end first. Swapping in a trained model (e.g. an Isolation Forest or LSTM on real telemetry) is the natural next step — see Roadmap.

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend liveness + count of tracked vehicles. Polled by the dashboard's LIVE TELEMETRY indicator. |
| `POST` | `/api/vehicles` | Submit/update a vehicle's telemetry + route + environment inputs. Returns the synthesized output. |
| `GET` | `/api/vehicles` | List all currently tracked vehicles with their latest synthesized data. |
| `PUT` | `/api/vehicles/{old_name}/rename` | Rename a tracked vehicle, keeping its data. `404` if `old_name` doesn't exist, `409` if the new name is already taken. |

---

## Known limitations (be upfront about these in a demo)

- **In-memory storage only** — restarting the backend clears all submitted vehicles. Swap `FLEET_STORE` for SQLite/Postgres for persistence.
- **Heuristic, not learned** — the SoH/degradation/risk math is rule-based, not trained on real telemetry.
- **Supply Risk Radar, Manufacturing Quality, and Carbon Tracker panels on the dashboard are still simulated fleet-wide** and not yet wired to individually submitted vehicles.
- **Single-process, no auth** — fine for a hackathon demo, not production-ready.

---

## Roadmap

- [ ] Replace heuristic SoH/degradation with a trained model (Isolation Forest or LSTM) on real/synthetic time-series telemetry, and surface a "lead time" metric — how many days earlier the model flags degradation vs. a traditional BMS threshold.
- [ ] Add a Supply Risk agent that reads real/simulated supplier and news data.
- [ ] Persist `FLEET_STORE` to a real database.
- [ ] Wire Carbon Tracker and Manufacturing Quality panels to real per-vehicle/per-batch data.
- [ ] Add authentication and multi-user support.

---

## Contributors

| Name | Role |
|---|---|
| A | 1 |
| B | 2 |
| C | 3 |
| D | 4 |

---

## Tech stack

- **Backend:** Python, FastAPI
- **Frontend:** Vanilla HTML/CSS/JS (no build step — open directly or serve via FastAPI)
- **Data:** In-memory store (swap for SQLite/Postgres for persistence)
