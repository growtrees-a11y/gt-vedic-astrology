"""
PROJ-05: Vedic Astrology — FastAPI application layer.
Wraps main.py VedicChart + rules engine behind REST endpoints.
"""
import json
import hashlib
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from main import VedicChart, AstroRulesEngine, load_rules

app = FastAPI(
    title="Vedic Astrology API",
    description="Classical sidereal chart calculations with Redis caching",
    version="0.1.0",
)

# ── Redis cache (optional) ───────────────────────────────────────────

redis_client = None
try:
    import redis
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
except Exception:
    # Graceful degradation — cache disabled when Redis unavailable
    redis_client = None


def _chart_cache_key(birth_date: str, lat: float, lon: float) -> str:
    """Deterministic cache key for chart computations."""
    raw = f"{birth_date}:{lat}:{lon}"
    return "chart:" + hashlib.sha256(raw.encode()).hexdigest()


# ── Models ────────────────────────────────────────────────────────────

class ChartRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: int = 0
    minute: int = 0
    second: int = 0
    lat: float
    lon: float


class RulesRequest(BaseModel):
    planet: Optional[str] = None
    sign: Optional[str] = None
    house: Optional[int] = None


# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/health")
def health():
    status = {"status": "ok"}
    if redis_client:
        status["redis"] = "connected"
    else:
        status["redis"] = "unavailable"
    return status


@app.post("/chart")
def compute_chart(req: ChartRequest):
    """Compute a full Vedic (sidereal) birth chart."""
    dt = datetime(req.year, req.month, req.day, req.hour, req.minute, req.second)

    cache_key = None
    if redis_client:
        cache_key = _chart_cache_key(dt.isoformat(), req.lat, req.lon)
        cached = redis_client.get(cache_key)
        if cached:
            return {"cached": True, **json.loads(cached)}

    chart = VedicChart(dt, req.lat, req.lon)
    result = chart.full_chart()

    if cache_key and redis_client:
        redis_client.setex(cache_key, 3600, json.dumps(result))

    return {"cached": False, **result}


@app.post("/rules")
def evaluate_rules(req: RulesRequest):
    """Evaluate rules against a pre-computed chart snippet."""
    rules_path = os.path.join(os.path.dirname(__file__), "rules.json")
    rules = load_rules(rules_path)
    engine = AstroRulesEngine(rules)
    # Build a minimal chart from request filters
    chart = {
        "planets": {},
        "houses": {},
    }
    if req.planet and req.sign:
        chart["planets"][req.planet] = req.sign
    triggered = engine.evaluate(chart)
    return {"triggered": triggered}


@app.post("/rules/custom")
def evaluate_custom_rules(req: dict):
    """Evaluate custom rules against a chart (rules + chart data in body)."""
    rules = req.get("rules", [])
    chart = req.get("chart", {"planets": {}, "houses": {}})
    engine = AstroRulesEngine(rules)
    triggered = engine.evaluate(chart)
    return {"triggered": triggered}
