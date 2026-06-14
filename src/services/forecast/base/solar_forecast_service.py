from abc import ABC, abstractmethod
from datetime import date

from models.result import Result


class SolarForecastService(ABC):
    @abstractmethod
    def get_forecast_kwh(self, for_date: date) -> Result[float]: ...
