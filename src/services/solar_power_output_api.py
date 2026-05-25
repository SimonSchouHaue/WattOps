from __future__ import annotations

import logging
from datetime import date

import requests

from src.utils.config import Settings

logger = logging.getLogger("wattops.providers")


class SolarForecastProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_forecast_kwh(self, for_date: date) -> float:
        if not self._settings.solar_forecast_api_urls:
            return 0.0

        values: list[float] = []
        for url in self._settings.solar_forecast_api_urls:
            try:
                forecast = self._fetch_single(url, for_date)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Solar forecast source failed for '%s': %s", url, exc)
                continue
            values.append(forecast)

        if not values:
            raise ValueError("All configured solar forecast sources failed")

        return sum(values) / len(values)

    def _fetch_single(self, url: str, for_date: date) -> float:
        response = requests.get(url, params={"date": for_date.isoformat()}, timeout=15)
        response.raise_for_status()
        payload = response.json()

        if "forecast_kwh" in payload:
            return float(payload["forecast_kwh"])
        if "estimate_kwh" in payload:
            return float(payload["estimate_kwh"])
        if "forecast_wh" in payload:
            return float(payload["forecast_wh"]) / 1000.0

        raise ValueError(
            "Forecast payload does not contain forecast_kwh/estimate_kwh/forecast_wh"
        )
