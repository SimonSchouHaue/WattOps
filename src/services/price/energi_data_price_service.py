from datetime import date, datetime, timezone

import requests

from models.result import Result
from utils.config import Settings
from services.price.base.electricity_price_service import ElectricityPriceService

BASE_URL = "https://api.energidataservice.dk/dataset/DayAheadPrices"


class EnergiDataPriceService(ElectricityPriceService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_prices(self, for_date: date) -> Result[list[tuple[datetime, float]]]:
        params = {
            "offset": 0,
            "start": f"{for_date.isoformat()}T00:00",
            "end": f"{for_date.isoformat()}T23:45",
            "filter": f'{{"PriceArea":["{self.settings.price_area}"]}}',
            "sort": "TimeUTC ASC",
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=15)

            if not response.ok:
                return Result.fail(
                    f"energidataservice.dk HTTP {response.status_code}: {response.text}"
                )

            data = response.json()
            records = data.get("records", [])

            if not records:
                return Result.fail(
                    f"energidataservice.dk returned no prices"
                    f" for {for_date} ({self.settings.price_area})"
                )

            prices: list[tuple[datetime, float]] = []
            for record in records:
                ts = datetime.fromisoformat(record["TimeUTC"]).replace(
                    tzinfo=timezone.utc
                )
                price_dkk_per_kwh = record["DayAheadPriceDKK"] / 1000.0
                prices.append((ts, price_dkk_per_kwh))

            return Result.ok(prices)

        except requests.exceptions.Timeout:
            return Result.fail("Request timed out")
