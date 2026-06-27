import os
from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def str_to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    grid_first_max_minutes: int
    grid_first_min_minutes: int
    grid_first_minutes_after_sunrise: int
    grid_first_sunrise_fallback_hour: int
    growatt_api_key: str
    growatt_device_serial_number: str
    growatt_discharge_power_percent: int
    growatt_stop_soc_percent: int
    dry_run: bool
    planner_queue_name: str
    price_area: str
    price_export_threshold_dkk_kwh: float
    pvnode_api_key: str
    service_bus_fully_qualified_namespace: str
    solar_latitude: float
    solar_longitude: float
    solar_output_threshold_kwh: float
    solar_panel_azimuth: int
    solar_panel_kwp: float
    solar_panel_tilt: int
    solar_performance_ratio: float
    spike_threshold_multiplier: float
    solcast_api_key: str
    solcast_resource_id: str
    local_timezone: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            grid_first_max_minutes=int(os.getenv("GRID_FIRST_MAX_MINUTES", "360")),
            grid_first_min_minutes=int(os.getenv("GRID_FIRST_MIN_MINUTES", "60")),
            grid_first_minutes_after_sunrise=int(
                os.getenv("GRID_FIRST_MINUTES_AFTER_SUNRISE", "60")
            ),
            grid_first_sunrise_fallback_hour=int(
                os.getenv("GRID_FIRST_SUNRISE_FALLBACK_HOUR", "5")
            ),
            growatt_api_key=os.getenv("GROWATT_API_KEY", ""),
            growatt_device_serial_number=os.getenv("GROWATT_DEVICE_SERIAL_NUMBER", ""),
            growatt_discharge_power_percent=int(
                os.getenv("GROWATT_DISCHARGE_POWER_PERCENT", "50")
            ),
            growatt_stop_soc_percent=int(os.getenv("GROWATT_STOP_SOC_PERCENT", "25")),
            dry_run=str_to_bool(os.getenv("DRY_RUN", "true"), default=True),
            planner_queue_name=os.getenv("PLANNER_QUEUE_NAME", "planned-actions"),
            price_area=os.getenv("PRICE_AREA", "DK1"),
            price_export_threshold_dkk_kwh=float(
                os.getenv("PRICE_EXPORT_THRESHOLD_DKK_KWH", "0.1")
            ),
            pvnode_api_key=os.getenv("PVNODE_API_KEY", ""),
            service_bus_fully_qualified_namespace=os.getenv(
                "ServiceBusConnection__fullyQualifiedNamespace", ""
            ),
            solar_latitude=float(os.getenv("SOLAR_LATITUDE", "0.0")),
            solar_longitude=float(os.getenv("SOLAR_LONGITUDE", "0.0")),
            solar_output_threshold_kwh=float(
                os.getenv("SOLAR_OUTPUT_THRESHOLD_KWH", "20")
            ),
            solar_panel_azimuth=int(os.getenv("SOLAR_PANEL_AZIMUTH", "0")),
            solar_panel_kwp=float(os.getenv("SOLAR_PANEL_KWP", "5.0")),
            solar_panel_tilt=int(os.getenv("SOLAR_PANEL_TILT", "35")),
            solar_performance_ratio=float(os.getenv("SOLAR_PERFORMANCE_RATIO", "0.85")),
            spike_threshold_multiplier=float(
                os.getenv("SPIKE_THRESHOLD_MULTIPLIER", "3")
            ),
            solcast_api_key=os.getenv("SOLCAST_API_KEY", ""),
            solcast_resource_id=os.getenv("SOLCAST_RESOURCE_ID", ""),
            local_timezone=os.getenv("LOCAL_TIMEZONE", "UTC"),
        )
