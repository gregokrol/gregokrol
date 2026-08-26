from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import secrets
import subprocess
import sys
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .basket import compare_basket
from .city_cache import (
    cache_health,
    cached_cities,
    city_cache_status,
    cleanup_evicted_storage,
    queue_city_if_due,
    touch_city,
)
from .config import settings
from .db import init_db
from .demo import seed_demo
from .offers import list_store_offers
from .price_history import prune_price_history
from .service import data_health, list_chains, list_cities, list_stores_filtered, search_prices, status
from .source_registry import CHAIN_SOURCES


class BasketItem(BaseModel):
    q: str = Field(min_length=1, max_length=120)
    qty: float = Field(default=1, gt=0, le=100)


class BasketRequest(BaseModel):
    items: list[BasketItem] = Field(min_length=1, max_length=30)
    city: str | None = Field(default=None, max_length=120)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float = Field(default=settings.default_radius_km, gt=0, le=100)
    chains: list[str] | None = None
    include_coupons: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.db_path)
    prune_price_history(settings.db_path, settings.price_history_days)
    if settings.demo_mode:
        seed_demo(settings.db_path)
    yield


app = FastAPI(title="סל חכם", version="7.6.0", lifespan=lifespan)
STATIC = Path(__file__).resolve().parent / "static"
ROOT = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def protect_public_api(request: Request, call_next):
    if request.url.path.startswith("/api/") and settings.api_token:
        supplied = request.headers.get("authorization", "")
        expected = f"Bearer {settings.api_token}"
        if not secrets.compare_digest(supplied, expected):
            return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    return await call_next(request)


def _validate_location(lat: float | None, lng: float | None) -> None:
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=422, detail="lat and lng must be supplied together")


def _launch_city_refresh(city: str) -> None:
    logs = settings.raw_dir.parent.parent / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / "sync.log"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with log_path.open("a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "sync_prices.py"), "--city", city],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            creationflags=creationflags,
        )


def _activate_city(city: str | None) -> dict | None:
    if not city or not city.strip():
        return None
    if settings.demo_mode:
        return None
    touched = touch_city(settings.db_path, city, settings.max_cached_cities)
    if not touched:
        return None
    cleanup_evicted_storage(settings.raw_dir, touched["evicted"])
    queued = queue_city_if_due(
        settings.db_path,
        touched["city_key"],
        active_hours=settings.active_city_refresh_hours,
        inactive_hours=settings.inactive_city_refresh_hours,
    )
    if queued and not settings.demo_mode:
        try:
            _launch_city_refresh(touched["city_name"])
        except Exception as exc:
            # The hourly scheduler will pick up the queued city even if spawning the
            # immediate worker failed, so the request can still return cached data.
            print(f"Could not start city refresh: {type(exc).__name__}: {exc}", flush=True)
    return city_cache_status(
        settings.db_path,
        touched["city_name"],
        max_cities=settings.max_cached_cities,
        active_hours=settings.active_city_refresh_hours,
        inactive_hours=settings.inactive_city_refresh_hours,
    )


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "auth_required": bool(settings.api_token),
        **status(settings.db_path, settings.max_price_age_hours, settings.price_history_days),
        **cache_health(settings.db_path, settings.max_cached_cities),
    }


@app.get("/api/data-health")
def health_detail():
    return data_health(settings.db_path, settings.max_price_age_hours)


@app.get("/api/cities")
def cities():
    return {"cities": list_cities(settings.db_path)}


@app.get("/api/city-cache")
def city_cache():
    return {
        "max_cities": settings.max_cached_cities,
        "active_refresh_hours": settings.active_city_refresh_hours,
        "saved_refresh_hours": settings.inactive_city_refresh_hours,
        "cities": cached_cities(settings.db_path),
    }


@app.get("/api/chains")
def chains():
    active = {c["key"]: c for c in list_chains(settings.db_path)}
    return {
        "chains": [
            {
                "key": key,
                "name": name,
                "stores": active.get(key, {}).get("stores", 0),
                "configured": True,
            }
            for key, name in CHAIN_SOURCES
        ]
    }


@app.get("/api/stores")
def stores(
    city: str | None = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float, Query(gt=0, le=100)] = settings.default_radius_km,
    chain: list[str] | None = Query(default=None),
):
    _validate_location(lat, lng)
    rows = list_stores_filtered(settings.db_path, city, lat, lng, radius_km, chain, settings.max_price_age_hours)
    return {"count": len(rows), "stores": rows}


@app.get("/api/store-offers")
def store_offers(
    store_id: Annotated[str, Query(min_length=1, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=150)] = 60,
):
    result = list_store_offers(settings.db_path, store_id, settings.max_price_age_hours, limit)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail="store not found")
    return result


@app.get("/api/search")
def search(
    q: Annotated[str, Query(min_length=1, max_length=120)],
    city: str | None = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float, Query(gt=0, le=100)] = settings.default_radius_km,
    chain: list[str] | None = Query(default=None),
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
):
    _validate_location(lat, lng)
    cache = _activate_city(city)
    result = search_prices(
        settings.db_path,
        q,
        city,
        lat,
        lng,
        radius_km,
        settings.max_price_age_hours,
        chain,
        limit,
        history_days=settings.price_history_days,
    )
    result["city_cache"] = cache
    return result


@app.post("/api/basket")
def basket(payload: BasketRequest):
    _validate_location(payload.lat, payload.lng)
    cache = _activate_city(payload.city)
    result = compare_basket(
        settings.db_path,
        [item.model_dump() for item in payload.items],
        payload.city,
        payload.lat,
        payload.lng,
        payload.radius_km,
        settings.max_price_age_hours,
        payload.chains,
        payload.include_coupons,
    )
    result["city_cache"] = cache
    return result
