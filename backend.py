"""
EV Fleet Intelligence backend.

Runs the "agent" math that used to live only in Actual_Fleet.html's JS,
stores the latest synthesized result per named vehicle in memory, and
serves both dashboard.html and Actual_Fleet.html same-origin so there's
no CORS to fight with during the hackathon.

Run:
    pip install fastapi uvicorn --break-system-packages
    uvicorn backend:app --reload --port 8000

Then open:
    http://localhost:8000/                 -> dashboard.html
    http://localhost:8000/actual_fleet.html -> Actual_Fleet.html
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).parent

app = FastAPI(title="EV Fleet Intelligence Backend")

# In-memory store: { vehicle_name: synthesized_output_dict }
# Swap this for a real DB later; fine for a hackathon demo.
FLEET_STORE: dict[str, dict] = {}


class VehicleInput(BaseModel):
    name: str = Field(..., description="Vehicle identifier, e.g. VAN-014")
    temp: float = Field(..., description="Ambient temperature, °C")
    speed: float = Field(..., description="Vehicle speed, km/h")
    charge: float = Field(..., description="Current state of charge, %")
    cycles: float = Field(..., description="Charge cycles logged")
    distance: float = Field(..., description="Route distance, km")
    payload: float = Field(..., description="Payload weight, kg")
    weather_drag: float = Field(..., description="Aero drag multiplier from weather, e.g. 1.0-1.3")
    ghg: float = Field(..., description="Local grid GHG concentration, ppm CO2e")


def synthesize(v: VehicleInput) -> dict:
    """Port of the three agents' math (Fleet Planner, Telemetry, Supply/Env)."""

    # --- Fleet Planner Agent: energy required ---
    base_energy_per_km = 1.2 + (v.payload / 10000)
    speed_factor = 1.0 if v.speed <= 60 else 1 + (v.speed - 60) * 0.015
    total_energy = v.distance * base_energy_per_km * speed_factor * v.weather_drag

    # --- Telemetry Agent: degradation risk + a numeric SoH estimate ---
    risk_level, risk_reason = "LOW", "Optimal parameters."
    if v.temp > 40:
        risk_level, risk_reason = "CRITICAL", "Thermal runaway risk high due to temp > 40C."
    elif v.temp < 0:
        risk_level, risk_reason = "HIGH", "Cold weather significantly reducing cell efficiency."
    elif v.cycles > 2000:
        risk_level, risk_reason = "HIGH", "High cycle count indicates imminent capacity fade."
    elif v.charge < (total_energy / 3):
        risk_level, risk_reason = "WARNING", "Current SoC may be insufficient for route given drag factors."

    # Heuristic SoH score (0-100) — replace with a trained model later.
    health = 100.0
    health -= v.cycles / 50.0
    if v.temp > 40:
        health -= (v.temp - 40) * 1.5
    if v.temp < 0:
        health -= abs(v.temp) * 1.2
    health = max(5.0, min(100.0, health))

    degradation_rate = max(0.05, min(0.6, round((v.cycles / 10000) * 2, 2)))

    status_map = {"CRITICAL": "maint", "HIGH": "maint", "WARNING": "charge", "LOW": "active"}
    status = status_map[risk_level]

    # --- Supply/Env Agent: carbon savings vs. diesel baseline ---
    diesel_emissions = v.distance * 1.0  # kg CO2e, ~1kg/km diesel baseline
    ev_emissions = total_energy * (v.ghg / 1000)
    carbon_saved = max(diesel_emissions - ev_emissions, 0.0)

    return {
        "name": v.name,
        "health": round(health, 1),
        "cycles": v.cycles,
        "degradation_rate": degradation_rate,
        "status": status,
        "risk_level": risk_level,
        "risk_reason": risk_reason,
        "energy_kwh": round(total_energy, 1),
        "carbon_saved_kg": round(carbon_saved, 1),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


class RenameInput(BaseModel):
    new_name: str = Field(..., description="The new name to give this vehicle")


@app.get("/health")
def health():
    return {"status": "ok", "vehicles_tracked": len(FLEET_STORE)}


@app.post("/api/vehicles")
def upsert_vehicle(payload: VehicleInput):
    result = synthesize(payload)
    FLEET_STORE[payload.name] = result
    return result


@app.get("/api/vehicles")
def list_vehicles():
    return JSONResponse(list(FLEET_STORE.values()))


@app.put("/api/vehicles/{old_name}/rename")
def rename_vehicle(old_name: str, payload: RenameInput):
    if old_name not in FLEET_STORE:
        raise HTTPException(status_code=404, detail=f"Vehicle '{old_name}' not found")
    if payload.new_name in FLEET_STORE and payload.new_name != old_name:
        raise HTTPException(status_code=409, detail=f"A vehicle named '{payload.new_name}' already exists")
    record = FLEET_STORE.pop(old_name)
    record["name"] = payload.new_name
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    FLEET_STORE[payload.new_name] = record
    return record


# --- Serve the two dashboard pages same-origin (no CORS needed) ---
@app.get("/")
def serve_dashboard():
    return FileResponse(APP_DIR / "dashboard.html")


@app.get("/dashboard.html")
def serve_dashboard_named():
    return FileResponse(APP_DIR / "dashboard.html")


@app.get("/actual_fleet.html")
def serve_actual_fleet():
    return FileResponse(APP_DIR / "Actual_Fleet.html")
