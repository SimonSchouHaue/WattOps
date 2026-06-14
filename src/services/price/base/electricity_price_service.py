from abc import ABC, abstractmethod
from datetime import date, datetime

from models.result import Result


class ElectricityPriceService(ABC):
    @abstractmethod
    def get_prices(self, for_date: date) -> Result[list[tuple[datetime, float]]]: ...
