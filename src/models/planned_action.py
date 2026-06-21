from dataclasses import dataclass
from enum import Enum

from utils.config import utc_now_iso


class CommandName(str, Enum):
    SET_EXPORT_LIMIT = "set_export_limit"
    DISABLE_EXPORT_LIMIT = "disable_export_limit"
    SET_AC_CHARGE_WINDOW = "set_ac_charge_window"
    DISABLE_AC_CHARGE_WINDOW = "disable_ac_charge_window"
    ENABLE_GRID_FIRST = "enable_grid_first"
    DISABLE_GRID_FIRST = "disable_grid_first"


@dataclass(frozen=True)
class Command:
    name: CommandName
    value: str | int | float
    unit: str


@dataclass(frozen=True)
class Window:
    start: str
    end: str


@dataclass(frozen=True)
class Reason:
    type: str
    details: dict


@dataclass(frozen=True)
class PlannedAction:
    correlation_id: str
    command: Command
    window: Window
    reason: Reason
    scheduled_at: str

    def to_message(self) -> dict:
        command_name = (
            self.command.name.value
            if isinstance(self.command.name, CommandName)
            else str(self.command.name)
        )
        return {
            "schema_version": "1.0",
            "correlation_id": self.correlation_id,
            "command": {
                "name": command_name,
                "value": self.command.value,
                "unit": self.command.unit,
            },
            "window": {
                "start": self.window.start,
                "end": self.window.end,
            },
            "reason": {
                "type": self.reason.type,
                "details": self.reason.details,
            },
            "scheduled_at": self.scheduled_at,
            "created_at": utc_now_iso(),
        }

    @classmethod
    def from_message(cls, message: dict) -> "PlannedAction":
        command_name_raw = message["command"]["name"]
        return cls(
            command=Command(
                name=CommandName(command_name_raw),
                value=message["command"]["value"],
                unit=message["command"].get("unit", ""),
            ),
            window=Window(
                start=message["window"]["start"],
                end=message["window"]["end"],
            ),
            reason=Reason(
                type=message["reason"]["type"],
                details=message["reason"].get("details", {}),
            ),
            correlation_id=message.get("correlation_id", "none"),
            scheduled_at=message["scheduled_at"],
        )
