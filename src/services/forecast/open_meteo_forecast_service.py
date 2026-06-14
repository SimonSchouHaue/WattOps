import logging
from datetime import date

import requests

from models.result import Result
from utils.config import Settings
from services.forecast.base.solar_forecast_service import SolarForecastService

logger = logging.getLogger("wattops.open_meteo_forecast_service")

BASE_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoForecastService(SolarForecastService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_forecast_kwh(self, for_date: date) -> Result[float]:
        s = self.settings

        try:
            response = requests.get(
                BASE_URL,
                params={
                    "latitude": s.solar_latitude,
                    "longitude": s.solar_longitude,
                    "daily": "shortwave_radiation_sum",
                    "start_date": for_date.isoformat(),
                    "end_date": for_date.isoformat(),
                    "timezone": "UTC",
                },
                timeout=15,
            )

            if not response.ok:
                return Result.fail(f"HTTP {response.status_code}: {response.text}")

            radiation_list = (
                response.json().get("daily", {}).get("shortwave_radiation_sum")
            )
            if not radiation_list:
                return Result.fail("Response missing shortwave_radiation_sum")

            irradiance_kwh_m2 = radiation_list[0] / 3.6  # MJ/m² → kWh/m²
            value = irradiance_kwh_m2 * s.solar_panel_kwp
            return Result.ok(value)

        except requests.exceptions.Timeout:
            return Result.fail("Request timed out")
