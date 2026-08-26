from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass
class Settings:
    db_path: Path = Path(os.getenv("SAL_HACHAM_DB", str(BASE_DIR / "data" / "sal_hacham.sqlite3")))
    max_price_age_hours: int = int(os.getenv("SAL_HACHAM_MAX_AGE_HOURS", "5"))
    default_radius_km: float = float(os.getenv("SAL_HACHAM_RADIUS_KM", "30"))
    demo_mode: bool = os.getenv("SAL_HACHAM_DEMO", "1").strip().lower() not in {"0", "false", "no"}
    raw_dir: Path = Path(os.getenv("SAL_HACHAM_RAW_DIR", str(BASE_DIR / "data" / "raw")))
    api_token: str = os.getenv("SAL_HACHAM_API_TOKEN", "").strip()
    max_cached_cities: int = max(1, min(5, int(os.getenv("SAL_HACHAM_MAX_CITIES", "5"))))
    active_city_refresh_hours: int = max(1, int(os.getenv("SAL_HACHAM_ACTIVE_CITY_HOURS", "4")))
    inactive_city_refresh_hours: int = max(4, int(os.getenv("SAL_HACHAM_SAVED_CITY_HOURS", "24")))
    store_directory_refresh_hours: int = max(4, int(os.getenv("SAL_HACHAM_STORE_DIRECTORY_HOURS", "24")))
    price_history_days: int = max(1, min(365, int(os.getenv("SAL_HACHAM_HISTORY_DAYS", "30"))))

settings = Settings()
