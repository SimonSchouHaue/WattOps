from abc import ABC, abstractmethod
from datetime import date, datetime

from models.result import Result


class SunriseService(ABC):
    @abstractmethod
    def get_sunrise(self, for_date: date) -> Result[datetime]: ...
