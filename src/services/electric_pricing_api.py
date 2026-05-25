from __future__ import annotations

from datetime import date, datetime, time, timezone

import requests

from src.utils.config import Settings


class ElectricityPriceProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_prices(self, for_date: date) -> list[tuple[datetime, float]]:
        if not self._settings.price_api_url:
            return self._fallback_prices(for_date)

        headers = {}
        if self._settings.price_api_key:
            headers["Authorization"] = f"Bearer {self._settings.price_api_key}"

        response = requests.get(
            self._settings.price_api_url,
            params={"date": for_date.isoformat()},
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()

        values = payload.get("prices", payload)
        prices: list[tuple[datetime, float]] = []

        for item in values:
            ts = item.get("timestamp") or item.get("hour")
            price = item.get("price")
            if ts is None or price is None:
                continue

            timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            prices.append((timestamp.astimezone(timezone.utc), float(price)))

        if not prices:
            raise ValueError("Price API returned no usable prices")

        return prices

    def _fallback_prices(self, for_date: date) -> list[tuple[datetime, float]]:
        prices: list[tuple[datetime, float]] = []
        for hour in range(24):
            timestamp = datetime.combine(for_date, time(hour=hour, tzinfo=timezone.utc))
            price = 0.04 if 0 <= hour < 6 else 0.08 if 6 <= hour < 21 else 0.05
            prices.append((timestamp, price))
        return prices
