import logging
from datetime import date, datetime, timezone

import requests

from models.result import Result
from utils.config import Settings
from services.forecast.base.solar_forecast_service import SolarForecastService

logger = logging.getLogger("wattops.quartz_forecast_service")

BASE_URL = "https://open.quartz.solar/forecast/"


class QuartzForecastService(SolarForecastService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_forecast_kwh(self, for_date: date) -> Result[float]:
        s = self.settings
        timestamp = datetime.combine(for_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )

        payload = {
            "site": {
                "capacity_kwp": s.solar_panel_kwp,
                "latitude": s.solar_latitude,
                "longitude": s.solar_longitude,
                "orientation": s.solar_panel_azimuth,
                "tilt": s.solar_panel_tilt,
            },
            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        try:
            response = requests.post(
                BASE_URL,
                json=payload,
                headers={"accept": "application/json"},
                timeout=15,
            )

            if not response.ok:
                return Result.fail(f"HTTP {response.status_code}: {response.text}")

            power_kw_map: dict = (
                response.json().get("predictions", {}).get("power_kw", {})
            )
            if not power_kw_map:
                return Result.fail("Response missing predictions.power_kw")

            # Each entry is a 15-minute interval; energy (kWh) = power_kw * 0.25 h.
            daily_kwh = 0.0
            matched = 0
            for ts_str, power_kw in power_kw_map.items():
                try:
                    ts = datetime.fromisoformat(ts_str)
                except ValueError:
                    continue
                if ts.date() == for_date:
                    daily_kwh += power_kw * 0.25
                    matched += 1

            if matched == 0:
                return Result.fail(f"No Quartz periods found for {for_date}")

            # Add 10% buffer as Quartz seems to underpredict
            return Result.ok(daily_kwh * 1.1)

        except requests.exceptions.Timeout:
            return Result.fail("Quartz request timed out")
