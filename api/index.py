"""Latency analytics endpoint for the eShopCo Vercel assignment."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="eShopCo latency analytics")

# The dashboard can call this API from any website. The browser preflight is
# handled by CORSMiddleware; the endpoint itself accepts POST requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


class AnalyticsRequest(BaseModel):
    regions: list[str] = Field(..., description="Region names to summarize")
    threshold_ms: float = Field(..., description="Latency breach threshold")


def _find_data_file() -> Path:
    """Find the supplied bundle in common project locations or via env var."""
    configured = os.environ.get("TELEMETRY_FILE")
    candidates = ([Path(configured)] if configured else []) + [
        Path(__file__).resolve().parent / "q-vercel-latency.json",
        Path(__file__).resolve().parent.parent / "q-vercel-latency.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "q-vercel-latency.json was not found. Put it in the project root or api/ folder."
    )


def _records(value: Any) -> list[dict[str, Any]]:
    """Accept a JSON list or a common object wrapper containing that list."""
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in ("data", "records", "telemetry", "pings", "results"):
            if isinstance(value.get(key), list):
                return [row for row in value[key] if isinstance(row, dict)]
        # Some bundles group rows by region: {"emea": [{...}], "apac": [...]}.
        grouped: list[dict[str, Any]] = []
        for region, rows in value.items():
            if isinstance(rows, list):
                grouped.extend(
                    ({"region": region, **row} for row in rows if isinstance(row, dict))
                )
        if grouped:
            return grouped
    raise ValueError("The telemetry JSON must contain a list of records.")


def _field(record: dict[str, Any], choices: tuple[str, ...]) -> Any:
    normalized = {str(key).lower().replace("-", "_"): value for key, value in record.items()}
    for key in choices:
        if key in normalized:
            return normalized[key]
    return None


def _percentile_95(values: list[float]) -> float:
    """Return the interpolated 95th percentile (linear, as in common analytics tools)."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * 0.95
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


@app.post("/")
def calculate_analytics(request: AnalyticsRequest) -> dict[str, Any]:
    try:
        with _find_data_file().open("r", encoding="utf-8") as telemetry_file:
            rows = _records(json.load(telemetry_file))
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except (json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=500, detail=f"Invalid telemetry bundle: {error}") from error

    response: dict[str, Any] = {}
    for requested_region in request.regions:
        region_rows = [
            row for row in rows
            if str(_field(row, ("region", "region_name", "location")) or "").lower()
            == requested_region.lower()
        ]
        latencies: list[float] = []
        uptimes: list[float] = []
        for row in region_rows:
            latency = _field(row, ("latency_ms", "latency", "response_time_ms", "response_time"))
            uptime = _field(row, ("uptime", "uptime_pct", "uptime_percent", "availability"))
            try:
                if latency is not None:
                    latencies.append(float(latency))
                if uptime is not None:
                    uptimes.append(float(uptime))
            except (TypeError, ValueError):
                continue

        if not latencies or not uptimes:
            raise HTTPException(
                status_code=422,
                detail=f"No usable latency and uptime records found for region '{requested_region}'.",
            )

        response[requested_region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": _percentile_95(latencies),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(value > request.threshold_ms for value in latencies),
        }
    return response
