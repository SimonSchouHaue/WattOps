import logging
from datetime import date

import requests

from models.result import Result
from utils.config import Settings
from services.forecast.base.solar_forecast_service import SolarForecastService

logger = logging.getLogger("wattops.forecast_solar_forecast_service")

BASE_URL = "https://api.forecast.solar/estimate/watthours/day"


class ForecastSolarForecastService(SolarForecastService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_forecast_kwh(self, for_date: date) -> Result[float]:
        s = self.settings
        url = (
            f"{BASE_URL}"
            f"/{s.solar_latitude}"
            f"/{s.solar_longitude}"
            f"/{s.solar_panel_tilt}"
            f"/{s.solar_panel_azimuth-180}"
            f"/{s.solar_panel_kwp}"
        )

        try:
            response = requests.get(url, timeout=15)

            if not response.ok:
                return Result.fail(f"HTTP {response.status_code}: {response.text}")

            result: dict = response.json().get("result", {})
            if not result:
                return Result.fail("Response missing result data")

            date_str = for_date.isoformat()
            if date_str not in result:
                return Result.fail(
                    f"No forecast-solar-forecast data found for {for_date}"
                )

            wh = result[date_str]

            return Result.ok(wh / 1000)  # Wh → kWh

        except requests.exceptions.Timeout:
            return Result.fail("forecast-solar-forecast request timed out")
