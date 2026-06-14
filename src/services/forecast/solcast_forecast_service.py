import logging
from datetime import date, datetime, timezone

import requests

from models.result import Result
from utils.config import Settings
from services.forecast.base.solar_forecast_service import SolarForecastService

logger = logging.getLogger("wattops.solcast_forecast_service")

BASE_URL = "https://api.solcast.com.au/rooftop_sites"


class SolcastForecastService(SolarForecastService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_forecast_kwh(self, for_date: date) -> Result[float]:
        url = f"{BASE_URL}/{self.settings.solcast_resource_id}/forecasts?format=json"
        headers = {"Authorization": f"Bearer {self.settings.solcast_api_key}"}

        try:
            response = requests.get(url, headers=headers, timeout=15)

            if not response.ok:
                return Result.fail(f"HTTP {response.status_code}: {response.text}")

            forecasts = response.json().get("forecasts", [])
            if not forecasts:
                return Result.fail("No forecast data returned from Solcast")

            # Each period is PT30M (30 min), pv_estimate is average kW over the period.
            # Energy per period = pv_estimate * 0.5 kWh.
            # Filter periods whose period_end falls on for_date (in UTC).
            daily_kwh = 0.0
            matched = 0
            for period in forecasts:
                period_end_str = period.get("period_end", "")
                if not period_end_str:
                    continue
                period_end = datetime.fromisoformat(
                    period_end_str.replace("Z", "+00:00")
                )
                if period_end.date() == for_date:
                    daily_kwh += period.get("pv_estimate", 0.0) * 0.5
                    matched += 1

            if matched == 0:
                return Result.fail(f"No Solcast periods found for {for_date}")

            return Result.ok(daily_kwh)

        except requests.exceptions.Timeout:
            return Result.fail("Solcast request timed out")
