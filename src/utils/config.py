import os
from dataclasses import dataclass


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    service_bus_connection: str
    planner_queue_name: str
    price_threshold: float
    solar_output_threshold_kwh: float
    site_id: str
    device_id: str
    grid_first_start_hour: int
    grid_first_min_minutes: int
    grid_first_max_minutes: int
    price_api_url: str
    price_api_key: str
    solar_forecast_api_urls: tuple[str, ...]
    growatt_api_base_url: str
    growatt_dry_run: bool
    key_vault_url: str
    growatt_api_secret_name: str
    growatt_api_key: str

    @classmethod
    def from_env(cls) -> "Settings":
        raw_forecast_urls = os.getenv("SOLAR_FORECAST_API_URLS", "")
        forecast_urls = tuple(
            url.strip() for url in raw_forecast_urls.split(",") if url.strip()
        )

        return cls(
            service_bus_connection=os.getenv("SERVICE_BUS_CONNECTION", ""),
            planner_queue_name=os.getenv("PLANNER_QUEUE_NAME", "planner-actions"),
            price_threshold=float(os.getenv("PRICE_THRESHOLD", "0.05")),
            solar_output_threshold_kwh=float(
                os.getenv("SOLAR_OUTPUT_THRESHOLD_KWH", "20")
            ),
            site_id=os.getenv("SITE_ID", "home-1"),
            device_id=os.getenv("DEVICE_ID", "growatt-1"),
            grid_first_start_hour=int(os.getenv("GRID_FIRST_START_HOUR", "6")),
            grid_first_min_minutes=int(os.getenv("GRID_FIRST_MIN_MINUTES", "60")),
            grid_first_max_minutes=int(os.getenv("GRID_FIRST_MAX_MINUTES", "360")),
            price_api_url=os.getenv("PRICE_API_URL", ""),
            price_api_key=os.getenv("PRICE_API_KEY", ""),
            solar_forecast_api_urls=forecast_urls,
            growatt_api_base_url=os.getenv(
                "GROWATT_API_BASE_URL", "https://api.growatt.com"
            ),
            growatt_dry_run=_as_bool(
                os.getenv("GROWATT_DRY_RUN", "true"), default=True
            ),
            key_vault_url=os.getenv("KEY_VAULT_URL", ""),
            growatt_api_secret_name=os.getenv(
                "GROWATT_API_SECRET_NAME", "growatt-api-key"
            ),
            growatt_api_key=os.getenv("GROWATT_API_KEY", ""),
        )
