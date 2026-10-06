import json
from pathlib import Path
from typing import List, Optional
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Enable CORS for all origins (Required by assignment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load telemetry data once when the serverless container starts
DATA_PATH = Path(__file__).parent / "q-vercel-latency.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    TELEMETRY_DATA = json.load(f)


class RequestPayload(BaseModel):
    regions: List[str]
    threshold_ms: float


@app.get("/")
def home():
    return {"status": "ok", "message": "eShopCo Latency Analytics API"}


@app.post("/")
@app.post("/api")
def analyze_telemetry(payload: RequestPayload):
    requested_regions = set(payload.regions)
    threshold = payload.threshold_ms

    # Group telemetry records by region
    region_records = {r: [] for r in requested_regions}
    for record in TELEMETRY_DATA:
        reg = record.get("region")
        if reg in requested_regions:
            region_records[reg].append(record)

    results = {}

    for reg in payload.regions:
        records = region_records.get(reg, [])
        if not records:
            results[reg] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0,
            }
            continue

        latencies = [r["latency"] for r in records]
        uptimes = [r["uptime"] for r in records]

        # Compute required metrics
        avg_lat = float(np.mean(latencies))
        p95_lat = float(np.percentile(latencies, 95))
        avg_up = float(np.mean(uptimes))
        breach_count = int(sum(1 for l in latencies if l > threshold))

        results[reg] = {
            "avg_latency": avg_lat,
            "p95_latency": p95_lat,
            "avg_uptime": avg_up,
            "breaches": breach_count,
        }

    return results