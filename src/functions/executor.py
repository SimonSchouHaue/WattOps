from __future__ import annotations

from src.utils.config import Settings
from src.services.growatt_api import GrowattClient
from src.models.models import PlannedAction


def apply_planned_action(
    action: PlannedAction, settings: Settings, growatt_api_key: str
) -> None:
    client = GrowattClient(
        api_base_url=settings.growatt_api_base_url,
        api_key=growatt_api_key,
        dry_run=settings.growatt_dry_run,
    )

    if action.command.name == "set_export_limit":
        client.set_export_limit(
            site_id=action.target.site_id,
            device_id=action.target.device_id,
            percent=action.command.value,
        )
        return

    if action.command.name == "set_operating_mode":
        client.set_operating_mode(
            site_id=action.target.site_id,
            device_id=action.target.device_id,
            mode=str(action.command.value),
        )
        return

    raise ValueError(f"Unsupported command: {action.command.name}")
