import logging
from datetime import date, datetime, timezone

import requests

from models.result import Result
from utils.config import Settings
from services.sunrise.base.sunrise_service import SunriseService

logger = logging.getLogger("wattops.sunrise_sunset_service")

BASE_URL = "https://api.sunrise-sunset.org/json"


class SunriseSunsetService(SunriseService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_sunrise(self, for_date: date) -> Result[datetime]:
        s = self.settings

        try:
            response = requests.get(
                BASE_URL,
                params={
                    "lat": s.solar_latitude,
                    "lng": s.solar_longitude,
                    "date": for_date.isoformat(),
                    "formatted": 0,  # UTC ISO 8601 response
                },
                timeout=15,
            )

            if not response.ok:
                return Result.fail(f"HTTP {response.status_code}: {response.text}")

            data = response.json()

            sunrise_str = data.get("results", {}).get("sunrise")
            if not sunrise_str:
                return Result.fail("Response missing sunrise field")

            sunrise_dt = datetime.fromisoformat(sunrise_str).astimezone(timezone.utc)
            return Result.ok(sunrise_dt)

        except requests.exceptions.Timeout:
            return Result.fail("Request timed out")
