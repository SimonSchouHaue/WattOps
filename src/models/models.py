from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Command:
    name: str
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
class Target:
    site_id: str
    device_id: str


@dataclass(frozen=True)
class Policy:
    priority: int = 5
    allow_override: bool = True
    min_duration_minutes: int = 30


@dataclass(frozen=True)
class PlannedAction:
    command: Command
    window: Window
    reason: Reason
    target: Target
    correlation_id: str
    policy: Policy = Policy()

    def to_message(self) -> dict:
        return {
            "schema_version": "1.0",
            "message_id": str(uuid4()),
            "correlation_id": self.correlation_id,
            "command": {
                "name": self.command.name,
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
            "target": {
                "site_id": self.target.site_id,
                "device_id": self.target.device_id,
            },
            "policy": {
                "priority": self.policy.priority,
                "allow_override": self.policy.allow_override,
                "min_duration_minutes": self.policy.min_duration_minutes,
            },
            "created_at": _utc_now_iso(),
        }

    @classmethod
    def from_message(cls, message: dict) -> "PlannedAction":
        return cls(
            command=Command(
                name=message["command"]["name"],
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
            target=Target(
                site_id=message["target"]["site_id"],
                device_id=message["target"]["device_id"],
            ),
            correlation_id=message.get("correlation_id", str(uuid4())),
            policy=Policy(
                priority=message.get("policy", {}).get("priority", 5),
                allow_override=message.get("policy", {}).get("allow_override", True),
                min_duration_minutes=message.get("policy", {}).get(
                    "min_duration_minutes", 30
                ),
            ),
        )
