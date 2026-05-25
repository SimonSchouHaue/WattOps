from __future__ import annotations

import logging

import requests

logger = logging.getLogger("wattops.growatt")


class GrowattClient:
    def __init__(self, api_base_url: str, api_key: str, dry_run: bool = True) -> None:
        self._api_base_url = api_base_url.rstrip("/")
        self._api_key = api_key
        self._dry_run = dry_run

    def set_export_limit(
        self, site_id: str, device_id: str, percent: int | float
    ) -> None:
        self._post_command(
            command_name="set_export_limit",
            payload={
                "site_id": site_id,
                "device_id": device_id,
                "percent": percent,
            },
        )

    def set_operating_mode(self, site_id: str, device_id: str, mode: str) -> None:
        self._post_command(
            command_name="set_operating_mode",
            payload={
                "site_id": site_id,
                "device_id": device_id,
                "mode": mode,
            },
        )

    def _post_command(self, command_name: str, payload: dict) -> None:
        if self._dry_run:
            logger.info("DRY RUN Growatt command '%s': %s", command_name, payload)
            return

        url = f"{self._api_base_url}/commands/{command_name}"
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=20,
        )
        response.raise_for_status()
