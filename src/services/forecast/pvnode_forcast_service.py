import logging
from datetime import date

import requests

from models.result import Result
from utils.config import Settings
from services.forecast.base.solar_forecast_service import SolarForecastService

logger = logging.getLogger("wattops.pvnode_forecast_service")

BASE_URL = "https://api.pvnode.com/v1/forecast"


class PVnodeForecastService(SolarForecastService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_forecast_kwh(self, for_date: date) -> Result[float]:
        s = self.settings
        params = {
            "latitude": s.solar_latitude,
            "longitude": s.solar_longitude,
            "slope": s.solar_panel_tilt,
            "orientation": s.solar_panel_azimuth,
            "pv_power_kw": s.solar_panel_kwp,
            "forecast_days": 1,
            "past_days": 0,
            "required_data": "pv_watts",
        }
        headers = {"Authorization": f"Bearer {s.pvnode_api_key}"}

        try:
            response = requests.get(
                BASE_URL, params=params, headers=headers, timeout=15
            )

            if not response.ok:
                return Result.fail(f"HTTP {response.status_code}: {response.text}")

            data = response.json()

            date_prefix = for_date.isoformat()
            total_wh = 0.0
            found = False

            # 15-minute intervals: pv_watts (W) × 0.25 h = Wh per slot
            for entry in data["values"]:
                dtm = entry.get("dtm", "")
                if dtm.startswith(date_prefix):
                    total_wh += float(entry.get("pv_watts", 0.0)) * 0.25
                    found = True

            if not found:
                return Result.fail(f"No data for {for_date}")

            return Result.ok(total_wh / 1000.0)  # Wh → kWh

        except requests.exceptions.Timeout:
            return Result.fail("Request timed out")
